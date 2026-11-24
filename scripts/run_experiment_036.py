#!/usr/bin/env python3
"""Experiment 036 — Out-of-sample SLP characterization (CEEW, grouped meter splits)."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import textwrap
import time
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_036"
EXP_LINK = ROOT / "experiments/036_slp_out_of_sample_characterization"
FIG = OUT / "figures"
TAB = OUT / "tables"
SPL = OUT / "split_assignments"
MET = OUT / "metrics"
DAILY = ROOT / "data/processed/daily_profiles.parquet"
CFG = ROOT / "configs/ceew_foundation.json"
TODAY = pd.Timestamp.now("UTC").date().isoformat()
SLOTS = 96
DT_H = 0.25
K = 2
N_INIT = 20
TRAIN_FRAC = 0.70
SPLIT_SEEDS = (1042, 1043, 1044, 1045, 1046)
DPI = 150

# Experiment 032 windows (15-min slot indices, bin start)
MORNING = list(range(24, 36))  # 06:00–09:00
AFTERNOON = list(range(36, 72))  # 09:00–18:00
EVENING = list(range(72, 84))  # 18:00–21:00


def write_md(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")


def atomic_json(path: Path, obj: object) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    tmp.replace(path)


def as_profile(x) -> np.ndarray:
    if isinstance(x, (list, np.ndarray)):
        return np.asarray(x, dtype=np.float64)
    return np.asarray(ast.literal_eval(x), dtype=np.float64)


def peak_normalize_matrix(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    peak = X.max(axis=1)
    valid = peak > 0
    Y = np.zeros_like(X)
    Y[valid] = X[valid] / peak[valid, None]
    return Y, valid


def slot_to_hour(slot: int) -> float:
    return (slot + 0.5) * DT_H


def circular_mean_hour(slots: np.ndarray) -> float:
    ang = 2 * np.pi * (slots.astype(float) + 0.5) / SLOTS
    return float(np.arctan2(np.sin(ang).mean(), np.cos(ang).mean()) / (2 * np.pi) * 24 % 24)


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    x, y = np.asarray(x), np.asarray(y)
    if len(x) == 0 or len(y) == 0:
        return float("nan")
    gt = int(np.sum(x[:, None] > y[None, :]))
    lt = int(np.sum(x[:, None] < y[None, :]))
    return float((gt - lt) / (len(x) * len(y)))


def bh_fdr(pvals: np.ndarray) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    q = np.empty(n)
    prev = 1.0
    for i in range(n - 1, -1, -1):
        rank = i + 1
        prev = min(prev, ranked[i] * n / rank)
        q[i] = prev
    out = np.empty(n)
    out[order] = q
    return out


def match_centroid_labels(c0: np.ndarray, c1: np.ndarray, d0: np.ndarray, d1: np.ndarray) -> int:
    """Return flip (0 or 1) if test labels should swap to align with ref (c0,c1)."""
    cost = np.array(
        [
            [np.linalg.norm(d0 - c0), np.linalg.norm(d0 - c1)],
            [np.linalg.norm(d1 - c0), np.linalg.norm(d1 - c1)],
        ]
    )
    row, col = linear_sum_assignment(cost)
    # if cluster0 maps to ref1, flip
    flip = 0
    for r, c in zip(row, col):
        if r == 0 and c == 1:
            flip = 1
    return flip


@dataclass
class SplitResult:
    seed: int
    train_meters: list[str]
    test_meters: list[str]
    centroids: np.ndarray
    test_df: pd.DataFrame
    train_days: int
    test_days: int


def load_days() -> pd.DataFrame:
    dp = pd.read_parquet(DAILY)
    dp["date"] = pd.to_datetime(dp["date"])
    prof = dp.profile_kw.map(as_profile)
    dp["n_slots"] = prof.map(len)
    dp = dp[dp.n_slots == SLOTS].copy()
    dp["peak_to_avg"] = np.where(dp.mean_load_kw > 0, dp.peak_load_kw / dp.mean_load_kw, np.nan)
    e_chk = prof.map(lambda a: float(np.sum(a) * DT_H))
    dp["energy_residual"] = np.abs(e_chk - dp.daily_energy_kwh)
    dp = dp[dp.energy_residual < 0.5].reset_index(drop=True)
    return dp


def meter_split(meters: list[str], seed: int) -> tuple[list[str], list[str]]:
    rng = np.random.default_rng(seed)
    m = np.array(sorted(meters))
    rng.shuffle(m)
    n_train = int(np.floor(TRAIN_FRAC * len(m)))
    return m[:n_train].tolist(), m[n_train:].tolist()


def fit_split(dp: pd.DataFrame, seed: int) -> SplitResult:
    meters = dp.meter_id.unique().tolist()
    train_m, test_m = meter_split(meters, seed)
    assert not set(train_m) & set(test_m)

    tr = dp[dp.meter_id.isin(train_m)].copy()
    te = dp[dp.meter_id.isin(test_m)].copy()
    X_tr = np.vstack(tr.profile_kw.map(as_profile).to_numpy())
    X_te = np.vstack(te.profile_kw.map(as_profile).to_numpy())
    Y_tr, vtr = peak_normalize_matrix(X_tr)
    Y_te, vte = peak_normalize_matrix(X_te)
    tr, te = tr.loc[vtr].reset_index(drop=True), te.loc[vte].reset_index(drop=True)
    Y_tr = Y_tr[vtr]
    Y_te = Y_te[vte]

    km = KMeans(n_clusters=K, random_state=seed, n_init=N_INIT)
    km.fit(Y_tr)
    centroids = km.cluster_centers_
    d_tr = np.linalg.norm(Y_tr[:, None, :] - centroids[None, :, :], axis=2)
    d_te = np.linalg.norm(Y_te[:, None, :] - centroids[None, :, :], axis=2)
    lab_tr = d_tr.argmin(axis=1)
    lab_te = d_te.argmin(axis=1)

    def enrich(df: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
        df = df.copy()
        df["slp_group"] = labels.astype(int)
        profs = df.profile_kw.map(as_profile)
        rows = []
        for (_, row), p in zip(df.iterrows(), profs):
            tot = float(p.sum() * DT_H)
            e_m = float(p[MORNING].sum() * DT_H)
            e_a = float(p[AFTERNOON].sum() * DT_H)
            e_e = float(p[EVENING].sum() * DT_H)
            rows.append(
                {
                    "intra_day_std_kw": float(p.std()),
                    "intra_day_cv": float(p.std() / p.mean()) if p.mean() > 0 else np.nan,
                    "morning_energy_kwh": e_m,
                    "afternoon_energy_kwh": e_a,
                    "evening_energy_kwh": e_e,
                    "morning_frac": e_m / max(tot, 1e-9),
                    "afternoon_frac": e_a / max(tot, 1e-9),
                    "evening_frac": e_e / max(tot, 1e-9),
                }
            )
        extra = pd.DataFrame(rows)
        return pd.concat([df.reset_index(drop=True), extra], axis=1)

    te = enrich(te, lab_te)
    return SplitResult(seed, train_m, test_m, centroids, te, len(tr), len(te))


CHAR_COLS = [
    "daily_energy_kwh",
    "mean_load_kw",
    "load_factor",
    "peak_to_avg",
    "peak_slot",
    "morning_energy_kwh",
    "afternoon_energy_kwh",
    "evening_energy_kwh",
    "morning_frac",
    "afternoon_frac",
    "evening_frac",
    "intra_day_std_kw",
    "intra_day_cv",
]


def stats_table(test_df: pd.DataFrame, split_id: int) -> pd.DataFrame:
    rows = []
    for col in CHAR_COLS:
        g0 = test_df.loc[test_df.slp_group == 0, col].dropna().to_numpy()
        g1 = test_df.loc[test_df.slp_group == 1, col].dropna().to_numpy()
        u, p = stats.mannwhitneyu(g0, g1, alternative="two-sided") if len(g0) and len(g1) else (np.nan, np.nan)
        cd = cliffs_delta(g0, g1)
        rows.append(
            {
                "split_seed": split_id,
                "metric": col,
                "n_group0": len(g0),
                "n_group1": len(g1),
                "mean_g0": float(np.mean(g0)) if len(g0) else np.nan,
                "mean_g1": float(np.mean(g1)) if len(g1) else np.nan,
                "median_g0": float(np.median(g0)) if len(g0) else np.nan,
                "median_g1": float(np.median(g1)) if len(g1) else np.nan,
                "std_g0": float(np.std(g0)) if len(g0) else np.nan,
                "std_g1": float(np.std(g1)) if len(g1) else np.nan,
                "q25_g0": float(np.percentile(g0, 25)) if len(g0) else np.nan,
                "q75_g0": float(np.percentile(g0, 75)) if len(g0) else np.nan,
                "q25_g1": float(np.percentile(g1, 25)) if len(g1) else np.nan,
                "q75_g1": float(np.percentile(g1, 75)) if len(g1) else np.nan,
                "mannwhitney_u": float(u),
                "p_value": float(p),
                "cliffs_delta": cd,
            }
        )
    out = pd.DataFrame(rows)
    out["q_bh"] = bh_fdr(out["p_value"].to_numpy())
    if "peak_slot" in out["metric"].values:
        i = out[out.metric == "peak_slot"].index[0]
        circ0 = circular_mean_hour(test_df.loc[test_df.slp_group == 0, "peak_slot"].to_numpy())
        circ1 = circular_mean_hour(test_df.loc[test_df.slp_group == 1, "peak_slot"].to_numpy())
        out.loc[i, "circular_mean_hour_g0"] = circ0
        out.loc[i, "circular_mean_hour_g1"] = circ1
    return out


def centroid_ari_pairs(results: list[SplitResult]) -> pd.DataFrame:
    rows = []
    for i, j in combinations(range(len(results)), 2):
        a, b = results[i], results[j]
        flip = match_centroid_labels(a.centroids[0], a.centroids[1], b.centroids[0], b.centroids[1])
        c = b.centroids.copy()
        if flip:
            c = c[[1, 0]]
        # ARI between train-assigned labels doesn't apply across splits; correlate shapes
        corr0 = float(np.corrcoef(a.centroids[0], c[0])[0, 1])
        corr1 = float(np.corrcoef(a.centroids[1], c[1])[0, 1])
        rows.append({"split_a": a.seed, "split_b": b.seed, "centroid_corr_g0": corr0, "centroid_corr_g1": corr1})
    return pd.DataFrame(rows)


def verify_context(dp: pd.DataFrame) -> dict:
    from sklearn.metrics import adjusted_rand_score
    from sklearn.cluster import KMeans as KM

    X = np.vstack(dp.profile_kw.map(as_profile).to_numpy())
    Y, v = peak_normalize_matrix(X)
    Y = Y[v]
    km = KM(n_clusters=2, random_state=42, n_init=N_INIT)
    labels = km.fit_predict(Y)
    sil_idx = np.random.default_rng(42).choice(len(Y), size=min(10000, len(Y)), replace=False)
    from sklearn.metrics import silhouette_score

    sil = float(silhouette_score(Y[sil_idx], labels[sil_idx]))
    seeds_ari = []
    for s in range(10):
        l2 = KM(n_clusters=2, random_state=s, n_init=N_INIT).fit_predict(Y)
        seeds_ari.append(adjusted_rand_score(labels, l2))
    g = pd.DataFrame({"label": labels, "e": dp.loc[v].daily_energy_kwh.to_numpy(), "lf": dp.loc[v].load_factor.to_numpy()})
    return {
        "n_meters": int(dp.meter_id.nunique()),
        "n_days": int(len(dp)),
        "silhouette_k2_peak": sil,
        "seed_ari_min": float(min(seeds_ari)),
        "seed_ari_mean": float(np.mean(seeds_ari)),
        "cluster0_n": int((labels == 0).sum()),
        "cluster1_n": int((labels == 1).sum()),
        "cluster0_mean_kwh": float(g.loc[g.label == 0, "e"].mean()),
        "cluster1_mean_kwh": float(g.loc[g.label == 1, "e"].mean()),
        "cluster0_lf": float(g.loc[g.label == 0, "lf"].mean()),
        "cluster1_lf": float(g.loc[g.label == 1, "lf"].mean()),
    }


def make_figures(results: list[SplitResult], all_stats: pd.DataFrame, stab: pd.DataFrame) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    ref = results[0]
    x = np.arange(SLOTS) * DT_H
    fig, ax = plt.subplots(figsize=(8, 3.5))
    for c in range(K):
        ax.plot(x, ref.centroids[c], label=f"SLP group {c} (train fit, seed {ref.seed})")
    ax.set(xlabel="Hour", ylabel="Peak-normalized load", title="Training-derived SLP centroids (split 0)")
    ax.legend()
    fig.savefig(FIG / "exp036_train_centroids.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    te = ref.test_df
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for c, ax in zip((0, 1), axes):
        sub = te[te.slp_group == c].head(200)
        mats = np.vstack(sub.profile_kw.map(as_profile).to_numpy())
        Y, _ = peak_normalize_matrix(mats)
        for row in Y[::5]:
            ax.plot(x, row, color="C0" if c == 0 else "C1", alpha=0.08)
        ax.plot(x, Y.mean(axis=0), color="k", lw=2, label="Mean")
        ax.set(title=f"Held-out profiles — group {c} (n={len(te[te.slp_group==c])})")
        ax.set(xlabel="Hour")
    axes[0].set(ylabel="Peak-normalized load")
    fig.savefig(FIG / "exp036_heldout_profiles.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3.5))
    for c in (0, 1):
        sub = te[te.slp_group == c]
        Y, _ = peak_normalize_matrix(np.vstack(sub.profile_kw.map(as_profile).to_numpy()))
        med = np.median(Y, axis=0)
        q25, q75 = np.percentile(Y, [25, 75], axis=0)
        ax.plot(x, med, label=f"Group {c} median")
        ax.fill_between(x, q25, q75, alpha=0.2)
    ax.set(xlabel="Hour", ylabel="Peak-normalized load", title="Held-out central tendency (split 0)")
    ax.legend()
    fig.savefig(FIG / "exp036_heldout_bands.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    for col, fname, xlabel in [
        ("daily_energy_kwh", "exp036_energy_by_group.png", "kWh/day"),
        ("load_factor", "exp036_load_factor.png", "Load factor"),
        ("peak_to_avg", "exp036_peak_to_avg.png", "Peak-to-average"),
    ]:
        fig, ax = plt.subplots(figsize=(5, 3.5))
        te.boxplot(column=col, by="slp_group")
        plt.title(f"{col} by held-out SLP group")
        plt.suptitle("")
        fig.savefig(FIG / fname, dpi=DPI, bbox_inches="tight")
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(5, 3))
    for c in (0, 1):
        ax.hist(te.loc[te.slp_group == c, "peak_slot"].map(slot_to_hour), bins=24, alpha=0.5, label=f"Group {c}")
    ax.set(xlabel="Peak hour", ylabel="Count", title="Held-out peak timing")
    ax.legend()
    fig.savefig(FIG / "exp036_peak_hour.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3.5))
    frac = te.groupby("slp_group")[["morning_frac", "afternoon_frac", "evening_frac"]].mean()
    frac.plot(kind="bar", ax=ax)
    ax.set(title="Mean period energy fractions by group", ylabel="Fraction of daily energy")
    ax.legend(["Morning", "Afternoon", "Evening"])
    plt.xticks(rotation=0)
    fig.savefig(FIG / "exp036_period_fracs.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(["g0–g1 centroid corr (mean)"], [stab[["centroid_corr_g0", "centroid_corr_g1"]].mean().mean()])
    for i, (_, r) in enumerate(stab.iterrows()):
        ax.scatter([0], [0.5 * (r.centroid_corr_g0 + r.centroid_corr_g1)], alpha=0.5)
    ax.set(ylim=(0, 1.05), title="Cross-split centroid shape stability", ylabel="Correlation")
    fig.savefig(FIG / "exp036_cross_split_stability.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    med_delta = all_stats.groupby("metric")["cliffs_delta"].median()
    fig, ax = plt.subplots(figsize=(8, 4))
    med_delta.sort_values().plot(kind="barh", ax=ax)
    ax.axvline(0, color="k", lw=0.5)
    ax.set(xlabel="Median Cliff's δ across 5 splits", title="Effect sizes (held-out groups)")
    fig.savefig(FIG / "exp036_cliffs_delta_summary.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def audit_splits(results: list[SplitResult]) -> dict:
    checks = []
    for r in results:
        ok_disjoint = len(set(r.train_meters) & set(r.test_meters)) == 0
        checks.append({"seed": r.seed, "disjoint_meters": ok_disjoint, "n_train_m": len(r.train_meters), "n_test_m": len(r.test_meters)})
    return {"split_checks": checks, "all_disjoint": all(c["disjoint_meters"] for c in checks)}


def sync_new_submit(summary: dict) -> None:
    ns = ROOT / "new_submit"
    pairs = [
        (OUT / "experiment_036_summary.json", "138_exp036_summary.json"),
        (OUT / "results.md", "139_exp036_results.md"),
        (FIG / "exp036_train_centroids.png", "140_exp036_slp_centroids.png"),
        (FIG / "exp036_heldout_bands.png", "141_exp036_heldout_profiles.png"),
        (OUT / "limitations.md", "142_exp036_limitations.md"),
    ]
    for src, name in pairs:
        if src.exists():
            shutil.copy2(src, ns / name)
    idx = ns / "00_NEW_SUBMIT_INDEX.md"
    block = """
## Experiment 036 (SLP out-of-sample)

| File | Purpose |
|------|---------|
| `138_exp036_summary.json` | Out-of-sample SLP validation summary |
| `139_exp036_results.md` | Results digest |
| `140_exp036_slp_centroids.png` | Train-derived centroids |
| `141_exp036_heldout_profiles.png` | Held-out profile bands |
| `142_exp036_limitations.md` | Limitations |
"""
    txt = idx.read_text(encoding="utf-8") if idx.exists() else ""
    if "Experiment 036" not in txt:
        idx.write_text(txt.rstrip() + "\n" + block.strip() + "\n", encoding="utf-8")


def update_docs() -> None:
    for path, marker, block in [
        (ROOT / "research_log.md", "Experiment 036", f"\n\n## Experiment 036 — SLP out-of-sample ({TODAY})\n\nGrouped meter holdout; frozen train centroids; held-out characterization.\n"),
        (ROOT / "README.md", "Experiment 036", f"\n\n## Experiment 036 ({TODAY})\n\nOut-of-sample validation of K=2 peak-normalized SLPs (`results/forecasting/experiment_036/`).\n"),
    ]:
        if path.exists() and marker not in path.read_text(encoding="utf-8"):
            path.write_text(path.read_text(encoding="utf-8").rstrip() + block, encoding="utf-8")
    fi = ROOT / "results/figures/FIGURE_INDEX.md"
    if fi.exists() and "exp036" not in fi.read_text(encoding="utf-8"):
        fi.write_text(fi.read_text().rstrip() + "\n\n## Experiment 036\n\n`exp036_*` in `results/forecasting/experiment_036/figures/`.\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-repro", action="store_true", help="Run twice and compare checksums")
    args = parser.parse_args()
    t0 = time.perf_counter()
    for p in (OUT, FIG, TAB, SPL, MET, EXP_LINK):
        p.mkdir(parents=True, exist_ok=True)

    dp = load_days()
    ctx = verify_context(dp)
    atomic_json(OUT / "verified_context.json", ctx)

    def run_once() -> tuple[list[SplitResult], pd.DataFrame, pd.DataFrame]:
        results = [fit_split(dp, s) for s in SPLIT_SEEDS]
        for r in results:
            path = SPL / f"split_seed_{r.seed}.json"
            atomic_json(path, {"train_meters": r.train_meters, "test_meters": r.test_meters})
            r.test_df.to_parquet(SPL / f"test_assignments_seed_{r.seed}.parquet", index=False)
            np.save(SPL / f"centroids_seed_{r.seed}.npy", r.centroids)
        stats_all = pd.concat([stats_table(r.test_df, r.seed) for r in results], ignore_index=True)
        stab = centroid_ari_pairs(results)
        return results, stats_all, stab

    results, stats_all, stab = run_once()
    if args.verify_repro:
        results2, stats2, stab2 = run_once()
        h1 = hashlib.sha256(stats_all.to_csv().encode()).hexdigest()
        h2 = hashlib.sha256(stats2.to_csv().encode()).hexdigest()
        atomic_json(MET / "reproducibility_check.json", {"stats_match": h1 == h2, "hash1": h1, "hash2": h2})

    stats_all.to_csv(TAB / "heldout_group_statistics.csv", index=False)
    stab.to_csv(TAB / "cross_split_centroid_stability.csv", index=False)
    counts = pd.DataFrame(
        [
            {
                "seed": r.seed,
                "n_train_meters": len(r.train_meters),
                "n_test_meters": len(r.test_meters),
                "n_train_days": r.train_days,
                "n_test_days": r.test_days,
                "test_g0": int((r.test_df.slp_group == 0).sum()),
                "test_g1": int((r.test_df.slp_group == 1).sum()),
            }
            for r in results
        ]
    )
    counts.to_csv(TAB / "split_counts.csv", index=False)

    aud = audit_splits(results)
    atomic_json(OUT / "audit_report.json", aud)
    make_figures(results, stats_all, stab)

    median_cd = stats_all.groupby("metric")["cliffs_delta"].median()
    n_sig = int((stats_all.groupby("metric")["q_bh"].median() < 0.05).sum())

    conclusion = (
        "supported"
        if n_sig >= 6 and float(stab[["centroid_corr_g0", "centroid_corr_g1"]].mean().mean()) > 0.85
        else "partially_supported"
    )

    write_md(
        OUT / "methodology.md",
        f"""
        - Data: `daily_profiles.parquet`, 96 slots, completeness filter + energy residual < 0.5 kWh.
        - Peak normalization: P_t / max(P_t) (same as foundation).
        - K=2 KMeans, n_init={N_INIT}, train-only fit per split.
        - Assignment: nearest frozen centroid (Euclidean).
        - Grouped split: {TRAIN_FRAC:.0%} meters train / holdout meters; seeds {SPLIT_SEEDS}.
        - Period slots: morning {MORNING[0]}-{MORNING[-1]}, afternoon {AFTERNOON[0]}-{AFTERNOON[-1]}, evening {EVENING[0]}-{EVENING[-1]}.
        """,
    )
    write_md(
        OUT / "limitations.md",
        """
        - Shape-based (peak-normalized) SLPs; magnitude differences analysed separately on kWh.
        - Groups are daily pattern regimes, not verified consumer categories.
        - Five random meter splits; not geographic stratification.
        """,
    )
    write_md(
        OUT / "results.md",
        counts.to_string(index=False)
        + "\n\n"
        + median_cd.to_string()
        + f"\n\nMetrics with median BH q<0.05: {n_sig}/{len(CHAR_COLS)}.\nConclusion: **{conclusion}** for research question.",
    )
    write_md(OUT / "README.md", "# Experiment 036\n\n`/.venv/bin/python scripts/run_experiment_036.py`")
    write_md(
        EXP_LINK / "README.md",
        "# Experiment 036 (alias)\n\nPrimary outputs: `results/forecasting/experiment_036/`.\n",
    )
    shutil.copy2(OUT / "README.md", EXP_LINK / "RUN.md")

    summary = {
        "experiment": "036",
        "date": TODAY,
        "verified_context": ctx,
        "split_counts": counts.to_dict(orient="records"),
        "median_cliffs_delta": median_cd.to_dict(),
        "cross_split_centroid_corr_mean": float(stab[["centroid_corr_g0", "centroid_corr_g1"]].mean().mean()),
        "n_metrics_bh_sig_median_split": n_sig,
        "conclusion": conclusion,
        "audit": aud,
        "elapsed_sec": time.perf_counter() - t0,
    }
    atomic_json(OUT / "experiment_036_summary.json", summary)
    atomic_json(OUT / "experiment_config.json", {"k": K, "n_init": N_INIT, "train_frac": TRAIN_FRAC, "seeds": list(SPLIT_SEEDS)})

    sync_new_submit(summary)
    update_docs()
    write_md(OUT / "audit_report.md", json.dumps(aud, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
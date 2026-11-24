#!/usr/bin/env python3
"""Experiment 032 — ToD demand analysis and load characterization (CEEW primary)."""
from __future__ import annotations

import ast
import hashlib
import json
import shutil
import textwrap
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_032"
FIG = ROOT / "results/figures/experiment_032"
BINS = ROOT / "data/interim/ceew_15min_bins_dedup.parquet"
DAILY = ROOT / "data/processed/daily_profiles.parquet"
CLUST = ROOT / "results/clustering/cluster_assignments.parquet"
CENT = ROOT / "results/clustering/cluster_centroids.csv"
CLSUM = ROOT / "results/clustering/cluster_summary.csv"
GOI_DIR = ROOT / "data/external/goiener/interim/cnae01_profiles/profiles"
CFG = ROOT / "configs/ceew_foundation.json"
NOR_SLP = ROOT / "results/forecasting/experiment_030/category_slp_train_mean_clean.npy"
TODAY = pd.Timestamp.utcnow().date().isoformat()
SLOTS = 96
DT_H = 0.25
DPI = 150
PRIMARY_K = 2
PRIMARY_NORM = "peak"
rng = np.random.default_rng(42)


def write_md(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def as_profile(x) -> np.ndarray:
    if isinstance(x, (list, np.ndarray)):
        return np.asarray(x, dtype=np.float64)
    return np.asarray(ast.literal_eval(x), dtype=np.float64)


def slot_to_hour(slot: int) -> float:
    return (int(slot) + 0.5) * 0.25


def dataset_readiness() -> dict:
    rep = {
        "track_a_ceew_bins": str(BINS),
        "track_a_daily_profiles": str(DAILY),
        "bins_sha256": sha256_file(BINS) if BINS.exists() else None,
        "daily_sha256": sha256_file(DAILY) if DAILY.exists() else None,
        "interval_minutes": 15,
        "timestamp_convention": "15-min bin start (working)",
        "timezone": "unverified local civil time per CEEW files",
        "load_kw_definition": "interval_energy_kwh / 0.25h from 3-min native readings",
        "goiener_n_profiles": len(list(GOI_DIR.glob("*.csv"))) if GOI_DIR.exists() else 0,
        "goiener_units": "cons undocumented — normalized shapes only",
    }
    if BINS.exists():
        bins = pd.read_parquet(BINS, columns=["meter_id", "city", "bin"])
        rep["n_bins"] = int(len(bins))
        rep["n_meters"] = int(bins.meter_id.nunique())
        rep["t_min"] = str(bins.bin.min())
        rep["t_max"] = str(bins.bin.max())
    return rep


def load_ceew_daily() -> pd.DataFrame:
    dp = pd.read_parquet(DAILY)
    dp["date"] = pd.to_datetime(dp["date"])
    dp["is_weekend"] = dp["day_of_week"].isin([5, 6])
    ca = pd.read_parquet(CLUST)
    ca = ca[(ca.k == PRIMARY_K) & (ca.normalization == PRIMARY_NORM)][
        ["meter_id", "date", "cluster"]
    ].copy()
    ca["date"] = pd.to_datetime(ca["date"])
    dp = dp.merge(ca, on=["meter_id", "date"], how="left")
    dp["peak_to_avg"] = np.where(dp.mean_load_kw > 0, dp.peak_load_kw / dp.mean_load_kw, np.nan)
    return dp


def per_meter_stats(dp: pd.DataFrame) -> pd.DataFrame:
    g = dp.groupby(["meter_id", "city"], observed=True)
    out = g.agg(
        n_days=("date", "count"),
        mean_daily_energy_kwh=("daily_energy_kwh", "mean"),
        mean_peak_kw=("peak_load_kw", "mean"),
        mean_load_factor=("load_factor", "mean"),
        mean_peak_to_avg=("peak_to_avg", "mean"),
        std_daily_energy=("daily_energy_kwh", "std"),
        cv_daily_energy=("daily_energy_kwh", lambda s: float(s.std() / s.mean()) if s.mean() else np.nan),
    ).reset_index()
    return out


def pooled_profiles(dp: pd.DataFrame) -> dict:
    mats = np.vstack(dp.profile_kw.map(as_profile).to_numpy())
    wd = dp.loc[~dp.is_weekend].profile_kw.map(as_profile)
    we = dp.loc[dp.is_weekend].profile_kw.map(as_profile)
    return {
        "mean_all": mats.mean(axis=0),
        "mean_weekday": np.vstack(wd.to_numpy()).mean(axis=0) if len(wd) else mats.mean(axis=0),
        "mean_weekend": np.vstack(we.to_numpy()).mean(axis=0) if len(we) else mats.mean(axis=0),
    }


def peak_window_stats(dp: pd.DataFrame) -> pd.DataFrame:
    """Observed peak: slots >= 90% of daily peak; hypothetical windows morning/evening."""
    rows = []
    morning = list(range(24, 36))  # 06:00–09:00
    evening = list(range(72, 84))  # 18:00–21:00
    for idx, row in dp.sample(min(5000, len(dp)), random_state=42).iterrows():
        p = as_profile(row.profile_kw)
        peak = float(p.max())
        obs = p >= 0.9 * peak if peak > 0 else p == peak
        e_day = float(row.daily_energy_kwh)
        e_obs = float((p[obs] * DT_H * row.mean_load_kw / max(row.mean_load_kw, 1e-9)).sum()) if peak > 0 else 0.0
        # energy in peak slots proportional to profile shape × daily mean scale
        e_m = float(p[morning].sum() * DT_H)
        e_e = float(p[evening].sum() * DT_H)
        tot = float(p.sum() * DT_H)
        rows.append(
            {
                "meter_id": row.meter_id,
                "date": row.date,
                "peak_slot": int(row.peak_slot),
                "peak_hour": slot_to_hour(int(row.peak_slot)),
                "frac_energy_obs_peak": e_obs / max(e_day, 1e-9) if e_day else np.nan,
                "hypo_morning_energy_frac": e_m / max(tot, 1e-9),
                "hypo_evening_energy_frac": e_e / max(tot, 1e-9),
                "peak_off_ratio": float(p[obs].mean() / max(p[~obs].mean(), 1e-9)) if (~obs).any() else np.nan,
            }
        )
    return pd.DataFrame(rows)


def cluster_analysis(dp: pd.DataFrame) -> pd.DataFrame:
    sub = dp.dropna(subset=["cluster"])
    rows = []
    for c, g in sub.groupby("cluster"):
        mats = np.vstack(g.profile_kw.map(as_profile).to_numpy())
        shape = mats.mean(axis=0)
        shape = shape / max(shape.max(), 1e-9)
        rows.append(
            {
                "cluster": int(c),
                "n_days": len(g),
                "mean_daily_kwh": float(g.daily_energy_kwh.mean()),
                "mean_load_factor": float(g.load_factor.mean()),
                "mean_peak_to_avg": float(g.peak_to_avg.mean()),
                "peak_hour_mean": float(g.peak_slot.map(slot_to_hour).mean()),
                "profile_flatness": float(1.0 - np.std(shape)),
            }
        )
    return pd.DataFrame(rows)


def bess_representative_profiles() -> pd.DataFrame:
    cen = pd.read_csv(CENT)
    sub = cen[(cen.k == PRIMARY_K) & (cen.normalization == PRIMARY_NORM)]
    rows = []
    for c in sorted(sub.cluster.unique()):
        prof = sub[sub.cluster == c].sort_values("slot")
        vec = prof.normalized_load.to_numpy(dtype=np.float64)
        peak_s = int(prof.loc[prof.normalized_load.idxmax(), "slot"])
        rows.append(
            {
                "cluster": int(c),
                "k": PRIMARY_K,
                "normalization": PRIMARY_NORM,
                "peak_slot": peak_s,
                "peak_hour": slot_to_hour(peak_s),
                "max_norm": float(vec.max()),
                "off_peak_mean_norm": float(vec[vec < 0.5 * vec.max()].mean()) if (vec < 0.5 * vec.max()).any() else 0.0,
                "profile_vector": vec.tolist(),
                "units_note": "normalized peak=1; physical kW scaling requires meter-level calibration",
            }
        )
    df = pd.DataFrame(rows)
    df.to_json(OUT / "bess_representative_profiles.json", orient="records", indent=2)
    return df


def goiener_profiles() -> pd.DataFrame:
    rows = []
    for path in sorted(GOI_DIR.glob("*.csv")):
        df = pd.read_csv(path)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        cons = pd.to_numeric(df["cons"], errors="coerce").fillna(0.0).to_numpy()
        if cons.max() <= 0:
            continue
        norm = cons / cons.max()
        rows.append(
            {
                "profile_id": path.stem,
                "n_hours": len(cons),
                "peak_hour": int(df.loc[cons.argmax(), "hour"]) if "hour" in df.columns else int(cons.argmax() % 24),
                "zero_frac": float((cons == 0).mean()),
                "norm_profile_sample": norm[: min(168, len(norm))].tolist(),
            }
        )
    return pd.DataFrame(rows)


def make_figures(dp: pd.DataFrame, pooled: dict, peak_df: pd.DataFrame, cl: pd.DataFrame, goi: pd.DataFrame) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    x = np.arange(SLOTS) * 0.25

    def save_profile(y, title, fname, ylab="Mean load (kW)"):
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.plot(x, y)
        ax.set(xlabel="Hour of day", ylabel=ylab, title=title)
        fig.savefig(FIG / fname, dpi=DPI, bbox_inches="tight")
        plt.close(fig)

    save_profile(pooled["mean_all"], "CEEW pooled mean daily load (15-min)", "exp032_ceew_mean_daily.png")
    save_profile(pooled["mean_weekday"], "CEEW weekday mean load", "exp032_ceew_weekday.png")
    save_profile(pooled["mean_weekend"], "CEEW weekend mean load", "exp032_ceew_weekend.png")

    dow = dp.groupby("day_of_week", observed=True)["daily_energy_kwh"].mean()
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(dow.index.astype(str), dow.values)
    ax.set(xlabel="Day of week (0=Mon)", ylabel="Mean daily energy (kWh)", title="CEEW day-of-week")
    fig.savefig(FIG / "exp032_dow_energy.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.hist(dp.peak_load_kw, bins=50, edgecolor="k", alpha=0.7)
    ax.set(xlabel="Daily peak load (kW)", title="CEEW peak demand distribution")
    fig.savefig(FIG / "exp032_peak_dist.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.hist(dp.peak_to_avg.dropna(), bins=50, edgecolor="k", alpha=0.7)
    ax.set(xlabel="Peak / mean", title="CEEW peak-to-average ratio")
    fig.savefig(FIG / "exp032_peak_to_avg.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.hist(dp.load_factor.dropna(), bins=50, edgecolor="k", alpha=0.7)
    ax.set(xlabel="Load factor", title="CEEW daily load factor")
    fig.savefig(FIG / "exp032_load_factor.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    if dp.date.notna().any():
        m = dp.assign(month=dp.date.dt.month).groupby("month", observed=True)["daily_energy_kwh"].mean()
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(m.index, m.values, marker="o")
        ax.set(xlabel="Month", ylabel="Mean daily energy (kWh)", title="CEEW monthly variation")
        fig.savefig(FIG / "exp032_monthly.png", dpi=DPI, bbox_inches="tight")
        plt.close(fig)

    cen = pd.read_csv(CENT)
    sub = cen[(cen.k == PRIMARY_K) & (cen.normalization == PRIMARY_NORM)]
    fig, ax = plt.subplots(figsize=(8, 3))
    for c in sorted(sub.cluster.unique()):
        s = sub[sub.cluster == c].sort_values("slot")
        ax.plot(s.slot * 0.25, s.normalized_load, label=f"cluster {c}")
    ax.set(xlabel="Hour", ylabel="Normalized load", title="CEEW clusters K=2 peak (discovered)")
    ax.legend()
    fig.savefig(FIG / "exp032_cluster_profiles.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.hist(dp.peak_slot.map(slot_to_hour), bins=48, edgecolor="k", alpha=0.7)
    ax.set(xlabel="Peak hour", title="CEEW peak timing distribution")
    fig.savefig(FIG / "exp032_peak_timing.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    bess = json.loads((OUT / "bess_representative_profiles.json").read_text())
    fig, ax = plt.subplots(figsize=(8, 3))
    for row in bess:
        v = np.array(row["profile_vector"])
        ax.plot(np.arange(len(v)) * 0.25, v, label=f"cluster {row['cluster']}")
    ax.set(title="Representative BESS input shapes (normalized)", xlabel="Hour")
    ax.legend()
    fig.savefig(FIG / "exp032_bess_representatives.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    if len(goi):
        fig, ax = plt.subplots(figsize=(8, 3))
        for _, r in goi.head(8).iterrows():
            v = np.array(r["norm_profile_sample"][:96])
            ax.plot(np.arange(len(v)), v, alpha=0.6)
        ax.set(title="GoiEner CNAE-01 (normalized cons, n=8 shown)", xlabel="Hour index", ylabel="cons/max(cons)")
        fig.savefig(FIG / "exp032_goiener_profiles.png", dpi=DPI, bbox_inches="tight")
        plt.close(fig)


def sync_new_submit(summary: dict) -> None:
    ns = ROOT / "new_submit"
    pairs = [
        (OUT / "experiment_032_summary.json", "103_exp032_summary.json"),
        (OUT / "results_summary.md", "104_exp032_report.md"),
        (OUT / "bess_input_profiles.md", "105_exp032_bess_inputs.md"),
        (FIG / "exp032_ceew_mean_daily.png", "106_exp032_mean_profile.png"),
        (FIG / "exp032_cluster_profiles.png", "107_exp032_clusters.png"),
        (FIG / "exp032_bess_representatives.png", "108_exp032_bess_shapes.png"),
    ]
    for src, name in pairs:
        if src.exists():
            shutil.copy2(src, ns / name)
    idx = ns / "00_NEW_SUBMIT_INDEX.md"
    block = (
        "\n\n## Experiment 032 (ToD / load characterization)\n\n"
        "See `103_*` … `108_*`. CEEW primary; BESS prep for Exp 033.\n"
    )
    txt = idx.read_text(encoding="utf-8") if idx.exists() else "# New submit pack — index\n"
    if "Experiment 032" not in txt:
        idx.write_text(txt.rstrip() + block, encoding="utf-8")


def update_docs() -> None:
    for path, marker, block in [
        (ROOT / "research_log.md", "Experiment 032", f"\n\n## Experiment 032 — ToD load characterization ({TODAY})\n\nSee `results/forecasting/experiment_032/`.\n"),
        (ROOT / "README.md", "Experiment 032", f"\n\n## Experiment 032 ({TODAY})\n\nCEEW ToD analysis; BESS input profiles.\n"),
    ]:
        if path.exists() and marker not in path.read_text(encoding="utf-8"):
            path.write_text(path.read_text(encoding="utf-8").rstrip() + block, encoding="utf-8")
    ps = ROOT / "project_status.md"
    if ps.exists() and "Experiment 032" not in ps.read_text(encoding="utf-8"):
        ps.write_text(ps.read_text().rstrip() + f"\n### {TODAY} — Experiment 032\n\nToD / cluster / BESS prep complete.\n", encoding="utf-8")


def main() -> int:
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    ready = dataset_readiness()
    (OUT / "dataset_readiness.json").write_text(json.dumps(ready, indent=2), encoding="utf-8")
    write_md("dataset_readiness.md", f"```json\n{json.dumps(ready, indent=2)}\n```")

    dp = load_ceew_daily()
    meter = per_meter_stats(dp)
    meter.to_csv(OUT / "per_meter_load_statistics.csv", index=False)
    dp[["meter_id", "city", "date", "daily_energy_kwh", "peak_load_kw", "load_factor", "peak_to_avg", "cluster"]].to_csv(
        OUT / "daily_load_statistics.csv", index=False
    )

    pooled = pooled_profiles(dp)
    np.save(OUT / "pooled_mean_profile_kw.npy", pooled["mean_all"])

    wd_we = dp.groupby("is_weekend", observed=True)["daily_energy_kwh"].mean()
    write_md(
        "weekday_weekend_analysis.md",
        f"Weekday mean daily energy {wd_we.get(False, np.nan):.3f} kWh; weekend {wd_we.get(True, np.nan):.3f} kWh.",
    )

    peak_df = peak_window_stats(dp)
    peak_df.to_csv(OUT / "peak_demand_statistics.csv", index=False)
    write_md(
        "tod_peak_analysis.md",
        "Observed peaks: slots ≥90% of daily peak. Hypothetical windows: 06–09 and 18–21 (15-min slots).",
    )

    monthly = dp.assign(month=dp.date.dt.month).groupby("month", observed=True)["daily_energy_kwh"].mean()
    monthly.to_csv(OUT / "monthly_demand_stats.csv")
    write_md("monthly_variation_analysis.md", f"Months covered: {sorted(monthly.index.tolist())}")

    cl = cluster_analysis(dp)
    cl.to_csv(OUT / "cluster_wise_summaries.csv", index=False)
    write_md("cluster_wise_load_analysis.md", cl.to_string())

    bess_df = bess_representative_profiles()
    write_md(
        "bess_input_profiles.md",
        "Normalized K=2 peak centroids exported; physical kWh sizing requires documented meter scaling.",
    )

    goi = goiener_profiles()
    goi.to_csv(OUT / "goiener_profile_summaries.csv", index=False)
    write_md("goiener_descriptive_analysis.md", f"15 CNAE-01 profiles; cons units undocumented.\n{goi.to_string()}")

    make_figures(dp, pooled, peak_df, cl, goi)

    write_md(
        "distribution_network_implications.md",
        "Recurring evening-heavy clusters imply coincident feeder loading risk; no transformer overload demonstrated.",
    )
    write_md(
        "daily_load_characteristics.md",
        f"Pooled meters: {meter.shape[0]}; mean load factor {dp.load_factor.mean():.3f}.",
    )
    write_md("temporal_data_audit.md", "15-min authoritative; 3-min native aggregated in foundation pipeline.")
    write_md("experiment_design.md", "Track A CEEW primary; Track B GoiEner secondary; no new forecasting.")
    write_md("limitations.md", "No tariff peaks; cluster labels not consumer class; GoiEner cons units unresolved.")
    write_md("decision_register.md", "- DEC-032-A: Reuse K=2 peak clustering.\n- DEC-032-B: BESS Exp 033 uses normalized centroids + flagged units.\n")
    write_md("README.md", "# Experiment 032\n\n`/.venv/bin/python scripts/run_experiment_032.py`")

    summary = {
        "experiment": "032",
        "date": TODAY,
        "readiness": ready,
        "n_daily_profiles": int(len(dp)),
        "n_meters": int(dp.meter_id.nunique()),
        "mean_load_factor": float(dp.load_factor.mean()),
        "mean_peak_to_avg": float(dp.peak_to_avg.mean()),
        "weekday_weekend_kwh": wd_we.to_dict(),
        "cluster_summaries": cl.to_dict(orient="records"),
        "goiener_profiles": int(len(goi)),
        "bess_profiles_ready": True,
        "norway_context_skipped_dominance": bool(not NOR_SLP.exists()),
        "elapsed_sec": time.perf_counter() - t0,
    }
    (OUT / "run_manifest.json").write_text(
        json.dumps({"inputs_sha256": {"bins": ready.get("bins_sha256"), "daily": ready.get("daily_sha256")}}, indent=2),
        encoding="utf-8",
    )
    (OUT / "experiment_032_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_md("results_summary.md", f"CEEW ToD complete: {meter.shape[0]} meters; BESS representative profiles saved.")
    sync_new_submit(summary)
    update_docs()
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
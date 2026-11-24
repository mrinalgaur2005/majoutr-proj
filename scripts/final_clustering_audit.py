#!/usr/bin/env python3
"""Final clustering audit: diagnostics only. No forecasting."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.ceew_loader import iter_ceew
from src.profiles.normalize import energy_normalize, peak_normalize, profiles_to_matrix

DPI = 300
plt.rcParams.update({"font.size": 11, "axes.titlesize": 12, "figure.dpi": DPI})


def save_fig(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    if path.suffix == ".png":
        fig.savefig(path.with_suffix(".pdf"))
        fig.savefig(path.with_suffix(".svg"))
    plt.close(fig)


def cramers_v(table: pd.DataFrame) -> float:
    observed = table.to_numpy(dtype=float)
    n = observed.sum()
    if n == 0:
        return float("nan")
    row = observed.sum(axis=1, keepdims=True)
    col = observed.sum(axis=0, keepdims=True)
    expected = row @ col / n
    chi2 = ((observed - expected) ** 2 / np.where(expected == 0, np.nan, expected)).sum()
    r, c = observed.shape
    return float(np.sqrt(chi2 / (n * (min(r, c) - 1))))


def diagnose_coverage(out: Path) -> pd.DataFrame:
    mq = pd.read_csv(ROOT / "results/data_audit/meter_quality.csv")
    hi = set(mq.loc[mq.coverage_percent > 100, "meter_id"])
    parts = []
    for df in iter_ceew():
        g = df[df.meter_id.isin(hi)][["timestamp", "meter_id"]]
        if len(g):
            parts.append(g)
    raw = pd.concat(parts, ignore_index=True)
    rows = []
    for meter, g in raw.groupby("meter_id"):
        t = g.timestamp.dropna()
        expected = int((t.max() - t.min()).total_seconds() // 180) + 1
        slots = t.dt.floor("3min")
        multi = int((slots.value_counts() > 1).sum())
        rows.append(
            {
                "meter_id": meter,
                "rows": int(len(t)),
                "unique_timestamps": int(t.nunique()),
                "expected_3min_grid": expected,
                "row_coverage_percent": round(100 * len(t) / expected, 4),
                "unique_coverage_percent": round(100 * t.nunique() / expected, 4),
                "exact_duplicate_timestamps": int(len(t) - t.nunique()),
                "three_min_slots_with_two_rows": multi,
                "within_chunk_duplicate_count_in_meter_quality": int(
                    mq.loc[mq.meter_id == meter, "duplicate_timestamps"].iloc[0]
                ),
            }
        )
    diag = pd.DataFrame(rows)
    diag.to_csv(out / "coverage_over_100_diagnosis.csv", index=False)
    return diag


def meter_level(pdf: pd.DataFrame, X_peak: np.ndarray, X_energy: np.ndarray, out: Path) -> pd.DataFrame:
    pdf = pdf.copy()
    pdf["peak"] = list(X_peak)
    pdf["energy"] = list(X_energy)
    counts = pdf.groupby("meter_id").size()
    eligible = counts[counts >= 14].index
    rows = []
    for norm in ["peak", "energy"]:
        med = (
            pdf[pdf.meter_id.isin(eligible)]
            .groupby(["meter_id", "city"])[norm]
            .apply(lambda s: np.median(np.vstack(s.to_numpy()), axis=0))
        )
        ids = med.index
        X = np.vstack(med.to_numpy())
        for k in range(2, 7):
            km = KMeans(n_clusters=k, random_state=0, n_init=20).fit(X)
            rows.append(
                {
                    "normalization": norm,
                    "k": k,
                    "n_meters": len(X),
                    "min_complete_days": 14,
                    "silhouette": float(silhouette_score(X, km.labels_)),
                    "cluster_sizes": json.dumps(np.bincount(km.labels_).tolist()),
                }
            )
            if k == 2:
                assign = pd.DataFrame(
                    {
                        "meter_id": ids.get_level_values(0),
                        "city": ids.get_level_values(1),
                        "cluster": km.labels_,
                        "normalization": norm,
                    }
                )
                assign.to_csv(out / f"meter_level_k2_{norm}.csv", index=False)
    tab = pd.DataFrame(rows)
    tab.to_csv(out / "meter_level_metrics.csv", index=False)
    return tab


def location_and_magnitude(assign: pd.DataFrame, pdf: pd.DataFrame, out: Path, fig: Path) -> dict:
    keep = pdf.reset_index().rename(columns={"index": "profile_index"})[
        ["profile_index", "daily_energy_kwh", "peak_load_kw", "load_factor", "peak_slot"]
    ]
    merged = assign.merge(keep, on="profile_index")
    loc_rows = []
    mag_rows = []
    for norm in ["peak", "energy"]:
        sub = merged[(merged.normalization == norm) & (merged.k == 2)]
        ct = pd.crosstab(sub.cluster, sub.city)
        loc_rows.append(
            {
                "normalization": norm,
                "k": 2,
                "cramers_v": cramers_v(ct),
                "bareilly_share_cluster0": float((sub[sub.cluster == 0].city == "Bareilly").mean()),
                "bareilly_share_cluster1": float((sub[sub.cluster == 1].city == "Bareilly").mean()),
                "overall_bareilly_share": float((sub.city == "Bareilly").mean()),
            }
        )
        for c, g in sub.groupby("cluster"):
            mag_rows.append(
                {
                    "normalization": norm,
                    "cluster": int(c),
                    "n": len(g),
                    "mean_energy_kwh": float(g.daily_energy_kwh.mean()),
                    "median_energy_kwh": float(g.daily_energy_kwh.median()),
                    "mean_peak_kw": float(g.peak_load_kw.mean()),
                    "mean_load_factor": float(g.load_factor.mean()),
                    "median_peak_hour": float(g.peak_slot.median() / 4),
                }
            )
        fig_ax, ax = plt.subplots(figsize=(7, 4))
        for c, g in sub.groupby("cluster"):
            ax.hist(g.daily_energy_kwh, bins=40, alpha=0.55, label=f"Cluster {c}", density=True)
        ax.set(xlabel="Daily energy (kWh)", ylabel="Density", title=f"Daily energy by cluster (K=2, {norm})")
        ax.legend()
        save_fig(fig_ax, fig / f"magnitude_energy_k2_{norm}.png")
    loc = pd.DataFrame(loc_rows)
    mag = pd.DataFrame(mag_rows)
    loc.to_csv(out / "location_cramers_v_k2.csv", index=False)
    mag.to_csv(out / "magnitude_vs_shape_k2.csv", index=False)
    return {"location": loc, "magnitude": mag}


def temporal_stability(pdf: pd.DataFrame, X_peak: np.ndarray, X_energy: np.ndarray, out: Path, fig: Path) -> pd.DataFrame:
    dates = pd.to_datetime(pdf.date)
    cutoff = dates.median()
    early = dates < cutoff
    late = ~early
    rows = []
    hours = np.arange(96) / 4
    for norm, X in [("peak", X_peak), ("energy", X_energy)]:
        km = KMeans(n_clusters=2, random_state=0, n_init=20).fit(X[early])
        pred_late = km.predict(X[late])
        km_late = KMeans(n_clusters=2, random_state=0, n_init=20).fit(X[late])
        rows.append(
            {
                "normalization": norm,
                "k": 2,
                "cutoff": str(cutoff.date()),
                "n_early": int(early.sum()),
                "n_late": int(late.sum()),
                "ari_early_model_vs_refit_late": float(adjusted_rand_score(pred_late, km_late.labels_)),
                "late_predicted_sizes": json.dumps(np.bincount(pred_late, minlength=2).tolist()),
            }
        )
        f, ax = plt.subplots(figsize=(8, 4))
        for c in range(2):
            ax.plot(hours, km.cluster_centers_[c], label=f"Early centroid {c}")
            ax.plot(hours, X[late][pred_late == c].mean(axis=0), ls="--", label=f"Late mean assigned {c}")
        ax.set(xlabel="Hour", ylabel=f"{norm}-normalized load", title=f"Temporal holdout K=2 ({norm})")
        ax.legend(fontsize=8)
        save_fig(f, fig / f"temporal_stability_k2_{norm}.png")
    tab = pd.DataFrame(rows)
    tab.to_csv(out / "temporal_stability_k2.csv", index=False)
    return tab


def main() -> None:
    out = ROOT / "results" / "clustering"
    diag_dir = ROOT / "results" / "data_audit"
    fig_c = ROOT / "results" / "figures" / "clustering"
    fig_d = ROOT / "results" / "figures" / "diagnostics"
    fig_n = ROOT / "results" / "figures" / "normalization"
    ppt = ROOT / "results" / "figures" / "ppt_ready"
    for d in (fig_c, fig_d, fig_n, ppt):
        d.mkdir(parents=True, exist_ok=True)

    print("coverage diagnosis")
    coverage = diagnose_coverage(diag_dir)

    pdf = pd.read_parquet(ROOT / "data/processed/daily_profiles.parquet")
    pdf = pdf[pdf.daily_energy_kwh > 0].reset_index(drop=True)
    X = profiles_to_matrix(pdf)
    X_peak, vp = peak_normalize(X)
    X_energy, ve = energy_normalize(X)
    both = vp & ve
    pdf = pdf.loc[both].reset_index(drop=True)
    X_peak, X_energy = X_peak[both], X_energy[both]

    print("meter-level sensitivity")
    meter = meter_level(pdf, X_peak, X_energy, out)

    assign = pd.read_parquet(ROOT / "results/clustering/cluster_assignments.parquet")
    print("location and magnitude")
    location_and_magnitude(assign, pdf, out, fig_d)

    print("temporal stability")
    temporal = temporal_stability(pdf, X_peak, X_energy, out, fig_d)

    hours = np.arange(96) / 4
    centroids = pd.read_csv(out / "cluster_centroids.csv")
    f, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=False)
    for ax, norm in zip(axes, ["peak", "energy"]):
        z = centroids[(centroids.normalization == norm) & (centroids.k == 2)]
        for c, g in z.groupby("cluster"):
            ax.plot(hours, g.sort_values("slot").normalized_load, label=f"Cluster {c}")
        ax.set(xlabel="Hour", title=f"K=2 centroids ({norm})")
        ax.legend()
    axes[0].set_ylabel("Normalized load")
    save_fig(f, fig_n / "peak_vs_energy_centroids_k2.png")

    summary = {
        "coverage_over_100_meters": coverage.to_dict(orient="records"),
        "meter_level_k2": meter[meter.k == 2].to_dict(orient="records"),
        "temporal": temporal.to_dict(orient="records"),
    }
    (out / "final_audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

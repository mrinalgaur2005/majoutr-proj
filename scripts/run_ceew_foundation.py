#!/usr/bin/env python3
"""Reproducible CEEW pipeline: audit → 15-min → profiles → clustering."""
from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.clustering.kmeans_profiles import describe_cluster_profiles, run_kmeans_grid
from src.data.audit_extended import run_extended_audit
from src.evaluation.location_comparison import (
    cluster_location_composition,
    location_profile_summary,
)
from src.preprocessing.aggregate_15min import aggregate_to_15min, save_15min_bins
from src.profiles.daily_profiles import (
    augment_meter_quality,
    build_daily_profiles,
    save_daily_profiles,
)
from src.profiles.normalize import energy_normalize, peak_normalize, profiles_to_matrix
from src.visualization.foundation_figures import (
    plot_clustering_results,
    plot_normalization_comparison,
    plot_profile_eda,
)

CONFIG_PATH = ROOT / "configs" / "ceew_foundation.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def main() -> None:
    cfg = load_config()
    run_ts = datetime.now(timezone.utc).isoformat()

    audit_dir = ROOT / "results" / "data_audit"
    fig_audit = ROOT / "results" / "figures" / "data_quality"
    fig_profiles = ROOT / "results" / "figures" / "profiles"
    fig_cluster = ROOT / "results" / "figures" / "clustering"
    profiles_dir = ROOT / "results" / "profiles"
    cluster_dir = ROOT / "results" / "clustering"
    interim = ROOT / "data" / "interim" / "ceew_15min_bins.parquet"
    processed = ROOT / "data" / "processed" / "daily_profiles.parquet"

    for d in [profiles_dir, cluster_dir]:
        d.mkdir(parents=True, exist_ok=True)

    skip_audit = os.environ.get("CEEW_SKIP_AUDIT") == "1"
    skip_agg = os.environ.get("CEEW_SKIP_AGG") == "1"

    if skip_audit and (audit_dir / "audit_summary.json").exists():
        print("Step 1: Skipping audit (CEEW_SKIP_AUDIT=1)...")
        audit_summary = json.loads(
            (audit_dir / "audit_summary.json").read_text(encoding="utf-8")
        )
    else:
        print("Step 1: Extended data audit...")
        audit_summary = run_extended_audit(
            audit_dir, fig_audit, extreme_kw=cfg["extreme_load_kw_threshold"]
        )

    if skip_agg and interim.exists():
        print("Step 2: Loading cached 15-minute bins...")
        bins = pd.read_parquet(interim)
        bin_stats = json.loads(
            (ROOT / "results" / "bin_stats.json").read_text(encoding="utf-8")
        )
    else:
        print("Step 2: 15-minute aggregation...")
        bins, bin_stats = aggregate_to_15min()
        save_15min_bins(bins, interim)
        (ROOT / "results" / "bin_stats.json").write_text(
            json.dumps(bin_stats, indent=2), encoding="utf-8"
        )

    print("Step 3: Daily profiles...")
    profile_df, day_meta, meter_extra = build_daily_profiles(
        bins, cfg["season_map"], slots=cfg["profile_slots"]
    )
    save_daily_profiles(profile_df, processed)
    day_meta.to_csv(profiles_dir / "daily_profile_summary.csv", index=False)
    meter_q = pd.read_csv(audit_dir / "meter_quality.csv")
    meter_q = augment_meter_quality(meter_q, meter_extra)
    meter_q.to_csv(audit_dir / "meter_quality.csv", index=False)

    all_zero_days = int((profile_df.daily_energy_kwh <= 0).sum())
    profile_df_nz = profile_df[profile_df.daily_energy_kwh > 0].reset_index(drop=True)

    print("Step 4: Profile EDA...")
    plot_profile_eda(profile_df_nz, fig_profiles, rng_seed=cfg["primary_random_seed"])
    loc_prof = location_profile_summary(profile_df_nz)
    loc_prof.to_csv(profiles_dir / "location_profile_summary.csv", index=False)

    X = profiles_to_matrix(profile_df_nz)
    X_peak, valid_peak = peak_normalize(X)
    X_energy, valid_energy = energy_normalize(X)
    both = valid_peak & valid_energy
    pdf = profile_df_nz.loc[both].reset_index(drop=True)
    X_peak = X_peak[both]
    X_energy = X_energy[both]

    peak_var = float(X_peak.var(axis=1).mean())
    energy_var = float(X_energy.var(axis=1).mean())
    plot_normalization_comparison(peak_var, energy_var, fig_profiles)

    norm_summary = {
        "profiles_after_complete_days": len(profile_df),
        "profiles_nonzero_energy": len(profile_df_nz),
        "profiles_for_clustering": len(pdf),
        "all_zero_complete_days_excluded": all_zero_days,
        "mean_row_variance_peak_norm": peak_var,
        "mean_row_variance_energy_norm": energy_var,
    }
    (profiles_dir / "normalization_summary.json").write_text(
        json.dumps(norm_summary, indent=2), encoding="utf-8"
    )

    print("Step 5: Clustering K=2..6...")
    all_metrics = []
    all_stability = []
    all_assignments = []
    all_centroids = []
    all_summaries = []
    all_loc = []

    for norm_name, Xn in [("peak", X_peak), ("energy", X_energy)]:
        res = run_kmeans_grid(
            Xn,
            pdf,
            k_values=cfg["k_values"],
            seeds=cfg["stability_seeds"],
            n_init=cfg["kmeans_n_init"],
            silhouette_subsample=cfg["silhouette_subsample_size"],
            primary_seed=cfg["primary_random_seed"],
            normalization=norm_name,
        )
        all_metrics.append(res["metrics"])
        all_stability.append(res["stability"])
        all_assignments.append(res["assignments"])
        all_centroids.append(res["centroids"])

        for k in cfg["k_values"]:
            a = res["assignments"][
                (res["assignments"].k == k)
                & (res["assignments"].normalization == norm_name)
            ]
            labels = a.sort_values("profile_index")["cluster"].to_numpy()
            summ = describe_cluster_profiles(pdf, labels, k)
            summ["k"] = k
            summ["normalization"] = norm_name
            all_summaries.append(summ)
            loc = cluster_location_composition(res["assignments"], k, norm_name)
            if not loc.empty:
                all_loc.append(loc)

        plot_clustering_results(
            res["metrics"],
            res["centroids"],
            res["stability"],
            pdf,
            res["assignments"],
            norm_name,
            fig_cluster,
        )

    metrics_df = pd.concat(all_metrics, ignore_index=True)
    stability_df = pd.concat(all_stability, ignore_index=True)
    assignments_df = pd.concat(all_assignments, ignore_index=True)
    centroids_df = pd.concat(all_centroids, ignore_index=True)
    summary_df = pd.concat(all_summaries, ignore_index=True)

    metrics_df.to_csv(cluster_dir / "cluster_metrics.csv", index=False)
    stability_df.to_csv(cluster_dir / "cluster_stability.csv", index=False)
    assignments_df.to_parquet(cluster_dir / "cluster_assignments.parquet", index=False)
    summary_df.to_csv(cluster_dir / "cluster_summary.csv", index=False)
    centroids_df.to_csv(cluster_dir / "cluster_centroids.csv", index=False)
    if all_loc:
        pd.concat(all_loc, ignore_index=True).to_csv(
            cluster_dir / "cluster_location_composition.csv", index=False
        )

    pipeline_summary = {
        "run_timestamp_utc": run_ts,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "config": cfg,
        "audit": audit_summary,
        "bin_stats": bin_stats,
        "profile_stats": {
            **norm_summary,
            "valid_100_meter_days": int(day_meta.valid_100.sum()),
            "valid_95_meter_days": int(day_meta.valid_95.sum()),
            "meter_days_total": int(len(day_meta)),
        },
    }
    (ROOT / "results" / "foundation_pipeline_summary.json").write_text(
        json.dumps(pipeline_summary, indent=2, default=str), encoding="utf-8"
    )

    print(json.dumps(pipeline_summary, indent=2, default=str))

    import subprocess

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "finalize_research_log.py")],
        check=True,
        cwd=str(ROOT),
    )


if __name__ == "__main__":
    main()

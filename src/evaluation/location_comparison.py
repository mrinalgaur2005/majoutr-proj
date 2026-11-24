"""Mathura vs Bareilly composition within clusters."""
from __future__ import annotations

import pandas as pd


def cluster_location_composition(
    assignments: pd.DataFrame,
    k: int,
    normalization: str,
) -> pd.DataFrame:
    sub = assignments[(assignments.k == k) & (assignments.normalization == normalization)]
    if sub.empty:
        return pd.DataFrame()
    ct = pd.crosstab(sub["cluster"], sub["city"], normalize="index") * 100
    ct = ct.reset_index().rename(columns={"cluster": "cluster_id"})
    ct["k"] = k
    ct["normalization"] = normalization
    return ct


def location_profile_summary(profile_df: pd.DataFrame) -> pd.DataFrame:
    return (
        profile_df.groupby("city")
        .agg(
            n_profiles=("meter_id", "count"),
            n_meters=("meter_id", "nunique"),
            mean_daily_energy_kwh=("daily_energy_kwh", "mean"),
            mean_peak_load_kw=("peak_load_kw", "mean"),
            median_peak_slot=("peak_slot", "median"),
        )
        .reset_index()
    )

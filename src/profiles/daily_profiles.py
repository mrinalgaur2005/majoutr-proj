"""Build 96-slot daily load profiles from 15-minute bins."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _season(month: int, season_map: dict) -> str:
    for name, months in season_map.items():
        if month in months:
            return name
    return "unknown"


def build_daily_profiles(
    bins: pd.DataFrame,
    season_map: dict,
    slots: int = 96,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return wide profiles DataFrame and per-meter-day summary."""
    b = bins.copy()
    b["date"] = b.bin.dt.date
    b["slot"] = b.bin.dt.hour * 4 + b.bin.dt.minute // 15

    wide = b.pivot(index=["meter_id", "city", "date"], columns="slot", values="load_kw")
    wide = wide.reindex(columns=range(slots))

    counts = wide.notna().sum(axis=1)
    meta = wide.reset_index()[["meter_id", "city", "date"]]
    meta["complete_slots"] = counts.values
    meta["valid_100"] = counts.values == slots
    meta["valid_95"] = counts.values >= int(0.95 * slots)

    valid = wide[counts == slots].copy()
    arr = valid.to_numpy(dtype=float)
    daily_energy_kwh = arr.sum(axis=1) * 0.25
    peak_load_kw = arr.max(axis=1)
    peak_slot = arr.argmax(axis=1)
    mean_load_kw = arr.mean(axis=1)
    load_factor = np.divide(
        mean_load_kw, peak_load_kw, out=np.zeros_like(mean_load_kw), where=peak_load_kw > 0
    )

    dates = pd.to_datetime(valid.index.get_level_values("date"))
    profile_df = pd.DataFrame(
        {
            "meter_id": valid.index.get_level_values("meter_id"),
            "city": valid.index.get_level_values("city"),
            "date": dates,
            "day_of_week": dates.dayofweek,
            "month": dates.month,
            "season": [_season(m, season_map) for m in dates.month],
            "completeness": 1.0,
            "daily_energy_kwh": daily_energy_kwh,
            "peak_load_kw": peak_load_kw,
            "peak_slot": peak_slot,
            "peak_time": [
                f"{(s // 4):02d}:{(s % 4) * 15:02d}" for s in peak_slot
            ],
            "mean_load_kw": mean_load_kw,
            "load_factor": load_factor,
        }
    )
    profile_df["profile_kw"] = list(arr)

    meta["date"] = pd.to_datetime(meta["date"])
    meta["year_month"] = meta["date"].dt.to_period("M")

    def _month_fully_complete(df: pd.DataFrame) -> int:
        dim = df["date"].iloc[0].days_in_month
        return int(df.valid_100.all() and df["date"].nunique() == dim)

    complete_months = (
        meta.groupby(["meter_id", "year_month"], group_keys=False)
        .apply(_month_fully_complete)
        .groupby(level=0)
        .sum()
    )
    complete_months.name = "complete_months"

    meter_quality_extra = meta.groupby("meter_id").agg(
        complete_days=("valid_100", "sum"),
        meter_days_total=("date", "count"),
        complete_days_95=("valid_95", "sum"),
    )
    meter_quality_extra = meter_quality_extra.join(complete_months, how="left")
    meter_quality_extra["complete_months"] = meter_quality_extra["complete_months"].fillna(0).astype(int)

    return profile_df, meta, meter_quality_extra


def augment_meter_quality(meter_quality: pd.DataFrame, extra: pd.DataFrame) -> pd.DataFrame:
    drop_cols = [
        c
        for c in ["complete_days", "complete_months", "meter_days_total", "complete_days_95"]
        if c in meter_quality.columns
    ]
    out = meter_quality.drop(columns=drop_cols, errors="ignore").merge(
        extra, on="meter_id", how="left"
    )
    out["complete_days"] = out["complete_days"].fillna(0).astype(int)
    out["complete_months"] = out["complete_months"].fillna(0).astype(int)
    return out


def save_daily_profiles(profile_df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    profile_df.to_parquet(path, index=False)

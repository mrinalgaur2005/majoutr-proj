"""Chunked 15-minute bin aggregation from 3-minute CEEW records."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.data.ceew_loader import iter_ceew


def aggregate_to_15min(chunksize: int = 250_000) -> tuple[pd.DataFrame, dict]:
    """Build 15-minute bins; load_kw set only for complete five-point bins."""
    parts = []
    malformed = 0
    off_boundary = 0
    partial_bin_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, "other": 0}

    for raw in iter_ceew(chunksize=chunksize):
        malformed += int(raw.timestamp.isna().sum())
        x = raw.dropna(subset=["timestamp", "interval_energy_kwh"]).copy()
        off_boundary += int(
            ((x.timestamp.dt.minute % 3 != 0) | (x.timestamp.dt.second != 0)).sum()
        )
        x["bin"] = x.timestamp.dt.floor("15min")
        parts.append(
            x.groupby(["meter_id", "city", "bin"], as_index=False).agg(
                energy_15min_kwh=("interval_energy_kwh", "sum"),
                raw_rows=("timestamp", "size"),
                unique_timestamps=("timestamp", "nunique"),
                min_timestamp=("timestamp", "min"),
                max_timestamp=("timestamp", "max"),
            )
        )

    bins = pd.concat(parts, ignore_index=True)
    bins = bins.groupby(["meter_id", "city", "bin"], as_index=False).agg(
        energy_15min_kwh=("energy_15min_kwh", "sum"),
        raw_rows=("raw_rows", "sum"),
        unique_timestamps=("unique_timestamps", "sum"),
        min_timestamp=("min_timestamp", "min"),
        max_timestamp=("max_timestamp", "max"),
    )

    for n in bins.raw_rows:
        key = int(n) if int(n) in partial_bin_counts else "other"
        partial_bin_counts[key] = partial_bin_counts.get(key, 0) + 1

    bins["complete"] = (
        (bins.raw_rows == 5)
        & (bins.unique_timestamps == 5)
        & ((bins.max_timestamp - bins.min_timestamp) == pd.Timedelta(minutes=12))
    )
    bins["load_kw"] = np.where(bins.complete, bins.energy_15min_kwh / 0.25, np.nan)

    stats = {
        "malformed_timestamps": malformed,
        "off_three_minute_boundaries": off_boundary,
        "partial_bin_row_counts": partial_bin_counts,
        "bins_total": len(bins),
        "bins_complete": int(bins.complete.sum()),
        "bins_incomplete": int((~bins.complete).sum()),
    }
    return bins, stats


def save_15min_bins(bins: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bins.to_parquet(path, index=False)

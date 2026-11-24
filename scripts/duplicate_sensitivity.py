#!/usr/bin/env python3
"""Compare current 15-minute bins with a deduplicated timeline for BR49–BR51.

Dedup rule, applied only in this sensitivity output: within each source file,
keep the first row for each (meter_id, timestamp). Measurements were verified
identical before this script is used for a decision.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.ceew_loader import FILES, RAW, RENAME
from src.profiles.normalize import energy_normalize, peak_normalize

METERS = ["BR49", "BR50", "BR51"]


def dedup_bins_for_meters() -> pd.DataFrame:
    parts = []
    for name in FILES["Bareilly"]:
        path = RAW / name
        with path.open("r", encoding="utf-8", errors="ignore") as source:
            sep = "\t" if "\t" in source.readline() else ","
        for chunk in pd.read_csv(path, sep=sep, chunksize=250_000):
            chunk = chunk.rename(columns=RENAME)
            chunk["meter_id"] = chunk["meter_id"].astype(str).str.strip('"')
            chunk = chunk[chunk.meter_id.isin(METERS)]
            if chunk.empty:
                continue
            chunk["timestamp"] = pd.to_datetime(chunk["timestamp"], errors="coerce")
            chunk["interval_energy_kwh"] = pd.to_numeric(chunk["interval_energy_kwh"], errors="coerce")
            chunk = chunk.dropna(subset=["timestamp", "interval_energy_kwh"])
            chunk["source_file"] = name
            parts.append(chunk[["timestamp", "meter_id", "interval_energy_kwh", "source_file"]])
    raw = pd.concat(parts, ignore_index=True)
    raw = raw.sort_values(["source_file", "meter_id", "timestamp"], kind="mergesort")
    raw = raw.drop_duplicates(["meter_id", "timestamp", "source_file"], keep="first")
    raw["bin"] = raw.timestamp.dt.floor("15min")
    bins = raw.groupby(["meter_id", "bin"], as_index=False).agg(
        energy_15min_kwh=("interval_energy_kwh", "sum"),
        raw_rows=("timestamp", "size"),
        unique_timestamps=("timestamp", "nunique"),
        min_timestamp=("timestamp", "min"),
        max_timestamp=("timestamp", "max"),
    )
    bins["city"] = "Bareilly"
    bins["complete"] = (
        (bins.raw_rows == 5)
        & (bins.unique_timestamps == 5)
        & ((bins.max_timestamp - bins.min_timestamp) == pd.Timedelta(minutes=12))
    )
    bins["load_kw"] = np.where(bins.complete, bins.energy_15min_kwh / 0.25, np.nan)
    return bins


def daily_from_bins(bins: pd.DataFrame) -> pd.DataFrame:
    b = bins[bins.complete].copy()
    b["date"] = b.bin.dt.floor("D")
    b["slot"] = b.bin.dt.hour * 4 + b.bin.dt.minute // 15
    wide = b.pivot_table(index=["meter_id", "date"], columns="slot", values="load_kw", aggfunc="first")
    wide = wide.reindex(columns=range(96))
    complete = wide.notna().all(axis=1)
    wide = wide.loc[complete]
    energy = wide.to_numpy().sum(axis=1) * 0.25
    peak = wide.to_numpy().max(axis=1)
    out = wide.reset_index()
    out["daily_energy_kwh"] = energy
    out["peak_load_kw"] = peak
    return out


def main() -> None:
    out = ROOT / "results" / "data_audit"
    current = pd.read_parquet(ROOT / "data/interim/ceew_15min_bins.parquet")
    current = current[current.meter_id.isin(METERS)].copy()
    dedup = dedup_bins_for_meters()
    both = current.merge(
        dedup,
        on=["meter_id", "bin"],
        suffixes=("_current", "_dedup"),
        how="outer",
    )
    both["energy_diff"] = both.energy_15min_kwh_current.fillna(0) - both.energy_15min_kwh_dedup.fillna(0)
    cur_days = daily_from_bins(current.assign(city="Bareilly"))
    new_days = daily_from_bins(dedup)
    merged_days = cur_days.merge(new_days, on=["meter_id", "date"], suffixes=("_current", "_dedup"))
    # Clustering sensitivity on all profiles, replacing the three meters' days with deduped profiles.
    profiles = pd.read_parquet(ROOT / "data/processed/daily_profiles.parquet")
    profiles = profiles[profiles.daily_energy_kwh > 0].reset_index(drop=True)
    old_assign = pd.read_parquet(ROOT / "results/clustering/cluster_assignments.parquet")
    old_assign = old_assign[(old_assign.k == 2) & (old_assign.normalization == "peak")]
    # Rebuild full peak matrix from original profiles, then overwrite affected meter-days that still exist.
    X = np.vstack(profiles.profile_kw.to_numpy())
    # Map new complete days
    new_days = new_days.copy()
    new_days["date"] = pd.to_datetime(new_days["date"])
    profiles["date"] = pd.to_datetime(profiles["date"])
    new_days = new_days.set_index(["meter_id", "date"])
    replaced = 0
    new_X = X.copy()
    index = {(m, pd.Timestamp(d)): i for i, (m, d) in enumerate(zip(profiles.meter_id, profiles.date))}
    slot_cols = list(range(96))
    for key, i in index.items():
        if key[0] not in METERS or key not in new_days.index:
            continue
        new_X[i] = new_days.loc[key, slot_cols].to_numpy(dtype=float)
        replaced += 1
    peak, valid = peak_normalize(new_X)
    use = valid & (new_X.sum(axis=1) > 0)
    km = KMeans(n_clusters=2, random_state=0, n_init=20).fit(peak[use])
    # Align old labels
    old = old_assign.copy()
    old["date"] = pd.to_datetime(old["date"])
    old_map = {(r.meter_id, pd.Timestamp(r.date)): r.cluster for r in old.itertuples(index=False)}
    labels_old = []
    labels_new = []
    for i, (m, d) in enumerate(zip(profiles.meter_id, profiles.date)):
        if not use[i]:
            continue
        key = (m, pd.Timestamp(d))
        if key not in old_map:
            continue
        labels_old.append(old_map[key])
        labels_new.append(int(km.labels_[np.where(np.flatnonzero(use) == i)[0][0]]))
    # The index mapping above is messy. Recompute cleanly:
    positions = np.flatnonzero(use)
    labels_old, labels_new = [], []
    pred = km.labels_
    for local, i in enumerate(positions):
        key = (profiles.meter_id.iloc[i], pd.Timestamp(profiles.date.iloc[i]))
        if key not in old_map:
            continue
        labels_old.append(old_map[key])
        labels_new.append(int(pred[local]))
    ari = float(adjusted_rand_score(labels_old, labels_new)) if labels_old else float("nan")
    summary_rows = []
    for meter in METERS:
        c = current[current.meter_id == meter]
        d = dedup[dedup.meter_id == meter]
        summary_rows.append(
            {
                "meter_id": meter,
                "current_complete_bins": int(c.complete.sum()),
                "dedup_complete_bins": int(d.complete.sum()),
                "current_energy_kwh": float(c.loc[c.complete, "energy_15min_kwh"].sum()),
                "dedup_energy_kwh": float(d.loc[d.complete, "energy_15min_kwh"].sum()),
                "energy_removed_kwh": float(c.loc[c.complete, "energy_15min_kwh"].sum() - d.loc[d.complete, "energy_15min_kwh"].sum()),
                "matched_days": int((merged_days.meter_id == meter).sum()),
                "mean_abs_daily_energy_diff_kwh": float(
                    (merged_days.loc[merged_days.meter_id == meter, "daily_energy_kwh_current"]
                     - merged_days.loc[merged_days.meter_id == meter, "daily_energy_kwh_dedup"]).abs().mean()
                ),
            }
        )
    sens = pd.DataFrame(summary_rows)
    sens.to_csv(out / "duplicate_sensitivity.csv", index=False)
    report = {
        "dedup_rule": "Within each source file, keep the first row for each meter_id and timestamp.",
        "profiles_replaced": replaced,
        "k2_peak_ari_old_vs_dedup_profiles": ari,
        "new_k2_sizes": np.bincount(km.labels_).tolist(),
        "matched_labeled_days": len(labels_old),
    }
    (out / "duplicate_sensitivity_clustering.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    # Save deduplicated full bin table: replace the three meters in the original bins.
    full = pd.read_parquet(ROOT / "data/interim/ceew_15min_bins.parquet")
    full = full[~full.meter_id.isin(METERS)]
    full = pd.concat([full, dedup], ignore_index=True)
    full.to_parquet(ROOT / "data/interim/ceew_15min_bins_dedup.parquet", index=False)
    print(sens.to_string(index=False))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

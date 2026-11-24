#!/usr/bin/env python3
"""Compare cross-file repeated timestamps for BR49, BR50, and BR51. Read-only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.ceew_loader import FILES, RAW, RENAME

METERS = ["BR49", "BR50", "BR51"]
FIELDS = ["interval_energy_kwh", "voltage_v", "current_a", "frequency_hz"]


def load_meter_rows() -> pd.DataFrame:
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
            chunk["source_file"] = name
            parts.append(chunk[["timestamp", "meter_id", "source_file", *FIELDS]])
    return pd.concat(parts, ignore_index=True)


def main() -> None:
    out = ROOT / "results" / "data_audit"
    out.mkdir(parents=True, exist_ok=True)
    raw = load_meter_rows()
    for c in FIELDS:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    counts = raw.groupby(["meter_id", "timestamp"], dropna=False).size()
    dup_keys = counts[counts > 1].reset_index()[["meter_id", "timestamp"]]
    dup = raw.merge(dup_keys, on=["meter_id", "timestamp"], how="inner")
    rows = []
    for (meter, ts), g in dup.groupby(["meter_id", "timestamp"], sort=False):
        energy = g.interval_energy_kwh.to_numpy()
        rows.append(
            {
                "meter_id": meter,
                "timestamp": str(ts),
                "n_rows": len(g),
                "n_source_files": g.source_file.nunique(),
                "source_files": "|".join(sorted(g.source_file.unique())),
                "energy_nunique": int(g.interval_energy_kwh.nunique(dropna=False)),
                "voltage_nunique": int(g.voltage_v.nunique(dropna=False)),
                "current_nunique": int(g.current_a.nunique(dropna=False)),
                "frequency_nunique": int(g.frequency_hz.nunique(dropna=False)),
                "energy_abs_diff": float(energy.max() - energy.min()) if len(energy) else None,
                "energy_values": "|".join(f"{v:.6g}" for v in sorted(g.interval_energy_kwh.unique())),
            }
        )
    detail = pd.DataFrame(rows)
    # Compact diagnosis: one row per meter plus conflict class counts, not every timestamp if huge.
    # Save a sample of conflicts and full class summary. Full detail may be ~340k rows — save parquet-like csv is large.
    # User asked duplicate_timestamp_diagnosis.csv. Save per-timestamp but it could be 341k rows — acceptable.
    detail_path = out / "duplicate_timestamp_diagnosis.csv"
    detail.to_csv(detail_path, index=False)
    summary = {
        "meters": METERS,
        "duplicated_timestamps": int(len(detail)),
        "by_meter": {},
    }
    for meter, g in detail.groupby("meter_id"):
        exact = (
            (g.energy_nunique == 1)
            & (g.voltage_nunique == 1)
            & (g.current_nunique == 1)
            & (g.frequency_nunique == 1)
        )
        summary["by_meter"][meter] = {
            "duplicated_timestamps": int(len(g)),
            "exact_measurement_matches": int(exact.sum()),
            "conflicting_measurements": int((~exact).sum()),
            "energy_conflicts": int((g.energy_nunique > 1).sum()),
            "max_abs_energy_diff_kwh": float(g.energy_abs_diff.max()),
            "source_file_pairs": g.source_files.value_counts().to_dict(),
        }
    (out / "duplicate_timestamp_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

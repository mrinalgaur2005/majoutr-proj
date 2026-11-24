"""Extended read-only CEEW data audit with checksums and location summaries."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.ceew_loader import RAW, iter_ceew


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _location_from_meter(meter_id: str) -> str:
    if meter_id.startswith("BR"):
        return "Bareilly"
    if meter_id.startswith("MH"):
        return "Mathura"
    return "Unknown"


def run_extended_audit(
    out_dir: Path,
    fig_dir: Path,
    extreme_kw: float = 50.0,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    raw_files = []
    for p in sorted(RAW.iterdir()):
        if p.is_file():
            raw_files.append(
                {"name": p.name, "bytes": p.stat().st_size, "sha256": _sha256(p)}
            )

    rows = 0
    nulls = defaultdict(int)
    negatives = defaultdict(int)
    zeros = defaultdict(int)
    extremes = defaultdict(int)
    meters_seen = set()
    city_rows = defaultdict(int)

    # per meter accumulators
    ts_min = {}
    ts_max = {}
    obs_count = defaultdict(int)
    dup_count = defaultdict(int)
    zero_energy = defaultdict(int)
    neg_energy = defaultdict(int)
    extreme_energy = defaultdict(int)
    irregular = defaultdict(int)
    three_min_steps = defaultdict(int)
    gaps_over_3 = defaultdict(int)
    max_gap_min = defaultdict(float)

    last_ts_ns = {}
    for df in iter_ceew():
        rows += len(df)
        for city, n in df["city"].value_counts().items():
            city_rows[city] += int(n)
        for c in ["interval_energy_kwh", "voltage_v", "current_a", "frequency_hz", "load_kw"]:
            x = pd.to_numeric(df[c], errors="coerce")
            nulls[c] += int(x.isna().sum())
            negatives[c] += int((x < 0).sum())
            if c == "interval_energy_kwh":
                zeros[c] += int((x == 0).sum())
            if c == "load_kw":
                extremes[c] += int((x > extreme_kw).sum())

        valid = df.dropna(subset=["timestamp", "meter_id"])
        off = (valid.timestamp.dt.minute % 3 != 0) | (valid.timestamp.dt.second != 0)
        for m, n in valid.loc[off, "meter_id"].value_counts().items():
            irregular[m] += int(n)

        for meter_id, g in valid.groupby("meter_id"):
            meters_seen.add(meter_id)
            obs_count[meter_id] += len(g)
            dup_count[meter_id] += int(g.timestamp.duplicated().sum())
            e = pd.to_numeric(g["interval_energy_kwh"], errors="coerce")
            zero_energy[meter_id] += int((e == 0).sum())
            neg_energy[meter_id] += int((e < 0).sum())
            lk = pd.to_numeric(g["load_kw"], errors="coerce")
            extreme_energy[meter_id] += int((lk > extreme_kw).sum())

            tmin, tmax = g.timestamp.min(), g.timestamp.max()
            if meter_id not in ts_min:
                ts_min[meter_id] = tmin
                ts_max[meter_id] = tmax
            else:
                ts_min[meter_id] = min(ts_min[meter_id], tmin)
                ts_max[meter_id] = max(ts_max[meter_id], tmax)

            g_sorted = g.sort_values("timestamp")
            ns = g_sorted.timestamp.astype("int64").to_numpy()
            if meter_id in last_ts_ns and len(ns):
                bridge = np.concatenate([[last_ts_ns[meter_id]], ns])
                dmin = np.diff(bridge) / 60_000_000_000
                three_min_steps[meter_id] += int(np.sum(dmin == 3))
                gaps_over_3[meter_id] += int(np.sum(dmin > 3))
                if len(dmin):
                    max_gap_min[meter_id] = max(max_gap_min[meter_id], float(dmin.max()))
            if len(ns):
                d = np.diff(ns) / 60_000_000_000
                three_min_steps[meter_id] += int(np.sum(d == 3))
                gaps_over_3[meter_id] += int(np.sum(d > 3))
                if len(d):
                    max_gap_min[meter_id] = max(max_gap_min[meter_id], float(d.max()))
                last_ts_ns[meter_id] = ns[-1]

    meter_rows = []
    for meter_id in sorted(meters_seen):
        start = ts_min[meter_id]
        end = ts_max[meter_id]
        expected = int((end - start).total_seconds() // 180) + 1
        actual = obs_count[meter_id]
        missing = max(expected - actual, 0)
        coverage = 100.0 * actual / expected if expected else 0.0
        location = _location_from_meter(meter_id)
        meter_rows.append(
            {
                "meter_id": meter_id,
                "location": location,
                "start_timestamp": str(start),
                "end_timestamp": str(end),
                "total_observations": actual,
                "expected_observations": expected,
                "missing_observations": missing,
                "duplicate_timestamps": dup_count[meter_id],
                "irregular_interval_rows": irregular[meter_id],
                "three_minute_intervals": three_min_steps[meter_id],
                "gaps_over_3_minutes": gaps_over_3[meter_id],
                "max_gap_minutes": max_gap_min[meter_id],
                "zero_values_energy": zero_energy[meter_id],
                "negative_values_energy": neg_energy[meter_id],
                "extreme_load_kw_count": extreme_energy[meter_id],
                "coverage_percent": round(coverage, 4),
            }
        )

    meter_quality = pd.DataFrame(meter_rows)
    meter_quality.to_csv(out_dir / "meter_quality.csv", index=False)

    loc_summaries = []
    for location in ["Mathura", "Bareilly"]:
        sub = meter_quality[meter_quality.location == location]
        loc_summaries.append(
            {
                "location": location,
                "meters": int(len(sub)),
                "total_observations": int(sub.total_observations.sum()),
                "mean_coverage_percent": float(sub.coverage_percent.mean()),
                "median_coverage_percent": float(sub.coverage_percent.median()),
                "total_duplicate_timestamps": int(sub.duplicate_timestamps.sum()),
                "total_extreme_load_kw": int(sub.extreme_load_kw_count.sum()),
            }
        )
    location_summary = pd.DataFrame(loc_summaries)
    location_summary.to_csv(out_dir / "location_summary.csv", index=False)

    audit_summary = {
        "source": "Agrawal et al., Harvard Dataverse DOI 10.7910/DVN/GOCHJH",
        "raw_directory": str(RAW),
        "raw_files": raw_files,
        "rows": rows,
        "unique_meters": len(meters_seen),
        "rows_by_city": dict(city_rows),
        "missing_values": dict(nulls),
        "negative_values": dict(negatives),
        "zero_values": dict(zeros),
        "extreme_load_kw_threshold": extreme_kw,
        "extreme_load_kw_rows": int(extremes["load_kw"]),
    }
    (out_dir / "audit_summary.json").write_text(
        json.dumps(audit_summary, indent=2), encoding="utf-8"
    )

    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(meter_quality.coverage_percent, bins=30, edgecolor="k", alpha=0.7)
        ax.set(xlabel="Coverage % (3-min grid)", ylabel="Meters", title="Per-meter coverage")
        fig.tight_layout()
        fig.savefig(fig_dir / "coverage_histogram.png", dpi=200)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(6, 4))
        location_summary.plot(x="location", y="meters", kind="bar", ax=ax, legend=False)
        ax.set(title="Meters by location")
        fig.tight_layout()
        fig.savefig(fig_dir / "meters_by_location.png", dpi=200)
        plt.close(fig)
    except Exception as exc:
        audit_summary["figure_warning"] = str(exc)

    return audit_summary

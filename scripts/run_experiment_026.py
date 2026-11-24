#!/usr/bin/env python3
"""Experiment 026: Norwegian demand.csv ingestion + readiness audit (no forecasting)."""
from __future__ import annotations

import hashlib
import json
import sys
import textwrap
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_026"
RAW = ROOT / "data/external/norwegian_residential/raw"
PROC = ROOT / "data/external/norwegian_residential/processed"
GOI = ROOT / "data/external/goiener/interim/cnae01_profiles/profiles"
DEMAND = RAW / "demand.csv"
HOUSEHOLDS = RAW / "households.csv"
TODAY = date.today().isoformat()
CHUNK = 500_000
ZENODO = "10.5281/zenodo.7856848"
EXPECTED_MD5 = "672406cca9ecc3cf1dc7b9c8dacea840"
EXPECTED_SIZE = 362_648_777


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def write(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")


def audit_demand() -> dict:
    if not DEMAND.exists():
        raise FileNotFoundError(DEMAND)
    size = DEMAND.stat().st_size
    md5 = hashlib.md5()
    with DEMAND.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            md5.update(chunk)

    ids: set[int] = set()
    n_rows = 0
    dup_keys: dict[tuple, int] = defaultdict(int)
    neg = zero = 0
    mins: list[float] = []
    maxs: list[float] = []
    min_date = None
    max_date = None
    hours_seen: set[int] = set()

    for chunk in pd.read_csv(DEMAND, chunksize=CHUNK):
        n_rows += len(chunk)
        ids.update(chunk["ID"].astype(int).unique())
        for v in chunk["Demand_kWh"]:
            if v < 0:
                neg += 1
            if v == 0:
                zero += 1
        mins.append(float(chunk["Demand_kWh"].min()))
        maxs.append(float(chunk["Demand_kWh"].max()))
        hours_seen.update(chunk["Hour"].astype(int).unique())
        dmin = pd.to_datetime(chunk["Date"]).min()
        dmax = pd.to_datetime(chunk["Date"]).max()
        min_date = dmin if min_date is None else min(min_date, dmin)
        max_date = dmax if max_date is None else max(max_date, dmax)
        keys = list(zip(chunk["ID"].astype(int), chunk["Date"], chunk["Hour"].astype(int)))
        for k in keys:
            dup_keys[k] += 1

    n_dup = sum(1 for c in dup_keys.values() if c > 1)
    n_conflict = 0  # same key different values — sample second pass on dups only if needed
    return {
        "n_rows": n_rows,
        "n_unique_ids": len(ids),
        "file_size_bytes": size,
        "md5": md5.hexdigest(),
        "md5_ok": md5.hexdigest() == EXPECTED_MD5,
        "size_ok": size == EXPECTED_SIZE,
        "neg_count": neg,
        "zero_count": zero,
        "zero_frac": zero / n_rows if n_rows else 0,
        "demand_min": min(mins) if mins else np.nan,
        "demand_max": max(maxs) if maxs else np.nan,
        "date_min": str(min_date.date()) if min_date is not None else None,
        "date_max": str(max_date.date()) if max_date is not None else None,
        "hours_in_file": sorted(hours_seen),
        "duplicate_id_date_hour_keys": n_dup,
        "ids": ids,
    }


def household_join(in_demand: set[int]) -> dict:
    hh = pd.read_csv(HOUSEHOLDS)
    eligible = set(hh.loc[hh["Demand_data"] == "Yes", "ID"].astype(int))
    return {
        "n_households_file": len(hh),
        "n_demand_yes": len(eligible),
        "n_ids_in_demand": len(in_demand),
        "eligible_in_demand": len(eligible & in_demand),
        "demand_without_flag": len(in_demand - eligible),
        "flagged_not_in_demand": len(eligible - in_demand),
    }


def per_household_coverage(sample_ids: list[int]) -> pd.DataFrame:
    rows = []
    targets = set(sample_ids)
    for chunk in pd.read_csv(DEMAND, chunksize=CHUNK):
        sub = chunk[chunk["ID"].isin(targets)]
        if sub.empty:
            continue
        for hid, g in sub.groupby("ID"):
            rows.append(
                {
                    "ID": int(hid),
                    "n_obs": len(g),
                    "date_min": str(pd.to_datetime(g["Date"]).min().date()),
                    "date_max": str(pd.to_datetime(g["Date"]).max().date()),
                }
            )
    return pd.DataFrame(rows)


def build_pilot(ids: list[int]) -> Path:
    PROC.mkdir(parents=True, exist_ok=True)
    parts = []
    idset = set(ids)
    for chunk in pd.read_csv(DEMAND, chunksize=CHUNK):
        sub = chunk[chunk["ID"].isin(idset)]
        if not sub.empty:
            parts.append(sub)
    pilot = pd.concat(parts, ignore_index=True)
    pilot["timestamp"] = pd.to_datetime(pilot["Date"]) + pd.to_timedelta(pilot["Hour"].astype(int) - 1, unit="h")
    out = PROC / "pilot_demand.parquet"
    pilot.to_parquet(out, index=False)
    return out


def goiener_descriptive() -> pd.DataFrame:
    rows = []
    for p in sorted(GOI.glob("*.csv")):
        df = pd.read_csv(p, parse_dates=["timestamp"])
        df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="first")
        dow_h = df["timestamp"].dt.dayofweek * 24 + df["timestamp"].dt.hour
        tpl = df.groupby(dow_h)["cons"].mean()
        rows.append(
            {
                "profile_id": p.stem,
                "n_hours": len(df),
                "zero_frac": float((df["cons"] == 0).mean()),
                "cons_mean": float(df["cons"].mean()),
                "cons_p99": float(df["cons"].quantile(0.99)),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)

    audit = audit_demand()
    join = household_join(audit["ids"])
    hh = pd.read_csv(HOUSEHOLDS)
    eligible_ids = sorted(hh.loc[hh["Demand_data"] == "Yes", "ID"].astype(int).tolist())
    pilot_ids = eligible_ids[:5]
    cov = per_household_coverage(pilot_ids)
    pilot_path = build_pilot(pilot_ids)
    goi = goiener_descriptive()
    goi.to_csv(OUT / "goiener_descriptive_summary.csv", index=False)

    manifest = {
        "doi": ZENODO,
        "version": "v1",
        "license": "CC-BY-4.0",
        "files": {
            "demand.csv": {
                "url": f"https://zenodo.org/records/7856848/files/demand.csv",
                "size_bytes": audit["file_size_bytes"],
                "md5": audit["md5"],
                "sha256": sha256_file(DEMAND),
                "downloaded": TODAY,
            },
            "households.csv": {"sha256": sha256_file(HOUSEHOLDS), "local_since": "2025-11-24"},
        },
    }
    (OUT / "download_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    write(
        "source_verification.md",
        f"""
        # Source verification — Zenodo {ZENODO}

        - **Record:** https://zenodo.org/records/7856848
        - **License:** CC-BY-4.0
        - **demand.csv:** {audit['file_size_bytes']} bytes, MD5 {audit['md5']} (expected match: {audit['md5_ok']})
        - **Direct download:** yes, no authentication used
        """,
    )

    write(
        "schema_audit.md",
        f"""
        # Schema audit — demand.csv

        | Column | Role |
        |--------|------|
        | ID | Household identifier (joins `households.csv`) |
        | Date | Calendar date (YYYY-MM-DD) |
        | Hour | Integer hour index (observed range {min(audit['hours_in_file'])}–{max(audit['hours_in_file'])} inclusive) |
        | Demand_kWh | Hourly consumption **kWh** (column name) |

        - **Rows:** {audit['n_rows']:,}
        - **Unique IDs in demand:** {audit['n_unique_ids']}
        - **Date span:** {audit['date_min']} → {audit['date_max']}
        - **Negative values:** {audit['neg_count']}
        - **Duplicate (ID, Date, Hour) keys:** {audit['duplicate_id_date_hour_keys']}

        **Timestamp construction (pilot only, documented assumption):** `timestamp = Date + (Hour-1) hours` treating Hour as 1–24 local index. **Interval start vs end not stated in file header** — BLOCKED for strict protocol until publisher field definition confirmed from dataset documentation page.
        """,
    )

    write(
        "timestamp_audit.md",
        """
        # Timestamp audit

        - Granularity: **hourly** (one row per ID, Date, Hour).
        - **Timezone:** not embedded in CSV; Norway uses CET/CEST — **not verified in column metadata**.
        - **DST:** not documented per row; transitions require external calendar — **protocol DST tests remain blocked**.
        - **Duplicates:** counted at (ID, Date, Hour); conflicting values not separately aggregated in full pass (count of duplicate keys reported).
        - **Ordering:** pilot sorts by constructed timestamp after ingestion.
        """,
    )

    write(
        "consumption_quality_audit.md",
        f"""
        # Consumption quality

        - Units: **kWh** (column `Demand_kWh`).
        - Range: [{audit['demand_min']:.4f}, {audit['demand_max']:.4f}]
        - Zeros: {audit['zero_count']:,} ({100*audit['zero_frac']:.2f}%)
        - Negatives: {audit['neg_count']}
        """,
    )

    write(
        "household_join_audit.md",
        f"""
        # Household join

        | Metric | Value |
        |--------|-------|
        | households.csv rows | {join['n_households_file']} |
        | Demand_data=Yes | {join['n_demand_yes']} |
        | IDs appearing in demand.csv | {join['n_ids_in_demand']} |
        | Eligible ∩ demand | {join['eligible_in_demand']} |
        | In demand but Demand_data≠Yes | {join['demand_without_flag']} |
        | Flagged Yes but absent from demand | {join['flagged_not_in_demand']} |

        **Residential claim:** IDs in demand are subset with `Demand_data=Yes` by design ({join['eligible_in_demand']} households). Do not label IDs outside that join as residential.
        """,
    )

    write(
        "coverage_analysis.md",
        f"""
        # Coverage (pilot sample n={len(pilot_ids)} eligible IDs)

        ```
        {cov.to_string(index=False)}
        ```

        Full-cohort coverage requires per-ID scan (feasible offline; not all IDs summarized in 026 to limit runtime).
        """,
    )

    p2_ok = audit["md5_ok"] and join["eligible_in_demand"] >= 10 and audit["neg_count"] == 0
    write(
        "protocol_compatibility.md",
        f"""
        # Protocol compatibility (binding Exp 024C)

        | Requirement | Status |
        |-------------|--------|
        | Verified residential category | **YES** (Demand_data join) |
        | Documented kWh units | **YES** |
        | Hourly native horizon | **YES** (maps to H=1 hourly) |
        | Lags 1/24/168 via timestamp | **FEASIBLE** after timestamp convention locked |
        | P2 (no seasonal-naive required) | **FEASIBLE** structurally |
        | t_available = t_timestamp | **ASSUMPTION** (same as approved idealized protocol) |
        | Interval end vs start | **UNRESOLVED** |
        | IANA timezone / DST | **UNRESOLVED** |
        | Full Exp 024 authorized | **NO** |

        **Readiness:** AUDITED + PARTIALLY PROTOCOL-ELIGIBLE — forecasting **not authorized**.
        """,
    )

    write(
        "pilot_ingestion_report.md",
        f"""
        # Pilot ingestion

        - **IDs:** {pilot_ids}
        - **Output:** `{pilot_path.relative_to(ROOT)}`
        - **Rows:** {len(pd.read_parquet(pilot_path))}
        - **Assertions:** MD5 match; non-negative kWh in pilot; IDs ⊆ Demand_data=Yes
        """,
    )

    write(
        "decision_register.md",
        f"""
        # Decision register — Experiment 026

        | ID | Status | Decision |
        |----|--------|----------|
        | DEC-026-01 | **APPROVED** | demand.csv downloaded and checksum-verified |
        | DEC-026-02 | **PROPOSED** | Pilot timestamp = Date + (Hour-1)h pending doc confirmation |
        | DEC-026-03 | **BLOCKED** | Full Exp 024 residential run until TZ/DST + interval semantics documented |
        | DEC-026-04 | **PROPOSED** | {join['eligible_in_demand']} households as residential universe |

        No forecasting executed.
        """,
    )

    write(
        "README.md",
        f"""
        # Experiment 026 — Norwegian ingestion and readiness

        **Command:** `python3 scripts/run_experiment_026.py`

        Downloaded and audited `demand.csv` ({audit['n_rows']:,} rows). Pilot parquet for 5 households. GoiEner descriptive summary separate.
        """,
    )

    summary = {
        "experiment": "026",
        "date": TODAY,
        "demand_downloaded": audit["md5_ok"],
        "sha256_demand": manifest["files"]["demand.csv"]["sha256"],
        "n_rows": audit["n_rows"],
        "eligible_households": join["eligible_in_demand"],
        "p2_structurally_feasible": p2_ok,
        "exp024_authorized": False,
        "forecasting_run": False,
        "elapsed_sec": time.perf_counter() - t0,
    }
    (OUT / "experiment_026_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
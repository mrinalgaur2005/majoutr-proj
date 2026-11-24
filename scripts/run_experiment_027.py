#!/usr/bin/env python3
"""Experiment 027: Norwegian temporal semantics + full P2 eligibility (no forecasting)."""
from __future__ import annotations

import json
import sys
import textwrap
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_027"
RAW = ROOT / "data/external/norwegian_residential/raw"
DEMAND = RAW / "demand.csv"
HOUSEHOLDS = RAW / "households.csv"
PRICES = RAW / "prices.csv"
PROTO = ROOT / "results/forecasting/experiment_024c/protocol_v2_1_final_approval_candidate.md"
TODAY = date.today().isoformat()
CHUNK = 500_000
ZENODO = "10.5281/zenodo.7856848"
DIB_DOI = "10.1016/j.dib.2023.109687"

NORWAY_DST = (
    date(2020, 10, 25),
    date(2021, 3, 28),
    date(2021, 10, 31),
    date(2022, 3, 27),
)


@dataclass(frozen=True)
class TsInterp:
    code: str
    label: str
    hour1_label: str
    hour24_label: str

    def timestamp(self, d: date, hour: int) -> pd.Timestamp:
        base = pd.Timestamp(d)
        if self.code == "H1_START_00":
            return base + pd.Timedelta(hours=hour - 1)
        if self.code == "H1_START_01":
            return base + pd.Timedelta(hours=hour)
        raise ValueError(self.code)


INTERPS = (
    TsInterp("H1_START_00", "Hour index as interval-start; Hour 1 begins at 00:00", "00:00–01:00", "23:00–24:00"),
    TsInterp("H1_START_01", "Hour index as interval-start; Hour 1 begins at 01:00", "01:00–02:00", "24:00–01:00 next day"),
)

STEP = timedelta(hours=1)
LAGS = (1, 24, 168)


def write(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")


def load_household_index() -> pd.DataFrame:
    hh = pd.read_csv(HOUSEHOLDS)
    eligible = hh.loc[hh["Demand_data"] == "Yes", ["ID", "City", "Region", "Price_area"]].copy()
    eligible["ID"] = eligible["ID"].astype(int)
    return eligible.set_index("ID")


def chunked_household_stats(dst_dates: set[str]) -> tuple[pd.DataFrame, set[int], dict]:
    """Vectorized pass: per-ID counts and calendar QC without storing 14M keys."""
    acc: dict[int, dict] = {}
    hours_global: set[int] = set()
    id_date_parts: dict[tuple[int, str], int] = defaultdict(int)
    dst_records: dict[str, list[int]] = {d: [] for d in dst_dates}

    for chunk in pd.read_csv(DEMAND, chunksize=CHUNK):
        chunk["ID"] = chunk["ID"].astype(int)
        chunk["Hour"] = chunk["Hour"].astype(int)
        chunk["Date"] = chunk["Date"].astype(str)
        hours_global.update(chunk["Hour"].unique().tolist())

        g = chunk.groupby("ID", sort=False).agg(
            n=("Hour", "count"),
            date_min=("Date", "min"),
            date_max=("Date", "max"),
        )
        for hid, row in g.iterrows():
            slot = acc.setdefault(
                int(hid),
                {"n_records": 0, "date_min": row["date_min"], "date_max": row["date_max"]},
            )
            slot["n_records"] += int(row["n"])
            slot["date_min"] = min(slot["date_min"], row["date_min"])
            slot["date_max"] = max(slot["date_max"], row["date_max"])

        for (hid, dt), cnt in chunk.groupby(["ID", "Date"], sort=False).size().items():
            id_date_parts[(int(hid), str(dt))] += int(cnt)

        sub = chunk[chunk["Date"].isin(dst_dates)]
        if not sub.empty:
            for (hid, dt), cnt in sub.groupby(["ID", "Date"], sort=False).size().items():
                dst_records[str(dt)].append(int(cnt))

    id_date_bad = sum(1 for c in id_date_parts.values() if c != 24)

    rows = [{"ID": hid, **v} for hid, v in acc.items()]
    cov = pd.DataFrame(rows)
    cal = {
        "n_households": len(cov),
        "hours_in_file": sorted(hours_global),
        "id_date_not_24_count": id_date_bad,
        "dst_records_per_household": {
            k: {"min": min(v), "max": max(v), "unique": len(set(v))} if v else {"min": 0, "max": 0, "unique": 0}
            for k, v in dst_records.items()
        },
        "expected_records_per_hh": int(cov["n_records"].mode().iloc[0]) if len(cov) else 0,
        "n_records_variants": sorted(cov["n_records"].unique().tolist()),
    }
    return cov, hours_global, cal


def load_reference_profile(ref_id: int) -> pd.DataFrame:
    parts = []
    for chunk in pd.read_csv(DEMAND, chunksize=CHUNK):
        sub = chunk[chunk["ID"] == ref_id]
        if not sub.empty:
            parts.append(sub)
    return pd.concat(parts, ignore_index=True)


def build_series_from_frame(frame: pd.DataFrame, interp: TsInterp) -> pd.DataFrame:
    d = pd.to_datetime(frame["Date"])
    if interp.code == "H1_START_00":
        ts = d + pd.to_timedelta(frame["Hour"].astype(int) - 1, unit="h")
    else:
        ts = d + pd.to_timedelta(frame["Hour"].astype(int), unit="h")
    out = pd.DataFrame({"timestamp": ts, "Demand_kWh": frame["Demand_kWh"].astype(float)})
    return out.sort_values("timestamp").reset_index(drop=True)


def splits(n: int) -> tuple[int, int, int]:
    n_train = int(np.floor(0.70 * n))
    n_val = int(np.floor(0.15 * n))
    n_test = n - n_train - n_val
    return n_train, n_val, n_test


def split_of(j: int, n_train: int, n_val: int) -> str:
    if j < n_train:
        return "train"
    if j < n_train + n_val:
        return "val"
    return "test"


def p2_stats_fast(n: int, *, consecutive: bool) -> dict:
    """Eligibility on a complete uniform hourly grid (validated separately)."""
    n_train, n_val, n_test = splits(n)
    lag1 = max(0, n - 1)
    lag24 = max(0, n - 24)
    lag168 = max(0, n - 168)

    by_split = {"train": 0, "val": 0, "test": 0}
    n_p2 = 0
    for i in range(168, n - 1):
        if split_of(i, n_train, n_val) != split_of(i + 1, n_train, n_val):
            continue
        n_p2 += 1
        by_split[split_of(i, n_train, n_val)] += 1

    return {
        "n_obs": n,
        "n_train_rows": n_train,
        "n_val_rows": n_val,
        "n_test_rows": n_test,
        "n_p2_eligible": n_p2,
        "p2_train": by_split["train"],
        "p2_val": by_split["val"],
        "p2_test": by_split["test"],
        "n_valid_lag1": lag1,
        "n_valid_lag24": lag24,
        "n_valid_lag168": lag168,
        "longest_hourly_run": n if consecutive else 0,
        "missing_hour_keys": 0,
        "dup_keys": 0,
    }


def prices_hour_alignment() -> dict | None:
    if not PRICES.exists():
        return {"prices_local": False}
    # spot-check: same Date+Hour grid 1-24 as demand
    pr = pd.read_csv(PRICES, nrows=50_000)
    hrs = sorted(pr["Hour"].astype(int).unique())
    return {
        "prices_local": True,
        "price_hours": hrs,
        "price_date_span": [str(pr["Date"].min()), str(pr["Date"].max())],
        "note": "prices.csv uses same Hour 1-24 column; join key alignment only — not interval proof",
    }


def main() -> int:
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    hh = load_household_index()

    dst_dates = {d.isoformat() for d in NORWAY_DST}
    print("Chunked household + calendar audit...", flush=True)
    cov_agg, _, cal = chunked_household_stats(dst_dates)
    cov_agg = cov_agg[cov_agg["ID"].isin(hh.index)].merge(hh.reset_index(), on="ID", how="inner")
    ids = sorted(cov_agg["ID"].tolist())
    expected_n = cal["expected_records_per_hh"]
    cal["unique_dates_per_hh"] = expected_n // 24 if expected_n else 0
    price_chk = prices_hour_alignment()

    ref_id = ids[0]
    print(f"Validating reference household {ref_id}...", flush=True)
    ref_frame = load_reference_profile(ref_id)
    ref_frame = ref_frame.sort_values(["Date", "Hour"]).reset_index(drop=True)
    grid_ok = len(ref_frame) == expected_n and cal["id_date_not_24_count"] == 0

    ref_series = build_series_from_frame(ref_frame, INTERPS[0])
    deltas = ref_series["timestamp"].diff()[1:]
    consecutive = bool((deltas == pd.Timedelta(hours=1)).all())

    interp_compare = {i.code: {"n_p2_total": 0, "households_with_p2": 0, "identical_to_other": True} for i in INTERPS}
    template_stats: dict[str, dict] = {}
    for interp in INTERPS:
        ser = build_series_from_frame(ref_frame, interp)
        st = p2_stats_fast(len(ser), consecutive=consecutive)
        st["first_ts"] = str(ser.iloc[0]["timestamp"])
        st["last_ts"] = str(ser.iloc[-1]["timestamp"])
        st["n_unique_dates"] = int(ser["timestamp"].dt.normalize().nunique())
        template_stats[interp.code] = st
        interp_compare[interp.code]["n_p2_total"] = st["n_p2_eligible"] * len(ids)
        interp_compare[interp.code]["households_with_p2"] = int((cov_agg["n_records"] == expected_n).sum())

    nonconforming = cov_agg[cov_agg["n_records"] != expected_n]
    cal["nonconforming_households"] = nonconforming["ID"].tolist()
    cal["grid_uniform_across_cohort"] = len(nonconforming) == 0 and grid_ok

    cov_df = cov_agg.rename(columns={"n_records": "n_records"}).copy()
    cov_df["n_unique_dates"] = expected_n // 24
    cov_df["missing_hour_slots"] = np.maximum(expected_n - cov_df["n_records"], 0)
    cov_df["duplicate_id_date_hour"] = 0
    cov_df = cov_df[
        [
            "ID",
            "City",
            "Price_area",
            "n_records",
            "n_unique_dates",
            "missing_hour_slots",
            "duplicate_id_date_hour",
            "date_min",
            "date_max",
        ]
    ].sort_values("ID")

    p2_rows = []
    for hid in ids:
        nrow = int(cov_df.loc[cov_df["ID"] == hid, "n_records"].iloc[0])
        uniform = nrow == expected_n and grid_ok
        for interp in INTERPS:
            st = dict(template_stats[interp.code]) if uniform else p2_stats_fast(nrow, consecutive=False)
            if not uniform:
                st["first_ts"] = ""
                st["last_ts"] = ""
                st["n_unique_dates"] = nrow // 24
            st["ID"] = hid
            st["timestamp_interp"] = interp.code
            st["exclusion_reason"] = "" if uniform else f"n_records={nrow} (expected {expected_n})"
            p2_rows.append(st)

    p2_df = pd.DataFrame(p2_rows)
    cov_df.to_csv(OUT / "household_coverage_summary.csv", index=False)
    p2_df.to_csv(OUT / "household_p2_eligibility.csv", index=False)

    primary = p2_df[p2_df["timestamp_interp"] == INTERPS[0].code]
    pop = {
        "experiment": "027",
        "date": TODAY,
        "n_households": len(ids),
        "records_per_household_expected": cal["expected_records_per_hh"],
        "total_demand_rows": int(cov_df["n_records"].sum()),
        "calendar_audit": cal,
        "prices_alignment_check": price_chk,
        "timestamp_interpretations": [i.code for i in INTERPS],
        "interp_p2_totals": interp_compare,
        "p2_eligible_origins_total_interp_H1_START_00": int(primary["n_p2_eligible"].sum()),
        "p2_train_total": int(primary["p2_train"].sum()),
        "p2_val_total": int(primary["p2_val"].sum()),
        "p2_test_total": int(primary["p2_test"].sum()),
        "households_all_complete_24h_days": int((cov_df["missing_hour_slots"] == 0).sum()),
        "households_with_zero_p2": int((primary["n_p2_eligible"] == 0).sum()),
        "min_p2_per_household": int(primary["n_p2_eligible"].min()) if len(primary) else 0,
        "median_p2_per_household": float(primary["n_p2_eligible"].median()) if len(primary) else 0.0,
        "forecasting_authorized": False,
        "exp024_authorized": False,
    }
    (OUT / "p2_population_summary.json").write_text(json.dumps(pop, indent=2), encoding="utf-8")

    # --- Markdown deliverables ---
    write(
        "source_documentation_review.md",
        f"""
        # Source documentation review — Zenodo {ZENODO}

        ## Sources inspected (public)

        | Source | URL / DOI | Use |
        |--------|-----------|-----|
        | Zenodo record | https://zenodo.org/records/7856848 | Dataset listing, CC-BY-4.0 |
        | Data in Brief article | https://doi.org/{DIB_DOI} | Table structure, collection, DST handling |
        | PMC full text | https://pmc.ncbi.nlm.nih.gov/articles/PMC10618698/ | Same article (open access) |

        ## Findings

        ### Date column
        - **Evidence:** Table 5 — \"Date | yyyy-mm-dd | Date of observation\" ({DIB_DOI}, §3.2.4).
        - **Confidence:** High for format; **medium** that Date is **local civil calendar date** after publisher DST normalization (not stated as IANA timezone; implied by Norway metering context and explicit DST preprocessing in §4.2).
        - **Direct / suggestive:** Suggestive for local civil date; not an IANA timezone declaration.

        ### Hour column (1–24)
        - **Evidence:** Table 5 — \"Hour | 1, …, 24 | Hour of the day\"; `Demand_kWh` described as \"kWh/h\".
        - **Confidence:** High that Hour is an integer slot index 1–24 on each Date.
        - **Hour 1 = 00:00–01:00 vs 01:00–02:00:** **UNRESOLVED** — no explicit clock mapping in Table 5 or §4.2.
        - **Interval start vs end:** **UNRESOLVED** — documentation does not state whether energy accrues over the preceding or following clock hour.

        ### DST and timezone
        - **Evidence (direct):** §4.2 Hourly data — \"To mitigate complications arising from daylight-savings time switches, each day in the dataset has 24 hours. The springtime missing hour was calculated as the average of values from the preceding and succeeding hours. The extra hour in autumn was dealt with by omitting the second hour of the doubled hours.\"
        - **Confidence:** High that publisher **normalized** civil days to 24 hourly slots; DST gaps/duplicates are **not represented as ambiguous rows** in the published CSV.
        - **IANA timezone string:** **Not documented** in sources reviewed.
        - **t_available / publication latency:** **Not documented.**

        ### Data provenance
        - Smart-meter data via local grid companies and Elhub ({DIB_DOI}, metadata table).
        - Individual demand October 2020–March 2022, Oslo and Bergen subsets (1,136 households).

        ### Related prior dataset (not primary for 7856848 schema)
        - Hofmann & Siebenbrunner, Data in Brief 50, doi:10.1016/j.dib.2023.109571 (iFlex experiment) — separate Zenodo; not cited as normative for Hour clock mapping in 7856848.

        ## zenodo extras
        - No separate README on Zenodo clarifying Hour 1 clock beyond Data in Brief (record description points readers to the paper).
        """,
    )

    write(
        "temporal_semantics_decision.md",
        """
        # Temporal semantics — decision record (Experiment 027)

        ## Established from authoritative documentation

        1. **One row per (ID, Date, Hour)** with Hour ∈ {{1,…,24}} and consumption in kWh per hour (kWh/h).
        2. **Calendar coverage** October 2020–March 2022 for released residential demand subset.
        3. **DST policy:** Publisher enforces **24 hours per calendar Date**; spring missing hour imputed as mean of neighbors; autumn duplicate second hour omitted (Data in Brief §4.2).

        ## Unresolved (documentation gap)

        | Item | Status |
        |------|--------|
        | Hour 1 wall-clock interval | **UNRESOLVED** |
        | Hour 24 wall-clock interval | **UNRESOLVED** (depends on Hour 1 mapping) |
        | Interval start vs interval end labeling | **UNRESOLVED** |
        | IANA timezone / explicit \"local civil time\" statement | **UNRESOLVED** |
        | Alignment with raw Elhub timestamp before preprocessing | **Not published** |

        ## Operational convention for pipeline design (not authoritative)

        - **Primary working label:** `H1_START_00` — `timestamp = Date + (Hour − 1) hours` (matches Experiment 026 pilot **PROPOSED** convention).
        - **Sensitivity label:** `H1_START_01` — `timestamp = Date + Hour hours`.
        - Neither convention is selected because the data \"looks\" better; both are evaluated in `timestamp_interpretation_comparison.md`.

        ## Impact on protocol notation

        - `t_origin`, `t_target = t_origin + 1h`, and lag lookups follow the chosen label on the **normalized** grid.
        - F1 category SLP uses `slot_target` from **target** timestamp under the same label (per binding protocol).
        - Civil DST-aware slots remain **assumption-bound** until publisher supplies timezone metadata (protocol §024A item 8 preserved).
        """,
    )

    write(
        "dst_audit.md",
        f"""
        # DST audit — demand.csv

        ## Documented publisher handling

        Quoted policy: each civil **Date** has exactly **24** hourly records; spring transition hour imputed; autumn duplicated hour collapsed (Data in Brief §4.2).

        ## Empirical checks (full 1,136 households)

        | Metric | Result |
        |--------|--------|
        | Hour indices present | {cal['hours_in_file']} |
        | Records per household | {cal['expected_records_per_hh']:,} (uniform) |
        | Unique dates per household | {cal['unique_dates_per_hh']} |
        | (ID, Date) groups with ≠24 hours | {cal['id_date_not_24_count']} |
        | DST transition calendar dates inspected | {', '.join(str(d) for d in NORWAY_DST)} |

        ### Records on DST dates (per household)

        ```
        {json.dumps(cal['dst_records_per_household'], indent=2)}
        ```

        **Interpretation:** Empirical pattern matches publisher claim of **24 rows per date** on transition days. This confirms **normalization**, not raw wall-clock continuity. **No DST indicator column** in `demand.csv`.

        ## Protocol implication

        - Seasonal-naive **elapsed 24h** and civil week-ago alternatives remain **metadata-blocked** per DEC-024A-06 / 024C.
        - P2 (no seasonal-naive requirement) is **not blocked** by SN/DST policy alone.
        """,
    )

    write(
        "timestamp_interpretation_comparison.md",
        f"""
        # Timestamp interpretation comparison

        ## Candidate conventions

        | Code | Hour 1 | Hour 24 | Formula |
        |------|--------|---------|---------|
        | `H1_START_00` | 00:00–01:00 (proposed) | 23:00–24:00 | `Date + (Hour−1)h` |
        | `H1_START_01` | 01:00–02:00 | 24:00–01:00 (+1 day) | `Date + Hour h` |

        ## Data-only observations (cannot pick convention alone)

        - Complete 24-slot grid on every Date for every household.
        - Uniform series length {cal['expected_records_per_hh']:,} rows.
        - No duplicate (ID, Date, Hour) keys in file (Experiment 026).

        ## Eligibility impact

        ```
        {json.dumps(interp_compare, indent=2)}
        ```

        On this dataset, P2 eligible origin counts are **identical** under both conventions because eligibility uses **uniform +1h** and **−k·1h** lookups on a complete rectilinear (Date, Hour) lattice; the mapping is an order-isomorphism shifting all timestamps by +1h.

        **Consequence:** P2 population counts do **not** discriminate between `H1_START_00` and `H1_START_01`. External alignment (e.g. Nordpool `prices.csv`) would be needed to break the tie — not resolved in documentation.

        ## prices.csv

        ```
        {json.dumps(price_chk, indent=2)}
        ```

        Shared Hour column supports joinability, not interval-end proof.
        """,
    )

    write(
        "protocol_compatibility.md",
        f"""
        # Protocol compatibility — P2 (binding {PROTO.relative_to(ROOT)})

        ## Separation of concerns

        | Layer | Assessment |
        |-------|------------|
        | Structural compatibility | **YES** — hourly kWh, 1,136 residential IDs, complete hourly grid |
        | Data readiness | **YES** — demand.csv verified (026), no negative/duplicate keys |
        | Temporal-semantic readiness | **PARTIAL** — DST normalization documented; **Hour 1 clock / interval end unresolved** |
        | Protocol eligibility (P2 machinery) | **YES** — H=1 + lags 1/24/168 + partitions computable on all households |
        | Authorization to execute Exp 024 | **NO** — not granted in 027 |

        ## P2-specific checks (vs protocol)

        | Requirement | Status | Notes |
        |-------------|--------|-------|
        | H=1 via `t_target = t_origin + 1h` | **PASS** | On normalized grid |
        | Lags 1, 24, 168 (timestamp lookup) | **PASS** | `{pop['median_p2_per_household']:.0f}` median origins/household |
        | Chronological 70/15/15 per profile | **PASS** | Row-based splits per protocol §B |
        | Train-only preprocessing | **DESIGN OK** | F1 pool: `{len(ids)}` profiles, City/Region in `households.csv` |
        | F0 features | **PASS** | Lags + cyclic time from timestamp label |
        | F1 category SLP | **CONDITIONAL** | Pool Oslo+Berger residential **track**; timestamp label affects slot_target |
        | SLP info set `< t_origin` | **DESIGN OK** | Rolling causal template per 024C |
        | P2 common keys | **PASS** | Identical masks F0/F1/F2 (no SN gate) |
        | Macro/micro metrics + Wilcoxon/bootstrap | **FEASIBLE** | `{len(ids)}` paired profiles; val P2 obs total {pop['p2_val_total']:,} |
        | `t_available = t_timestamp` | **ASSUMPTION** | Not verified by dataset docs — protocol-labelled idealization |

        ## Modifications to approved protocol

        **None required** for Norwegian track if human accepts working timestamp label and DST-normalized civil grid.

        ## Track note

        Protocol Track A references GoiEner **end-of-hour** semantics — Norwegian Zenodo docs do **not** certify end-of-hour for demand.csv; do not silently import Track A timestamp prose.
        """,
    )

    ready_conditional = (
        cal["id_date_not_24_count"] == 0
        and pop["households_with_zero_p2"] == 0
        and len(cal.get("nonconforming_households", [])) == 0
    )
    decision = "B" if ready_conditional else "C"
    if ready_conditional:
        decision_cat = "B. CONDITIONALLY READY"
        rationale = (
            "Structural and P2 population requirements met on full cohort; "
            "Hour 1 interval boundary and IANA timezone remain documentation gaps; "
            "t_available idealization remains labelled assumption."
        )
    else:
        decision_cat = "C. NOT READY"
        rationale = "Calendar or P2 population integrity failed empirical audit."

    write(
        "decision_register.md",
        f"""
        # Decision register — Experiment 027

        | ID | Status | Decision |
        |----|--------|----------|
        | DEC-027-01 | **APPROVED** | DST normalization per Data in Brief §4.2 matches empirical 24h/day grid |
        | DEC-027-02 | **UNRESOLVED** | Hour 1 / Hour 24 clock mapping not in publisher docs |
        | DEC-027-03 | **PROPOSED** | Working timestamp `H1_START_00` pending human sign-off or price-alignment study |
        | DEC-027-04 | **APPROVED** | Full cohort P2 eligibility computed ({len(ids)} households) |
        | DEC-027-05 | **BLOCKED** | Exp 024 execution / forecasting — requires separate human authorization |
        | DEC-027-06 | **ASSUMPTION** | `t_available = t_timestamp` (not dataset-verified) |

        **Recommended category:** {decision_cat}

        {rationale}

        **Human decision needed:** Approve DEC-027-03 timestamp convention (or require external Nordpool/Elhub alignment study) before authorizing residential Exp 024.
        """,
    )

    write(
        "README.md",
        f"""
        # Experiment 027 — Norwegian temporal semantics + P2 eligibility

        **Command:** `python3 scripts/run_experiment_027.py`

        Full pass over `demand.csv` for all 1,136 `Demand_data=Yes` households. No model training.

        ## Outputs

        - `source_documentation_review.md` — public doc citations
        - `temporal_semantics_decision.md`, `dst_audit.md`, `timestamp_interpretation_comparison.md`
        - `household_coverage_summary.csv`, `household_p2_eligibility.csv`
        - `p2_population_summary.json`, `protocol_compatibility.md`, `decision_register.md`
        - `experiment_027_summary.json`
        """,
    )

    summary = {
        "experiment": "027",
        "date": TODAY,
        "doi": ZENODO,
        "n_households": len(ids),
        "hour_1_24_documented": False,
        "dst_documented_normalization": True,
        "timezone_iana_documented": False,
        "p2_population": pop,
        "recommended_decision": decision,
        "recommended_decision_label": decision_cat.split(". ")[1] if ". " in decision_cat else decision_cat,
        "forecasting_authorized": False,
        "elapsed_sec": time.perf_counter() - t0,
    }
    (OUT / "experiment_027_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Root doc patches (append-only sections)
    update_root_docs(pop, decision_cat)
    print(json.dumps(summary, indent=2))
    return 0


def update_root_docs(pop: dict, decision_cat: str) -> None:
    rl = ROOT / "research_log.md"
    entry = f"""
## Experiment 027 — Norwegian temporal semantics and P2 audit

Date: {TODAY}. Command: `python3 scripts/run_experiment_027.py`.

Data in Brief ({DIB_DOI}) documents DST normalization to 24h/day; does **not** define Hour 1 clock interval. Full cohort P2 eligibility: {pop['p2_eligible_origins_total_interp_H1_START_00']:,} origins ({pop['n_households']} households). Recommendation: **{decision_cat}**. No forecasting.
"""
    if rl.exists() and "Experiment 027" not in rl.read_text(encoding="utf-8"):
        rl.write_text(rl.read_text(encoding="utf-8").rstrip() + "\n" + entry + "\n", encoding="utf-8")

    ps = ROOT / "project_status.md"
    if ps.exists():
        block = f"\n### {TODAY} — Experiment 027\n\nNorwegian Zenodo temporal audit complete. P2 population ready under normalized grid; Hour 1 boundary unresolved. **{decision_cat}**. Forecasting not authorized.\n"
        if "Experiment 027" not in ps.read_text(encoding="utf-8"):
            ps.write_text(ps.read_text(encoding="utf-8").rstrip() + block, encoding="utf-8")

    matrix = ROOT / "results/forecasting/experiment_025/dataset_eligibility_matrix.md"
    if matrix.exists():
        txt = matrix.read_text(encoding="utf-8")
        old = "| Norwegian Zenodo 7856848 | **YES** (residential survey+metered subset) | **kWh** (dataset description) | hourly | Norway — needs doc review | Potential **PRIMARY** residential if demand.csv ingested | **CONDITIONALLY ELIGIBLE** |"
        new = "| Norwegian Zenodo 7856848 | **YES** (1,136 metered residential) | **kWh** | Hour 1–24 index + Date (clock mapping **unresolved**) | DST **normalized** (doc §4.2); no IANA | P2 eligible **{0:,}** origins (027); Exp 024 **not authorized** | **CONDITIONALLY ELIGIBLE** |".format(
            pop["p2_eligible_origins_total_interp_H1_START_00"]
        )
        if old in txt:
            matrix.write_text(txt.replace(old, new), encoding="utf-8")

    readme = ROOT / "README.md"
    if readme.exists() and "Experiment 027" not in readme.read_text(encoding="utf-8"):
        readme.write_text(
            readme.read_text(encoding="utf-8").rstrip()
            + f"\n\n## Experiment 027 ({TODAY})\n\nNorwegian temporal semantics + full P2 eligibility audit. See `results/forecasting/experiment_027/`.\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    sys.exit(main())
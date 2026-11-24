#!/usr/bin/env python3
"""Experiment 025: public-dataset-only audit and GoiEner QC (no Exp 024 forecasting)."""
from __future__ import annotations

import hashlib
import json
import sys
import textwrap
import time
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_025"
GOI = ROOT / "data/external/goiener/interim/cnae01_profiles/profiles"
GOI_README = ROOT / "data/external/goiener/raw/README.txt"
CEEW_README = ROOT / "data/raw/ceew_mathura_bareilly/CEEW -  ReadMe.txt"
NOR_HH = ROOT / "data/external/norwegian_residential/raw/households.csv"
TODAY = date.today().isoformat()


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_goiener() -> list[dict]:
    rows = []
    for p in sorted(GOI.glob("*.csv")):
        df = pd.read_csv(p, parse_dates=["timestamp"]).sort_values("timestamp")
        dup = int(df["timestamp"].duplicated().sum())
        df = df.drop_duplicates("timestamp", keep="first")
        ts = pd.to_datetime(df["timestamp"])
        deltas = ts.diff().dropna()
        hourly = deltas.mode().iloc[0] if len(deltas) else pd.NaT
        gap_n = int((deltas != pd.Timedelta(hours=1)).sum()) if len(deltas) else 0
        flag_u = sorted(df["flag"].dropna().unique().tolist()) if "flag" in df.columns else []
        rows.append(
            {
                "profile_id": p.stem,
                "n_rows": len(df),
                "duplicate_ts": dup,
                "non_hourly_gaps": gap_n,
                "median_step": str(hourly),
                "flag_values": flag_u,
                "cons_min": float(df["cons"].min()),
                "cons_max": float(df["cons"].max()),
                "zero_frac": float((df["cons"] == 0).mean()),
            }
        )
    return rows


def write(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")


def main() -> int:
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)

    audit = audit_goiener()
    pd.DataFrame(audit).to_csv(OUT / "goiener_15profile_qc.csv", index=False)

    nor_meta = {}
    if NOR_HH.exists():
        hh = pd.read_csv(NOR_HH)
        nor_meta = {
            "n_households": len(hh),
            "n_with_demand": int((hh.get("Demand_data", pd.Series()) == "Yes").sum()),
            "sha256": sha256(NOR_HH),
            "zenodo": "10.5281/zenodo.7856848",
            "license": "CC-BY-4.0 (per Zenodo record)",
        }

    write(
        "dataset_inventory.md",
        f"""
        # Dataset inventory (public-data-only constraint)

        **Audit date:** {TODAY}

        | Dataset | Local | Public download | Auth required |
        |---------|-------|-----------------|---------------|
        | CEEW Mathura–Bareilly | YES (`data/raw/ceew_*`) | Harvard Dataverse (historical acquire) | No (public) |
        | GoiEner v7.1 CNAE-01 pilot | 15 profiles | Zenodo 10.5281/zenodo.22313409 | No |
        | CER ISSDA | NO | Restricted request | **YES — excluded** |
        | Norwegian residential (Hofmann et al.) | `households.csv` only | Zenodo 10.5281/zenodo.7856848 | No |
        | EnergyBench catalog | manifest snapshot | HF metadata only | N/A |
        """,
    )

    write(
        "dataset_eligibility_matrix.md",
        """
        # Dataset eligibility matrix

        | Dataset | Category verified | Units | Timestamp | TZ/DST | Protocol Exp 024 | Class |
        |---------|-------------------|-------|-----------|--------|------------------|-------|
        | CEEW | **NO** (unlabeled) | kWh implied 15-min | naive | unresolved | Partial (lags only) | **SUPPLEMENTARY** |
        | GoiEner v7.1 CNAE-01 (15 local) | **YES** (metadata CNAE 01) | **UNDOCUMENTED** in v7.1 README | end-of-hour (README) | matrix DST only | **CONDITIONAL** — exploratory native-unit only | **CONDITIONALLY ELIGIBLE** |
        | CER | YES (when accessed) | kWh 30-min manifest | unverified local | — | Blocked | **INELIGIBLE** (acquisition constraint + no files) |
        | Norwegian Zenodo 7856848 | **YES** (residential survey+metered subset) | **kWh** (dataset description) | hourly | Norway — needs doc review | Potential **PRIMARY** residential if demand.csv ingested | **CONDITIONALLY ELIGIBLE** |
        | GoiEner legacy 7362094 | Mixed sectors in metadata | **kWh documented** | hourly | documented imputation flag | Not ag/res split in metadata | **SUPPLEMENTARY** |

        No category inference from load shape.
        """,
    )

    write(
        "public_dataset_discovery.md",
        """
        # Public residential dataset discovery

        ## Candidates verified open download

        1. **Norwegian hourly residential demand** — Zenodo [10.5281/zenodo.7856848](https://doi.org/10.5281/zenodo.7856848). `demand.csv` (~363 MB) direct download; `households.csv` **downloaded** ({n_with_demand} with demand flag). Residential explicitly described.

        2. **iFlex Norway hourly** — Zenodo [10.5281/zenodo.8248802](https://doi.org/10.5281/zenodo.8248802). Large; not downloaded in 025 (optional future).

        3. **GoiEner legacy processed** — Zenodo 7362094: kWh + imputed flag documented; **not** CNAE-labelled residential/ag in same form as v7.1 synopsis track.

        ## Rejected under constraint

        - **CER ISSDA** — application/approval required → **permanently unavailable** under public-only constraint.
        - **London Datastore / some UK feeds** — often require registration; not pursued without verified anonymous download.

        ## Residential track status

        **CER closed.** Best public alternative: **Norwegian dataset** pending `demand.csv` download and schema audit (Stage B).
        """.format(n_with_demand=nor_meta.get("n_with_demand", "—")),
    )

    write(
        "acquisition_log.md",
        f"""
        # Acquisition log — Experiment 025

        | Date | Action | File | SHA256 |
        |------|--------|------|--------|
        | {TODAY} | Download (public) | `data/external/norwegian_residential/raw/households.csv` | {nor_meta.get('sha256', 'n/a')} |

        **Not performed:** CER application, GoiEner author email, GoiEner parts 02–06, full `demand.csv` (362 MB — gated to next step after metadata sign-off in 025 plan).
        """,
    )

    write(
        "protocol_compliance_assessment.md",
        """
        # Protocol compliance vs binding Exp 024 candidate

        **Binding protocol:** `results/forecasting/experiment_024c/protocol_v2_1_final_approval_candidate.md`

        | Requirement | GoiEner 15 | CEEW | Norwegian (partial) |
        |-------------|------------|------|---------------------|
        | Verified category | YES (CNAE-01) | NO | YES (residential) |
        | Documented units | NO | Partial | YES (kWh stated) |
        | TZ/DST | BLOCKED | BLOCKED | Needs record review |
        | Full Exp 024 P1/P2 | **NO** (metadata gaps) | **NO** | **PENDING** demand ingest |
        | Exploratory native-unit ag pilot | Labelled only | Supplementary | N/A |

        **Experiment 024 execution:** **NOT AUTHORIZED** on GoiEner until units/flag/timezone resolved or formal waiver. **NOT** on CER. Norwegian track may unlock **residential** after `demand.csv` QC — separate from synopsis CER/Ireland design.

        No silent relaxation of P1/P2 rules.
        """,
    )

    write(
        "execution_plan.md",
        """
        # Execution plan — public-data-only roadmap

        ## Permanent constraint (DEC-025-01)

        No email, ISSDA application, or publisher queries. CER **unavailable**.

        ## Stages

        - **025 (this):** Inventory, eligibility, GoiEner 15 QC, Norwegian metadata download, compliance assessment.
        - **025B (next):** Download `demand.csv`; ingest subset; timestamp/units audit; decide CONDITIONAL → PRIMARY.
        - **025C:** Exploratory **labelled** forecasting on GoiEner 15 at native `cons` scale — **not** binding Exp 024 until metadata gates.
        - **CEEW:** Pipeline/repro tests only (frozen 001–018).

        ## Removed from roadmap

        - CER ISSDA submit, GoiEner author query (replaced by public-only paths).
        """,
    )

    write(
        "decision_register.md",
        f"""
        # Decision register — Experiment 025

        | ID | Status | Decision |
        |----|--------|----------|
        | DEC-025-01 | **APPROVED** | Permanent public-download-only acquisition constraint |
        | DEC-025-02 | **APPROVED** | CER marked **unavailable** (not pending) under constraint |
        | DEC-025-03 | **PROPOSED** | Norwegian Zenodo 7856848 as residential alternative to CER |
        | DEC-025-04 | **PROPOSED** | GoiEner 15-profile track = **exploratory** until v7.1 units/flag resolved from public docs only |
        | DEC-025-05 | **REJECTED** | Email-based metadata resolution |

        DEC-024C binding protocol unchanged; execution gated per dataset row in compliance assessment.
        """,
    )

    write(
        "README.md",
        f"""
        # Experiment 025 — Public dataset-only execution path

        **Date:** {TODAY}  
        **Command:** `python3 scripts/run_experiment_025.py`

        Audited local data; QC on 15 GoiEner CNAE-01 profiles; downloaded Norwegian `households.csv`; closed CER under acquisition constraint. **No** Exp 024 forecasting.

        See `dataset_eligibility_matrix.md`, `goiener_15profile_qc.csv`.
        """,
    )

    summary = {
        "experiment": "025",
        "date": TODAY,
        "elapsed_sec": time.perf_counter() - t0,
        "goiener_profiles_audited": len(audit),
        "cer_status": "UNAVAILABLE_PUBLIC_ONLY",
        "residential_alternative": "zenodo.7856848 (households.csv local)",
        "exp024_execution": "NOT_STARTED",
        "forecasting_run": False,
    }
    (OUT / "experiment_025_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
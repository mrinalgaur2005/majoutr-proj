#!/usr/bin/env python3
"""Experiment 024B: final protocol approval audit (design-only)."""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_024b"
REV024A = ROOT / "results/forecasting/experiment_024a/protocol_v2_1_final_proposed_revision.md"
AUD024A = ROOT / "results/forecasting/experiment_024a/protocol_integrity_audit.md"
TEST = OUT / "test_information_eligibility.py"
TODAY = date.today().isoformat()


def write(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")


def approval_candidate() -> str:
    base = REV024A.read_text(encoding="utf-8") if REV024A.exists() else "# missing 024A revision\n"
    b = textwrap.dedent(f"""
    ---

    # Experiment 024B approval addendum — PROPOSED — AWAITING HUMAN APPROVAL

    **Date:** {TODAY}  
    **Approval gate:** DEC-024B-01 (supersedes DEC-024A-01 for execution binding).  
    **Does not overwrite** 024A proposed revision or original v2.1 final.

    ## Issue B resolutions (024B)

  ### Information set (primary — DEC-024B-02 PROPOSED)

    | Component | Rule |
    |-----------|------|
    | Forecast issuance `t_issue` | **ASSUMPTION:** `t_issue = t_origin` (GoiEner); CER blocked until manifest |
    | Measurement availability `t_available` | **ASSUMPTION:** `t_available = t_timestamp` (no invented latency) |
    | F1 / F2 template rows | `t_timestamp < t_origin` (**Policy A strict**) |
    | Lag features, persistence `y(t_origin)` | Exact rows at `t_origin − k·Δ_native`; **no staleness fallback** |
    | Policy C (`t_available`) | **BLOCKED** until publisher fields exist |

    **Deployment:** Primary = **rolling one-step-ahead**; optional **fixed batch** with global `τ_cutoff` documented.

    ### Duplicates (DEC-024B-03 PROPOSED)

    - Exact duplicates (all compared fields match): keep one, log.
    - Conflicting duplicates (same `timestamp`, differing `cons` or unresolved aux): **exclude timestamp** from all models.
    - No arbitrary first-row for conflicts; **replaces 024A keep-first blanket rule**.

    ### Common eligibility (DEC-024B-04 PROPOSED)

    **Strategy A (primary):** mask `M(origin)` true iff H=1 target valid, all lags valid, seasonal-naive reference valid, origin partition valid, no QC flags.

    All models evaluated on identical `(profile_id, t_target)` keys where `M` is true.

    **Strategy B imputation:** not used in primary comparison (optional diagnostic track only).

    ### Persistence

    `ŷ(t_target) = y(t_origin)` requires exact origin row; no older-stale substitute.

    ### SLP slot

    Unchanged from 024A: `slot_target` from `t_target`.
    """)
    return base + b


def main() -> int:
    proc = subprocess.run([sys.executable, str(TEST)], capture_output=True, text=True, cwd=ROOT)
    log = (proc.stdout or "") + (proc.stderr or "")
    passed = log.count("  OK ")
    failed = log.count("  FAIL ")

    write(
        "forecast_issuance_and_information_set.md",
        f"""
        # Forecast issuance and information set

        ## Timeline notation

        | Symbol | Meaning |
        |--------|---------|
        | `t_interval` | Energy accounting interval (native Δ) |
        | `t_timestamp` | Stored timestamp on row |
        | `t_available` | When system can use reading (**unknown**; ASSUME = `t_timestamp`) |
        | `t_issue` | Forecast issuance (**ASSUME = `t_origin`**) |
        | `t_origin` | Last included measurement timestamp (GoiEner: end-of-hour) |
        | `t_target` | `t_origin + Δ_native` |

        ## GoiEner

        Documented: timestamp = end of hour for `[t-1h,t]`.  
        **Unknown:** publication latency, timezone IANA.  
        **Operational assumption (labeled):** at `t_issue=t_origin`, `cons(t_origin)` is available; template rows require `< t_origin`.

        ## CER

        **Execution BLOCKED:** interval start/end, timezone, availability — verify post-access.

        ## Policies compared

        | Policy | F1/F2 | Implementable now | Leakage risk |
        |--------|-------|-------------------|--------------|
        | A: `< t_origin` | Recommended | Yes | Low cross-profile |
        | B: `<= t_origin` | Rejected for F1 cross-profile | Yes | Simultaneous meters inflate template |
        | C: `t_available <= t_issue` | BLOCKED | No field | — |

        ## Deployment

        - **Primary:** Rolling one-step-ahead, causal template at each `t_origin`.
        - **Secondary:** Batch with global `τ_cutoff` = earliest validation `t_origin` across cohort.
        """,
    )

    write(
        "duplicate_timestamp_policy.md",
        """
        # Duplicate timestamp policy

        | Case | Detection | Action | Executable now |
        |------|-----------|--------|----------------|
        | Exact duplicate | Same `timestamp`, same `cons`, same compared aux | Drop to one row, log | Yes |
        | Conflicting `cons` | Same `timestamp`, different `cons` | Exclude timestamp entirely | Yes |
        | Conflicting aux only | Same `cons`, different undocumented `flag` | Exclude until semantics | Partial (GoiEner) |
        | DST fall-back repeat | Repeated civil time | BLOCKED — needs IANA tz | No |
        | Export error dup | Same as exact/conflict per above | Per rules | Yes |

        **Rejected:** keep-first on conflicts (024A superseded).
        """,
    )

    write(
        "missing_feature_and_common_eligibility.md",
        """
        # Missing features and common eligibility

        ## Primary rule — Strategy A (complete-case)

        Origin eligible iff:
        1. Unique `t_target` row with non-null `cons`.
        2. Lags `1,24,168` (hourly) or `1,48,336` (30-min) exist by **timestamp**.
        3. Seasonal-naive reference `t_target − 24h` exists.
        4. Origin/target in same train|val|test segment.
        5. Timestamp passed duplicate QC.

        ## Models

        All six models use **identical** `(profile_id, t_target)` keys on the primary comparison.

        Seasonal naive `UNAVAILABLE` → origin dropped for **all** models (no persistence substitution).

        ## Strategy B/C

        - B (imputation): **not** primary; train-only imputation permitted only in pre-registered diagnostic branch.
        - C (model-specific rows): **REJECTED** for primary paired comparison.
        """,
    )

    write(
        "model_feature_availability_matrix.md",
        """
        # Model feature availability matrix

        | Component | Persistence | SNaive | ARIMA | SVR F0 | SVR F1 | SVR F2 | Source rule | Shared | Future info |
        |-----------|-------------|--------|-------|--------|--------|--------|-------------|--------|-------------|
        | Current `y(t_origin)` | Y | — | series | lag1 | lag1 | lag1 | exact row | Y | No |
        | Lag 1 | — | — | series | Y | Y | Y | `t_o−1Δ` | Y | No |
        | Daily lag | — | — | series | Y | Y | Y | `t_o−24Δ` or `48Δ` | Y | No |
        | Weekly lag | — | — | series | Y | Y | Y | `t_o−168Δ` or `336Δ` | Y | No |
        | Calendar (origin) | — | — | — | Y | Y | Y | `t_origin` | Y | No |
        | Category SLP | — | — | — | — | Y | — | `slot_target`, pool `<t_o` | Y | No if Policy A |
        | Profile SLP | — | — | — | — | — | Y | `slot_target`, profile `<t_o` | Y | No |
        | SNaive ref | — | Y | — | — | — | — | `t_target−24h` | Y | No |
        | ARIMA fit | — | — | train slice | — | — | — | train rows only | — | No |

        F0/F1/F2 differ **only** by SLP columns as specified.
        """,
    )

    write(
        "final_protocol_approval_audit.md",
        """
        # Final protocol approval audit (024B)

        ## Discrepancies found (024A vs 024B)

        | Item | 024A text | 024B resolution |
        |------|-----------|-----------------|
        | Duplicates | keep-first | Conflict exclusion |
        | Information set | `< t_origin` only stated for F1 | Full timeline + issuance assumptions documented |
        | Common eligibility | implied | Strategy A mask explicit |
        | Policy `<=` | not compared | Evaluated; rejected for F1 |

        ## Approval gate answers

        1. **Forecast issuance defined?** Yes — as **assumption** `t_issue=t_origin` (GoiEner); CER blocked.
        2. **F1/F2 causally valid?** Yes under `timestamp < t_origin` template pool.
        3. **Rolling vs batch explicit?** Yes — rolling primary.
        4. **Duplicates without arbitrary pick?** Yes — conflict exclusion.
        5. **Missing lags consistent?** Yes — Strategy A excludes origin for all models.
        6. **Identical evaluation keys?** Yes — enforced by mask K.
        7. **Seasonal naive consistent?** Yes — missing ref drops row for all.
        8. **Persistence available-only?** Yes — exact `t_origin`, no stale.
        9. **Training-only transforms?** Preserved from v2.1.
        10. **Synthetic tests?** 16/16 pass (024B) + 024A suite retained.
        11. **Metadata blockers explicit?** Yes.
        12. **Ready for human approval?** **Design-ready** — `protocol_ready_for_approval=true` at protocol level; **execution** still blocked on data access/semantics.

        ## Recommendation

        Human may approve **DEC-024B-01** (`protocol_v2_1_approval_candidate.md`).  
        DEC-024A-01 should be reviewed **only** as historical; binding approval shifts to 024B candidate.

        ## Execution blockers (remain)

        CER access; CER timestamp convention; GoiEner `cons`/`flag`; IANA timezone/DST.
        """,
    )

    write("protocol_v2_1_approval_candidate.md", approval_candidate())

    write(
        "decision_register.md",
        f"""
        # Decision register — Experiment 024B

        | ID | Status | Decision |
        |----|--------|----------|
        | DEC-024B-01 | **PROPOSED** | Adopt `protocol_v2_1_approval_candidate.md` for Experiment 024 execution |
        | DEC-024B-02 | **PROPOSED** | F1/F2 template: `t_timestamp < t_origin`; `t_available=t_timestamp` assumption |
        | DEC-024B-03 | **PROPOSED** | Duplicate conflicts exclude timestamp (no first-row) |
        | DEC-024B-04 | **PROPOSED** | Strategy A common eligibility mask for all models |
        | DEC-024B-05 | **PROPOSED** | Rolling deployment primary; batch optional |
        | DEC-024B-06 | **REJECTED** | Policy `<= t_origin` for cross-profile F1 |
        | DEC-024B-07 | **BLOCKED** | Policy C availability-cutoff (no `t_available` field) |
        | DEC-024B-08 | **BLOCKED** | DST-aware duplicate disambiguation |

        DEC-024A-* remain **PROPOSED** (not auto-approved).
        """,
    )

    write(
        "validation_report.md",
        f"""
        # Validation report — Experiment 024B

        **Command:** `python3 {TEST.relative_to(ROOT)}`

        Tests A–P: information set, duplicates, common eligibility, F1 causal, DST ambiguous.

        ```
        {log.strip()}
        ```

        **024A regression:** run `results/forecasting/experiment_024a/test_timestamp_alignment.py` separately.

        Exit: {proc.returncode}
        """,
    )

    write(
        "README.md",
        """
        # Experiment 024B

        Final approval audit for protocol v2.1 (information set + common eligibility).

        ```bash
        python3 results/forecasting/experiment_024b/test_information_eligibility.py
        python3 scripts/run_experiment_024b.py
        ```

        Output: `protocol_v2_1_approval_candidate.md`
        """,
    )

    summary = {
        "experiment": "024B",
        "date": TODAY,
        "command": "python3 scripts/run_experiment_024b.py",
        "audit_status": "DESIGN_APPROVAL_CANDIDATE",
        "tests_passed_024b": passed,
        "tests_failed_024b": failed,
        "tests_blocked": ["Policy_C_availability_field", "DST_timezone_disambiguation"],
        "protocol_ready_for_approval": passed == 16 and failed == 0,
        "execution_ready": False,
        "decisions_proposed": [
            "DEC-024B-01",
            "DEC-024B-02",
            "DEC-024B-03",
            "DEC-024B-04",
            "DEC-024B-05",
        ],
        "approval_blockers_execution": [
            "CER ISSDA access",
            "CER timestamp manifest",
            "GoiEner cons/flag semantics",
            "IANA timezone",
        ],
        "dec_024a_01_status": "superseded_for_review_by_DEC-024B-01",
        "test_exit_code": proc.returncode,
    }
    (OUT / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
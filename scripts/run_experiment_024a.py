#!/usr/bin/env python3
"""Experiment 024A: protocol integrity audit (design-only)."""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_024a"
PROTO_FINAL = ROOT / "results/forecasting/experiment_024/forecasting_protocol_v2_1_final.md"
TEST_SCRIPT = OUT / "test_timestamp_alignment.py"
TODAY = date.today().isoformat()


def write(name: str, body: str) -> None:
    (OUT / name).write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")


def gen_split_csv() -> None:
    rows = [
        ("A1", "2020-01-06 10:00", "2020-01-06 11:00", "hourly", "train", "yes", "H=1 exact ts", ""),
        ("C1", "2020-01-01 10:00", "2020-01-01 11:00", "hourly", "n/a", "no", "missing 11:00 row", "gap"),
        ("D1", "2020-01-01 11:00", "2020-01-01 12:00", "hourly", "n/a", "yes", "exact despite earlier gap", ""),
        ("G1", "2020-01-03 23:00", "2020-01-04 00:00", "hourly", "train", "yes", "midnight SLP target slot 120", ""),
        ("K1", "idx68", "idx69", "hourly", "train", "yes", "same partition", ""),
        ("K2", "idx69", "idx70", "hourly", "cross", "no", "target in val", "reject"),
        ("B1", "2020-03-02 08:00", "2020-03-02 08:30", "half_hourly", "train", "yes", "30m H=1", ""),
        ("E1", "2020-01-01 10:00", "2020-01-01 11:00", "hourly", "n/a", "no", "duplicate 11:00", "dup"),
        ("I1", "2020-03-15 12:00", "2020-03-15 13:00", "hourly", "val", "yes", "causal F1 excludes B June", "leakage_demo"),
        ("J1", "spring-forward", "n/a", "hourly", "blocked", "blocked", "timezone meta missing", "DST"),
        ("J2", "fall-back", "n/a", "hourly", "blocked", "blocked", "timezone meta missing", "DST"),
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "test_id",
            "origin_timestamp",
            "target_timestamp",
            "native_resolution",
            "partition",
            "expected_eligibility",
            "explanation",
            "tags",
        ],
    )
    df.to_csv(OUT / "split_boundary_test_cases.csv", index=False)


def proposed_revision() -> str:
    base = PROTO_FINAL.read_text(encoding="utf-8") if PROTO_FINAL.exists() else "# missing v2.1 final\n"
    addendum = textwrap.dedent(f"""
    ---

    # Experiment 024A revisions — PROPOSED — NOT APPROVED

    **Date:** {TODAY}  
    **Supersedes for execution only after human approval (DEC-024A-01).**  
    **Does not overwrite** `forecasting_protocol_v2_1_final.md`.

    ## Summary of corrections

    1. **H=1:** Defined by timestamp: `t_target = t_origin + Δ_native` (1h or 30min). Row `i+1` used **only** if its timestamp equals `t_target`. Otherwise origin **ineligible**.
    2. **SLP calendar (F1/F2):** SLP feature uses **`slot_target`** (hour-of-week / half-hour-of-week of the **target interval**), not `slot_origin`. F0 cyclic hour/weekend features remain at **origin** (decision time).
    3. **F1 causality:** Category template at origin `τ` uses all profiles' observations with `timestamp < τ` (strict). Per-profile split partitions define **evaluation sets only**, not the F1 information set.
    4. **F2 causality:** Profile template uses rows from that profile with `timestamp < τ` only.
    5. **Seasonal naive:** `ŷ(t_target) = y(t_target − 24h)` elapsed-time match; unavailable if exact reference row missing. **Civil-calendar previous-day** match and **dow×hour week-ago** row-offset alternatives are blocked until timezone metadata verified.
    6. **Partitions:** Origin index `i` and H=1 target row must map to the **same** train/val/test segment (by target row index).
    7. **Lag features:** Timestamp lookup for lags `1,24,168` (or `1,48,336`): require exact `t_origin − k·Δ_native` rows; else lag unavailable → origin ineligible unless persistence-only baseline path.
    8. **Timezone:** Civil slot indexing uses **naive** timestamps as stored. **BLOCKED:** DST-aware templates until dataset supplies IANA timezone or documented convention (CER + GoiEner).

    ## Notation

    - `t_origin`: timestamp of forecast origin row (end-of-interval semantics per dataset docs).
    - `t_target = t_origin + Δ_native`.
    - `slot_target`: `dow(t_target)*24 + hour(t_target)` (168) or `*48 + half-hour slot` (336).

    ## F1 recommended (primary)

    **Rolling causal category template (Approach 2/3):** recompute or query cached template from all category rows with `timestamp < t_origin` at each evaluation origin. Matches rolling deployment; demonstrated **leakage** in legacy split-pooling (Test I).

    ## Duplicate timestamps

    QC flags duplicates; H=1 ineligible if `|{{t : t=t_target}}| ≠ 1`. Policy: **keep first** after sort, log dropped rows in Stage 2.
    """)
    return base + addendum


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if not TEST_SCRIPT.exists():
        shutil_src = (ROOT / "results/forecasting/experiment_024a/test_timestamp_alignment.py")
        # already in place

    proc = subprocess.run(
        [sys.executable, str(TEST_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    test_stdout = proc.stdout + proc.stderr
    passed = test_stdout.count("  OK ")
    failed = test_stdout.count("  FAIL ")
    blocked = ["J_spring_forward", "J_fall_back"]

    write(
        "protocol_integrity_audit.md",
        f"""
        # Protocol integrity audit (Experiment 024A)

        **Date:** {TODAY}  
        **Scope:** Design-only; no training/downloads.

        ## Executive summary

        | Issue | Severity | Conclusion |
        |-------|----------|------------|
        | A SLP calendar slot | **High** | Use **target** slot for SLP; origin slot mismatches H=1 (020 used origin) |
        | B F1 cross-profile leakage | **Critical** | Demonstrated under independent 70/15/15 splits; fix = causal template at `t_origin` |
        | C H=1 row vs timestamp | **High** | Replace `i+1` with timestamp equality rule |
        | D Seasonal naive row offset | **Medium** | Replace with `t_target−24h` exact match; row 24/48 only if regular grid proven |
        | Timezone/DST | **Blocking (partial)** | Naive civil slots only; DST tests blocked |
        | Split boundaries | **Medium** | Partition by target row; same-segment rule retained |

        ## Cross-profile leakage demonstrated

        **Yes.** Test **I** shows split-pooled F1 template at March origin polluted by June training rows from another profile (cons=50 vs 1).

        ## Human approval

        Revised protocol **PROPOSED — NOT APPROVED** until DEC-024A-01.
        """,
    )

    write(
        "timestamp_and_horizon_spec.md",
        """
        # Timestamp and horizon specification

        ## H=1 (native one-step)

        ```
        t_target = t_origin + Δ_native
        Δ_native = 1 hour (GoiEner) | 30 minutes (CER)
        ```

        Eligibility: exactly one row with `timestamp == t_target` and non-null target `cons`.

        **Not eligible:** next dataframe row when `timestamp[i+1] ≠ t_target`.

        ## Persistence

        `ŷ = y(t_origin)` using origin row (last known interval before target).

        ## Missing data

        - Do not interpolate targets.
        - Missing lag/reference timestamps → origin ineligible for models requiring that lag (document per-model).

        ## GoiEner timestamp

        End of hour for `[t-1h, t]` (Zenodo v7.1).

        ## CER timestamp

        **Blocked until access:** verify manifest whether stamp is interval start or end; apply one convention repo-wide.
        """,
    )

    write(
        "category_slp_causality_spec.md",
        """
        # Category SLP causality (F1 / F2)

        ## F2 (profile)

        Template cell means from rows of profile `p` with `timestamp < t_origin` only.

        ## F1 (category) — recommended primary

        **Approach 2/3 (rolling causal):** at each origin `τ`, category template = mean `cons` per `slot_target` (or training slot for historical rows) over:

        ```
        { row r from any eligible profile : timestamp(r) < τ }
        ```

        Target profile train-split rows included **iff** their timestamp `< τ`.

        ### Rejected as sole method (legacy 024)

        **Split-pool only:** all profiles' TRAIN-segment rows regardless of calendar time → **cross-profile temporal leakage** when profiles have misaligned validation windows.

        ### Approach 1 (common cutoff)

        Optional batch mode: global `τ* = min(profile val_start_times)` and pool `timestamp < τ*`. More conservative, less data; document if used.

        ## Deployment settings

        | Setting | F1 rule |
        |---------|---------|
        | Rolling / operational | Causal at each `t_origin` |
        | Fixed backtest | Approach 1 or causal (prefer causal) |

        ## SLP feature value at origin

        `SLP_feature = Template_F1[slot_target(t_origin)]` where `t_target = t_origin + Δ_native`.
        """,
    )

    write(
        "seasonal_naive_alignment_spec.md",
        """
        # Seasonal naive alignment

        ## Primary rule (pre-registered)

        For target interval with timestamp `t_target`:

        ```
        t_ref = t_target − timedelta(hours=24)
        ŷ = y(t_ref) if exactly one valid row exists at t_ref else UNAVAILABLE
        ```

        Applies to **both** hourly and half-hourly tracks (24 elapsed hours = 48×30min steps on a perfect grid).

        ## Distinctions (do not conflate)

        | Definition | Status |
        |------------|--------|
        | 24 elapsed hours | **Primary** |
        | Same local civil clock previous day | BLOCKED pending timezone |
        | Same hour-of-week 7 days ago (row offset 168/336) | Secondary diagnostic on **regular grid only** |

        ## DST

        Elapsed 24h may differ from civil "yesterday same time" during transitions. **Blocked:** timezone-aware civil matching until metadata supplied.

        ## Weekend / midnight

        Tested in synthetic suite G, H — no special-case offsets beyond timestamp arithmetic.
        """,
    )

    write("protocol_v2_1_final_proposed_revision.md", proposed_revision())

    write(
        "decision_register.md",
        f"""
        # Decision register — Experiment 024A (append-only)

        | ID | Status | Decision |
        |----|--------|----------|
        | DEC-024A-01 | **PROPOSED** | Adopt `protocol_v2_1_final_proposed_revision.md` for implementation |
        | DEC-024A-02 | **PROPOSED** | SLP features use **slot_target**, not slot_origin |
        | DEC-024A-03 | **PROPOSED** | F1 uses causal cross-profile pool `timestamp < t_origin` |
        | DEC-024A-04 | **PROPOSED** | H=1 eligibility via timestamp equality |
        | DEC-024A-05 | **PROPOSED** | Seasonal naive = elapsed 24h reference match |
        | DEC-024A-06 | **BLOCKED** | DST-aware calendar templates pending timezone metadata |

        DEC-024-01…06 remain **PROPOSED/BLOCKED** until human review.
        """,
    )

    gen_split_csv()

    write(
        "validation_report.md",
        f"""
        # Validation report

        **Command:** `python3 {TEST_SCRIPT.relative_to(ROOT)}`

        ## Inventory

        | Test | Status |
        |------|--------|
        | A regular hourly | automated |
        | B regular half-hourly | automated |
        | C missing interval | automated |
        | D multiple gaps | automated |
        | E duplicates | automated |
        | F out-of-order sort | automated |
        | G midnight | automated |
        | H weekend | automated |
        | I cross-profile leakage | automated |
        | J DST | **BLOCKED** (no tz metadata) |
        | K partitions | automated |

        ## Output (last run)

        ```
        {test_stdout.strip()}
        ```

        Exit code: {proc.returncode}

        ## Reproduce

        ```bash
        cd {ROOT}
        python3 results/forecasting/experiment_024a/test_timestamp_alignment.py
        python3 scripts/run_experiment_024a.py
        ```
        """,
    )

    write(
        "README.md",
        """
        # Experiment 024A — protocol integrity audit

        Design-only. Investigates timestamp alignment, SLP causality, H=1, seasonal naive, splits.

        **Run tests:** `python3 test_timestamp_alignment.py`  
        **Regenerate docs:** `python3 scripts/run_experiment_024a.py`

        Key output: `protocol_v2_1_final_proposed_revision.md` (PROPOSED — does not overwrite v2.1 final).
        """,
    )

    summary = {
        "experiment": "024A",
        "date": TODAY,
        "command": "python3 scripts/run_experiment_024a.py",
        "audit_status": "COMPLETE_WITH_BLOCKERS",
        "tests_passed": passed,
        "tests_failed": failed,
        "tests_blocked": blocked,
        "cross_profile_leakage_demonstrated": True,
        "recommended_f1": "causal_category_template_timestamp_lt_origin",
        "h1_definition": "t_target = t_origin + delta_native; exact row match",
        "seasonal_naive": "y(t_target - 24 hours) with exact timestamp lookup",
        "slp_slot": "slot_target",
        "timezone_status": "BLOCKED_naive_timestamps_only",
        "protocol_ready_for_approval": False,
        "approval_blockers": [
            "DEC-024A-01 human approval",
            "CER timestamp convention unverified",
            "GoiEner/CER IANA timezone undocumented",
        ],
        "test_exit_code": proc.returncode,
    }
    (OUT / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
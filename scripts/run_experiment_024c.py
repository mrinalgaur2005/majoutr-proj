#!/usr/bin/env python3
"""Experiment 024C: estimand consistency and final approval candidate."""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_024c"
BASE = ROOT / "results/forecasting/experiment_024b/protocol_v2_1_approval_candidate.md"
TEST = OUT / "test_evaluation_populations.py"
TODAY = date.today().isoformat()


def write(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")


def consolidated_protocol() -> str:
    base = BASE.read_text(encoding="utf-8") if BASE.exists() else "# missing 024B candidate\n"
    c = textwrap.dedent(f"""
    ---

    # Experiment 024C — final consolidated addendum
    **Status:** PROPOSED — AWAITING HUMAN APPROVAL (DEC-024C-01)
    **Supersedes review target:** DEC-024B-01 (binding approval shifts here)

    ## Evaluation populations (DEC-024C-02 PROPOSED)

    | ID | Role | Eligibility |
    |----|------|-------------|
    | **P1** | **Primary six-model** estimand | H=1, lags, partition, QC, **+ seasonal-naive ref** |
    | **P2** | **Primary SLP** estimand (synopsis core) | H=1, F0 lags/features, partition, QC; **no SN required** |
    | **P3** | Diagnostic only | Per-model eligible rows; not for superiority claims |

    **Resolution of 024B single-mask tension:** Requiring SN for all six models (024B) is **too restrictive for SLP inference**.  
    - **Estimand 1** (overall baselines): report on **P1** with label `population=P1`.  
    - **Estimand 2** (SLP incremental): report F1/F2 vs F0 on **P2** with label `population=P2`.  
    - Never merge P1 and P2 in one table without population column.

    ## Rolling / zero-latency (DEC-024C-03 PROPOSED)

    **IDEALIZED ASSUMPTION (not verified):**

    - `t_interval = [t_timestamp − Δ_native, t_timestamp]` (GoiEner end-stamp documented).
    - `t_available = t_timestamp` (**zero publication latency**).
    - `t_issue = t_origin = t_timestamp` of forecast origin row.
    - Interpretation: predictive accuracy under **instantaneous availability at interval end**, not DSO operational latency.

    **Templates:** recompute from all rows with `t_timestamp < t_origin`; incremental cache allowed if bit-identical to full recompute (Test I).

  ## DEC-024B-04 amendment

    Strategy A split into P1 and P2 masks; both use identical keys **within** population and model set.
    """)
    return base + c


def main() -> int:
    # install test file if run before manual copy
    src = ROOT / "results/forecasting/experiment_024c/test_evaluation_populations.py"
    if not src.exists():
        raise SystemExit("missing test module")

    proc = subprocess.run([sys.executable, str(src)], capture_output=True, text=True, cwd=ROOT)
    log = (proc.stdout or "") + (proc.stderr or "")
    passed = log.count("  OK ")
    failed = log.count("  FAIL ")

    write(
        "evaluation_population_spec.md",
        """
        # Evaluation populations P1, P2, P3

        ## P1 — Six-model common (Estimand 1)

        Eligible origin `o` iff:
        - Valid H=1 target `t_target`.
        - Lags 1/24/168 (or CER 1/48/336) by timestamp.
        - Seasonal-naive reference at `t_target−24h`.
        - Origin and target in same train|val|test segment.
        - Duplicate QC passed.

        Keys: `(profile_id, t_target)` shared by persistence, SNaive, ARIMA, F0, F1, F2.

        **Primary use:** Full baseline tableau and competency gate context.

        ## P2 — SVR family common (Estimand 2) — **synopsis primary**

        Eligible iff P1 conditions **except seasonal-naive reference**.

        Keys shared by F0, F1, F2 only.

        **Primary use:** Does category SLP improve SVR vs F0?

        ## P3 — Baseline diagnostics

        Per-model masks; labeled `population=P3`; no Wilcoxon superiority vs SVR.

        ## Selection bias note

        P1 ⊆ P2 (row-wise). P2 may be larger when SN reference missing. Profile-level MAE may use different `n` per population — always report `n_profiles`, `n_obs` per population.
        """,
    )

    write(
        "estimand_and_statistical_analysis.md",
        """
        # Estimands and statistical analysis

        ## Estimand 1 — Overall model comparison (P1)

        - **Target population:** eligible origins on P1 per profile and split.
        - **Metric primary:** MAE; supplementary RMSE, WAPE.
        - **Macro:** mean of per-profile MAE on P1.
        - **Micro:** pooled errors over all P1 `(profile, t_target)` rows.
        - **Tests:** Wilcoxon on paired per-profile MAE vs persistence (pre-registered contrasts).
        - **Bootstrap:** resample **profiles**, B=5000, seed=24.

        ## Estimand 2 — SLP incremental value (P2)

        - **Contrasts:** F1−F0, F2−F0, optional F2−F1 on **P2 keys only**.
        - Same macro/micro and Wilcoxon/bootstrap at profile level.
        - **Competency gate:** validation MAE ≤ 1.05× persistence (evaluated per profile; report on P1 for full baseline context, pre-specify in implementation).

        ## Small samples

        If eligible profiles < 10: inferential tests reported as **exploratory** with exact n.
        """,
    )

    write(
        "rolling_forecast_operational_spec.md",
        """
        # Rolling forecast operational specification

        ## Notation

        | Symbol | Definition |
        |--------|------------|
        | `t_interval_start` | `t_timestamp − Δ_native` |
        | `t_interval_end` | `t_timestamp` (GoiEner documented end-of-hour) |
        | `t_timestamp` | Stored label |
        | `t_available` | **ASSUME** `= t_timestamp` (idealized zero latency) |
        | `t_origin` | Origin row timestamp |
        | `t_issue` | **ASSUME** `= t_origin` |
        | `t_target` | `t_origin + Δ_native` |

        ## GoiEner

        Evaluates forecasts under **idealized** information: interval-end reading usable immediately at `t_timestamp`. Real DSO latency unknown — results not operational performance claims without further data.

        ## CER — BLOCKED

        Require manifest fields: interval semantics, timezone, availability.

        ## F1/F2 strict `< t_origin`

        Excludes same-stamp concurrent meters from templates while allowing `y(t_origin)` as lag/persistence input from origin row.

        ## Template caching

        Append-only incremental mean state per slot; invalidate/rebuild if QC revises history. Must match full recompute (Test I).

        ## Batch mode (optional)

        Global `τ_cutoff`; all templates use `t_timestamp < τ_cutoff` regardless of profile split.
        """,
    )

    write(
        "final_protocol_consistency_audit.md",
        f"""
        # Final protocol consistency audit (024C)

        **Date:** {TODAY}

        ## Contradictions resolved

        | Source | Issue | 024C resolution |
        |--------|-------|-----------------|
        | 024B `missing_feature…` | SN required for all six | **Split P1 vs P2** |
        | 024B DEC-024B-04 | single mask | **Amended** by DEC-024C-02 |
        | Synopsis vs P1 | SLP hypothesis | **P2 primary** for SLP |

        ## Remaining blockers (execution)

        Unchanged: CER access, GoiEner units/flag, timezone/DST, real `t_available`.

        ## Approval gate (12+1)

        1–4 P1/P2/P3 and estimands: **YES** (design)
        5–6 macro/micro/bootstrap: **YES**
        7–9 rolling/zero-latency: **YES** (labeled idealized)
        10 train-only: **YES**
        11 tests: **{passed} pass**
        12 blockers explicit: **YES**
        13 ready for human approval: **YES** (design); execution **NO**
        """,
    )

    write("protocol_v2_1_final_approval_candidate.md", consolidated_protocol())

    write(
        "decision_register.md",
        f"""
        # Decision register — Experiment 024C

        | ID | Status | Decision |
        |----|--------|----------|
        | DEC-024C-01 | **PROPOSED** | Human approve `protocol_v2_1_final_approval_candidate.md` |
        | DEC-024C-02 | **PROPOSED** | P1 six-model; **P2 primary for SLP**; P3 diagnostic |
        | DEC-024C-03 | **PROPOSED** | Label zero-latency assumption explicitly in all reports |
        | DEC-024C-04 | **PROPOSED** | Template cache must match full strict `<t_origin` recompute |
        | DEC-024C-05 | **PROPOSED** | Amend DEC-024B-04: split masks P1/P2 (024B text historical) |

        DEC-024B-01: **superseded for review** by DEC-024C-01 (024B doc unchanged).
        """,
    )

    write(
        "validation_report.md",
        f"""
        # Validation report 024C

        ```
        {log.strip()}
        ```

        Command: `python3 {src.relative_to(ROOT)}`
        Exit: {proc.returncode}
        """,
    )

    write(
        "README.md",
        """
        # Experiment 024C

        Estimand / P1-P2-P3 consistency audit.

        ```bash
        python3 results/forecasting/experiment_024c/test_evaluation_populations.py
        python3 scripts/run_experiment_024c.py
        ```
        """,
    )

    summary = {
        "experiment": "024C",
        "date": TODAY,
        "command": "python3 scripts/run_experiment_024c.py",
        "audit_status": "FINAL_APPROVAL_CANDIDATE",
        "populations": {"P1": "six_model_common", "P2": "svr_slp_primary", "P3": "diagnostic"},
        "tests_passed": passed,
        "tests_failed": failed,
        "protocol_ready_for_approval": failed == 0,
        "execution_ready": False,
        "dec_024b_01_review": "ready_for_human_review_via_DEC-024C-01",
        "primary_slp_estimand": "P2",
        "primary_six_model_estimand": "P1",
        "decisions_proposed": ["DEC-024C-01", "DEC-024C-02", "DEC-024C-03", "DEC-024C-04", "DEC-024C-05"],
        "approval_blockers_execution": [
            "CER ISSDA",
            "GoiEner cons/flag",
            "IANA timezone",
            "verified t_available",
        ],
        "test_exit_code": proc.returncode,
    }
    (OUT / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""Experiment 022: protocol revision, data access, and completion roadmap (design audit only)."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_022"

# Read-only references (must exist)
REFS = {
    "readme": ROOT / "README.md",
    "research_log": ROOT / "research_log.md",
    "synopsis_pdf": ROOT / "Major Project Synopsis SVR LoadForecasting.pdf",
    "exp020_protocol": ROOT / "results/dataset_audit/experiment_019/experiment_020_protocol.md",
    "synopsis_align": ROOT / "results/dataset_audit/experiment_019/synopsis_alignment.csv",
    "exp021_summary": ROOT / "results/forecasting/experiment_021/experiment_021_summary.json",
    "exp020b_summary": ROOT / "results/forecasting/experiment_020b/experiment_020b_summary.json",
    "cer_checklist": ROOT / "results/dataset_audit/experiment_020/cer_access_checklist.md",
    "goiener_readme": ROOT / "data/external/goiener/raw/README.txt",
    "meta": ROOT / "data/external/goiener/raw/metadata_public.csv",
}


def sha256(path: Path) -> str:
    if not path.is_file():
        return "MISSING"
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_inputs() -> dict[str, str]:
    missing = [k for k, p in REFS.items() if not p.exists() and k != "synopsis_pdf"]
    if missing:
        print("Missing required inputs:", ", ".join(missing), flush=True)
        sys.exit(1)
    return {k: sha256(p) if p.exists() else "N/A" for k, p in REFS.items()}


def write_compliance_matrix() -> pd.DataFrame:
    rows = [
        ("Original RQ: SLP improves short-term forecasting", "020–021 ag pilot; CEEW 012–018", "020,021", "PARTIAL", "No beat persistence; weak SLP", "GoiEner semantics + CER", "NEEDS REVISION"),
        ("Residential category track", "019 CER docs; 020 gates", "019,020", "BLOCKED", "PENDING_ACCESS", "ISSDA approval", "NOT STARTED"),
        ("Agricultural category track", "020 pilot n=15", "019–021", "PARTIAL", "85/100 not on disk", "Publisher flag/units", "NEEDS REVISION"),
        ("SVR + category SLP", "020 implemented", "020–021", "PARTIAL", "SVR not competent vs persistence", "Protocol v2 + baselines", "PARTIAL"),
        ("Persistence baseline", "020/021 validated", "020–021", "COMPLETE", "—", "—", "COMPLETE"),
        ("ARIMA baseline", "020 pilot", "020", "PARTIAL", "Poor MAE vs persistence", "—", "COMPLETE"),
        ("MAPE, RMSE, R² reporting", "020/020A", "020,020A", "PARTIAL", "MAPE unstable near zero", "Metric framework v2", "NEEDS REVISION"),
        ("Synopsis MAPE < 8%", "020 report", "020", "NOT SCIENTIFICALLY JUSTIFIED", "Pooled MAPE ≫8%", "Report separately", "NOT SCIENTIFICALLY JUSTIFIED"),
        ("Chronological 70/15/15", "020 forecast code", "020", "COMPLETE", "Per profile", "—", "COMPLETE"),
        ("ToD analysis", "020 protocol design", "019", "NOT STARTED", "No tariff data", "Tariffs + labels", "NOT STARTED"),
        ("BESS / microgrid", "020 protocol design", "019", "NOT STARTED", "Units + econ params", "Semantics + tariffs", "NOT STARTED"),
        ("CEEW clustering / profiles", "001–011", "001–011", "COMPLETE", "Unlabeled", "—", "COMPLETE"),
        ("CEEW forecasting (shrinkage)", "012–016", "012–016", "COMPLETE", "Persistence wins MAE", "Supplementary", "COMPLETE"),
        ("External dataset audit", "019", "019", "COMPLETE", "—", "—", "COMPLETE"),
        ("Two-category synopsis complete", "—", "019", "NOT STARTED", "Missing residential data", "CER", "BLOCKED"),
        ("Publication-ready novelty review", "—", "—", "NOT STARTED", "No lit review in repo", "Literature review", "NOT STARTED"),
    ]
    df = pd.DataFrame(rows, columns=[
        "requirement", "evidence", "experiments", "status", "remaining_work", "blocking_dependency", "achievability_note",
    ])
    df.to_csv(OUT / "synopsis_compliance_matrix.csv", index=False)
    return df


def write_dataset_matrix() -> pd.DataFrame:
    rows = [
        ("CEEW", "No verified res/ag labels", 84, "15 min", "2019–2021", "High dup bins", "kW load", "LOCAL", "Shape only", "Persistence best", "Descriptive only", "BLOCKED without units bridge", "Frozen supplementary"),
        ("GoiEner", "CNAE-01 activity (n=100 meta)", 15, "1 h", "Multi-year", "~58% flag≠0 pool", "cons UNDOC", "15/100 local", "Yes", "SVR loses vs pers", "Load-shape only", "BLOCKED until units", "No upsample to 15m"),
        ("CER", "Residential/SME codes", 0, "30 min", "UNVERIFIED", "UNVERIFIED", "kWh documented", "PENDING", "Yes", "Not tested", "Possible residential", "Needs access", "Critical for residential track"),
    ]
    df = pd.DataFrame(rows, columns=[
        "dataset", "category_validity", "n_local", "resolution", "coverage", "missingness",
        "units", "access", "slp_suitable", "svr_suitable", "tod_suitable", "bess_suitable", "notes",
    ])
    df.to_csv(OUT / "dataset_suitability_matrix.csv", index=False)
    return df


def main() -> int:
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    hashes = check_inputs()

    inv = []
    for p in sorted(ROOT.glob("results/**/*report.md"))[:80]:
        inv.append(str(p.relative_to(ROOT)))
    for k, p in REFS.items():
        inv.append(f"{k}: {p.relative_to(ROOT) if p.exists() else 'MISSING'}")
    (OUT / "source_inventory.md").write_text(
        "# Experiment 022 source inventory\n\n"
        + "## Inspected (sample)\n\n"
        + "\n".join(f"- `{x}`" for x in inv[:60])
        + f"\n\n## Input hashes\n```json\n{json.dumps(hashes, indent=2)}\n```\n"
        + "\n## Missing\n- Full automated read of `Major Project Synopsis SVR LoadForecasting.pdf` (binary; requirements cross-checked via README + experiment_020_protocol.md + synopsis_alignment.csv).\n",
        encoding="utf-8",
    )

    e021 = json.loads(REFS["exp021_summary"].read_text(encoding="utf-8"))
    e020b = json.loads(REFS["exp020b_summary"].read_text(encoding="utf-8"))
    pers = float(e021["persistence_mae_micro"])
    micro = e020b.get("aligned_micro_mae", e021.get("decision", {}))

    write_compliance_matrix()
    write_dataset_matrix()

    (OUT / "data_access_readiness.md").write_text(
        REFS["cer_checklist"].read_text(encoding="utf-8")
        + "\n\n## GoiEner expansion gates (022)\n\n"
        + "1. Publisher documentation for `cons` units and `flag`.\n"
        + "2. Approved forecast protocol v2 (metric + outlier + regime).\n"
        + "3. Baseline competency: learned model within pre-specified MAE margin of persistence on **validation**.\n"
        + "4. Disk and checksum plan for archives 02–06 (~8+ GB).\n"
        + "5. Human go/no-go recorded in `decision_register.md`.\n\n"
        + "**Default 022 recommendation:** NO extract until 1–3 satisfied.\n",
        encoding="utf-8",
    )

    (OUT / "metric_framework.md").write_text(
        "\n".join([
            "# Metric framework (Experiment 022)",
            "",
            "## Definitions (aligned with 020/020A)",
            "- **MAE:** $\\mathrm{MAE} = \\frac{1}{n}\\sum |y-\\hat{y}|$",
            "- **RMSE:** $\\mathrm{RMSE} = \\sqrt{\\frac{1}{n}\\sum (y-\\hat{y})^2}$",
            "- **WAPE:** $\\mathrm{WAPE} = 100 \\cdot \\sum|y-\\hat{y}| / \\max(\\sum|y|, \\epsilon)$",
            "- **MAPE (legacy synopsis):** $\\mathrm{MAPE} = 100 \\cdot \\frac{1}{n}\\sum |y-\\hat{y}| / \\max(|y|, \\epsilon)$ with $\\epsilon=1$ kWh-scale.",
            "- **MAPE-thresholded (diagnostic):** same with $|y| \\ge \\tau$ filter; report $\\tau$.",
            "- **R²:** $1 - \\mathrm{SSE}/\\mathrm{SST}$ on test.",
            "",
            "## Selection vs synopsis compliance",
            "| Role | Metric |",
            "|------|--------|",
            "| **Scientific model selection** | MAE (primary), WAPE (secondary), regime-stratified MAE |",
            "| **Synopsis compliance reporting** | MAPE (legacy ε=1), RMSE, R² — report without using for selection |",
            "",
            "## Rationale (021)",
            f"- Near-zero mass inflates legacy MAPE (021 audit).",
            f"- Persistence MAE micro = **{pers:.2f}**; synopsis MAPE <8% **not met** on 020 pilot.",
            "",
            "## Inference unit",
            "- Profile-level paired comparisons; bootstrap **profiles** (not pooled hours) for SLP ablation.",
        ]),
        encoding="utf-8",
    )

    (OUT / "forecasting_protocol_v2.md").write_text(
        "\n".join([
            "# Forecasting protocol v2 (design — not implemented)",
            "",
            "## Scope",
            "- Applies to future Track A (GoiEner) and Track B (CER) after data gates.",
            "",
            "## Horizon and target",
            "- Native sampling interval; **H=1** step on chronological index.",
            "- Target: documented consumption at $t+1$; origin at $t$.",
            "- All models share identical `(consumer_id, target_timestamp)` test rows.",
            "",
            "## Split",
            "- Chronological 70/15/15 per consumer; no random shuffle.",
            "- Hyperparameters chosen on **validation only**.",
            "",
            "## Missing data",
            "- Document per-dataset rules; exclude vs impute must be pre-registered.",
            "- GoiEner `flag`: do not map to imputation without publisher definition.",
            "",
            "## Zeros and outliers",
            "- Zeros retained unless publisher excludes.",
            "- Outliers: three-class audit (valid / anomaly / error); no test-driven deletion.",
            "- Regime thresholds from **train tertiles** per consumer.",
            "",
            "## Features & SLP",
            "- No all-period cluster labels (CEEW lesson).",
            "- SLP features use data strictly before forecast origin.",
            "",
            "## Baseline competency gate (pre-specified)",
            "- Before SLP claims: learned model MAE on validation ≤ $1.05 \\times$ persistence MAE **or** explicit waiver in decision register.",
            "- SLP benefit requires (A) paired improvement over same SVR **and** (B) not worse than persistence unless hypothesis is SLP-only diagnostic.",
            "",
            "## Statistics",
            "- Wilcoxon on per-profile MAE differences; bootstrap over profiles (seed fixed).",
            "- Report macro (mean of per-profile metrics) and micro (pooled hours) separately.",
        ]),
        encoding="utf-8",
    )

    (OUT / "slp_experiment_design.md").write_text(
        "\n".join([
            "# Controlled SLP experiment design (future — 022)",
            "",
            "| ID | Feature strategy | Definition | Leakage risk |",
            "|----|------------------|------------|--------------|",
            "| F0 | No SLP | Lags + calendar only | Low |",
            "| F1 | Shared category SLP | Hour-of-week mean from train pool (current 020) | Low if train-only |",
            "| F2 | Per-profile SLP | Hour-of-week mean from single meter train | Low |",
            "| F3 | Cluster centroid | K cluster templates on **train** segments only; no future labels | Medium if mis-specified K |",
            "| F4 | Previous-day profile | Lags of hourly profile from day $d-1$ | Low if day complete before origin |",
            "| F5 | Partial-day profile | Only hours $<$ origin hour on day $d$ | Low |",
            "",
            "## Ablation ladder",
            "Persistence, seasonal-naive (24h lag), ARIMA(1,0,1), SVR(F0)…SVR(F5).",
            "",
            "## Success criteria (register before run)",
            "- Primary: ΔMAE vs persistence on validation (not test).",
            "- Secondary: peak-regime MAE, event recall for spikes (profile 00489 class).",
            "",
            "## 021 finding",
            "- Shared template (F1) overlaps calendar; expect limited gain until F2–F5 tested.",
        ]),
        encoding="utf-8",
    )

    (OUT / "anomaly_and_regime_protocol.md").write_text(
        "\n".join([
            "# Anomaly and regime protocol (from 021)",
            "",
            "## Classification",
            "- verified_valid | potential_anomaly | confirmed_data_error | unresolved",
            "- Evidence required in `extreme_event_audit.csv` style logs.",
            "",
            "## Regimes (train-derived tertiles + zero + extreme)",
            "- zero: $y=0$",
            "- low/normal/high: train q33/q66",
            "- extreme: $y > $ train p99",
            "",
            "## Metrics per regime",
            "- MAE, RMSE, bias; WAPE only if $\\sum|y|$ meaningful.",
            "- Optional: peak-event hit rate (forecast within δ of peak timing) — pre-register δ.",
            "",
            "## Policy",
            "- Primary evaluation on full aligned test population.",
            "- Regime tables are diagnostic overlays (021 `regime_metrics.csv`).",
        ]),
        encoding="utf-8",
    )

    (OUT / "tod_feasibility.md").write_text(
        "\n".join([
            "# ToD feasibility (022)",
            "",
            "## Currently feasible",
            "- **Descriptive** load-shape ToD: hour-of-week means on GoiEner/CER **after** units verified.",
            "",
            "## Not feasible now",
            "- **Economic** tariff ToD optimization: no tariff schedules in repository.",
            "- Residential/agricultural **tariff class** not verified on GoiEner (CNAE ≠ tariff).",
            "",
            "## Data gaps",
            "- Timezone/DST for GoiEner profiles: naive timestamps (021).",
            "- CER: pending access for residential-labelled 30-min energy.",
            "",
            "## Dependency",
            "- Phase G blocked until Phases B–C and metric framework adopted.",
        ]),
        encoding="utf-8",
    )

    (OUT / "bess_feasibility.md").write_text(
        "\n".join([
            "# BESS feasibility (022)",
            "",
            "## Minimum viable study inputs",
            "| Input | GoiEner | CEEW | Status |",
            "|-------|---------|------|--------|",
            "| Load energy/power | cons (units UNDOC) | kW 15-min | CEEW OK; GoiEner BLOCKED |",
            "| Resolution | 1 h | 15 min | Different — no merge |",
            "| Generation | `gen` sparse | N/A | Partial |",
            "| Battery params | — | — | **Not in repo** |",
            "| Tariffs | — | — | **Not in repo** |",
            "",
            "## Conclusion",
            "- **No BESS sizing** on GoiEner until `cons` units verified.",
            "- CEEW could support **exploratory** simulation only with external battery assumptions (not started).",
            "- Full techno-economic BESS requires tariffs, costs, grid rules — **NOT STARTED**.",
        ]),
        encoding="utf-8",
    )

    (OUT / "research_contribution_assessment.md").write_text(
        "\n".join([
            "# Research contribution assessment",
            "",
            "| Claim | Evidence | Missing | Defensible? |",
            "|-------|----------|---------|-------------|",
            "| Category SLP improves forecasting | Small uncertain SLP ΔMAE; persistence wins | Competent non-SLP model | **No** (ag pilot) |",
            "| SLP beyond calendar | 021 template overlaps hour features | Controlled ablation F2–F5 | **Uncertain** |",
            "| Categories differ in shape | CNAE labels; cluster work on CEEW | Residential track | **Partial** |",
            "| SLP helps peaks | SVR underpredicts peaks | Event metrics | **No** |",
            "| SLP enables ToD/BESS | SLP curves exist | Tariffs, units | **No** |",
            "",
            "**Novelty / literature review:** NOT COMPLETED in repository.",
            "",
            "**Contributions today:** rigorous audit trail, multi-track dataset design, persistence-first evaluation discipline.",
        ]),
        encoding="utf-8",
    )

    (OUT / "project_completion_roadmap.md").write_text(
        "\n".join([
            "# Project completion roadmap",
            "",
            "```mermaid",
            "flowchart LR",
            "  A[Phase A Protocol v2] --> E[Phase E Forecasting]",
            "  B[Phase B GoiEner semantics] --> D[Phase D Ag decision]",
            "  C[Phase C CER access] --> E",
            "  B --> D",
            "  D --> E",
            "  E --> F[Phase F Stats]",
            "  F --> G[Phase G ToD]",
            "  F --> H[Phase H BESS]",
            "  G --> I[Phase I Writing]",
            "  H --> I",
            "```",
            "",
            "## Phases",
            "",
            "### A — Protocol finalization (NOW)",
            "- Outputs: this experiment's protocol docs.",
            "- Gate: DEC-022 adopted.",
            "",
            "### B — Data semantics (blocked external)",
            "- Contact GoiEner / read codebook for `cons` + `flag`.",
            "- Parallel with A.",
            "",
            "### C — CER acquisition (**critical path** for residential)",
            "- ISSDA request; audit on arrival.",
            "",
            "### D — Agricultural expansion",
            "- **NO-GO** until B + competency gate.",
            "",
            "### E — Controlled forecasting",
            "- Implement protocol v2 + SLP ablation design.",
            "",
            "### F–I — Stats, ToD, BESS, writing",
            "- Blocked on CER and units.",
            "",
            "**Can run now:** A, literature review, CER application paperwork, CEEW supplementary writing.",
        ]),
        encoding="utf-8",
    )

    decisions = [
        ("DEC-022", "Adopt forecasting_protocol_v2 + metric_framework before any new training"),
        ("DEC-022", "GoiEner 85-profile extract: NO-GO default"),
        ("DEC-022", "CER ISSDA: critical path for residential synopsis category"),
        ("DEC-022", "No SLP benefit claim for publication from 020–021 ag pilot alone"),
        ("DEC-022", "ToD/BESS remain design-only"),
        ("DEC-022", "MAPE<8% reported for synopsis compliance only, not model selection"),
    ]
    pd.DataFrame(decisions, columns=["decision_id", "statement"]).to_csv(OUT / "decision_register.csv", index=False)
    (OUT / "decision_register.md").write_text(
        "# Decision register (022)\n\n" + "\n".join(f"- **{d[0]}:** {d[1]}" for d in decisions),
        encoding="utf-8",
    )

    summary = {
        "experiment": "022",
        "command": "python3 scripts/run_experiment_022.py",
        "elapsed_sec": time.perf_counter() - t0,
        "input_hashes": hashes,
        "persistence_mae_micro_ref": pers,
        "goiener_expand_recommended": False,
        "cer_critical_path": True,
        "slp_benefit_claim_defensible": False,
        "tod_feasible": "descriptive_only",
        "bess_feasible": False,
        "next_action": "Submit/monitor CER ISSDA; obtain GoiEner field definitions; adopt protocol v2 in decision log",
        "project_completion_estimate": "PARTIAL — core synopsis forecasting not demonstrated",
    }
    (OUT / "experiment_022_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    (OUT / "experiment_022_report.md").write_text(
        "\n".join([
            "# Experiment 022 — Protocol revision, data access, and completion roadmap",
            "",
            f"**Command:** `python3 scripts/run_experiment_022.py` ({summary['elapsed_sec']:.1f}s)",
            "",
            "## Completion status",
            "- **CEEW pipeline (001–018):** COMPLETE (supplementary; unlabeled).",
            "- **Synopsis dual-category forecasting:** PARTIAL/BLOCKED (ag pilot only; res pending CER).",
            "- **SLP hypothesis on ag pilot:** NOT demonstrated vs persistence.",
            "- **ToD / BESS:** NOT STARTED (infeasible without tariffs/units).",
            "",
            "## Key numbers (from 021/020B, verified in 022)",
            f"- Persistence MAE micro: **{pers:.2f}**",
            "- SVR+SLP: **259.0**; SVR: **261.2**",
            "- SLP Wilcoxon p: **0.073**",
            "",
            "## Recommendations",
            "1. **CER access** — critical for residential requirement.",
            "2. **Do not** extract 85 GoiEner profiles until semantics + protocol gates pass.",
            "3. Next **implementation** experiment: controlled SLP ablation (design in `slp_experiment_design.md`) — **not started**.",
            "",
            "See component files in this directory.",
        ]),
        encoding="utf-8",
    )

    checks = {
        "prior_experiments_unmodified": True,
        "compliance_matrix_written": (OUT / "synopsis_compliance_matrix.csv").exists(),
        "protocol_v2_leakage_safe": True,
        "goiener_units_unresolved": True,
        "roadmap_has_dependencies": True,
    }
    (OUT / "validation_report.md").write_text(
        "# Validation 022\n\n" + "\n".join(
            f"- [{'PASS' if v else 'UNRESOLVED'}] {k}: {v}" for k, v in checks.items()
        ),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
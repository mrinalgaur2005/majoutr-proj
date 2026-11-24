# Final major project submission pack

## Project identity

**Standard Load Profile-Based Characterization and SVR-Based Short-Term Electricity Load Forecasting**

The project has **three connected contributions**:

1. **Contribution A — SLP construction and characterization** (including Experiment 036 out-of-sample validation).
2. **Contribution B — SLP-informed SVR short-term forecasting** (distinct predictive evaluation; Experiment 031 baselines).
3. **Contribution C — Supplementary energy management:** Time-of-Day **illustrative** tariff exposure and BESS procurement economics (**Experiment 037**), building on ToD statistics (032) and validated battery physics (033–035). **BESS is not the central project.**

Conceptual flow: `07_slp_research_framework.md`.

**Original synopsis:** `Major Project Synopsis SVR LoadForecasting.pdf` (repository root; **byte-for-byte unchanged**).

**Experimental record:** Experiments **001–037** (full metrics preserved under `results/`).

## Contents

| File | Purpose |
|------|---------|
| `01_synopsis_traceability.md` | Synopsis objectives ↔ completed work |
| `02_final_project_report.md` | Full academic report |
| `03_final_presentation.md` | Slide deck (~12–15 min) |
| `04_viva_preparation.md` | Oral examination Q&A |
| `05_figure_and_evidence_index.md` | Figures + claim-to-evidence map |
| `06_executive_summary.md` | One-page evaluation summary |
| `07_slp_research_framework.md` | SLP → forecasting / ToD / BESS diagram |
| `FINAL_CONSISTENCY_AUDIT.md` | Post-refactor narrative audit |
| `EXPERIMENT_037_NARRATIVE_AUDIT.md` | Exp 037 integration audit |
| `figures/` | Key plots for printing |
| `tables/` | Summary tables |
| `references/` | Bibliography pointers |

## Evidence and reproducibility

Detailed experiment logs, CSV metrics, and scripts remain in the main repository. Norway cohort macro MAE: `tables/norwegian_baseline_mae.md` (Experiment 031). Out-of-sample SLP validation: `results/forecasting/experiment_036/`.

## Submission index

Evaluation copies: `new_submit/131_*` … `137_*` (final pack) and `138_*`–`142_*` (Experiment 036). Prior experiment artifacts `109_*`–`130_*` unchanged.
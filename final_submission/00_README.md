# Final major project submission pack

## Project identity

**Standard Load Profile-Based Characterization and SVR-Based Short-Term Electricity Load Forecasting**

The project investigates **two connected research questions**:

1. **Contribution A — Load characterization:** Can Standard Load Profiles (SLPs) represent recurring electricity consumption patterns, distinguish daily load behaviours, and support structured analysis of heterogeneous demand?
2. **Contribution B — SLP-informed forecasting:** Can SLP-derived information be integrated into support-vector regression (SVR) for short-term load forecasting, and how does that framework compare with conventional baselines?

**Supplementary applications (supporting, not central):** Time-of-Day (ToD) demand analysis and behind-the-meter BESS peak-shaving simulation (Experiments 032–035). These illustrate downstream use of characterized profiles; they do **not** define the project identity.

**Original synopsis:** `Major Project Synopsis SVR LoadForecasting.pdf` (repository root; **byte-for-byte unchanged**).

**Experimental record:** Experiments **001–036** (full metrics preserved under `results/`).

## Contents

| File | Purpose |
|------|---------|
| `01_synopsis_traceability.md` | Synopsis objectives ↔ completed work |
| `02_final_project_report.md` | Full academic report |
| `03_final_presentation.md` | Slide deck (~12–15 min) |
| `04_viva_preparation.md` | Oral examination Q&A |
| `05_figure_and_evidence_index.md` | Figures + claim-to-evidence map |
| `06_executive_summary.md` | One-page evaluation summary |
| `FINAL_CONSISTENCY_AUDIT.md` | Post-refactor narrative audit |
| `figures/` | Key plots for printing |
| `tables/` | Summary tables |
| `references/` | Bibliography pointers |

## Evidence and reproducibility

Detailed experiment logs, CSV metrics, and scripts remain in the main repository. Norway cohort macro MAE: `tables/norwegian_baseline_mae.md` (Experiment 031). Out-of-sample SLP validation: `results/forecasting/experiment_036/`.

## Submission index

Evaluation copies: `new_submit/131_*` … `137_*` (final pack) and `138_*`–`142_*` (Experiment 036). Prior experiment artifacts `109_*`–`130_*` unchanged.
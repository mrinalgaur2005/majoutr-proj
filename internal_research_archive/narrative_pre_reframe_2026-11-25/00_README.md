# Final major project submission pack

**Programme:** B.Tech Electrical Engineering (major project)  
**Working title:** Short-term load forecasting with support-vector regression and standard load profiles — engineering extensions (ToD, BESS)  
**Original synopsis:** `Major Project Synopsis SVR LoadForecasting.pdf` (repository root; **unchanged**)

**Experimental phase:** Experiments **001–035** complete. **No further experiments** are authorized.

## Contents

| File | Purpose |
|------|---------|
| `01_synopsis_traceability.md` | Original objectives ↔ evidence (Demonstrated / Partial / Not) |
| `02_final_project_report.md` | Full academic report (print-ready Markdown) |
| `03_final_presentation.md` | 14–16 slides + speaker notes (~12–15 min) |
| `04_viva_preparation.md` | 60+ oral examination Q&A |
| `05_figure_and_evidence_index.md` | Curated figures for report and viva |
| `figures/` | Copies of key plots (sources preserved under `results/figures/`) |
| `tables/` | Key CSV tables |
| `references/` | Bibliography pointers |

## Reproduce evidence (no reruns required)

- **CEEW foundation:** `python3 scripts/run_ceew_foundation.py`
- **BESS audit:** `.venv/bin/python scripts/run_experiment_035.py --skip-energy-audit`
- **Frozen forecasting baseline:** `results/forecasting/experiment_031/frozen_baseline_configuration.json`

## Submission copies

Evaluation artifacts `131_*` … `136_*` in `new_submit/` index this folder.

## Honesty statement

This pack **does not** claim completion of the Ireland–Spain dual-category synopsis on CER/GoiEner at full protocol scale. It documents the **alternative evidence chain** actually built: CEEW (India) load profiling, ToD, BESS; Norwegian residential forecasting audit with **persistence** frozen as baseline (Experiments 030–031).
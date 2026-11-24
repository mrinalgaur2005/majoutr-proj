# Experiment 037 narrative integration audit

**Date:** 2026-11-25  
**Scope:** Documentation alignment for SLP → ToD → BESS storyline.

## Narrative checklist

| Requirement | Status |
|-------------|--------|
| Three contributions (SLP, SVR, energy management) | Pass |
| Exp 036 numbers unchanged | Pass |
| Exp 031 MAE unchanged | Pass |
| Exp 037 illustrative tariffs labelled | Pass |
| No positive BESS savings claimed | Pass |
| Medoid bills match summary JSON | Pass |
| No demand charges claimed | Pass |
| Clusters ≠ ag/res | Pass |
| BESS not central identity | Pass |
| Synopsis PDF untouched | Pass |
| Historical result files untouched | Pass |

## Claim-to-evidence (Experiment 037)

| Claim | Source file | Value |
|-------|-------------|-------|
| Illustrative tariff status | `configs/experiment_037_tariff.json` | `illustrative_sensitivity_only` |
| Moderate off/shoulder/peak (₹/kWh) | same | 5 / 8 / 12 |
| Group 0 medoid flat bill | `tables/stage_a_tariff_bills.csv` | ~108.24 |
| Group 0 medoid ToD bill | same / summary | ~108.91 |
| Group 1 medoid flat / ToD | same | ~20.06 / ~23.80 |
| Relative ToD change group 1 | computed | ~+18.6% |
| BESS incremental savings 5/2 moderate | `experiment_037_summary.json` | ₹0 both groups |
| Peak reduction with no-BESS opt | same | 0% |
| n_bess_rows | same | 240 |
| validation_all_pass | same | true |

## Figures integrated (final pack)

| Figure | Path | Report § |
|--------|------|----------|
| ToD schedule | `final_submission/figures/exp037_tariff_schedule.png` | 16.3 |
| Period energy by group | `figures/exp037_period_energy_by_group.png` | 16.4 |
| Flat vs ToD bills | `figures/exp037_flat_vs_tod_bills.png` | 16.4 |
| Spread sensitivity | `figures/exp037_spread_sensitivity.png` | 16.7 |

## Files modified in this integration pass

- `final_submission/02_final_project_report.md` — integrated Chapter 16
- `final_submission/03_final_presentation.md` — SLP→ToD→BESS slides
- `final_submission/04_viva_preparation.md` — §O Q73–Q86
- `final_submission/06_executive_summary.md` — Contribution C
- `final_submission/00_README.md` — three contributions
- `final_submission/05_figure_and_evidence_index.md` — Exp 037 entries
- `final_submission/07_slp_research_framework.md` — new
- `final_submission/FINAL_CONSISTENCY_AUDIT.md` — updated
- `final_submission/EXPERIMENT_037_NARRATIVE_AUDIT.md` — this file
- `README.md` — identity block
- `research_log.md` — narrative note
- `new_submit/00_NEW_SUBMIT_INDEX.md`, `137_*` via build script

## Unresolved issues

- Presentation timing may require dropping slide 15 (Exp 035 peak) for strict 15-minute limit.
- Report title page placeholders (institution/name) still manual.
- `pytest` not installed; tariff unit tests run via direct import.

## Auditor conclusion

**Pass** — integrated story consistent with Experiment 037 numerical outputs and academic integrity constraints.
# New submit pack — index

## Experiment 029–032

See `79_*` … `108_*` (029 audit, 030 corrected forecast, 031 baseline, 032 ToD).

## Experiment 033 (BESS simulation)

| File | Purpose |
|------|---------|
| `109_exp033_summary.json` | Executive BESS results |
| `110_exp033_results.md` | Simulation results |
| `111_exp033_limitations.md` | Assumptions / no tariff |
| `112_exp033_c0_bess.png` | Cluster 0 medoid before/after |
| `113_exp033_c1_bess.png` | Cluster 1 medoid before/after |
| `114_exp033_sensitivity.png` | Capacity–power heatmap |
| `115_exp033_rule_vs_opt.png` | Rule vs LP benchmark |

Detail: `results/forecasting/experiment_033/`.
## Experiment 034 (BESS audit)

| File | Purpose |
|------|---------|
| `116_exp034_summary.json` | Audit verdict and validated peaks |
| `117_exp034_energy_balance.md` | Energy accounting findings |
| `118_exp034_corrected_results.md` | Corrected cyclic rule + exclusive LP |
| `119_exp034_peak_compare.png` | Recomputed peak reductions |
| `120_exp034_loss_correction.png` | Defective `loss_kwh` vs conversion loss |
| `121_exp034_heatmap_c0_opt.png` | LP sensitivity (cluster 0) |
| `122_exp034_validated_comparison.png` | Fair rule vs optimized comparison |
| `123_exp034_limitations.md` | Residual limitations |

Preserved: `109_*`–`115_*` (Experiment 033 evidence unchanged).
## Experiment 035 (BESS consolidation)

| File | Purpose |
|------|---------|
| `124_exp035_summary.json` | Final validation verdict |
| `125_exp035_bess_comparison.md` | Medoid dispatch comparison table |
| `126_exp035_energy_balance.md` | 320-scenario balance audit |
| `127_exp035_project_readiness.md` | Synopsis vs evidence |
| `128_exp035_dispatch_comparison.png` | Peak reduction by method |
| `129_exp035_sensitivity_c0_lp.png` | LP sensitivity (cluster 0) |
| `130_exp035_limitations.md` | Remaining caveats |

Artifacts `109_*`–`123_*` preserved unchanged.
## Final evaluation pack (submission folder)

| File | Purpose |
|------|---------|
| `131_final_submission_README.md` | Index to `final_submission/` |
| `132_synopsis_traceability.md` | Synopsis ↔ evidence |
| `133_final_project_report.md` | Full report |
| `134_final_presentation.md` | Slide deck (Markdown) |
| `135_viva_preparation.md` | Oral exam Q&A |
| `136_figure_evidence_index.md` | Figure map + claim index |
| `137_executive_summary.md` | One-page SLP characterization + SVR narrative |

Folder: `final_submission/` (figures include `exp036_*`). Consistency audit: `final_submission/FINAL_CONSISTENCY_AUDIT.md`.

Narrative refocus (2026-11-25): prior submission text archived under `internal_research_archive/narrative_pre_reframe_2026-11-25/`. **Integrated Experiment 036** in final pack (same date).
## Experiment 036 (SLP out-of-sample)

| File | Purpose |
|------|---------|
| `138_exp036_summary.json` | Out-of-sample SLP validation summary |
| `139_exp036_results.md` | Results digest |
| `140_exp036_slp_centroids.png` | Train-derived centroids |
| `141_exp036_heldout_profiles.png` | Held-out profile bands |
| `142_exp036_limitations.md` | Limitations |

## Narrative integration (2026-11-25)

| File | Purpose |
|------|---------|
| `143_final_consistency_audit.md` | Post-refactor claim/narrative audit |

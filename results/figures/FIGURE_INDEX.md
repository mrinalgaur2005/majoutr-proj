# Figure Index

| ID | Figure | Path | Experiment | Purpose | Data | Parameters |
|----|--------|------|------------|---------|------|------------|
| FIG-001 | Per-meter coverage | `results/figures/data_quality/coverage_histogram.png` | 001 | Show coverage spread | `meter_quality.csv` | 3-min expected grid; row counts |
| FIG-002 | Meters by city | `results/figures/data_quality/meters_by_location.png` | 001 | Sample size by location | `location_summary.csv` | 84 meters |
| FIG-003 | Mean profiles by city | `results/figures/profiles/mean_profiles_by_location.png` | 003 | Compare Mathura and Bareilly shapes | `daily_profiles.parquet` | Non-zero complete days; kW |
| FIG-004 | Weekday vs weekend | `results/figures/profiles/weekday_weekend.png` | 003 | Calendar structure | same | Mon–Fri vs Sat–Sun |
| FIG-005 | Metrics vs K (peak) | `results/figures/clustering/metrics_vs_k_peak.png` | 005 | Internal cluster validity | `cluster_metrics.csv` | K=2–6; silhouette n=10000 |
| FIG-006 | Metrics vs K (energy) | `results/figures/clustering/metrics_vs_k_energy.png` | 005 | Internal cluster validity | `cluster_metrics.csv` | K=2–6; silhouette n=10000 |
| FIG-007 | K=2 centroids peak | `results/figures/clustering/centroids_k2_peak.png` | 005 | Shape of peak-normalized solution | `cluster_centroids.csv` | seed 0, n_init=20 |
| FIG-008 | K=2 centroids energy | `results/figures/clustering/centroids_k2_energy.png` | 005 | Shape of energy-normalized solution | `cluster_centroids.csv` | seed 0, n_init=20 |
| FIG-009 | Peak vs energy K=2 | `results/figures/normalization/peak_vs_energy_centroids_k2.png` | 006 | Compare what each norm separates | centroids | K=2 |
| FIG-010 | Energy by cluster (peak) | `results/figures/diagnostics/magnitude_energy_k2_peak.png` | 006 | Magnitude vs shape | assignments + profiles | K=2 peak |
| FIG-011 | Temporal holdout peak | `results/figures/diagnostics/temporal_stability_k2_peak.png` | 006 | Persistence after 2020-05-21 | profiles | K=2 peak |
| FIG-012 | Temporal holdout energy | `results/figures/diagnostics/temporal_stability_k2_energy.png` | 006 | Persistence after 2020-05-21 | profiles | K=2 energy |

PPT copies of the same data: `results/figures/ppt_ready/`.

| FIG-013 | Test MAE by model | `results/figures/forecasting/model_mae_h1.png` | 012 | Compare H=1 test error | `baseline_metrics.csv` | RBF SVR, C=100, epsilon=0.2 |
| FIG-014 | Test RMSE by model | `results/figures/forecasting/model_rmse_h1.png` | 012 | Same comparison in RMSE | `baseline_metrics.csv` | H=1 |
| FIG-015 | Actual vs predicted sample | `results/figures/forecasting/actual_vs_predicted_sample.png` | 012 | Show a short test trace | `predictions/test_h1.parquet` | First 288 test steps |
| FIG-016 | SLP error histogram | `results/figures/forecasting/error_distribution_slp.png` | 012 | Error distribution | test predictions | H=1 |

Generating scripts: `scripts/run_ceew_foundation.py` (FIG-001–008), `scripts/final_clustering_audit.py` (FIG-009–012), and `scripts/run_ceew_forecasting.py` (FIG-013–016).

Interpretation of FIG-013: persistence has the lowest MAE. SLP does not beat it.

| FIG-025 | Persistence MAE by meter | `results/figures/forecasting/exp013_persistence_mae_distribution.png` | 013 | Spread of persistence skill | `per_meter_metrics.csv` | H=1 persistence |
| FIG-026 | Learned MAE by meter | `results/figures/forecasting/exp013_learned_mae_distribution.png` | 013 | Spread of ridge lag+cyclic | `per_meter_metrics.csv` | per meter |
| FIG-027 | Micro MAE | `results/figures/forecasting/exp013_micro_mae.png` | 013 | Pooled test error | `micro_metrics.csv` | all eligible meters |
| FIG-028 | Macro MAE | `results/figures/forecasting/exp013_macro_mae.png` | 013 | Unweighted meter average | `macro_metrics.csv` | 68 meters |
| FIG-029 | Persistence vs ridge | `results/figures/forecasting/exp013_persistence_vs_learned.png` | 013 | Meter-level comparison | `per_meter_metrics.csv` | diagonal means equal MAE |
| FIG-030 | MAE by city | `results/figures/forecasting/exp013_by_city.png` | 013 | Mathura vs Bareilly | `micro_metrics.csv` | micro |
| FIG-031 | MAE by load level | `results/figures/forecasting/exp013_by_load.png` | 013 | High vs low training load | `subgroup_metrics.csv` | split at median train mean |
| FIG-032 | Autocorrelation | `results/figures/forecasting/exp013_autocorrelation.png` | 013 | Why persistence is strong | `autocorrelation_summary.csv` | training window |
| FIG-033 | Example trace | `results/figures/forecasting/exp013_actual_vs_predicted.png` | 013 | One meter, three days | experiment 013 predictions | first eligible meter |
| FIG-034 | Error distribution | `results/figures/forecasting/exp013_error_distribution.png` | 013 | Persistence vs ridge residuals | test predictions | H=1 |

FIG-025–034 are Experiment 013. They do not replace FIG-015–016 from Experiment 012. Interpretation: persistence has the lowest MAE. Ridge has lower RMSE. No SLP claim.

| FIG-035 | Delta distribution | `results/figures/forecasting/exp014_delta_distribution.png` | 014 | Test \|ΔP\| histogram | experiment 014 predictions | H=1 |
| FIG-036 | Delta actual vs pred | `results/figures/forecasting/exp014_delta_actual_vs_predicted.png` | 014 | Ridge delta scatter | 50k sample | H=1 |
| FIG-037 | Reconstructed MAE | `results/figures/forecasting/exp014_reconstructed_mae.png` | 014 | Micro MAE all models | `micro_load_metrics.csv` | primary metric |
| FIG-038 | Persistence vs ridge | `results/figures/forecasting/exp014_persistence_vs_residual_ridge.png` | 014 | Per-meter MAE | `per_meter_load_metrics.csv` | ridge_both |
| FIG-039 | MAE by movement | `results/figures/forecasting/exp014_mae_by_movement.png` | 014 | \|ΔP\| tertiles | `movement_subgroup_metrics.csv` | training cuts |
| FIG-040 | MAE by city | `results/figures/forecasting/exp014_mae_by_city.png` | 014 | Mathura vs Bareilly | `micro_load_metrics.csv` | micro |
| FIG-041 | MAE by load | `results/figures/forecasting/exp014_mae_by_load.png` | 014 | High vs low train mean | `subgroup_load_metrics.csv` | median split |
| FIG-042 | Per-meter MAE | `results/figures/forecasting/exp014_per_meter_comparison.png` | 014 | MAE histograms | `per_meter_load_metrics.csv` | 68 meters |
| FIG-043 | Example trace | `results/figures/forecasting/exp014_example_trace.png` | 014 | Median \|ΔP\| train meter | experiment 014 predictions | 288 steps |
| FIG-044 | Error distribution | `results/figures/forecasting/exp014_error_distribution.png` | 014 | Persistence vs ridge both | test predictions | H=1 |

FIG-035–044: persistence wins full-sample MAE; ridge helps mainly in large \|ΔP\| tertile (FIG-039). No SLP claim.

| FIG-045 | MAE and RMSE | `results/figures/forecasting/exp015_mae_rmse_vs_persistence.png` | 015 | Test error for every candidate | `micro_load_metrics.csv` | H=1, 68 meters |
| FIG-046 | Per-meter MAE difference | `results/figures/forecasting/exp015_per_meter_mae_diff.png` | 015 | Meter MAE minus persistence | `per_meter_mae_diff.csv` | zero line is a tie |
| FIG-047 | Delta actual vs predicted | `results/figures/forecasting/exp015_delta_actual_vs_predicted.png` | 015 | One median-volatility meter | experiment 015 predictions | first 288 test steps |
| FIG-048 | Error distribution | `results/figures/forecasting/exp015_error_distribution.png` | 015 | Persistence vs selected shrink | test predictions | H=1 |
| FIG-049 | Subgroup MAE | `results/figures/forecasting/exp015_subgroup_mae.png` | 015 | Peak, weekday, load level | `subgroup_load_metrics.csv` | forecast-time rules |
| FIG-050 | Retrospective movement | `results/figures/forecasting/exp015_retrospective_movement.png` | 015 | Realized \|ΔP\| tertiles | `subgroup_load_metrics.csv` | not used for selection |
| FIG-051 | Validation selection | `results/figures/forecasting/exp015_validation_selection.png` | 015 | Model choice before test | `validation_selection.csv` | lowest validation MAE |

FIG-045–051 are Experiment 015. Pooled MAE can fall by a fraction of a percent while the median meter does not. No SLP claim.

| FIG-052 | Per-meter MAE change | `results/figures/forecasting/exp016_per_meter_mae_diff.png` | 016 | Shrink minus persistence by meter | `per_meter_diagnostics.csv` | grey bars are λ=0; paper |
| FIG-053 | Validation vs test | `results/figures/forecasting/exp016_val_vs_test_improvement.png` | 016 | Whether validation gains hold | `per_meter_diagnostics.csv` | paper |
| FIG-054 | Lambda distribution | `results/figures/forecasting/exp016_lambda_distribution.png` | 016 | How often λ is zero | `per_meter_diagnostics.csv` | presentation |
| FIG-055 | Lambda vs test change | `results/figures/forecasting/exp016_lambda_vs_test_diff.png` | 016 | Selected λ against test MAE difference | `per_meter_diagnostics.csv` | paper |
| FIG-056 | Pooled vs median | `results/figures/forecasting/exp016_pooled_vs_median.png` | 016 | Pooled gain is not the median meter | `statistical_comparison.csv` | paper |
| FIG-057 | City MAE | `results/figures/forecasting/exp016_city_mae.png` | 016 | Bareilly and Mathura pooled MAE | `per_meter_diagnostics.csv` | presentation |
| FIG-058 | Change size by λ | `results/figures/forecasting/exp016_feature_by_lambda.png` | 016 | Training \|ΔP\| for λ=0 vs λ>0 | `feature_diagnostics.csv` | validation grouping, not a test outcome |
| FIG-059 | Change size vs test | `results/figures/forecasting/exp016_feature_vs_test_diff.png` | 016 | Retrospective association | `per_meter_diagnostics.csv` | not used for selection |
| FIG-060 | Bootstrap intervals | `results/figures/forecasting/exp016_bootstrap_ci.png` | 016 | Meter-resample uncertainty | `statistical_comparison.csv` | seed 16, 2000 draws |
| FIG-061 | Frozen rule | `results/figures/forecasting/exp016_rule_comparison.png` | 016 | Validation-chosen rule vs persistence | `selection_rule_results.csv` | rule is always shrink_meter |

FIG-052–061 are Experiment 016. The frozen rule does not improve on Experiment 015. No SLP claim.

| FIG-062 | Timestamp intervals | `results/figures/forecasting/exp017_timestamp_intervals.png` | 017 | 15-minute grid | `timestamp_interval_distribution.csv` | audit |
| FIG-063 | Timestamp anomalies | `results/figures/forecasting/exp017_timestamp_anomalies.png` | 017 | Non-15-minute gaps (sample) | `timestamp_anomalies.csv` | audit |
| FIG-064 | Split coverage | `results/figures/forecasting/exp017_meter_split_coverage.png` | 017 | Usable origins per meter | `split_audit.csv` | paper |
| FIG-065 | Test start spread | `results/figures/forecasting/exp017_split_boundaries.png` | 017 | First test origin by meter | `split_audit.csv` | audit |
| FIG-066 | Leakage classes | `results/figures/forecasting/exp017_feature_availability.png` | 017 | Feature audit counts | `leakage_audit.csv` | paper |
| FIG-067 | Baseline reproduction | `results/figures/forecasting/exp017_baseline_reproduction.png` | 017 | Saved vs recomputed MAE | `baseline_reproduction.csv` | audit |
| FIG-068 | Per-meter baseline | `results/figures/forecasting/exp017_per_meter_reproduction.png` | 017 | Persistence vs shrink MAE | `per_meter_reproduction.csv` | paper |

FIG-062–068: Experiment 017 audit. Status PASSED WITH UNRESOLVED LIMITATIONS (timezone). No SLP claim.

| FIG-069 | Model MAE | `results/figures/forecasting/exp018_model_mae_comparison.png` | 018 | Test micro MAE all models | `experiment_018_micro_metrics.csv` | paper |
| FIG-070 | Model RMSE | `results/figures/forecasting/exp018_model_rmse_comparison.png` | 018 | Test micro RMSE | `experiment_018_micro_metrics.csv` | paper |
| FIG-071 | Per-meter MAE | `results/figures/forecasting/exp018_per_meter_mae_comparison.png` | 018 | Persistence vs SLP ridge | `experiment_018_per_meter_metrics.csv` | paper |
| FIG-072 | Meter improvement | `results/figures/forecasting/exp018_per_meter_improvement.png` | 018 | MAE diff SLP − persistence | `experiment_018_statistical_tests.csv` | paper |
| FIG-073 | City MAE | `results/figures/forecasting/exp018_city_comparison.png` | 018 | Bareilly and Mathura | `experiment_018_city_metrics.csv` | presentation |
| FIG-074 | SLP distance | `results/figures/forecasting/exp018_slp_distance_distribution.png` | 018 | Nearest-centroid distance | `test_predictions.parquet` | audit |
| FIG-075 | Distance vs error | `results/figures/forecasting/exp018_slp_distance_vs_error.png` | 018 | Retrospective sample scatter | `test_predictions.parquet` | exploratory |
| FIG-076 | Ablation | `results/figures/forecasting/exp018_ablation_comparison.png` | 018 | SLP vs corr vs noise | `experiment_018_ablation_results.csv` | paper |
| FIG-077 | Negative control | `results/figures/forecasting/exp018_negative_control.png` | 018 | Noise vs SLP micro MAE | `experiment_018_negative_control.csv` | validation |
| FIG-078 | Bootstrap CI | `results/figures/forecasting/exp018_bootstrap_confidence_intervals.png` | 018 | Meter bootstrap median diff | `experiment_018_bootstrap_results.csv` | seed 18 |
| FIG-079 | Example trace | `results/figures/forecasting/exp018_example_forecast_trace.png` | 018 | Two-day forecast overlay | `test_predictions.parquet` | presentation |
| FIG-080 | Feature coverage | `results/figures/forecasting/exp018_feature_availability_audit.png` | 018 | Finite SLP per meter | `experiment_018_feature_availability.csv` | audit |

FIG-069–080: Experiment 018 SLP test. **Conclusion C** — no MAE benefit vs persistence.

| FIG-081 | CNAE counts | `results/figures/dataset_019/exp019_cnae_division_counts.png` | 019 | GoiEner v7.1 metadata | `category_counts.csv` | paper |
| FIG-082 | Resolution | `results/figures/dataset_019/exp019_sampling_resolution_comparison.png` | 019 | Native intervals by dataset | `sampling_resolution_audit.csv` | audit |
| FIG-083 | Coverage | `results/figures/dataset_019/exp019_coverage_distribution.png` | 019 | Rows per sampled profile | `goiener_profile_sample_audit.csv` | audit |
| FIG-084 | Missingness | `results/figures/dataset_019/exp019_missingness_comparison.png` | 019 | Partial missingness audit | `missingness_audit.csv` | audit |
| FIG-085 | CNAE 01 trace | `results/figures/dataset_019/exp019_example_daily_profiles_by_cnae.png` | 019 | Hourly `cons` sample | `goiener_profile_sample_audit.csv` | presentation |
| FIG-086 | Synopsis status | `results/figures/dataset_019/exp019_dataset_eligibility_table.png` | 019 | Requirement status counts | `synopsis_alignment.csv` | paper |

FIG-081–086: Experiment 019 dataset feasibility. Multi-dataset synopsis track recommended.

| FIG-087 | Forecast trace | `results/figures/experiment_020a/exp020a_actual_vs_predicted_trace.png` | 020A | Profile 00489 test week | `predictions/test_predictions.parquet` | presentation |
| FIG-088 | Per-profile MAE | `results/figures/experiment_020a/exp020a_per_profile_mae.png` | 020A | All models | `reproduced_per_profile_metrics.csv` | paper |
| FIG-089 | SVR WAPE ablation | `results/figures/experiment_020a/exp020a_svr_slp_wape.png` | 020A | SLP vs no-SLP | `reproduced_per_profile_metrics.csv` | validation |
| FIG-090 | Actual distribution | `results/figures/experiment_020a/exp020a_actual_distribution.png` | 020A | Pooled test actuals | `test_predictions.parquet` | audit |
| FIG-091 | Zero fraction | `results/figures/experiment_020a/exp020a_zero_fraction.png` | 020A | Per profile | `per_profile_splits.csv` | audit |
| FIG-092 | Error distribution | `results/figures/experiment_020a/exp020a_error_distribution.png` | 020A | SVR+SLP errors | `test_predictions.parquet` | audit |
| FIG-093 | SLP ablation MAE | `results/figures/experiment_020a/exp020a_svr_ablation_mae.png` | 020A | Paired SVR | `slp_ablation_paired.csv` | paper |
| FIG-094 | Category SLP curve | `results/figures/experiment_020a/exp020a_category_slp_hourly.png` | 020A | Hour-of-day template | `category_slp_hour_of_week.npy` (020) | paper |

FIG-087–094: Experiment 020A audit. Persistence wins mean MAE; SLP edge on mean MAPE only; not sufficient to scale pilot.

| FIG-095 | MAE macro vs micro | `results/figures/experiment_020b/exp020b_fig01_original_vs_aligned_mae.png` | 020B | Aligned audit | `experiment_020b_summary.json` | audit |
| FIG-096 | RMSE macro vs micro | `results/figures/experiment_020b/exp020b_fig02_original_vs_aligned_rmse.png` | 020B | Aligned audit | `experiment_020b_summary.json` | audit |
| FIG-097 | Macro vs micro | `results/figures/experiment_020b/exp020b_fig03_macro_vs_micro_mae.png` | 020B | Aligned audit | `experiment_020b_summary.json` | audit |
| FIG-098 | SLP Δ MAE | `results/figures/experiment_020b/exp020b_fig04_slp_mae_delta_diverging.png` | 020B | Aligned audit | `experiment_020b_summary.json` | audit |
| FIG-099 | SLP delta histogram | `results/figures/experiment_020b/exp020b_fig05_slp_delta_distribution.png` | 020B | Aligned audit | `experiment_020b_summary.json` | audit |
| FIG-100 | Bootstrap CI | `results/figures/experiment_020b/exp020b_fig06_bootstrap_mae_ci.png` | 020B | Aligned audit | `experiment_020b_summary.json` | audit |
| FIG-101 | Quality class dist | `results/figures/experiment_020b/exp020b_fig07_imputation_distribution.png` | 020B | Aligned audit | `experiment_020b_summary.json` | audit |
| FIG-102 | MAE by flag class | `results/figures/experiment_020b/exp020b_fig08_mae_by_quality_class.png` | 020B | Aligned audit | `experiment_020b_summary.json` | audit |
| FIG-103 | SLP vs zeros | `results/figures/experiment_020b/exp020b_fig09_slp_vs_zero_frac.png` | 020B | Aligned audit | `experiment_020b_summary.json` | audit |
| FIG-104 | SLP vs flag_zero | `results/figures/experiment_020b/exp020b_fig10_slp_vs_completeness.png` | 020B | Aligned audit | `experiment_020b_summary.json` | audit |
| FIG-105 | Example trace | `results/figures/experiment_020b/exp020b_fig11_example_trace.png` | 020B | Aligned audit | `experiment_020b_summary.json` | audit |
| FIG-106 | Alignment counts | `results/figures/experiment_020b/exp020b_fig12_alignment_counts.png` | 020B | Aligned audit | `experiment_020b_summary.json` | audit |

FIG-095–106: Experiment 020B integrity audit.

| FIG-107 | Coverage | `results/figures/experiment_021/exp021_fig01_coverage.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |
| FIG-108 | Missingness | `results/figures/experiment_021/exp021_fig02_missingness.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |
| FIG-109 | Zeros | `results/figures/experiment_021/exp021_fig03_zeros.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |
| FIG-110 | Consumption dist | `results/figures/experiment_021/exp021_fig04_consumption_dist.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |
| FIG-111 | Timestamp gaps | `results/figures/experiment_021/exp021_fig05_timestamp_gaps.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |
| FIG-112 | Extreme events | `results/figures/experiment_021/exp021_fig06_extreme_events.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |
| FIG-113 | Trace | `results/figures/experiment_021/exp021_fig07_trace.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |
| FIG-114 | Scatter | `results/figures/experiment_021/exp021_fig08_scatter.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |
| FIG-115 | Residuals | `results/figures/experiment_021/exp021_fig09_residuals.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |
| FIG-116 | Residuals vs actual | `results/figures/experiment_021/exp021_fig10_residual_vs_actual.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |
| FIG-117 | Regime MAE | `results/figures/experiment_021/exp021_fig11_regime_mae.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |
| FIG-118 | Per-profile MAE | `results/figures/experiment_021/exp021_fig12_per_profile_mae.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |
| FIG-119 | SLP delta | `results/figures/experiment_021/exp021_fig13_slp_delta.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |
| FIG-120 | SLP template | `results/figures/experiment_021/exp021_fig14_slp_template.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |
| FIG-121 | SLP vs zeros | `results/figures/experiment_021/exp021_fig15_slp_vs_zeros.png` | 021 | Diagnostic audit | experiment_021_summary.json | audit |

FIG-107–121: Experiment 021 failure audit.

| FIG-122 | Literature timeline | `results/figures/experiment_023/exp023_literature_timeline.png` | 023 | Literature/audit | experiment_023_summary.json | audit |
| FIG-123 | Synopsis status dashboard | `results/figures/experiment_023/exp023_synopsis_dashboard.png` | 023 | Literature/audit | experiment_023_summary.json | audit |
| FIG-124 | Access dependencies | `results/figures/experiment_023/exp023_access_dependencies.png` | 023 | Literature/audit | experiment_023_summary.json | audit |

FIG-122–124: Experiment 023.

| FIG-125 | Execution workflow | `results/figures/experiment_024_design/exp024_design_workflow.png` | 024-design | Protocol audit | experiment_024_summary.json | design |
| FIG-126 | Dual-track architecture | `results/figures/experiment_024_design/exp024_dual_track.png` | 024-design | Protocol audit | experiment_024_summary.json | design |
| FIG-127 | Split and leakage rule | `results/figures/experiment_024_design/exp024_split_leakage.png` | 024-design | Protocol audit | experiment_024_summary.json | design |
| FIG-128 | Dataset readiness | `results/figures/experiment_024_design/exp024_readiness.png` | 024-design | Protocol audit | experiment_024_summary.json | design |

| FIG-129 | SLP workflow | `results/figures/experiment_024_design/exp024_slp_workflow.png` | 024-design | Protocol audit | experiment_024_summary.json | design |
| FIG-130 | Model comparison architecture | `results/figures/experiment_024_design/exp024_model_comparison.png` | 024-design | Protocol audit | experiment_024_summary.json | design |
| FIG-131 | Synopsis dependency map | `results/figures/experiment_024_design/exp024_synopsis_dependencies.png` | 024-design | Protocol audit | experiment_024_summary.json | design |

FIG-125–131: Experiment 024 design.

| FIG-132 | Val MAE comparison | `results/figures/experiment_028/exp028_val_mae_comparison_H1_START_00.png` | 028 | Norwegian exploratory SVR | `experiment_028_summary.json` | audit |
| FIG-133 | Timestamp sensitivity | `results/figures/experiment_028/exp028_timestamp_sensitivity_f1.png` | 028 | Dual H1 mapping | `timestamp_robustness.json` | audit |
| FIG-134 | Category SLP heatmap | `results/figures/experiment_028/exp028_category_slp_heatmap.png` | 028 | Native slot template | `category_slp_native_slot_train_snapshot.npy` | paper |
| FIG-135 | SLP improvement dist | `results/figures/experiment_028/exp028_improvement_distribution.png` | 028 | Track A vs B paired | per-household metrics | audit |

FIG-132–135: Experiment 028 Norwegian residential exploratory (not Exp 024).
| FIG-136 | Exp 029 corrected SLP | `results/forecasting/experiment_029/corrected_category_slp_heatmap.png` | 029 | Audit heatmap | memmap QC | audit |

## Experiment 034

`exp034_*` in `results/figures/experiment_034/` — BESS audit figures.

## Experiment 035

`exp035_*` — final BESS validation figures.

## Final evaluation pack

Curated copies and map: `final_submission/05_figure_and_evidence_index.md`.

**Submission-facing interpretation:** Prefer figures F1–F5 in that index for the **SLP + SVR** narrative (profiles, clusters, forecasting evaluation). Historical captions in this file (e.g. early CEEW benchmark notes) remain as **archived experiment context**; consult `final_submission/06_executive_summary.md` for the evaluation storyline.

## Experiment 036

`exp036_*` in `results/forecasting/experiment_036/figures/`.

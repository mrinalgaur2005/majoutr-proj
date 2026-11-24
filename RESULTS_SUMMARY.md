# Results summary

## Scope and provenance

These are reproducible results from a 45-day, six-meter **synthetic** generator—not CEEW Uttar Pradesh telemetry. The canonical command and configuration are in [run_all_experiments.py](/home/mrinalgaur/Desktop/majou-proj/run_all_experiments.py) and [final_experiment_config.json](/home/mrinalgaur/Desktop/majou-proj/results/final_experiment_config.json).

## Canonical one-step result

On 634 final-holdout 15-minute points, the full AR+cyclic+weather+SLP SVR produced RMSE 0.402445 kW, MAE 0.295920 kW, MAPE 0.946141%, WAPE 0.824622%, and R² 0.999541. Seasonal naive produced RMSE 0.412732 kW and MAPE 0.945162%; persistence produced RMSE 9.191068 kW and MAPE 11.786565%. Full values are in [final_metrics.csv](/home/mrinalgaur/Desktop/majou-proj/results/final_metrics.csv), with row-level traces in [final_predictions.csv](/home/mrinalgaur/Desktop/majou-proj/results/final_predictions.csv).

The R² is high because this is a smooth, deterministic synthetic process with a strong daily lag. It must not be presented as real-feeder validation. The scatter and residual diagnostics are [actual_vs_predicted.png](/home/mrinalgaur/Desktop/majou-proj/figures/actual_vs_predicted.png) and [residuals.png](/home/mrinalgaur/Desktop/majou-proj/figures/residuals.png).

## Ablation and clustering

The available ablation does not establish a broad “SLP advantage”: AR+SLP RMSE (0.313935 kW) was better than AR-only (0.356377 kW), whereas the full feature set was worse (0.402445 kW). Feature effects are conditional on this generator and one split. See `results/feature_ablation.csv`.

K=2 is strongly separated in this synthetic data (silhouette 0.9800); K=3–5 degrade. This validates recovery of the generator’s two mechanisms, not real consumer classes. See `results/clustering_sensitivity.csv` and `results/clustering_stability.json`.

## Not established

No fair ARIMA/SARIMA, direct/recursive 48-hour forecast, rolling-origin significance test, real-data imputation ablation, ToD multi-window cost study, BESS sensitivity, or dispatch energy-balance validation has been run. Existing microgrid and ToD figures/reports are historical and non-canonical. They should not be cited as final evidence.

The imputation ablation shows identical scores for forward fill, linear, and cubic interpolation. At 15-minute aggregation no bin was fully missing in this generated run, so the comparison contains no meaningful imputation intervention. It is not evidence that the methods are equivalent.

## Research Readiness Assessment

1. Fixed: a traceable synthetic canonical experiment, holdout-before-tuning, training-only SLP fitting, CV boundary export, robust metrics, sensitivity/ablation artifacts, and transparent horizon status.
2. Remaining: real data provenance, causal imputation, fair ARIMA/multi-step testing, rolling robustness, and microgrid revalidation.
3. Unperformed experiments are explicitly listed above rather than fabricated.
4. Remove/soften claims of real CEEW validation, identified customer types, unit commitment, perfect forecasting, and SLP financial superiority.
5. The implementation supports only a limited synthetic one-step forecasting conclusion; it does not yet support the project’s real-world technical conclusions.

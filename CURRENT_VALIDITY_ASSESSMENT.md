# Current validity assessment

## Local data-provenance determination

**No real CEEW Uttar Pradesh dataset was found locally.** I searched the repository, its accessible parent locations under `/home/mrinalgaur` for CEEW/Uttar-Pradesh-named and common tabular data formats, project documentation/configuration, notebook files, and all data-loading code. The project contains no raw CSV, TSV, Parquet, Feather, HDF5, Excel, or notebook dataset. The only project CSV files are generated experiment outputs in `results/`.

Every executable modelling entry point constructs `IndianFeederTelemetryGenerator`: `load_forecasting_unit_commitment.py:527`, `phase3_benchmarking_evaluation.py:466`, `phase4_microgrid_unit_commitment.py:92`, `phase5_aggregate_tod_analysis.py:144`, `svr_feature_engineering_tuning.py:266`, and `run_all_experiments.py:142`. No `read_csv`, `read_parquet`, `read_excel`, or equivalent data-ingestion path exists in project modelling code.

Accordingly, items 2–8 for a real local CEEW file—path, format, columns, sampling, meter count, temporal coverage, and category labels—are **not available**. The current pipeline cannot consume real CEEW data without a new ingestion/schema-mapping layer; its inputs require a timestamp-indexed table containing meter kW columns and, currently, temperature, solar irradiance, wind speed, weekend and holiday fields. Existing reported results were not generated from real CEEW data: the executable sources create synthetic data and no stored real input exists.

## A. What is valid

- The current canonical run is reproducible synthetic evidence: six generated meters, 3-minute source data, 15-minute aggregation, 634-point final chronological holdout, and a persisted result trace in `results/final_predictions.csv`.
- The canonical runner fits its SLP on its raw training period, uses past-only target lags, holds out the final 15% before tuning, and places scaling inside the CV pipeline. These facts do not eliminate the separately documented non-causal interpolation limitation.
- The reported one-step synthetic metrics are mechanically correct for that run: SVR RMSE 0.402445 kW, MAPE 0.946141%, R² 0.999541. The scatter plot and residual plot are consistent with those values.

## B. What is not valid

- It is not a validation on CEEW, Uttar Pradesh, India, real consumers, or a real feeder.
- It does not identify real residential or agricultural consumers. Those demand mechanisms are constructed directly in the generator (`load_forecasting_unit_commitment.py:80-95`).
- It is not evidence of a 48-hour forecast, since the canonical setup is one-step-ahead at 15 minutes.
- It is not a production/deployment result: cubic spline/linear interpolation is currently global and may use later data when filling missing observations.
- Existing historical ARIMA, ToD, and microgrid numbers cannot be treated as canonical real-data evidence.

## C. What the synthetic experiment demonstrates

It demonstrates that the code can learn the daily structure deliberately encoded in this generator. The generator specifies agricultural pumping windows (00:00–06:00 and 12:00–15:00) and deterministic Gaussian residential peaks, with small independent noise. That makes the next day highly predictable from the prior day.

Diagnostics support this explanation rather than direct target copying:

| Diagnostic, canonical holdout | Result | Interpretation |
|---|---:|---|
| Corr(target, lag_96) | 0.999759 | Near-repeated 24-hour synthetic shape dominates. |
| Corr(target, lag_1) | 0.880249 | Strong short-term continuity. |
| Corr(actual, SVR prediction) | 0.999771 | Consistent with the high R², but not independent evidence of real-world validity. |
| Seasonal-naive RMSE | 0.412732 kW | Nearly matches SVR RMSE of 0.402445 kW. |
| Top 10% load points | 64 points; RMSE 0.576891 kW; MAPE 0.766363% | The smooth generated peaks are also predictable. |
| Full SVR vs AR+SLP ablation | 0.402445 vs 0.313935 kW RMSE | Extra cyclic/weather features did not improve this particular synthetic split. |

No target-derived feature is directly inserted into X at the same timestamp: feature construction reads indices `t-1`, `t-2`, and `t-96` while the target is index `t` (`load_forecasting_unit_commitment.py:224-250`). Therefore the high result is principally explained by the generator’s strong periodic structure and an easy one-step task, not by a same-row target copy. However, global spline interpolation remains a possible boundary look-ahead pathway and prevents a claim of fully leakage-free online evaluation.

## D. What it does not demonstrate

It does not establish that SLP features improve real load forecasting, that SVR is superior to seasonal naive in practice, that clustering recovers customer classes, or that the method improves tariff or microgrid decisions. It also does not establish robustness to outages, meter heterogeneity, weather forecast error, holidays, seasonal change, or multi-step error accumulation.

## E. Requirements for real-data validation

Provide an authorized, documented raw smart-meter dataset with: meter identifier; timezone-aware timestamp; active energy or power plus units; original interval; coverage dates; meter/feeder metadata; consumer-category metadata if category claims are intended; missing/outage flags; and a data dictionary/license. If weather is a model feature, provide weather observations and, for operational claims, forecast-vintage weather available at each forecast origin.

Build a separate ingestion pipeline without touching the synthetic sanity-check runner. It must map the source schema, audit duplicates/intervals/missingness/units, perform causal fold-wise imputation, fit SLPs only in training windows, and evaluate seasonal naive plus fair rolling-origin baselines on untouched real test windows.

## F. Presentation judgement

The project can be presented as a **software prototype and synthetic-method sanity check**, provided every quantitative slide/table is labelled “synthetic telemetry generated by `IndianFeederTelemetryGenerator`.” It cannot be presented as a research study validating a method on CEEW or Indian real-world smart-meter data without real-data validation. The appropriate claim is: “On a deliberately structured synthetic feeder, the implementation reproduces a strong daily pattern; real-data generalization has not been evaluated.”

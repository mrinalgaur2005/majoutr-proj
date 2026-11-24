# Research technical audit

Audit date: 2026-09-17. This repository contains **no CEEW Uttar Pradesh data file**. All executable paths inspected generate telemetry with `IndianFeederTelemetryGenerator`; consequently, none of the existing numerical results are evidence about CEEW customers or a real feeder.

## Critical validity issues

| Location | Current behaviour and problem | Type | Severity | Correction / rerun |
|---|---|---|---|---|
| `load_forecasting_unit_commitment.py:38-104`, `phase_1_processing.py:152-185`, `phase5_aggregate_tod_analysis.py:116-121` | Synthetic loads are generated from the same hard-coded residential/agricultural mechanisms later “identified” by clustering, while reports frame the work in a CEEW-UP context. | F | CRITICAL | Relabel all results synthetic; supply documented raw CEEW data before real-world claims. Rerun required. |
| `load_forecasting_unit_commitment.py:137-139` | Cubic spline is fit across the full series and `bfill` uses future values. This crosses the train/test boundary. | A, B | CRITICAL | Impute each training fold using only preceding observations, or drop affected forecast origins. Rerun required. |
| `load_forecasting_unit_commitment.py:142-198` | K-Means/SLPs are fit on the entire time span before chronological splitting. | A, B | CRITICAL | Fit SLPs only on the raw training period within each evaluation origin. The canonical runner does this; rerun on real data is still required. |
| `phase5_aggregate_tod_analysis.py:167-181` | Tuners are fit on full `X_res`, `X_agri`, and `X_agg`, including the later holdout. | A, B | CRITICAL | Tune on the training partition only; retain the final 15% untouched. Rerun required. |

## Major methodological issues

| Location | Current behaviour and problem | Type | Severity | Correction / rerun |
|---|---|---|---|---|
| `load_forecasting_unit_commitment.py:298-306` | ARIMA is one 15-minute recursive forecast extending through the full holdout, whereas SVR uses observed test lags at every step. It is not a like-for-like baseline. | C | HIGH | Evaluate one-step ARIMA rolling-origin or make every model recursive/direct at the same horizon. Rerun. |
| `load_forecasting_unit_commitment.py:215-256` | Weather at target time is silently treated as known. | D, F | HIGH | State a weather-forecast source/vintage or use lagged/forecast weather. Rerun if operational claim is made. |
| `load_forecasting_unit_commitment.py:174-196`; `phase_1_processing.py:113-119` | “Residential” and “Agricultural” are assigned from centroid evening ratio, not external labels. | F | HIGH | Use “evening-peaked/profile cluster” unless meter metadata validates categories. Rerun not needed for terminology. |
| `load_forecasting_unit_commitment.py:336-417` | 1.5 MW PV, 600 kW wind, 500 kW fuel cell, 1 MW diesel and 2 MWh BESS serve roughly tens of kW. No scale rationale is supplied. | D, F | HIGH | Re-size or explicitly model a scaled representative feeder. Rerun dispatch. |
| `load_forecasting_unit_commitment.py:394-414` | This is single-bus LP economic dispatch, not unit commitment: no binary commitment/start-up/shutdown decisions and no network constraints. | F | HIGH | Call it “single-bus linear economic dispatch”; add MILP only if UC is required. |

## Minor methodological issues

| Location | Current behaviour and problem | Type | Severity | Correction / rerun |
|---|---|---|---|---|
| `load_forecasting_unit_commitment.py:322-329` | Metrics omit MAE, sMAPE/WAPE, zero-denominator policy, NaN policy and precision. | B, F | MEDIUM | Use canonical metrics implementation and report full precision. Rerun. |
| `load_forecasting_unit_commitment.py:99-102` | Missingness is injected across columns then resampled; no raw-to-resampled missingness audit is retained. | E | MEDIUM | Persist missingness by meter and interval. |
| `load_forecasting_unit_commitment.py:412-413` | `state_of_charge_initial=0.4` is an absolute PyPSA energy value (MWh), not documented as a fraction. | D | MEDIUM | Document as 0.4 MWh/20% or set deliberately; validate final SoC. |
| `phase5_aggregate_tod_analysis.py:DEFAULT_PHASE4_KPIS` | Hard-coded dispatch KPIs can become stale and are not experimental results. | F | MEDIUM | Remove constants from reporting; compute every value from saved dispatch. |

## Reproducibility issues

| Location | Current behaviour and problem | Type | Severity | Correction / rerun |
|---|---|---|---|---|
| Repository-wide | No dataset, versioned configuration, canonical result files, or master command existed. Reports contain conflicting metrics/epsilon values. | E, F | HIGH | `run_all_experiments.py` now writes canonical synthetic artifacts; real-data rerun remains needed. |
| `FINAL_OUTPUT.md`, `FINAL_OUTPUT_2.md` | Narrative embeds stale, inconsistent numbers and strong claims. | E, F | HIGH | Treat as historical, not final results; regenerate reports from `results/`. |

## Reporting/interpretation issues

Existing “proves”, “production-ready”, “flawlessly”, “perfect/near-perfect”, “necessary”, “unit commitment”, and “peak shaved = BESS discharge” language is unsupported. In particular, the reported ToD errors in `FINAL_OUTPUT_2.md` show aggregate error ₹2.91 versus SLP ₹9.10, so that realization does **not** support lower SLP financial error.

## Things already technically sound

- 15-minute resampling and 96-slot daily construction are internally consistent.
- Lag indexing at `load_forecasting_unit_commitment.py:224-250` uses past target observations for a one-step forecast.
- `StandardScaler` is inside `Pipeline` during `GridSearchCV` (`:264-282`), preventing scaler leakage within CV.
- `TimeSeriesSplit` preserves order; the canonical runner persists exact boundaries in `results/cv_splits.json`.
- The tariff code applies 0.25 h conversion and 18:00–22:00 boundaries correctly (`phase5_aggregate_tod_analysis.py:232-258`, subject to a real-data rerun).

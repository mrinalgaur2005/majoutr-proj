# Frozen forecasting baseline (post-audit)

Version: Experiment 017 freeze, audit date in experiment_017_summary.json.

## Data
- Source: CEEW Mathura–Bareilly smart meters (Harvard Dataverse DOI 10.7910/DVN/GOCHJH).
- Input file: `data/interim/ceew_15min_bins_dedup.parquet`
- Sampling: 15-minute bins from complete five-point 3-minute aggregates.
- Load: `load_kw` average power (kW) for a **complete 15-minute bin** = sum of five 3-minute interval energies / **0.25 h**. Each 3-minute interval uses `t_kWh / 0.05 h` when forming the bin.
- Timestamps: timezone-naive; timezone semantics **unresolved**.

## Population
- 68 eligible meters (same rule as Experiments 013–016).
- Usable origins: train ≥1344, validation ≥288, test ≥288.
- Test evaluation rows: 835,410 (H=1).

## Chronological split (forecast origin t)
- Train: 2019-01-01 ≤ t < 2020-07-01
- Validation: 2020-07-01 ≤ t < 2021-01-01
- Test: t ≥ 2021-01-01
- Target: load at t+15 minutes.

## Models
- **Persistence / zero-change:** P̂(t+15m) = P(t).
- **Frozen learned baseline:** Experiment 015 per-meter shrinkage of Ridge delta.
  - Ridge delta lags: ΔP(t), ΔP(t-1), … at lags {1,2,4,8,12,24,48,96}.
  - Ridge α ∈ {0.1,1,10,100} chosen by validation MAE on delta.
  - Shrinkage λ ∈ {0,0.25,0.5,0.75,1} chosen by validation MAE on reconstructed load.
  - Scaler fit on train for tuning; refit on train+validation before test prediction.

## Metrics
- Primary: MAE (kW) on reconstructed load.
- Secondary: RMSE, R², per-meter MAE, median/mean meter MAE.
- Inference unit: meter (68), not individual 15-minute rows.

## Frozen test metrics (recomputed in 017)
- Persistence MAE: 0.107447 kW
- Shrink MAE: 0.107011 kW
- Persistence RMSE: 0.270548 kW
- Shrink RMSE: 0.266110 kW

## Reproduce
```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_015.py
```

## Test isolation
- No test rows used for α, λ, or rule selection.
- Experiment 016 rule chosen on validation only.

## Known limitations
- Timestamp timezone not established.
- Pooled shrink gain ~0.4%; median meter difference 0.
- All-period cluster labels must not enter forecasting.

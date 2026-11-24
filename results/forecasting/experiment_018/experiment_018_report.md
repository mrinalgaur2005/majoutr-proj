# Experiment 018 — Leakage-safe SLP forecasting

**Conclusion C.** Validation-selected primary model: `ridge_delta_cyclic_slp`.

**Command (training):** `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_018.py`

**Finalize:** `python3 scripts/finalize_experiment_018.py`

## Question

Does causal daily load-profile (peak-normalized K=2 centroid distance + optional trailing correlation) improve H=1 load forecasts beyond persistence and frozen Experiment 015 shrinkage?

## Protocol

- 68 meters, 835,410 test origins (reconciled with Experiment 017 `split_audit.csv`).
- Population centroids refit using profiles with `date <` forecast origin calendar day.
- Ridge on load change + delta lags + calendar; α chosen on validation only.
- Primary SLP arm selected by lowest validation pooled load MAE among `ridge_delta_cyclic`, `ridge_delta_cyclic_slp`, `ridge_delta_cyclic_slp_corr`.
- Comparators: persistence and frozen 015/013 predictions merged without refit.

## Test metrics (micro MAE kW)

| Model | MAE | RMSE |
|-------|-----:|-----:|
| persistence | 0.107447 | 0.270548 |
| frozen_shrink_015 | 0.107011 | 0.266110 |
| frozen_ridge_lag_cyclic_013 | 0.117321 | 0.250303 |
| ridge_delta_cyclic | 0.111346 | 0.262079 |
| ridge_delta_cyclic_slp | 0.111347 | 0.262079 |
| ridge_delta_cyclic_slp_corr | 0.111337 | 0.262074 |
| ridge_delta_cyclic_slp_noise | 0.111361 | 0.262083 |

- Median per-meter MAE: persistence 0.054859; ridge_delta_cyclic_slp 0.060928.
- Meters improved / worse / tied vs persistence: 4 / 64 / 0.
- Wilcoxon signed-rank (Pratt, 68 meters): p=2.006e-10.
- Bootstrap median MAE diff 95% CI: [0.001933, 0.004085].

## Predeclared success criteria

- micro_mae_leq_1p02_persistence: FAIL
- median_meter_leq_persistence: FAIL
- bareilly_ok: PASS
- mathura_ok: PASS
- meters_improved_ge_10: FAIL
- beats_frozen_shrink_015_micro: FAIL

## Answers (Part 13)

1. Recurring profile information did **not** improve forecasting under causal features (micro MAE rose vs persistence).
2. Beat persistence: **no** (0.111347 vs 0.107447).
3. Beat frozen 015 shrinkage: **no** (0.111347 vs 0.107011).
4. Median per-meter MAE improved: **no** (0.060928 vs 0.054859).
5. Meters improved: 4 of 68.
6. City consistency: both cities worse than persistence at micro level.
7. Negative control: noise feature MAE 0.111361 — no spurious SLP gain.
8. Wilcoxon indicates systematic **worsening** vs persistence (p≪0.05), not improvement.
9. SLP block did not beat the no-SLP ridge_delta_cyclic arm (ΔMAE ≈ 9.17e-07).
10. Limitations: timezone-naive timestamps (017); energy-normalization sensitivity not run; validation prediction parquet not saved in this run.

**DEC-016:** Do not claim SLP forecasting benefit. Persistence remains the MAE reference; frozen shrink_015 remains the best learned pooled baseline. SLP distance is implemented leakage-safely but does not generalize.

Validation checks failed: none
# Experiment 020A — Forecast evaluation and SLP ablation audit

**Date:** 2026-11-24  
**Command:** `OMP_NUM_THREADS=1 python3 scripts/run_experiment_020a.py` (~622 s, 15 profiles, no downloads)  
**Scope:** Independent audit of Experiment 020 agriculture pilot. **`results/forecasting/experiment_020/` unchanged.**

## 1. Reproduction

All **25/25** pooled macro metrics (mean of per-profile metrics, as in Experiment 020) match Experiment 020 within tolerance `1e-4` (`reproduction_check.csv`).

Predictions saved for the first time: `predictions/test_predictions.parquet` (53,244 rows = 15 profiles × ~3,550 aligned test origins × 5 models).

**Sample alignment**

| Model group | Test origin definition (020 script) | `n` per profile |
|-------------|-------------------------------------|-----------------|
| Persistence, seasonal lag-24, ARIMA | Full chronological `test_idx` | `n_test_origins_exp020_style` |
| SVR ± SLP | Lag-filtered origins (`build_xy`) | `n_test_origins_svr` |

For 14/15 profiles the two counts differ by **1** (last test origin dropped for lag features). Metrics in 020 pair persistence/ARIMA preds with SVR-filtered `yte` (truncated arrays). Saved predictions use **aligned lag-filtered timestamps** for all models so paired ablations are fair.

## 2. Metric audit

**MAPE denominator (unchanged from 020):** `denom = max(|y_actual|, 1.0)` kWh-equivalent scale on `cons`.

**Pooled micro** (all test points stacked, identical timestamps across models):

| model | MAE | RMSE | MAPE % | WAPE % | R² |
|-------|-----|------|--------|--------|-----|
| persistence | 192.8 | 528.7 | 311.5 | 31.8 | 0.764 |
| seasonal_lag24 | 354.6 | 843.6 | 3093.6 | 58.5 | 0.398 |
| arima_101 | 511.0 | 891.1 | 4288.2 | 84.2 | 0.329 |
| svr_no_slp | 261.2 | 665.7 | 1430.9 | 43.1 | 0.625 |
| svr_category_slp | 259.0 | 658.3 | 1385.1 | 42.7 | 0.634 |

**Zero / near-zero (pooled test actuals):** 11,634 observations with `actual == 0` (21.8%); 17,703 with `|actual| < 10` (33.2%). See `zero_nearzero_audit.csv`, `mape_sensitivity_analysis.csv`.

**MAPE sensitivity** (pooled micro, same denominator rule; thresholds exclude low-|y| hours from the *sum* only):

| threshold `|y| ≥` | n incl. | persistence MAPE | SVR+SLP MAPE | SVR MAPE |
|-------------------|---------|------------------|--------------|----------|
| 0 | 53,244 | 311% | 1385% | 1431% |
| 1 | 41,610 | 100% | 427% | 447% |
| 10 | 35,541 | 78% | 157% | 163% |
| 100 | 29,957 | 43% | 51% | 52% |

At `|y| ≥ 100`, SVR+SLP **does not** beat persistence on MAPE (51% vs 43%). Original high MAPE values are **not** silently dropped in primary tables; sensitivity is additive.

## 3. Per-profile summary

Splits and zero fractions: `per_profile_splits.csv`. Full per-model metrics: `reproduced_per_profile_metrics.csv`.

**Macro averages (mean across 15 profiles — matches 020 reporting):**

| model | mean MAE | mean RMSE | mean MAPE | mean WAPE |
|-------|----------|-----------|-----------|-----------|
| persistence | 213.5 | 464.8 | 257.9 | 46.6 |
| svr_category_slp | 286.9 | 584.2 | 1010.1 | 58.7 |
| svr_no_slp | 289.0 | 588.3 | 1050.1 | 59.0 |

**Medians (per-profile MAE):** persistence 192.3; SVR-no-SLP 246.3; SVR+SLP 241.2.

**SVR+SLP vs persistence (per profile):** 3/15 profiles have lower SVR+SLP MAE than persistence (`02631`, `03552`, `04717`). No model wins on **mean** MAE across profiles.

## 4. SLP ablation (paired, aligned test timestamps)

| quantity | value |
|----------|-------|
| Profiles with lower MAE (SLP vs no-SLP) | **10 / 15** |
| Profiles with higher MAE | 5 / 15 |
| Mean paired MAE difference (SLP − no-SLP) | **−2.07** kWh |
| Mean relative MAE change | **−0.7%** |
| Mean paired WAPE difference | **−0.29** pp |
| Pooled micro MAPE change (SLP − no-SLP) | **−45.7** pp |
| Wilcoxon signed-rank on per-profile MAE diffs | **p = 0.073** (not significant at α=0.05) |

Profiles worsened with SLP: `02817`, `03095`, `03552`, `04721`, `04949`. Largest gain: `01003` (−18.4 MAE). Largest loss: `04949` (+11.6 MAE).

**Do not** claim a general SLP win from pooled MAPE alone; WAPE and MAE show a **small** average edge with mixed per-profile sign.

## 5. Data quality and features

Documented in `data_quality_audit.md`:

- Target `cons` is the documented harmonized load series.
- `flag` imputation markers are **not** excluded in training or test.
- Category SLP pools **train segments of all 15 local profiles** (forecast-time category template, not single-meter-only).
- ARIMA: multi-step from train+val end.
- Horizon: 1 h ahead; hourly native resolution.

**FIG-085 (Exp 019 CNAE trace):** refreshed in Experiment 020 audit from verified extracted CNAE-01 CSVs (not synthetic). 020A adds `exp020a_category_slp_hourly.png` (train-pooled template).

## 6. Figures

`results/figures/experiment_020a/` and `results/figures/ppt_ready/` (selected). Indexed as FIG-087–094.

## 7. Decisions (A–F)

| ID | Question | Answer |
|----|----------|--------|
| **A** | Is reported SLP improvement (mean MAPE) reproducible? | **Yes** — 1010% vs 1050% macro mean matches 020. |
| **B** | Does improvement persist under MAE, RMSE, WAPE? | **Partially** — median/mean MAE and mean WAPE favor SLP slightly; RMSE same direction; gains are small; Wilcoxon n.s. |
| **C** | Across many profiles or few? | **10/15** MAE improve; **5** worsen; not uniform. |
| **D** | Any learned model beat persistence? | **No** on mean/median MAE; persistence best macro MAE (213.5). |
| **E** | Is MAPE &lt; 8% meaningful here? | **No** — heavy zeros/near-zeros inflate MAPE; synopsis target not met; use WAPE/MAE for this dataset. |
| **F** | Justify expanding to 85 profiles? | **No** — persistence wins; SLP marginal; still no CER/residential; need access plan before scale-up. |

## 8. Limitations and open questions

- Agriculture-only, 15/100 CNAE-01, single archive part.
- Category SLP uses cross-profile training pool available only after multi-profile deployment.
- Timestamp timezone still naive.
- No Experiment 021, ToD, or BESS started.

## Artifacts

| File | Role |
|------|------|
| `reproduced_per_profile_metrics.csv` | Per profile × model |
| `reproduced_pooled_metrics.csv` | Macro mean (020 style) |
| `pooled_micro_metrics.csv` | Micro pooled |
| `slp_ablation_paired.csv` | SVR ablation |
| `experiment_020a_summary.json` | Machine-readable decisions |
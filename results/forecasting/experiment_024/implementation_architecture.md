# Implementation architecture (plan only — not implemented)

**Binding spec:** `results/forecasting/experiment_024c/protocol_v2_1_final_approval_candidate.md`  
**No `run_experiment_024.py` in this phase.**

## Layered modules (future)

```
data_adapters/     # GoiEner hourly, CER 30-min — dataset-specific
time_core/         # H=1, lags, seasonal naive, slots, strict <
qc/                # dedupe, conflict exclusion, sort
splits/            # 70/15/15 index + partition rules
eligibility/       # P1, P2, P3 masks → common keys
slp/               # rolling F1 category, F2 profile + cache validator
features/          # F0 shared; F1/F2 add one SLP column
models/            # persistence, sn, arima, svr
preprocess/        # train-only scalers
tune/              # validation-only HP grid
eval/              # macro/micro, Wilcoxon, bootstrap seed 24
report/            # population-tagged outputs
```

## Contracts (I/O)

| Stage | Input | Output |
|-------|--------|--------|
| Adapter | Raw CSV/ISSDA | `profiles/{id}.parquet` (timestamp, cons, qc_flag) |
| QC | parquet | `qc_report.json`, cleaned parquet |
| Splits | cleaned | `split_manifest.json` per profile |
| Eligibility | cleaned + splits | `keys_P1.parquet`, `keys_P2.parquet` |
| SLP | train history < t_origin | `slp_lookup(origin)` → slot_target cell |
| Fit | train origins on P2 keys | `model_bundle.pkl` per profile/model |
| Predict | frozen bundle + test keys | `predictions_{population}.parquet` |
| Stats | predictions | `metrics_{population}.csv`, `tests.json` |

## Shared vs dataset-specific

- **Shared:** time_core, eligibility logic, models, eval, stats.  
- **Specific:** Δ_native, lag tuple, adapter parsing, CER allocation join.

## Reproducibility

- Pin random seed 24; log git hash, protocol path, approval date, population tags on every artifact.
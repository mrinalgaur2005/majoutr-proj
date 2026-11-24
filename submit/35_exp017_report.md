# Experiment 017 — Temporal integrity and forecast evaluation audit

**Final status:** AUDIT PASSED WITH UNRESOLVED LIMITATIONS

**Command:** `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_017.py`

## Summary

This experiment audits timestamps, chronological splits, feature leakage, and baseline reproducibility for Experiments 013–016. No new forecasting models were trained. Experiment 018 (SLP) was not implemented.

## 017A — Timestamps

- **Verified:** `ceew_15min_bins_dedup.parquet` uses timezone-naive `datetime64` bins; no duplicate `(meter_id, bin)` among complete rows; median adjacent gap is 15 minutes for all meters with series length > 1.
- **Unresolved:** CEEW ReadMe does not state whether `x_Timestamp` is IST, UTC, or another convention. Do not assign a timezone without documentary evidence.
- **Plausible:** Uttar Pradesh has no DST; naive timestamps are treated as ordered civil time for splitting and calendar features.

## 017B — Splits

- Forecast **origins** `t`: train `2019-01-01 ≤ t < 2020-07-01`, validation `2020-07-01 ≤ t < 2021-01-01`, test `t ≥ 2021-01-01`.
- Target for H=1: `t + 15 minutes`.
- Recomputed eligibility matches Experiment 015 for all 84 meters (68 eligible).
- Origin index sets are disjoint across train/validation/test. Lag features at a validation or test origin may read values from earlier calendar periods (including training); they do not read future targets.

## 017C — Leakage

- Ridge α, Huber params, shrinkage λ, gate τ, and Experiment 016 rule: selected on validation only; frozen before test.
- StandardScaler: fit train for tuning; refit train+validation before test predict (documented nested protocol).
- Retrospective `|ΔP(t+1)|` tertiles and all-period cluster labels are **not** pipeline inputs.
- Calendar features for target slot at H=1: SAFE WITH CONDITIONS (known next interval clock).

## 017D — Baseline reproduction

| Model | Saved MAE | Recomputed MAE | Match |
|-------|----------:|---------------:|:-----:|
| Persistence | 0.107447 | 0.107447 | yes |
| Shrink per meter | 0.107011 | 0.107011 | yes |
| Shrink global | 0.107047 | 0.107047 | yes |
| Ridge delta | 0.110784 | 0.110784 | yes |

- `zero_change` equals `P(t)` exactly (max abs diff 0).
- 835,410 rows, 68 meters, unique `(meter, time)` keys.
- Experiment 016 `pred_load_rule` matches Experiment 015 `pred_load_shrink_meter`.

## 017E — Frozen baseline

See `frozen_baseline_specification.md`, `frozen_baseline_metrics.csv`, and `baseline_artifact_manifest.json` (SHA-256 of key artifacts under `frozen_artifacts/`).

## 017F — Experiment 018

Design only: `experiment_018_slp_protocol.md`.

## Discrepancies

See `methodology_discrepancies.csv` (notably Experiment 012 `dataset_split.json` test start date vs 013–016 origin rule; eligibility `train_rows` vs `usable_*`).

## Decision

**DEC-015:** The 013–016 evaluation protocol is sufficiently leakage-free for a cautious SLP ablation (Experiment 018), subject to unresolved timestamp semantics and the requirement that SLP features use only information available before each forecast origin.
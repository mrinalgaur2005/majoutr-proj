# Experiment 021 — GoiEner semantics and forecasting failure audit

**Date:** 2026-11-24  
**Command:** `python3 scripts/run_experiment_021.py` (~156 s, no training, no downloads)  
**Inputs:** 020A/020B predictions (SHA256 in `experiment_021_summary.json`), 15 local CNAE-01 CSVs, GoiEner README/metadata.

## Executive summary

**Classification B:** Experiment 020B results are **technically trustworthy** on aligned micro metrics. SVR and SVR+SLP **underperform persistence** because of strong hourly persistence in `cons`, high zero/near-zero mass, and **SVR over-smoothing** (predicted variance ≈59% of actual; negative bias ≈−59 kWh mean). SLP adds **no convincing** benefit (class B small/uncertain, per 020B). **Do not** expand to 85 profiles without protocol fixes.

## Part 021A — Data semantics (verified)

| Claim | Status |
|-------|--------|
| GoiEner v7.1, 28,900 metadata rows | **28900** in `metadata_public.csv` |
| CNAE division 01 = 100 | **100** (`cnae_division==1`) |
| Hourly native | **Median Δt = 1 h** (see `profile_quality_audit.csv`) |
| `cons` / `flag` / `self` / `gen` columns | **Present** in all 15 CSVs |
| End-of-interval timestamps (README) | **Documented**; loader uses rows as-is (naive TZ) |
| part01-only local extract | **15/100** CNAE-01 |

**`cons`:** README — “Electricity consumption”, harmonized SIMEL, original magnitude. **Units not stated** in README. **Not** rescaled in `load_series`.

**Flag:** README lists column; **meaning not defined** (see `flag_semantics_audit.md`, consistent with 020B).

## Part 021B — Target alignment

- **H=1:** target `y[i+1]`, features through hour `i` (`build_xy`).
- **Persistence:** `ŷ[i+1] = y[i]` — verified on samples (`target_alignment_examples.csv`; 0 mismatches in check).
- **020A/020B:** identical target timestamps across five models — sufficient for **row alignment**; semantics consistent with code (not a one-hour timestamp bug).

## Part 021C — Failure diagnosis

**020B micro MAE reproduced** (all models OK within 1e-3).

| Model | MAE | var_pred / var_actual | Mean bias |
|-------|-----|------------------------|-----------|
| persistence | 192.8 | **0.9999** | +0.06 |
| SVR+SLP | 259.0 | **0.585** | **−58.6** |
| SVR no-SLP | 261.2 | **0.588** | **−57.6** |

- SVR **compresses dynamics** and **underpredicts** on average.
- ARIMA multi-step **overpredicts** (bias +134.5).
- Extreme events catalogued in `extreme_event_audit.csv` (mostly `unresolved` / `verified_valid`; spikes present in raw data, e.g. profile **00489**).
- **MAPE:** 21%+ test hours with |actual|<1 → synopsis **8% MAPE not meaningful** (`diagnostics/mape_validity.md`).

## Part 021D–E — SLP and profiles

- Category template: train-only, pooled 15 profiles, **no val/test leakage** (`slp_feature_audit.md`).
- Template variation exists (CV≈0.8) but feature overlaps calendar encodings already in SVR.
- Per-profile SLP ΔMAE mixed (`profile_level_metrics.csv`); improvements **not** explained by single factor (descriptive scatter FIG-121).

## Research decision (021F)

See `research_decision.md`. **Trust 020B:** yes. **Expand 85:** no. **Next (not started):** protocol/metric revision design doc + CER residential track when available.

## Outputs

All under `results/forecasting/experiment_021/`; figures `results/figures/experiment_021/` (FIG-107–121).
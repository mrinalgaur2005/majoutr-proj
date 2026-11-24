# Experiment 024 — authoritative final design

**Version:** 024-design-1.0  
**Execution status:** NOT STARTED  
**Design status:** DESIGN_READY_WITH_BLOCKERS

## Hypothesis (primary)

On verified consumer categories with leakage-safe protocol, category-specific SLP features (F1) improve SVR **validation** MAE versus SVR without SLP (F0), evaluated with persistence competency gate and profile-level inference.

## Tracks

- **Track A — GoiEner CNAE-01** (agricultural): hourly, native `cons`.
- **Track B — CER residential**: 30-min kWh, Residential allocation code.

## Supporting documents

| Document | Path |
|----------|------|
| Initial audit | `initial_design_audit.md` |
| Synopsis alignment | `synopsis_alignment.md` |
| Dataset readiness | `dataset_readiness_and_eligibility.md` |
| Protocol v2.1 final | `forecasting_protocol_v2_1_final.md` |
| Statistics | `statistical_analysis_plan.md` |
| Regimes | `regime_and_anomaly_protocol.md` |
| SLP | `slp_experiment_protocol.md` |
| ToD/BESS | `tod_bess_dependency_assessment.md` |
| Positioning | `research_positioning.md` |
| Execution | `experiment_024_execution_plan.md` |
| Comparability | `dual_track_comparability.md` |

## Blockers

1. CER ISSDA not submitted/approved (Track B).
2. GoiEner `cons`/`flag` unresolved (expansion + unit claims).
3. Protocol v2.1 final human approval pending.

## Ready to execute when

- G-B1 + G-B3 and/or G-A1 + G-A2 + local ag policy approved.
- `run_experiment_024.py` implemented and split tests pass.

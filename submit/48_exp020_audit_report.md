# Experiment 020 — Dataset audit and readiness (Part 1)

**Extracted CNAE-01 profiles:** 15 / 100
**Part01 only (019 audit):** 15 / 100 — corrected by scanning all six archives.

## CNAE interpretation
- Division **01** = agriculture-related **economic activity** (CNAE), not electricity tariff class.
- Division **98** (n≈23,712) is **not** residential — do not map to synopsis residential.

## Gates
{
  "GATE1_dataset_integrity_full": false,
  "GATE1_local_integrity": true,
  "GATE1_partial": "15/100 profiles extracted locally",
  "GATE2_profile_quality": true,
  "GATE3_category_validity_residential": false,
  "GATE3_category_validity_agriculture": true,
  "GATE3_note": "CER residential PENDING_ACCESS; not a completed two-category synopsis study.",
  "GATE4_slp_readiness": true,
  "GATE5_forecast_readiness": true,
  "GATE6_evaluation_readiness": true,
  "GATE_note": "Full 100-profile audit needs parts 02\u201306 on disk or --allow-download."
}

## Forecasting authorization
`experiment_020_data_readiness.json`: forecasting_authorized=True

CER residential track remains pending. Two-category synopsis **not complete**.
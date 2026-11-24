# Target alignment audit (021B)

- Horizon **H=1** hour on hourly index (not wall-clock skip).
- All five models in 020A/B share identical `(file_id, target_timestamp)` rows.
- Persistence: $\hat{y}_{t+1} = y_{t}$ at row index (last known cons at origin hour).
- Seasonal lag-24: $\hat{y}_{t+1} = y_{t-23}$ index (168h weekly cycle uses 24h lag in code).
- Manual persistence check mismatches (sampled): **0**
- Val/test not used in SLP template (train 70% only) — see leakage audit.
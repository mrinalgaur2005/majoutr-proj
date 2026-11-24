# Anomaly and regime protocol (from 021)

## Classification
- verified_valid | potential_anomaly | confirmed_data_error | unresolved
- Evidence required in `extreme_event_audit.csv` style logs.

## Regimes (train-derived tertiles + zero + extreme)
- zero: $y=0$
- low/normal/high: train q33/q66
- extreme: $y > $ train p99

## Metrics per regime
- MAE, RMSE, bias; WAPE only if $\sum|y|$ meaningful.
- Optional: peak-event hit rate (forecast within δ of peak timing) — pre-register δ.

## Policy
- Primary evaluation on full aligned test population.
- Regime tables are diagnostic overlays (021 `regime_metrics.csv`).
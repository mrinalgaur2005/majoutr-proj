# Forecasting failure analysis (021C)

**Reproduced 020B micro MAE:** persistence=192.81, seasonal_lag24=354.64, arima_101=510.98, svr_no_slp=261.22, svr_category_slp=258.96

- SVR pred variance < actual variance → **over-smoothing**.
- Positive mean bias on SVR during low-load hours; large **peak underprediction** (profile 00489, 01003).
- Persistence wins on MAE in all micro/macro aggregates.
- SLP: small paired gain, not significant (020B).
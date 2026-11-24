# Experiment 020A data-quality notes

- **Target:** `cons` = hourly harmonized consumption (README principal variable).
- **`flag` column:** not excluded in Experiment 020 `load_series`; imputed/missing-marked hours may be included.
- **Category SLP:** template pools **training segments of all 15 profiles** (cross-meter category average).
  This matches a published category SLP but is not per-meter-only.
- **Horizon:** H=1 hour; targets are `cons` at t+1 with end-of-interval timestamps.
- **Alignment note:** Experiment 020 computed persistence/ARIMA on full `test_idx` but SVR on lag-filtered origins;
  020A saved predictions on **aligned** lag-filtered origins for all models; reproduction CSV matches 020 script math.
- **ARIMA:** multi-step forecast from train+val end (not rolling per-origin).
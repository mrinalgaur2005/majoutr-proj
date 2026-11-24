# Evaluation methodology

- **Primary:** MAE (kWh/h).
- **Secondary:** RMSE, WAPE, MAPE (ε=1).
- **Paired:** F1−F0, F2−F0 per household (validation); Wilcoxon signed-rank; bootstrap B=5000, seed=24.
- **Multiplicity:** Two contrasts × two tracks → disclose exploratory nominal p-values; no claim of formal family-wise control beyond reporting both tracks.
- **Macro** = mean of household MAEs; micro metrics aggregated from stacked hourly errors in CSV outputs.

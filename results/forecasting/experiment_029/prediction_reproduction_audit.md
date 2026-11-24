# Prediction reproduction audit

- Full prediction parquet: **not saved** for all 1,136 households.
- Sample test predictions: {'sample_predictions_present': True, 'n_rows': 39380, 'n_households': 20, 'duplicate_origin_keys': 0, 'columns': ['track', 'ID', 'origin_index', 'Date', 'Hour', 'y_true', 'pred_persistence', 'pred_F0', 'pred_F1', 'pred_F2'], 'note': 'Full-cohort predictions not saved; metrics recomputable only from per_household_metrics CSV'}

- Household-level MAE **reproduced** from `per_household_metrics_*.csv` (matches aggregate JSON: True).
- Wilcoxon F1−F0 p-value **reproduced**: True.
- Test split was **not** used for C tuning (`--fast` fixed C=10 on validation in implementation).

Metrics in Experiment 028 are **internally consistent** with saved CSVs; they do **not** prove F1 features were correctly constructed.

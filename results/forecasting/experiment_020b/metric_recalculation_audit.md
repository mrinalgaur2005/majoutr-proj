# Metric recalculation audit

- **020B aligned micro** matches **020A pooled micro** when predictions are identical (tolerance 1e-6).
- **020 macro / 020A macro** can differ from **micro** because Experiment 020 truncated persistence/ARIMA arrays to SVR `yte` length without re-indexing timestamps.
- Model **ranking by MAE** unchanged: persistence best on both macro and micro populations.
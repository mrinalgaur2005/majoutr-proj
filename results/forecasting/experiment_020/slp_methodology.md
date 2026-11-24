# SLP methodology (Experiment 020 pilot)

- **Template:** mean `cons` by hour-of-week (168 bins) from **training segment only**.
- **Feature:** template value at forecast origin (leakage-safe; no same-day future).
- **Category:** CNAE division 01 consumers pooled for template (n=local profiles).
- **Comparison:** SVR with lags+calendar ± SLP template value.
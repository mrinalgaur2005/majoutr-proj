# Alignment validation (Experiment 020B)

- Input rows: **266220**
- Duplicate (file, timestamp, model): **0**
- Intersection equals full set all profiles: **True**

## Experiment 020 vs 020A
- Experiment **020** paired persistence/ARIMA on full `test_idx` with SVR-filtered `yte` (documented in 020A).
- Experiment **020A** saved predictions on **aligned lag-filtered** timestamps for all five models.
- 020B primary comparison uses that **aligned** population (matches 020A pooled micro).

Misalignment affected **macro 020-style** metrics vs **micro** metrics; not the paired SVR rows in 020A parquet.
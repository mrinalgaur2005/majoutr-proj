# Data schema audit (Experiment 020B)

## Prediction artifact (020A)
- Path: `results/forecasting/experiment_020a/predictions/test_predictions.parquet`
- Columns: `file_id`, `timestamp`, `model`, `actual`, `predicted`
- 5 models × aligned test target timestamps per profile

## Profile CSVs
- Harmonized hourly GoiEner profiles under `data/external/goiener/interim/cnae01_profiles/profiles/`.
- Forecast target: `cons` (per README and Experiment 020 harmonization).
- Profiles audited: **15**
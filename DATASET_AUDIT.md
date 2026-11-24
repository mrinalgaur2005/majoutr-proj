# Dataset audit

The only dataset used by executable code is synthetic telemetry emitted by `IndianFeederTelemetryGenerator` in `load_forecasting_unit_commitment.py`. No CEEW files, meter metadata, raw CSV/Parquet, or external residential/agricultural labels exist in this repository.

The reproducible audit result is [dataset_audit.json](/home/mrinalgaur/Desktop/majou-proj/results/dataset_audit.json). It establishes: 6 synthetic meters, 2026-09-17 through 2026-10-31, 3-minute source sampling, 4,523 missing cells (1.904% of all cells), no duplicate timestamps, no irregular source intervals, and no negative meter readings. “Agricultural”/“residential” behaviours are latent generator rules, not real-world labels; K-Means outputs remain inferred profile clusters.

No claim about the number of CEEW meters, CEEW date coverage, CEEW missingness, or CEEW labels can be made from this project. To perform that audit, add the licensed raw data and metadata under a documented `data/` path, then rerun the audit before modelling.

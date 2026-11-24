# CEEW real-data validation status

## Dataset and ingestion

The authoritative CEEW Harvard Dataverse data has been downloaded unchanged to `data/raw/ceew_mathura_bareilly/`. A separate real-data loader is available at `src/data/ceew_loader.py`; it outputs timestamp, meter ID, interval energy, derived load, voltage, current, frequency, and city. It does not touch the synthetic pipeline or synthetic results.

## Status

The real-data audit and ingestion layer are complete. Real SLP clustering and forecasting have **not yet been executed** and no CEEW model metric, cluster claim, or real-data validation claim is made in this report. This separation is intentional: the 21.8-million-row source requires a memory-bounded 15-minute preparation stage and causal missing-data policy before modelling.

## Required next stages

1. Build 15-minute per-meter energy sums only for complete five-record bins, then calculate average kW.
2. Use the saved gap/coverage audit to exclude long outages rather than blanket spline imputation.
3. Create daily 96-slot profiles, evaluate K=2–6 with neutral cluster names and stability tests.
4. Use chronological train/validation/test windows and compare persistence, seasonal-naive, SVR-lag, and SVR-lag+SLP without weather unless a separately documented weather layer is added.

The synthetic experiment remains a controlled sanity check and must never be combined with future CEEW metrics.

# Experiment 020 protocol (design only — not implemented in 019)

## A. Research question

Does **SVR** forecasting with **category-specific standardized load profiles (SLP)**
improve short-term load forecasts versus persistence and ARIMA for **verified consumer categories**,
consistent with the original project synopsis?

**Note:** Experiment 018 on unlabeled CEEW tested one Ridge+centroid SLP design only;
it does not invalidate this synopsis hypothesis on labelled external data (DEC-017).

## B. Datasets and tracks

- **Track A (GoiEner):** CNAE division 01 agriculture (n=100 profiles in metadata) +
  at least one non-agriculture division (e.g. 10, 47) for category-specific SLPs.
- **Track B (CER):** Residential allocation code (pending ISSDA files); SME as second utility category, not agriculture.
- **Track C (CEEW):** Frozen `results/forecasting/` baseline; no invented labels.

## C. Harmonization
- Units: document kWh vs kW per dataset; CER 30-min energy → power if needed without fake 15-min grids.
- GoiEner: respect interval-end timestamps on profiles; hourly native unless sub-hourly confirmed.
- Timezone: document from README; no silent IST/UTC assumptions.

## D. SLP (leakage-safe)
- Category-specific daily/hourly SLPs fit on training segment only.
- Peak or energy normalization fixed by validation; no test selection.

## E. Models
- Persistence; ARIMA (orders by validation); SVR ± SLP ± weather.

## F. Features
- Lagged load, day type, time-of-day, category SLP distance/shape, weather where available.

## G. Evaluation
- Chronological **70/15/15** per consumer where duration permits.
- **MAPE, RMSE, R²**; per-category and aggregate; consumer-level bootstrap.

## H. Ablations
- SVR without SLP; with SLP; without weather; category-SLP vs pooled SLP.

## I. Cross-dataset
- Compare only with documented unit and horizon alignment.

## J. Downstream (design)
- Category-wise ToD tariff stress; simulated microgrid high solar — no operational claims before metrics.
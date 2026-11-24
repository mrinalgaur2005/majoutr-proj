# CER research proposal draft (for human completion)

> **Placeholder:** [INSTITUTION], [SUPERVISOR NAME], [STUDENT NAME], [EMAIL]

## Title
Short-term residential load forecasting with leakage-safe standardised load profiles and support vector regression

## Synopsis alignment (preserved)
This project tests whether **category-specific recurring load-profile information** improves **short-term** forecasts vs persistence and ARIMA, using **SVR** with and without SLP features.

## Why CER data
- GoiEner public metadata lacks verified **residential** domestic labels.
- CER trial provides **Residential / SME** allocation codes (ISSDA checklist in repo).
- Required for the **second synopsis consumer category** alongside GoiEner agriculture (CNAE-01).

## Planned use (no results claimed)
- Native **30-minute** kWh intervals; no upsampling.
- Chronological **70/15/15** per meter.
- Models: persistence, seasonal naive, ARIMA, SVR ± category SLP.
- Metrics: **MAE/WAPE** for selection; legacy **MAPE** reported separately for synopsis compliance.
- Paired statistical tests at **profile** level.

## Prior work disclosure
- A 15-profile GoiEner agriculture **pilot** did **not** beat persistence; SLP effect statistically uncertain (Experiments 020–021).
- CEEW pipeline (001–018) is supplementary unlabeled analysis.

## Outputs
Thesis chapters; conference/journal submission of **derived** aggregate results; no redistribution of raw CER microdata.
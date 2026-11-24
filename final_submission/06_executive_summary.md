# Executive summary

## Title

**Standard Load Profile-Based Characterization and SVR-Based Short-Term Electricity Load Forecasting**

## Three connected contributions

1. **SLP construction and characterization** (primary)
2. **SLP-informed SVR short-term forecasting** (primary, distinct research question)
3. **Supplementary energy management:** illustrative ToD tariff exposure and BESS procurement economics (Experiment 037)

## Contribution A — Load characterization

CEEW: 84 meters, **43,555** daily profiles. K=2 peak-normalized SLPs (silhouette ≈ **0.242**). **Experiment 036:** five 58/26 meter splits; held-out groups distinguishable (median Cliff's δ load factor **+0.98**, peak-to-average **−0.98**); centroid stability **≈ 0.983**. Pattern **regimes**, not verified consumer categories.

## Contribution B — Forecasting

Norwegian test macro MAE: persistence **0.4361**, SVR **0.4457**, SVR+SLP **0.4537** — **comparable**; limited incremental benefit from tested encodings. Descriptive SLP validity does not imply forecast gain.

## Contribution C — ToD and BESS (Experiment 037)

After validating SLP characterization, the project asks whether **temporal patterns** imply different **illustrative** ToD bill exposure and whether BESS can shift purchases profitably.

- **Tariffs:** Configurable **illustrative** INR/kWh scenarios — **not** actual utility rates.
- **ToD exposure:** Moderate spread medoids — group 0 **+0.6%** vs flat; group 1 **+18.6%** relative ToD increase (MH31 representative day).
- **BESS:** Under 90% round-trip efficiency, cyclic SOC, and tested spreads, **no positive incremental procurement savings** on medoids (₹0 at 5 kWh / 2 kW). Optimizer selects no operation. **Peak reduction ≠ bill savings** without demand charges.

## Takeaway

**Standard Load Profiles provide a structured representation of electricity consumption that supports forecasting research, temporal demand analysis, and evaluation of energy-management strategies** under explicit assumptions — without claiming guaranteed economic benefits.

## Synopsis

Original Ireland–Spain dual-category track incomplete; synopsis PDF unchanged. Details: `01_synopsis_traceability.md`. Framework diagram: `07_slp_research_framework.md`.
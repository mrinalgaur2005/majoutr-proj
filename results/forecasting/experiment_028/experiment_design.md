# Experiment design

**Classification:** `EXPLORATORY — NORWEGIAN RESIDENTIAL — DUAL TIMESTAMP SENSITIVITY`

Not a protocol-compliant Experiment 024 execution.

- **Data:** Zenodo 7856848, 1,136 residential households (`Demand_data=Yes`).
- **Tracks:** `H1_START_00`, `H1_START_01` (027 unresolved clock convention).
- **Models:** Persistence, seasonal-naive (diagnostic), SVR F0/F1/F2.
- **Split:** Chronological 70/15/15 per household on row index after sort.
- **Primary unit of inference:** household (paired Wilcoxon + bootstrap).

# Dataset harmonization (Experiment 020)

| Track | Dataset | Category | Interval | Target | Timestamp | Units |
|-------|---------|----------|----------|--------|-----------|-------|
| A | GoiEner v7.1 | CNAE **01** (economic activity) | 1 h native | `cons` | End of interval | README: hourly consumption (`cons`) |
| B | CER ISSDA | Residential (allocation code) | 30 min native | kWh / interval | Day+slot codes | **Not available** (PENDING_ACCESS) |
| C | CEEW (frozen) | None verified | 15 min | `load_kw` | Naive | kW — supplementary only |

Do not concatenate tracks. Do not upsample GoiEner to 15 min or CER to 15 min.
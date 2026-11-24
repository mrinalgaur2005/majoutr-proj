# Household join

| Metric | Value |
|--------|-------|
| households.csv rows | 4446 |
| Demand_data=Yes | 1136 |
| IDs appearing in demand.csv | 1136 |
| Eligible ∩ demand | 1136 |
| In demand but Demand_data≠Yes | 0 |
| Flagged Yes but absent from demand | 0 |

**Residential claim:** IDs in demand are subset with `Demand_data=Yes` by design (1136 households). Do not label IDs outside that join as residential.

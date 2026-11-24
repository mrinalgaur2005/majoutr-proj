# Timestamp audit

- Granularity: **hourly** (one row per ID, Date, Hour).
- **Timezone:** not embedded in CSV; Norway uses CET/CEST — **not verified in column metadata**.
- **DST:** not documented per row; transitions require external calendar — **protocol DST tests remain blocked**.
- **Duplicates:** counted at (ID, Date, Hour); conflicting values not separately aggregated in full pass (count of duplicate keys reported).
- **Ordering:** pilot sorts by constructed timestamp after ingestion.

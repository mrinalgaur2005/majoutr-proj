# Schema audit — demand.csv

| Column | Role |
|--------|------|
| ID | Household identifier (joins `households.csv`) |
| Date | Calendar date (YYYY-MM-DD) |
| Hour | Integer hour index (observed range 1–24 inclusive) |
| Demand_kWh | Hourly consumption **kWh** (column name) |

- **Rows:** 14,913,408
- **Unique IDs in demand:** 1136
- **Date span:** 2020-10-01 → 2022-03-31
- **Negative values:** 0
- **Duplicate (ID, Date, Hour) keys:** 0

**Timestamp construction (pilot only, documented assumption):** `timestamp = Date + (Hour-1) hours` treating Hour as 1–24 local index. **Interval start vs end not stated in file header** — BLOCKED for strict protocol until publisher field definition confirmed from dataset documentation page.

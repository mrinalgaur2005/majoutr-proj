# Timestamp sensitivity design

Two independent pipelines. Original `Date`, `Hour`, `Demand_kWh` unchanged.

| Track | Timestamp construction |
|-------|------------------------|
| H1_START_00 | `Date + (Hour - 1) hours` |
| H1_START_01 | `Date + Hour hours` |

Row order (publisher Date, Hour slots) is identical; lag/target eligibility uses index-equivalent grids (verified via identical origin counts in 027).

SLP slots use **native publisher Hour (1–24)** and **weekday from Date** — not IANA timezone claims.

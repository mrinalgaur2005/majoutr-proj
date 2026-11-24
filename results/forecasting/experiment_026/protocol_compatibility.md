# Protocol compatibility (binding Exp 024C)

| Requirement | Status |
|-------------|--------|
| Verified residential category | **YES** (Demand_data join) |
| Documented kWh units | **YES** |
| Hourly native horizon | **YES** (maps to H=1 hourly) |
| Lags 1/24/168 via timestamp | **FEASIBLE** after timestamp convention locked |
| P2 (no seasonal-naive required) | **FEASIBLE** structurally |
| t_available = t_timestamp | **ASSUMPTION** (same as approved idealized protocol) |
| Interval end vs start | **UNRESOLVED** |
| IANA timezone / DST | **UNRESOLVED** |
| Full Exp 024 authorized | **NO** |

**Readiness:** AUDITED + PARTIALLY PROTOCOL-ELIGIBLE — forecasting **not authorized**.

# Dataset eligibility matrix

| Dataset | Category verified | Units | Timestamp | TZ/DST | Protocol Exp 024 | Class |
|---------|-------------------|-------|-----------|--------|------------------|-------|
| CEEW | **NO** (unlabeled) | kWh implied 15-min | naive | unresolved | Partial (lags only) | **SUPPLEMENTARY** |
| GoiEner v7.1 CNAE-01 (15 local) | **YES** (metadata CNAE 01) | **UNDOCUMENTED** in v7.1 README | end-of-hour (README) | matrix DST only | **CONDITIONAL** — exploratory native-unit only | **CONDITIONALLY ELIGIBLE** |
| CER | YES (when accessed) | kWh 30-min manifest | unverified local | — | Blocked | **INELIGIBLE** (acquisition constraint + no files) |
| Norwegian Zenodo 7856848 | **YES** (1,136 metered residential) | **kWh** | Hour 1–24 index + Date (clock mapping **unresolved**) | DST **normalized** (doc §4.2); no IANA | P2 eligible **14,719,152** origins (027); Exp 024 **not authorized** | **CONDITIONALLY ELIGIBLE** |
| GoiEner legacy 7362094 | Mixed sectors in metadata | **kWh documented** | hourly | documented imputation flag | Not ag/res split in metadata | **SUPPLEMENTARY** |

No category inference from load shape.

**028 exploratory run (2026-11-24):** Norwegian SVR±SLP executed as non–Exp-024 sensitivity study; synopsis dual-category **not** closed.

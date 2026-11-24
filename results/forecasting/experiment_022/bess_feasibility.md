# BESS feasibility (022)

## Minimum viable study inputs
| Input | GoiEner | CEEW | Status |
|-------|---------|------|--------|
| Load energy/power | cons (units UNDOC) | kW 15-min | CEEW OK; GoiEner BLOCKED |
| Resolution | 1 h | 15 min | Different — no merge |
| Generation | `gen` sparse | N/A | Partial |
| Battery params | — | — | **Not in repo** |
| Tariffs | — | — | **Not in repo** |

## Conclusion
- **No BESS sizing** on GoiEner until `cons` units verified.
- CEEW could support **exploratory** simulation only with external battery assumptions (not started).
- Full techno-economic BESS requires tariffs, costs, grid rules — **NOT STARTED**.
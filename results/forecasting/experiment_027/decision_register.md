# Decision register — Experiment 027

| ID | Status | Decision |
|----|--------|----------|
| DEC-027-01 | **APPROVED** | DST normalization per Data in Brief §4.2 matches empirical 24h/day grid |
| DEC-027-02 | **UNRESOLVED** | Hour 1 / Hour 24 clock mapping not in publisher docs |
| DEC-027-03 | **PROPOSED** | Working timestamp `H1_START_00` pending human sign-off or price-alignment study |
| DEC-027-04 | **APPROVED** | Full cohort P2 eligibility computed (1136 households) |
| DEC-027-05 | **BLOCKED** | Exp 024 execution / forecasting — requires separate human authorization |
| DEC-027-06 | **ASSUMPTION** | `t_available = t_timestamp` (not dataset-verified) |

**Recommended category:** B. CONDITIONALLY READY

Structural and P2 population requirements met on full cohort; Hour 1 interval boundary and IANA timezone remain documentation gaps; t_available idealization remains labelled assumption.

**Human decision needed:** Approve DEC-027-03 timestamp convention (or require external Nordpool/Elhub alignment study) before authorizing residential Exp 024.

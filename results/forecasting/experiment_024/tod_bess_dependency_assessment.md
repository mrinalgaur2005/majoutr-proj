# ToD and BESS dependency assessment — Experiment 024

**Execution:** NOT STARTED (synopsis downstream objectives).

## Time-of-Day

| Dependency | Track A | Track B | Status |
|------------|---------|---------|--------|
| Tariff periods | Not in GoiEner v7.1 profile CSV | CER trial tariff/stimulus fields in allocation | B partial |
| Load resolution | Hourly native | 30-min native | OK for shape |
| Category labels | CNAE-01 | Residential Code | Gated |

- **024 delivers:** hourly/30-min load shapes and forecast errors only.
- Economic ToD savings require tariff schedule + verified units.

## BESS

| Dependency | Available? |
|------------|------------|
| Load units for power/energy | GoiEner blocked; CER kWh post-access |
| Tariff / price series | Not in local repo |
| Battery P/E/η | Not specified — do not invent |
| Objective (min cost vs peak shave) | Synopsis intent only |

**Blocked** until Track B units confirmed and tariff documentation obtained.

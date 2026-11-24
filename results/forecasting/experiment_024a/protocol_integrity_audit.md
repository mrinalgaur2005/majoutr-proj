# Protocol integrity audit (Experiment 024A)

**Date:** 2026-11-24  
**Scope:** Design-only; no training/downloads.

## Executive summary

| Issue | Severity | Conclusion |
|-------|----------|------------|
| A SLP calendar slot | **High** | Use **target** slot for SLP; origin slot mismatches H=1 (020 used origin) |
| B F1 cross-profile leakage | **Critical** | Demonstrated under independent 70/15/15 splits; fix = causal template at `t_origin` |
| C H=1 row vs timestamp | **High** | Replace `i+1` with timestamp equality rule |
| D Seasonal naive row offset | **Medium** | Replace with `t_target−24h` exact match; row 24/48 only if regular grid proven |
| Timezone/DST | **Blocking (partial)** | Naive civil slots only; DST tests blocked |
| Split boundaries | **Medium** | Partition by target row; same-segment rule retained |

## Cross-profile leakage demonstrated

**Yes.** Test **I** shows split-pooled F1 template at March origin polluted by June training rows from another profile (cons=50 vs 1).

## Human approval

Revised protocol **PROPOSED — NOT APPROVED** until DEC-024A-01.

# Proposed Experiment 024 (design only — NOT STARTED)

**Hypothesis:** On verified categories, leakage-safe SLP features improve SVR **validation** MAE vs SVR without SLP, and models meet persistence competency gate.

**Tracks:**
- **B (primary if CER arrives):** Residential meters, 30-min native, H=1 interval.
- **A (secondary):** GoiEner CNAE-01 only if flag/units resolved + v2.1 adopted.

**Minimum n:** CER — all available residential meters post-QC (power analysis deferred); GoiEner — do not expand beyond 15 without go gate.

**Models:** persistence, lag-24/seasonal naive, ARIMA, SVR(F0–F2 from 022 design).

**Blocked if:** CER absent → residential half not runnable; document partial ag-only sub-study.
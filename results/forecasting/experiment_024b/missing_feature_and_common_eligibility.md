# Missing features and common eligibility

## Primary rule — Strategy A (complete-case)

Origin eligible iff:
1. Unique `t_target` row with non-null `cons`.
2. Lags `1,24,168` (hourly) or `1,48,336` (30-min) exist by **timestamp**.
3. Seasonal-naive reference `t_target − 24h` exists.
4. Origin/target in same train|val|test segment.
5. Timestamp passed duplicate QC.

## Models

All six models use **identical** `(profile_id, t_target)` keys on the primary comparison.

Seasonal naive `UNAVAILABLE` → origin dropped for **all** models (no persistence substitution).

## Strategy B/C

- B (imputation): **not** primary; train-only imputation permitted only in pre-registered diagnostic branch.
- C (model-specific rows): **REJECTED** for primary paired comparison.

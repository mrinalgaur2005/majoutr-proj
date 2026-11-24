# Evaluation populations P1, P2, P3

## P1 — Six-model common (Estimand 1)

Eligible origin `o` iff:
- Valid H=1 target `t_target`.
- Lags 1/24/168 (or CER 1/48/336) by timestamp.
- Seasonal-naive reference at `t_target−24h`.
- Origin and target in same train|val|test segment.
- Duplicate QC passed.

Keys: `(profile_id, t_target)` shared by persistence, SNaive, ARIMA, F0, F1, F2.

**Primary use:** Full baseline tableau and competency gate context.

## P2 — SVR family common (Estimand 2) — **synopsis primary**

Eligible iff P1 conditions **except seasonal-naive reference**.

Keys shared by F0, F1, F2 only.

**Primary use:** Does category SLP improve SVR vs F0?

## P3 — Baseline diagnostics

Per-model masks; labeled `population=P3`; no Wilcoxon superiority vs SVR.

## Selection bias note

P1 ⊆ P2 (row-wise). P2 may be larger when SN reference missing. Profile-level MAE may use different `n` per population — always report `n_profiles`, `n_obs` per population.

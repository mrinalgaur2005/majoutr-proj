# Category-specific SLP experiment protocol — Experiment 024

Reference: `results/forecasting/experiment_022/slp_experiment_design.md` (F0–F5); **024 primary:** F0–F2.

## Representation

- **Time:** hour-of-week index h = 24×dow + hour (GoiEner); CER: 48×dow + half-hour slot.
- **Weekday/weekend:** encoded in calendar features (F0); SLP cells pool all train days.
- **Seasonal:** optional month-of-year template **F6 extension** — not primary 024 (register before use).

## F1 category template

1. Collect training rows from all **eligible** profiles in track (same category).
2. For each h, mean(cons) across training rows hitting h.
3. Store template + per-cell count; drop cells with count < 5 (use global train mean fallback).

## F2 profile template

Same as F1 but single profile train segment.

## Missing intervals

Templates use observed rows only; no imputed cons in template build.

## Normalization

- Templates in **raw cons units** (Track B kWh; Track A native).
- SVR input scaling: StandardScaler on features, fit train origins only.

## Conditions tested

| Condition | Question |
|-----------|----------|
| F1 vs F0 | Category recurring pattern helps SVR? |
| F2 vs F0 | Profile-specific pattern helps beyond lags? |
| F2 vs F1 | Individual shape vs pooled category |

## Leakage checks (Stage 3 validation)

- Assert no val/test timestamp in template build logs.
- For random origins, SLP feature == template lookup at calendar(h(i)).

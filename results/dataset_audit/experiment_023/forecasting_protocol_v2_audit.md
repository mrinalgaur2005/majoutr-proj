# Forecasting protocol v2 audit

Source: `results/forecasting/experiment_022/forecasting_protocol_v2.md`

## Strengths
- Native resolution; shared test timestamps; chronological split; train-only SLP; persistence gate.

## Gaps addressed in v2.1
1. **Split boundaries:** Use per-consumer integer indices; last `floor(0.7n)`, `floor(0.85n)` rows.
2. **Calendar alignment:** Do **not** require same calendar dates across consumers.
3. **Missing timestamps:** Predictions only at observed indices; gaps do not create synthetic targets.
4. **Val/test gap:** No overlap; targets with `origin+1` in val belong to val targets.
5. **Cross-boundary targets:** Exclude origins where `i+1` crosses split boundary.
6. **Incomplete history:** Require `i >= max(lags)` (e.g. 168).
7. **Macro vs micro:** Report both; infer at profile level.
8. **Normalization:** Fit scalers on train origins only.

## Proposed changes recorded in `forecasting_protocol_v2_1.md` (does not replace v2).
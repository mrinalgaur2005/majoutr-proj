# Experiment 022 — Protocol revision, data access, and completion roadmap

**Command:** `python3 scripts/run_experiment_022.py` (0.0s)

## Completion status
- **CEEW pipeline (001–018):** COMPLETE (supplementary; unlabeled).
- **Synopsis dual-category forecasting:** PARTIAL/BLOCKED (ag pilot only; res pending CER).
- **SLP hypothesis on ag pilot:** NOT demonstrated vs persistence.
- **ToD / BESS:** NOT STARTED (infeasible without tariffs/units).

## Key numbers (from 021/020B, verified in 022)
- Persistence MAE micro: **192.81**
- SVR+SLP: **259.0**; SVR: **261.2**
- SLP Wilcoxon p: **0.073**

## Recommendations
1. **CER access** — critical for residential requirement.
2. **Do not** extract 85 GoiEner profiles until semantics + protocol gates pass.
3. Next **implementation** experiment: controlled SLP ablation (design in `slp_experiment_design.md`) — **not started**.

See component files in this directory.
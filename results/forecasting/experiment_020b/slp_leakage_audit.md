# SLP leakage audit (Experiment 020B)

## Implementation (Experiment 020 `run_experiment_020_forecast.py`)
1. `category_slp()` aggregates mean `cons` by hour-of-week using **chronological train slice only** (`slice(0, 70%)`) from each profile.
2. Template is computed **once** before the per-profile loop; validation and test periods are excluded from template counts.
3. SLP feature at origin `i` uses template value at hour/dow of row `i` — no future consumption from the same day beyond origin.
4. SVR scalers fit on **train origins only** (not val/test).

## Cross-profile pooling
- Template pools train segments from all **15** local CNAE-01 profiles — category information available at forecast time by design, but not a single-meter-only template.

## Findings
- **No test/val leakage** into category template or SVR scaling in the reference implementation.
- **No per-origin template refresh** using future data; static train-only template.
- Cross-profile train pooling is a **methodological choice**, not timestamp leakage.

## Corrected artifact
- No corrected forecasts required for leakage; 020A predictions remain the historical reference.
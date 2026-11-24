# Metric framework (Experiment 022)

## Definitions (aligned with 020/020A)
- **MAE:** $\mathrm{MAE} = \frac{1}{n}\sum |y-\hat{y}|$
- **RMSE:** $\mathrm{RMSE} = \sqrt{\frac{1}{n}\sum (y-\hat{y})^2}$
- **WAPE:** $\mathrm{WAPE} = 100 \cdot \sum|y-\hat{y}| / \max(\sum|y|, \epsilon)$
- **MAPE (legacy synopsis):** $\mathrm{MAPE} = 100 \cdot \frac{1}{n}\sum |y-\hat{y}| / \max(|y|, \epsilon)$ with $\epsilon=1$ kWh-scale.
- **MAPE-thresholded (diagnostic):** same with $|y| \ge \tau$ filter; report $\tau$.
- **R²:** $1 - \mathrm{SSE}/\mathrm{SST}$ on test.

## Selection vs synopsis compliance
| Role | Metric |
|------|--------|
| **Scientific model selection** | MAE (primary), WAPE (secondary), regime-stratified MAE |
| **Synopsis compliance reporting** | MAPE (legacy ε=1), RMSE, R² — report without using for selection |

## Rationale (021)
- Near-zero mass inflates legacy MAPE (021 audit).
- Persistence MAE micro = **192.81**; synopsis MAPE <8% **not met** on 020 pilot.

## Inference unit
- Profile-level paired comparisons; bootstrap **profiles** (not pooled hours) for SLP ablation.
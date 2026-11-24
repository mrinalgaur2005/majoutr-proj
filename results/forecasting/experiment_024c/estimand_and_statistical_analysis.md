# Estimands and statistical analysis

## Estimand 1 — Overall model comparison (P1)

- **Target population:** eligible origins on P1 per profile and split.
- **Metric primary:** MAE; supplementary RMSE, WAPE.
- **Macro:** mean of per-profile MAE on P1.
- **Micro:** pooled errors over all P1 `(profile, t_target)` rows.
- **Tests:** Wilcoxon on paired per-profile MAE vs persistence (pre-registered contrasts).
- **Bootstrap:** resample **profiles**, B=5000, seed=24.

## Estimand 2 — SLP incremental value (P2)

- **Contrasts:** F1−F0, F2−F0, optional F2−F1 on **P2 keys only**.
- Same macro/micro and Wilcoxon/bootstrap at profile level.
- **Competency gate:** validation MAE ≤ 1.05× persistence (evaluated per profile; report on P1 for full baseline context, pre-specify in implementation).

## Small samples

If eligible profiles < 10: inferential tests reported as **exploratory** with exact n.

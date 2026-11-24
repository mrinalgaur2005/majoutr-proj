# Forecasting protocol v2 (design — not implemented)

## Scope
- Applies to future Track A (GoiEner) and Track B (CER) after data gates.

## Horizon and target
- Native sampling interval; **H=1** step on chronological index.
- Target: documented consumption at $t+1$; origin at $t$.
- All models share identical `(consumer_id, target_timestamp)` test rows.

## Split
- Chronological 70/15/15 per consumer; no random shuffle.
- Hyperparameters chosen on **validation only**.

## Missing data
- Document per-dataset rules; exclude vs impute must be pre-registered.
- GoiEner `flag`: do not map to imputation without publisher definition.

## Zeros and outliers
- Zeros retained unless publisher excludes.
- Outliers: three-class audit (valid / anomaly / error); no test-driven deletion.
- Regime thresholds from **train tertiles** per consumer.

## Features & SLP
- No all-period cluster labels (CEEW lesson).
- SLP features use data strictly before forecast origin.

## Baseline competency gate (pre-specified)
- Before SLP claims: learned model MAE on validation ≤ $1.05 \times$ persistence MAE **or** explicit waiver in decision register.
- SLP benefit requires (A) paired improvement over same SVR **and** (B) not worse than persistence unless hypothesis is SLP-only diagnostic.

## Statistics
- Wilcoxon on per-profile MAE differences; bootstrap over profiles (seed fixed).
- Report macro (mean of per-profile metrics) and micro (pooled hours) separately.
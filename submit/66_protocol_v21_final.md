# Forecasting protocol v2.1 — FINAL (Experiment 024 design)

    **Status:** PROPOSED — requires human approval (DEC-024-01).  
    **Does not replace:** `results/forecasting/experiment_022/forecasting_protocol_v2.md` or `results/dataset_audit/experiment_023/forecasting_protocol_v2_1.md`.

    This document merges v2, v2.1 additions, and 024 audit clarifications.

    ---

    ## Base protocol (from v2 — unchanged intent)

    > # Forecasting protocol v2 (design — not implemented)

> ## Scope
> - Applies to future Track A (GoiEner) and Track B (CER) after data gates.

> ## Horizon and target
> - Native sampling interval; **H=1** step on chronological index.
> - Target: documented consumption at $t+1$; origin at $t$.
> - All models share identical `(consumer_id, target_timestamp)` test rows.

> ## Split
> - Chronological 70/15/15 per consumer; no random shuffle.
> - Hyperparameters chosen on **validation only**.

> ## Missing data
> - Document per-dataset rules; exclude vs impute must be pre-registered.
> - GoiEner `flag`: do not map to imputation without publisher definition.

> ## Zeros and outliers
> - Zeros retained unless publisher excludes.
> - Outliers: three-class audit (valid / anomaly / error); no test-driven deletion.
> - Regime thresholds from **train tertiles** per consumer.

> ## Features & SLP
> - No all-period cluster labels (CEEW lesson).
> - SLP features use data strictly before forecast origin.

> ## Baseline competency gate (pre-specified)
> - Before SLP claims: learned model MAE on validation ≤ $1.05 \times$ persistence MAE **or** explicit waiver in decision register.
> - SLP benefit requires (A) paired improvement over same SVR **and** (B) not worse than persistence unless hypothesis is SLP-only diagnostic.

> ## Statistics
> - Wilcoxon on per-profile MAE differences; bootstrap over profiles (seed fixed).
> - Report macro (mean of per-profile metrics) and micro (pooled hours) separately.

    ---

    ## v2.1 additions (finalized)

    ### A. Horizon H=1

    | Track | Interval | Target | Origin |
    |-------|----------|--------|--------|
    | A GoiEner | 1 h | `cons[i+1]` at next row | Row `i`, features ≤ `i` |
    | B CER | 30 min | kWh at `i+1` | Row `i`, features ≤ `i` |

    - **GoiEner:** timestamp = **end** of hour containing energy for `[t-1h, t]`.
    - **CER:** use manifest time codes; treat target timestamp as documented interval end/start consistently in loader (document choice in Stage 1 audit).

    - **First eligible origin:** `i >= max(LAGS)` (default lags 1, 24, 168 in 020 — CER 30-min: use lags 1, 48, 336).
    - **Last eligible origin in split S:** largest `i` such that `i+1` index lies in S.

    ### B. Chronological split (per profile)

    Let `n` = number of observed rows after QC.

    ```
    n_train = floor(0.70 * n)
    n_val   = floor(0.15 * n)
    n_test  = n - n_train - n_val
  TRAIN = [0, n_train)
    VAL   = [n_train, n_train + n_val)
    TEST  = [n_train + n_val, n)
    ```

    - No shuffle. Profiles may have different calendar spans.
    - **Forbidden:** any target whose index `i+1` is not in the same split as origin's split assignment for training targets (origins in TRAIN predict train targets only; val/test analogous).
    - Hyperparameter tuning: **validation only**.

    ### C. Leakage prevention

    - Scalers: fit on **train origins** of each profile (same for SVR input).
    - Category SLP template (F1): hour-of-week mean using **training rows of all eligible profiles in track**, excluding val/test rows.
    - F2 profile template: train segment of **that profile only**.
    - For forecast at train/val/test origin at `i`, SLP feature uses template cell matching calendar at `i` (not future).
    - **Self-inclusion (F1):** target profile's train rows contribute to category pool (standard practice); val/test never contribute.

    ### D. Model family (preserve 022 F0–F2)

    | Model | Definition |
    |-------|------------|
    | Persistence | ŷ[i+1] = y[i] |
    | Seasonal naive | ŷ[i+1] = y[i+24] (GoiEner) or y[i+48] (CER) when index exists |
    | ARIMA | ARIMA(1,0,1) on train series; refit per profile optional (pre-register) |
    | SVR F0 | Lags + sin/cos hour + weekend — no SLP |
    | SVR F1 | F0 + category hour-of-week SLP from train pool |
    | SVR F2 | F0 + per-profile hour-of-week SLP from train only |

    SVR hyperparameters: grid from 020; select on validation MAE. F0 vs F1 vs F2 differ **only** by SLP feature column(s).

    ### E. Resolution

    - **Separate pipelines** per track. No pooled micro metrics across tracks.

    ### Competency gate (DEC-022 preserved)

    Validation MAE(model) ≤ 1.05 × Validation MAE(persistence) per profile.

    - Failing profiles: report explicitly; exclude from SLP superiority claims only if pre-registered (default: include with flag).

    ### SLP claim

    Requires SVR(F1 or F2) beats SVR(F0) on **validation** (paired across profiles) AND report vs persistence.

    ### Statistics

    Wilcoxon signed-rank on per-profile MAE deltas; bootstrap resample **profiles** (B=5000, seed=24); macro + micro metrics per `metric_framework.md`.

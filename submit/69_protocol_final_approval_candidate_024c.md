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

---

# Experiment 024A revisions — PROPOSED — NOT APPROVED

**Date:** 2026-11-24  
**Supersedes for execution only after human approval (DEC-024A-01).**  
**Does not overwrite** `forecasting_protocol_v2_1_final.md`.

## Summary of corrections

1. **H=1:** Defined by timestamp: `t_target = t_origin + Δ_native` (1h or 30min). Row `i+1` used **only** if its timestamp equals `t_target`. Otherwise origin **ineligible**.
2. **SLP calendar (F1/F2):** SLP feature uses **`slot_target`** (hour-of-week / half-hour-of-week of the **target interval**), not `slot_origin`. F0 cyclic hour/weekend features remain at **origin** (decision time).
3. **F1 causality:** Category template at origin `τ` uses all profiles' observations with `timestamp < τ` (strict). Per-profile split partitions define **evaluation sets only**, not the F1 information set.
4. **F2 causality:** Profile template uses rows from that profile with `timestamp < τ` only.
5. **Seasonal naive:** `ŷ(t_target) = y(t_target − 24h)` elapsed-time match; unavailable if exact reference row missing. **Civil-calendar previous-day** match and **dow×hour week-ago** row-offset alternatives are blocked until timezone metadata verified.
6. **Partitions:** Origin index `i` and H=1 target row must map to the **same** train/val/test segment (by target row index).
7. **Lag features:** Timestamp lookup for lags `1,24,168` (or `1,48,336`): require exact `t_origin − k·Δ_native` rows; else lag unavailable → origin ineligible unless persistence-only baseline path.
8. **Timezone:** Civil slot indexing uses **naive** timestamps as stored. **BLOCKED:** DST-aware templates until dataset supplies IANA timezone or documented convention (CER + GoiEner).

## Notation

- `t_origin`: timestamp of forecast origin row (end-of-interval semantics per dataset docs).
- `t_target = t_origin + Δ_native`.
- `slot_target`: `dow(t_target)*24 + hour(t_target)` (168) or `*48 + half-hour slot` (336).

## F1 recommended (primary)

**Rolling causal category template (Approach 2/3):** recompute or query cached template from all category rows with `timestamp < t_origin` at each evaluation origin. Matches rolling deployment; demonstrated **leakage** in legacy split-pooling (Test I).

## Duplicate timestamps

QC flags duplicates; H=1 ineligible if `|{t : t=t_target}| ≠ 1`. Policy: **keep first** after sort, log dropped rows in Stage 2.

  ---

  # Experiment 024B approval addendum — PROPOSED — AWAITING HUMAN APPROVAL

  **Date:** 2026-11-24  
  **Approval gate:** DEC-024B-01 (supersedes DEC-024A-01 for execution binding).  
  **Does not overwrite** 024A proposed revision or original v2.1 final.

  ## Issue B resolutions (024B)

### Information set (primary — DEC-024B-02 PROPOSED)

  | Component | Rule |
  |-----------|------|
  | Forecast issuance `t_issue` | **ASSUMPTION:** `t_issue = t_origin` (GoiEner); CER blocked until manifest |
  | Measurement availability `t_available` | **ASSUMPTION:** `t_available = t_timestamp` (no invented latency) |
  | F1 / F2 template rows | `t_timestamp < t_origin` (**Policy A strict**) |
  | Lag features, persistence `y(t_origin)` | Exact rows at `t_origin − k·Δ_native`; **no staleness fallback** |
  | Policy C (`t_available`) | **BLOCKED** until publisher fields exist |

  **Deployment:** Primary = **rolling one-step-ahead**; optional **fixed batch** with global `τ_cutoff` documented.

  ### Duplicates (DEC-024B-03 PROPOSED)

  - Exact duplicates (all compared fields match): keep one, log.
  - Conflicting duplicates (same `timestamp`, differing `cons` or unresolved aux): **exclude timestamp** from all models.
  - No arbitrary first-row for conflicts; **replaces 024A keep-first blanket rule**.

  ### Common eligibility (DEC-024B-04 PROPOSED)

  **Strategy A (primary):** mask `M(origin)` true iff H=1 target valid, all lags valid, seasonal-naive reference valid, origin partition valid, no QC flags.

  All models evaluated on identical `(profile_id, t_target)` keys where `M` is true.

  **Strategy B imputation:** not used in primary comparison (optional diagnostic track only).

  ### Persistence

  `ŷ(t_target) = y(t_origin)` requires exact origin row; no older-stale substitute.

  ### SLP slot

  Unchanged from 024A: `slot_target` from `t_target`.

  ---

  # Experiment 024C — final consolidated addendum
  **Status:** PROPOSED — AWAITING HUMAN APPROVAL (DEC-024C-01)
  **Supersedes review target:** DEC-024B-01 (binding approval shifts here)

  ## Evaluation populations (DEC-024C-02 PROPOSED)

  | ID | Role | Eligibility |
  |----|------|-------------|
  | **P1** | **Primary six-model** estimand | H=1, lags, partition, QC, **+ seasonal-naive ref** |
  | **P2** | **Primary SLP** estimand (synopsis core) | H=1, F0 lags/features, partition, QC; **no SN required** |
  | **P3** | Diagnostic only | Per-model eligible rows; not for superiority claims |

  **Resolution of 024B single-mask tension:** Requiring SN for all six models (024B) is **too restrictive for SLP inference**.  
  - **Estimand 1** (overall baselines): report on **P1** with label `population=P1`.  
  - **Estimand 2** (SLP incremental): report F1/F2 vs F0 on **P2** with label `population=P2`.  
  - Never merge P1 and P2 in one table without population column.

  ## Rolling / zero-latency (DEC-024C-03 PROPOSED)

  **IDEALIZED ASSUMPTION (not verified):**

  - `t_interval = [t_timestamp − Δ_native, t_timestamp]` (GoiEner end-stamp documented).
  - `t_available = t_timestamp` (**zero publication latency**).
  - `t_issue = t_origin = t_timestamp` of forecast origin row.
  - Interpretation: predictive accuracy under **instantaneous availability at interval end**, not DSO operational latency.

  **Templates:** recompute from all rows with `t_timestamp < t_origin`; incremental cache allowed if bit-identical to full recompute (Test I).

## DEC-024B-04 amendment

  Strategy A split into P1 and P2 masks; both use identical keys **within** population and model set.

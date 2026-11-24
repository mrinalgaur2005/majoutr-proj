# Experiment 024 — initial design audit

  **Date:** 2026-11-24  
  **Type:** Design-only (Experiment 024 design audit, not execution)

  ## Documents inspected

  | Artifact | Location | Note |
  |----------|----------|------|
  | Protocol v2 | `results/forecasting/experiment_022/forecasting_protocol_v2.md` | Frozen 022 design |
  | Protocol v2.1 **proposal** | `results/dataset_audit/experiment_023/forecasting_protocol_v2_1.md` | **Not** under `experiment_022/` (discrepancy) |
  | Metric framework | `results/forecasting/experiment_022/metric_framework.md` | MAE primary |
  | SLP F0–F5 | `results/forecasting/experiment_022/slp_experiment_design.md` | 024 core uses F0–F2 |
  | Regime protocol | `results/forecasting/experiment_022/anomaly_and_regime_protocol.md` | Train tertiles |
  | 024 sketch | `results/dataset_audit/experiment_023/experiment_024_proposed_design.md` | Superseded by this experiment |
  | Pilot code | `scripts/run_experiment_020_forecast.py` | F1 category SLP implemented |
  | 021 evidence | `results/forecasting/experiment_021/experiment_021_summary.json` | Persistence wins MAE |

  ## 1. Already implemented

  - CEEW pipeline (001–018): clustering, shrinkage forecasting, SLP protocol 018 (no MAE win vs persistence).
- GoiEner CNAE-01 **pilot** (020/020A/020B/021): 15 profiles, chronological 70/15/15, SVR±SLP, ARIMA, persistence, aligned micro metrics.
  - Leakage-safe **category** hour-of-week template from train pool (matches F1).
  - Literature review (023): 9 verified DOIs.
  - CER access **package** (023): not submitted.

  ## 2. Experimentally validated

  - Persistence is strong on GoiEner ag pilot (micro MAE ≈ 192.8 vs SVR ≈ 261).
  - SLP Wilcoxon **not significant** at conventional levels (021); SLP constructs without index leakage.
  - MAPE unstable on zero-heavy `cons`; WAPE/MAE preferred (022 metric framework).
  - 020A reproduced 020 metrics (25/25).

  ## 3. Remains proposed design

  - Full Experiment 024 dual-track execution.
  - Protocol v2.1 **final** adoption (this experiment produces `forecasting_protocol_v2_1_final.md`).
  - F2 per-profile SLP ablation at scale.
  - CER residential track ingestion and QC.
  - Regime stratification on CER (pending documentation review post-access).

  ## 4. Blocked — data access

  - **Track B (CER):** No local interval files; ISSDA application **PREPARED_NOT_SUBMITTED**.
  - Residential inclusion requires `SME and Residential allocations.xlsx` after download.

  ## 5. Blocked — dataset semantics

  - GoiEner v7.1: `cons` **units undocumented**; `flag` **undefined** in README.
  - Expansion to 85 profiles: **NO-GO** (DEC-022/023).

  ## 6. Requires human decision (status PROPOSED)

  - **DEC-024-01:** Approve `forecasting_protocol_v2_1_final.md` for implementation.
  - **DEC-024-02:** Submit CER ISSDA application.
  - **DEC-024-03:** Send GoiEner author query (recommended before ag expansion).
  - **DEC-024-04:** Go/NO-GO on Track A with **native-unit** forecasting if units stay unresolved.

  ## 7. Must implement before execution

  - `run_experiment_024.py` (not written): dual-track loaders, CER QC, split validator, SLP builder, model runners, stats module.
  - Split-boundary unit tests (origins with `i+1` crossing splits excluded).
  - Train-only scaler fit per profile.

  ## Document discrepancies and resolutions

  | Issue | Resolution |
  |-------|------------|
  | v2.1 path in prompt vs repo | Authoritative proposal: `dataset_audit/experiment_023/`; **final** copy in `experiment_024/forecasting_protocol_v2_1_final.md` |
  | 023 design Track B=CER vs naming | **Track A = GoiEner ag; Track B = CER residential** (synopsis order preserved in reporting) |
  | 020 uses `int(n*0.70)` not `floor` | **Final:** `i_train = floor(0.70*n_obs)` per v2.1 final (document equivalence when n large) |
  | MAPE ε=1 assumes kWh | GoiEner: use ε relative to train median \|y\| until units confirmed; CER: kWh from manifest |

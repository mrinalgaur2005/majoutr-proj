# Experiment 020B — Evaluation integrity and imputation sensitivity

**Date:** 2026-11-24  
**Command:** `python3 scripts/run_experiment_020b.py` (~134 s, seed **202**, bootstrap **5000**)  
**Inputs:** Experiment 020A `test_predictions.parquet` + local CNAE-01 CSVs (no re-forecast, no downloads).  
**Unchanged:** `experiment_020/`, `experiment_020a/`, CEEW 001–018.

## Research questions

| RQ | Finding |
|----|---------|
| **RQ1 Alignment** | 020A predictions are **fully intersected** (53,244 rows/model; 0 exclusions). Experiment **020 macro** paired unequal test-origin counts; **020B micro** uses one timestamp set. |
| **RQ2 Original vs aligned** | 020B aligned micro **matches 020A micro** (MAE Δ &lt; 1e-4). Macro mean MAE (020-style) ≠ micro pooled (e.g. persistence 213.5 vs 192.8). |
| **RQ3 Imputation / flag** | Official `flag` meaning **undocumented** in README; binary 0/1 used as operational tiers. Metrics differ by tier (see imputation outputs). |
| **RQ4 SLP on flag_zero** | Mean per-profile ΔMAE **−0.97** (7/12 profiles with flag_zero test hours improve); Wilcoxon p=0.38. |
| **RQ5 SLP leakage** | Train-only category template; val/test excluded (`slp_leakage_audit.md`). |
| **RQ6 020A conclusions** | **Stand**: persistence wins MAE; SLP edge small; Wilcoxon p≈0.073; expand not justified. |

## Aligned metrics (micro pooled)

| model | MAE | RMSE | WAPE % |
|-------|-----|------|--------|
| persistence | 192.8 | 528.7 | 31.8 |
| svr_category_slp | 259.0 | 658.3 | 42.7 |
| svr_no_slp | 261.2 | 665.7 | 43.1 |

## SLP ablation (aligned, ΔMAE = SLP − no-SLP)

| population | mean ΔMAE | micro ΔMAE | improved | Wilcoxon p | bootstrap mean CI |
|------------|-----------|------------|----------|------------|-------------------|
| all | **−2.07** | −2.26 | 10/15 | **0.073** | [−5.25, 0.91] |
| flag_zero (target hour) | −0.97 | −1.24 | 7/12 | 0.38 | [−4.18, 2.55] |
| flag_nonzero | −2.36 | −3.05 | 7/13 | 0.31 | [−6.28, 0.96] |

Test target hours: **23,436** flag_zero + **29,808** flag_nonzero (operational classes).

## Flag semantics (summary)

See `flag_semantics_audit.md`. README lists `flag` but does not define it. Individual profile files pre-date annual-matrix `n_imput`. **Do not** label flag=1 as officially “imputed” without publisher codebook.

## Final decisions (1–10)

1. **020 macro comparisons** were affected by mixed-origin pairing; **020A/020B aligned** comparisons were not.  
2. **Ranking unchanged:** persistence best MAE on macro and micro.  
3. **Yes**, persistence remains strongest.  
4. **Yes**, small SLP MAE improvement on aligned micro (−2.26).  
5. **Not** statistically significant (p=0.073; bootstrap CI crosses 0).  
6. SLP effect **smaller** on flag_zero-only (mean Δ −0.97).  
7. **Yes**, operational flag tier shifts MAE levels (see FIG-008).  
8. **No template leakage** from val/test into category SLP.  
9. **No** — 15-profile pilot still insufficient for 85-profile expansion.  
10. Next: CER access + disciplined full-sample protocol; optional single-meter SLP ablation.

**SLP hypothesis class: B** — small, uncertain improvement (not A/C/D).

## Artifacts

`results/forecasting/experiment_020b/` — CSVs, JSON, markdown audits; `predictions/aligned_test_predictions.parquet`.  
Figures: `results/figures/experiment_020b/` (FIG-095–106).
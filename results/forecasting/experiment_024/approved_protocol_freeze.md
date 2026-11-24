# Approved protocol freeze — Experiment 024

## A. Approval metadata

| Field | Value |
|-------|--------|
| Approved protocol path | `results/forecasting/experiment_024c/protocol_v2_1_final_approval_candidate.md` |
| Approval date | 2026-11-24 |
| Approved decision IDs | DEC-024C-01, DEC-024C-02, DEC-024C-03 |
| Approval authority | Human researcher (explicit formal approval) |
| Superseded for execution | Original v2.1 (`experiment_024/forecasting_protocol_v2_1_final.md`); 024A proposed revision; 024B approval candidate |
| Historical records | Preserved unchanged (no deletion) |
| Execution status | **NOT AUTHORIZED** — design approved only |

## B. Approved model family

1. Persistence  
2. Seasonal naive  
3. ARIMA(1,0,1)  
4. SVR F0 (lags + cyclic hour + weekend, no SLP)  
5. SVR F1 (F0 + category rolling causal SLP)  
6. SVR F2 (F0 + profile rolling causal SLP)  

## C. Approved evaluation design

- **P1:** Six-model common population (includes seasonal-naive reference requirement).  
- **P2:** SVR F0/F1/F2 common population — **primary SLP estimand**.  
- **P3:** Unpaired baseline diagnostics only.  
- P1 and P2 reported **separately** with explicit `population` labels.  

## D. Approved SLP methodology

- F1: rolling causal category template (`timestamp < t_origin` all profiles).  
- F2: rolling causal profile template (`timestamp < t_origin` same profile).  
- SLP feature uses **target interval calendar slot** (`slot_target`).  
- No validation/test or cross-profile future information in templates.  

## E. Approved timestamp and horizon methodology

- H=1: `t_target = t_origin + Δ_native`; exact timestamp match (no blind `i+1`).  
- Lags: GoiEner 1,24,168; CER 1,48,336 — exact timestamp lookup.  
- Seasonal naive: `y(t_target − 24h elapsed)` with exact match or unavailable.  
- Duplicates: exact dedupe; **conflicting** timestamps excluded (no arbitrary first-row).  

## F. Approved statistical methodology

- MAE primary; RMSE/WAPE supplementary.  
- Macro (per-profile) and micro (pooled) metrics.  
- Wilcoxon signed-rank on per-profile MAE; bootstrap profiles B=5000, seed=24.  
- Train-derived regime thresholds.  
- Competency gate: validation MAE ≤ 1.05 × persistence.  

## G. Approved operational assumption (idealized)

```
t_issue = t_origin
t_available = t_timestamp   # zero publication latency — ASSUMPTION, not verified
```

All published results must label forecasts as evaluated under this **idealized information set**, not verified DSO operational latency.

## H. Execution restriction

Protocol design is **frozen and approved**. Experiment 024 **Stage 1+** blocked until Stage 0 metadata gates (see `stage_0_dataset_readiness_plan.md`).
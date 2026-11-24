# Master project status

**Updated:** 2026-11-24 (protocol approval freeze)

## Synopsis

Short-term load forecasting with SVR ± category SLP on **verified residential and agricultural** smart-meter categories; ToD/BESS downstream. **Unchanged.**

## Approved protocol

- **Binding:** `results/forecasting/experiment_024c/protocol_v2_1_final_approval_candidate.md`  
- **Freeze record:** `approved_protocol_freeze.md`  
- **Design audits:** 024, 024A, 024B, 024C complete  

## Experiments completed (001–024C)

| Range | Role |
|-------|------|
| 001–018 | CEEW supplementary; persistence strongest; no SLP benefit demonstrated (018) |
| 019–023 | Dataset audit, pilots, literature, CER package |
| 024–024C | Protocol design → **APPROVED** |
| **024 execution** | **NOT STARTED** |

## Negative findings (preserved)

- CEEW: persistence wins MAE under tested formulation; shrinkage marginal.  
- GoiEner pilot (n=15): persistence **outperformed** SVR and SVR+SLP; SLP not convincingly beneficial.  
- **No** MAPE &lt;8% achievement; **no** SLP superiority claim.

## Track status

| Track | Design | Data | Execution |
|-------|--------|------|-----------|
| CEEW | Frozen supplementary | Local | No further forecast runs planned as synopsis core |
| GoiEner ag | Approved | 15/100 local | BLOCKED (metadata + expansion gate) |
| CER residential | Approved | No access | BLOCKED (ISSDA) |

## Next phase

**Experiment 025–026 (2026-11-24):** Public-only constraint. CER **unavailable**. Norwegian **demand.csv ingested** (1,136 residential HH); protocol residential track **audited, not authorized**. GoiEner 15-profile descriptive only.

**Not complete:** Original synopsis dual-track (Ireland CER residential + GoiEner ag at full protocol), hypothesis test under binding Exp 024, ToD/BESS.
### 2026-11-24 — Experiment 035

BESS validated for presentation; forecasting track frozen at persistence (031).

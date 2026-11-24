# Synopsis alignment — Experiment 024

Original synopsis preserved. This table maps **original objectives** to evidence and 024 role.

| Synopsis objective | Existing evidence | 024 contribution | Remaining work | Completion criteria |
|--------------------|-------------------|------------------|----------------|---------------------|
| Short-term load forecasting | 020 pilot; CEEW 012–016 | Native-resolution H=1 protocol both tracks | Execute 024 after gates | Test MAE/WAPE reported both tracks |
| Residential category | None on-meter | Track B design + CER eligibility rules | ISSDA access + QC | Residential Code meters evaluated |
| Agricultural category | GoiEner CNAE-01 n=15 | Track A protocol; optional F2 | Semantics + expansion gate | ≥15 eligible profiles post-QC |
| SVR forecasting | 020 implemented | F0/F1/F2 with frozen hyperparam grid | Implement 024 script | Competency gate on validation |
| SLP features | 020 F1 category template | Controlled F1 vs F2; train-only templates | Run ablation | Paired ΔMAE validation + test confirm |
| vs conventional (ARIMA, persistence) | 021 persistence wins | Pre-registered baselines | Same | Honest reporting if SVR fails gate |
| Category SLP improves forecast? | **Not demonstrated** | Primary hypothesis test | Full dual track | Validation SLP gain + stats |
| MAPE < 8% | Not met (020) | Synopsis reporting only | Report separately | No pass/fail on MAPE alone |
| ToD analysis | 019/022 design only | Dependency assessment doc | Tariff data | Descriptive load-shape after forecast |
| BESS application | Blocked 022 | Dependency assessment | Units + prices | Not in 024 scope |

**Novelty (023 preserved):** contribution = rigorous leakage-safe **category-labelled** evaluation, not SVR+SLP invention.

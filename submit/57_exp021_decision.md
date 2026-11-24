# Research decision (021F)

**Classification: B** — Results are technically valid; current SVR/SLP design is inadequate vs persistence.

1. **Trust 020B?** Yes for aligned micro metrics and pairing (reproduced).
2. **Persistence benchmark?** Valid for H=1 on this index.
3. **SVR adequate?** No — underpredicts variance and peaks.
4. **SLP correct?** Leakage-safe but weak added signal (correlated with calendar).
5. **Why poor?** Data zeros/spikes + simple persistence + RBF SVR smoothness + pooled template.
6. **Extract 85 profiles?** Not until protocol/metric issues addressed.
7. **Before scale:** semantics, metrics, anomaly policy, template design.
8. **Next:** Controlled protocol revision experiment (design only) or residential CER track when available.
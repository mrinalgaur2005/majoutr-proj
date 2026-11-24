# Final project readiness (Experiment 035)

## A. Demonstrated

- **CEEW residential load profiling (Mathura–Bareilly):** 84 meters, 15-minute `load_kw`, daily profiles, K=2 peak-normalized clusters (Experiments 032–033).
- **Time-of-day / demand shape analysis:** Load factors, peak-to-average, cluster statistics (032).
- **BESS peak-shaving simulation on physical profiles:** Rule, relaxed LP, MILP with exclusivity/no-export (033–035).
- **Energy accounting audit and conversion-loss metric** superseding defective `loss_kwh` (034–035).
- **Norwegian residential cohort forecasting pipeline** on clean matrix with cohort-scale benchmarks (030).
- **Frozen persistence baseline** after systematic baseline audit (031).

## B. Partially demonstrated

- **SVR ± SLP forecasting:** Implemented and benchmarked; **does not beat persistence** on corrected data (030–031).
- **Standard load profiles (SLP):** Used in Norwegian track; **CEEW category-specific agricultural SLP** not replicated from original Ireland–Spain synopsis.
- **Agricultural vs residential profiling:** CEEW urban residential only; GoiEner CNAE-01 profiles audited but not fused into forecasting (019).
- **BESS representative performance:** Medoid meter-days only; sensitivity characterized; **not population-wide**.
- **Rule-based cyclic peak shaving:** Feasible cluster 0 medoid; **infeasible** cluster 1 medoid under stated constraints (035).

## C. Not demonstrated

- **Ireland–Spain deployment comparison** from original synopsis (different geography/datasets).
- **Distribution-network transformer relief, voltage, feeder congestion** (no topology/ratings).
- **Tariff / ToD bill savings, payback, carbon** (no verified tariffs).
- **Microgrid unit commitment / full optimal power flow** (design references only).
- **CER/EnergyBench full ingestion** at scale (access/metadata checks only).

## Synopsis alignment statement

The repository delivers a **coherent alternative evidence chain** (CEEW ToD + BESS + Norwegian forecasting audit) that addresses the *engineering intent* of the major project (profiles → forecast → storage application) without completing every geography or asset class in the original synopsis text.

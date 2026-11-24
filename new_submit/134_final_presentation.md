# Final evaluation presentation (~12–15 minutes)

**Format:** 15 slides. **Audience:** Electrical engineering faculty (minimal ML background).

---

## Slide 1 — Title and team

**Message:** Scope and honest framing.

**Bullets:**
- Short-term load forecasting + ToD + BESS on smart-meter data
- CEEW (India) + Norwegian residential audit
- [Student name(s)], [Guide], B.Tech EE

**Figure:** None

**Speaker notes:** State upfront that the Ireland–Spain dual-category synopsis was blocked on data access; we document an alternative chain.

---

## Slide 2 — Motivation

**Message:** Peaks matter for distribution assets and flexibility.

**Bullets:**
- Growing peak demand and volatility
- Smart meters enable 15-minute visibility
- Storage can shave local peaks if operated within physics

**Figure:** `figures/exp032_peak_to_avg.png`

**Notes:** Peak-to-average spread motivates both forecasting and storage.

---

## Slide 3 — Original objectives (synopsis)

**Message:** What the proposal asked for.

**Bullets:**
- Residential + agricultural categories (Ireland/Spain)
- SVR + category SLPs, baselines, MAPE
- ToD and storage/microgrid extensions

**Figure:** None (refer to synopsis PDF)

**Notes:** Do not imply all objectives are complete.

---

## Slide 4 — Methodology workflow

**Message:** Engineering chain actually built.

**Bullets:**
- Data QA → profiles → clustering
- Forecasting benchmark (Norway)
- ToD (CEEW) → BESS simulation → audit (034–035)

**Figure:** `results/figures/experiment_024_design/exp024_synopsis_dependencies.png` (optional in repo)

**Notes:** Experiments 001–035 chronological in repo, not on slide.

---

## Slide 5 — Datasets

**Message:** Two evidence tracks.

**Bullets:**
- **CEEW:** 84 meters, 15-min, 43,555 days
- **Norway:** residential cohort for forecasting
- GoiEner/CER: audit only

**Figure:** `figures/exp032_ceew_mean_daily.png`

**Notes:** CEEW has no ag/res labels.

---

## Slide 6 — Load profile characterization

**Message:** Typical daily demand shape.

**Bullets:**
- Mean load factor ≈ 0.31
- Weekend ≈ weekday energy
- Peak timing analysed in Exp 032

**Figure:** Same as slide 5 or ToD weekday figure from Exp 032.

---

## Slide 7 — Clustering (K=2)

**Message:** Two shape regimes discovered.

**Bullets:**
- K=2 peak-normalized k-means
- Cluster 0: higher energy, flatter (LF 0.47)
- Cluster 1: lower energy, spikier (P2A 6.8)
- **Not** labelled residential/agricultural

**Figure:** `figures/exp032_cluster_profiles.png`

---

## Slide 8 — Forecasting setup

**Message:** Rigorous splits and baselines.

**Bullets:**
- Chronological train/val/test
- Macro MAE over households
- SVR + SLP features evaluated

**Figure:** None

---

## Slide 9 — Baseline comparison

**Message:** Persistence wins.

**Bullets:**
- Test macro MAE: **persistence 0.436**
- SVR tuned 0.446 — **worse**
- Frozen baseline = persistence (Exp 031)

**Figure:** `figures/exp031_test_macro_mae.png`

**Notes:** MAE, not peak reduction — keep units clear.

---

## Slide 10 — SVR findings

**Message:** Negative but valuable result.

**Bullets:**
- SVR implemented and tuned
- SLP features do not rescue performance vs persistence
- Data quality (Exp 030) essential before claiming model gains

**Figure:** `figures/exp031_pers_vs_svr_scatter.png`

---

## Slide 11 — Time-of-Day

**Message:** Clusters differ in peak behaviour.

**Bullets:**
- ToD statistics complete on CEEW
- Supports BESS representative selection
- No tariff savings claimed

**Figure:** `figures/exp032_peak_to_avg.png`

---

## Slide 12 — BESS model

**Message:** Behind-the-meter 5 kWh / 2 kW illustration.

**Bullets:**
- η_rt = 90%, SOC 10–90%, Δt = 15 min
- Grid import = load − discharge + charge (no export)
- Energy audit in Exp 034–035

**Figure:** `figures/exp033_soc_trajectory.png`

---

## Slide 13 — Rule vs MILP dispatch

**Message:** Optimisation beats rule on peak % with cyclic SOC.

**Bullets:**
- C0 medoid: **13%** rule (cyclic) vs **27%** MILP
- C1 medoid: **51%** rule vs **58%** MILP
- Cluster 1 **cyclic rule infeasible**

**Figure:** `figures/exp035_dispatch_comparison.png`

---

## Slide 14 — Engineering results (load shape)

**Message:** What faculty should remember.

**Bullets:**
- Physical meter-days BR29 / MH31
- Conversion loss ~0.03–0.12 kWh/day (not Exp 033 loss_kwh)
- Spiky cluster → larger % peak cut

**Figure:** `figures/exp033_cluster1_before_after.png` and/or `exp033_cluster0_before_after.png`

---

## Slide 15 — Limitations & conclusion

**Message:** Synopsis alignment honesty.

**Bullets:**
- Ireland–Spain categories: **not demonstrated**
- No transformer/voltage/tariff claims
- **Demonstrated:** profiling, ToD, BESS audit, persistence baseline
- Future: CER access, multi-day BESS, causal dispatch

**Figure:** `figures/exp034_conversion_loss.png` (optional: explain accounting fix)

**Notes:** End with “questions welcome.”
# Final Project Report

## Title page information

**Title:** Standard Load Profile-Based Characterization and SVR-Based Short-Term Electricity Load Forecasting

**Subtitle:** SLP characterization, out-of-sample validation, SLP-informed SVR evaluation, and integrated ToD / BESS energy-management analysis

**Degree:** B.Tech, Electrical Engineering (Major Project)

**Institution:** [Insert institution name]

**Student name(s):** [Insert name(s)]

**Guide:** [Insert guide name]

**Academic year:** 2025–26

---

## Abstract

Electricity consumption is heterogeneous across meters and days. This project develops **Standard Load Profile (SLP)** representations from 15-minute smart-meter data, validates their **descriptive usefulness** through rigorous out-of-sample testing, and evaluates **SLP-informed support-vector regression (SVR)** against strong forecasting baselines. On the CEEW Mathura–Bareilly dataset (84 meters, 43,555 complete daily profiles), peak-normalized K=2 clustering identifies two recurring **daily pattern regimes** (not verified consumer categories). **Experiment 036** shows that training-frozen centroids assign held-out meter-days to groups with distinguishable load factor, energy, peakiness, and diurnal structure (13/13 metrics: median Benjamini–Hochberg q < 0.05; median Cliff's δ up to 0.98 for load factor; centroid stability correlation ≈ 0.983). Forecasting evaluation on a corrected Norwegian residential cohort (1,136 households) yields test macro MAE **persistence 0.4361**, **SVR tuned 0.4457**, **SVR+SLP features 0.4537**—**comparable performance** with **limited incremental benefit** from the tested SLP encodings. **Experiment 037** links SLP groups to **illustrative** Time-of-Day tariff exposure and BESS procurement-cost analysis (building on Exp 032 ToD statistics and Exp 035 battery physics). Supplementary peak-shaving simulations (Experiments 033–035) remain distinct from tariff economics. The original Ireland–Spain residential/agricultural synopsis comparison was not completed at full protocol scale; traceability is documented without altering stored metrics or the synopsis PDF.

**Keywords:** standard load profiles, load characterization, clustering, support vector regression, short-term forecasting, smart metering, time-of-day analysis, battery energy storage

---

## 1. Introduction

Distribution planning and demand response depend on understanding **how** electricity is consumed across the day, not only **how much**. Standard Load Profiles compress high-dimensional daily curves into interpretable patterns. Machine-learning forecasters such as SVR can ingest calendar, lag, and profile-derived features—but whether SLP information **helps prediction** is an empirical question distinct from whether SLPs **describe** consumption well.

This project pursues **(A)** SLP-based load characterization, **(B)** SLP-informed SVR forecasting evaluation, and **(C)** supplementary energy-management analysis (ToD tariff exposure and BESS economics) grounded in the same profiles. See `07_slp_research_framework.md`.

## 2. Problem statement

1. Construct auditable daily load profiles from smart-meter data.
2. Identify recurring profile regimes and representative SLP centroids.
3. Validate that SLPs assign meaningfully to **unseen** meters (out-of-sample).
4. Integrate leakage-safe SLP features into SVR and compare with baselines.
5. (Supporting) Relate characterized profiles to ToD statistics and illustrative BESS dispatch.

## 3. Research objectives

| # | Objective | Primary track |
|---|-----------|---------------|
| O1 | Build 96-point daily profiles with QA | A |
| O2 | Peak-normalized clustering and SLP centroids | A |
| O3 | Out-of-sample SLP assignment and statistical validation | A (Exp 036) |
| O4 | SLP-informed SVR pipeline and baseline zoo | B |
| O5 | ToD statistics and peak-shaving physics (032–035) | Supporting |
| O6 | Integrated SLP → ToD → BESS economic evaluation (037) | Supporting |

Original synopsis objectives (dual geography, CER/GoiEner categories) are mapped in `01_synopsis_traceability.md`.

## 4. Literature review

Experiment 023 assembled verified references on SVR load forecasting, load-shape features, and smart-meter data quality. Empirical benefit of profile features is dataset- and encoding-dependent; this project reports measured outcomes rather than assumed superiority.

## 5. Dataset description

### 5.1 CEEW Mathura–Bareilly (characterization)

84 meters; 15-minute `load_kw`; **43,555** eligible daily profiles; predominantly 2019–2021. **No verified residential/agricultural labels.**

### 5.2 Norwegian residential (forecasting evaluation)

Open residential cohort (1,136 households) used after CEEW/CER access gates; corrected demand matrix (Experiment 030). **Evaluation cohort**, not a synopsis geography substitute.

### 5.3 GoiEner / CER (synopsis alignment)

Experiment 019 audits: GoiEner CNAE metadata and **15** on-disk agricultural pilot profiles; CER **pending access**. Not presented as a completed dual-country study.

## 6. Data preprocessing

Completeness thresholds, duplicate handling, energy residual checks; 3-minute to 15-minute binning with complete-bin rule; daily profile construction documented in foundation pipeline and Experiment 032.

## 7. Daily load-profile construction

Each meter-day: **96** observations at 15-minute resolution. Metadata includes daily energy (kWh), peak kW, load factor, peak-to-average ratio, and timestamp coverage flags.

Population summary (Experiment 032): mean load factor **0.312**; mean peak-to-average **4.76**; weekday/weekend daily energy comparable (~8.1 kWh).

## 8. Standard Load Profile generation

SLPs are **representative normalized daily shapes** (centroids) plus optional distance features for forecasting. Peak normalization \(P_t/\max_t P_t\) emphasizes **shape**; magnitude is retained in parallel for energy statistics.

## 9. Load-profile characterization and clustering

K-means on peak-normalized shapes; **K=2** retained for engineering interpretability and stability:

| Group | Days (in-sample fit) | Mean daily kWh | Mean LF | Notes |
|-------|----------------------|----------------|---------|-------|
| 0 | 19,063 | 10.93 | 0.467 | Flatter daily shape |
| 1 | 23,574 | 6.20 | 0.199 | Spikier daily shape |

In-sample silhouette (K=2, peak-normalized, subsample): **≈ 0.242**. Seed-to-seed label agreement ARI **≥ 0.999** (`verified_context.json`, Experiment 036). **These are daily pattern regimes, not verified consumer categories.**

## 10. Experiment 036: Out-of-sample characterization validation

**Research question:** Can SLPs learned from a subset of meters characterize distinct consumption patterns in previously unseen meters?

**Design (five repeated splits, seeds 1042–1046):**

- Grouped split: **58 train / 26 test meters** (70/30); no meter leakage.
- K=2 KMeans on peak-normalized **training days only**; centroids frozen.
- Test days assigned by nearest centroid (Euclidean).
- Consumption metrics computed on **held-out** unnormalized observations.
- Mann–Whitney U, Cliff's δ, Benjamini–Hochberg FDR; circular statistics for peak hour.
- Reproducibility: duplicate run `stats_match: true`.

**Results (held-out):**

- **13/13** metrics: median BH-adjusted **q < 0.05** across splits.
- Median Cliff's δ: load factor **+0.98**; peak-to-average **−0.98**; intra-day CV **−0.70**; daily energy **+0.29**; afternoon energy fraction **−0.40**; peak slot **+0.11**.
- Mean pairwise matched centroid correlation: **0.983**.
- **Conclusion:** Training-derived SLPs assign unseen meter-days to groups with distinguishable consumption characteristics. This supports **descriptive** usefulness; it does **not** prove forecasting improvement or consumer-class identity.

**Limitations:** Random meter splits (not geographic stratification); shape–magnitude partial confounding; modest peak-hour effect size.

Evidence: `results/forecasting/experiment_036/`; figures `exp036_*` in `final_submission/figures/`.

## 11. SVR forecasting methodology

RBF SVR with scaled features; chronological splits; macro MAE over households (Experiment 031). Hyperparameter search on validation. No retraining in this documentation pass.

## 12. SLP-informed forecasting framework

Train-only centroids; past-day profile distances; causality rules per Experiment 024 protocol revisions. Multiple encodings tested on CEEW (012–018) and Norwegian tracks (028–030).

## 13. Forecasting evaluation and baseline comparisons

**Norwegian cohort — test macro MAE (Experiment 031):**

| Model | Test MAE |
|-------|----------|
| Persistence | **0.4361** |
| SVR (tuned) | 0.4457 |
| SVR F0 (SLP-related features) | 0.4537 |
| Ridge | 0.4641 |

**Interpretation:** Persistence is a **strong reference** at this horizon. SVR ± tested SLP features remain in a **similar error band**; the evaluation does **not** establish operational advantage from the implemented encodings. Experiment 036 results are **independent** of this forecasting conclusion.

## 14. Discussion

- **Characterization vs forecasting:** Experiment 036 shows SLPs can **describe** heterogeneous patterns out-of-sample; Norwegian metrics show **limited predictive increment** from tested SLP features—both statements can hold simultaneously.
- **Shape vs magnitude:** Peak normalization drives clustering; energy and LF differences are measured on raw kWh/kW curves.
- **Synopsis gap:** Dual-category Ireland–Spain experiment not completed; CEEW/Norway chain documented transparently.

## 15. Foundational ToD statistics (Experiment 032)

Before tariff economics, Experiment 032 quantifies **when** energy is consumed: peak timing, weekend/weekday stacks, load-factor and peak-to-average distributions by cluster. This descriptive layer shows that SLP groups differ in **temporal structure**—a prerequisite for asking how the same groups would interact with **time-dependent prices**.

## 16. SLP-based Time-of-Use tariff analysis and battery energy storage evaluation (Experiment 037)

Integrated supplementary chapter linking **SLP characterization → illustrative ToD exposure → BESS procurement economics**. Peak-shaving physics from Experiments 033–035 is reused; Experiment 037 adds **energy-cost** objectives and explicit tariff windows. Conceptual flow: `07_slp_research_framework.md`.

### 16.1 Motivation

Once recurring daily patterns are identified (Sections 8–10), engineers can ask how those patterns interact with **time-varying electricity prices** and **behind-the-meter storage**. Different shapes place different fractions of daily energy in off-peak, shoulder, and peak periods. A BESS can shift grid purchases across those periods—but profitability depends on price spread, efficiency, power/energy limits, and cycling constraints. This is an **application of temporal information in load profiles**, not a separate optimisation project.

### 16.2 Relationship between SLPs and ToD tariffs

Time-of-Day (ToD) tariffs assign a price per kWh to each interval. For a fixed daily profile, the **procurement cost** is \(\sum_t P_t \cdot \Delta t \cdot \pi_t\) where \(\pi_t\) is the illustrative price. Two SLP groups with different diurnal shapes will accumulate different shares of energy in expensive periods even under the **same** tariff table.

### 16.3 Tariff scenarios and methodology

**No actual utility tariff** exists in the repository. `configs/experiment_037_tariff.json` defines **illustrative** INR/kWh scenarios (sensitivity only; **not** CEEW/Indian utility rates).

**Moderate spread (example):** off-peak **₹5**, shoulder **₹8**, peak **₹12** per kWh. Slot windows partition 96 × 15-minute intervals (off-peak: 00:00–06:00 and 22:00–24:00; shoulder: 06:00–09:00 and 18:00–22:00; peak: 09:00–18:00—see config for exact slot indices).

**Stage A:** Compute flat-reference bill and ToD bill per profile; period energy (off/shoulder/peak); optional **hypothetical** load-shift (not observed behaviour). Sample: 30 meter-days per SLP group plus medoids **BR29** (group 0) and **MH31** (group 1).

### 16.4 Results: differential tariff exposure

**Moderate spread, medoids (illustrative INR, single representative days):**

| SLP group | Medoid | Flat bill (₹) | ToD bill (₹) | Relative change (ToD vs flat) |
|-----------|--------|--------------:|-------------:|------------------------------:|
| 0 | BR29 | 108.24 | 108.91 | **+0.6%** (ToD higher) |
| 1 | MH31 | 20.06 | 23.80 | **+18.6%** (ToD higher) |

**Interpretation:** Group 0 has **higher absolute** illustrative bills (larger daily energy). Group 1's representative day incurs a **larger relative** ToD penalty because a greater share of its energy falls in peak-priced intervals. This demonstrates **differential tariff exposure** from different consumption patterns—not verified consumer categories or population-wide bills.

Sample means (moderate spread, n=30/group): group 0 mean ToD **₹69.36**/day; group 1 **₹39.46**/day (`tables/stage_a_tariff_bills.csv`).

### 16.5 Relationship between ToD tariffs and BESS

A battery can **charge** when \(\pi_t\) is low and **discharge** to reduce grid imports when \(\pi_t\) is high, subject to SOC, power, efficiency, no-export, and exclusive charge/discharge rules (Experiment 035 MILP formulation, adapted to **cost** objective in Experiment 037).

### 16.6 BESS optimization methodology

- **Physics:** Round-trip efficiency **90%**, SOC **10–90%**, initial SOC **50%**, cyclic final SOC, Δt = 15 min, no grid export.
- **Configurations:** 1–15 kWh capacity × 0.5–3 kW power (**240** scenario rows on two medoids × three ToD spreads × rule/MILP).
- **Methods:** No BESS baseline; rule-based ToD arbitrage; **MILP** procurement-cost minimization with binary exclusivity. If dispatch would **increase** cost vs no-BESS (losses + cycling), **`no_bess_optimal`** safeguard selects zero operation (documented).

### 16.7 Results: BESS economics

Under tested illustrative spreads (low/moderate/high), **no positive incremental procurement savings** on medoids across the capacity/power grid.

**Moderate spread, 5 kWh / 2 kW, MILP (from `experiment_037_summary.json`):**

| Group | ToD bill without BESS (₹) | With BESS (₹) | Incremental savings (₹) | Peak reduction |
|-------|--------------------------:|--------------:|------------------------:|----------------|
| 0 | 108.906 | 108.906 | **0** | **0%** |
| 1 | 23.804 | 23.804 | **0** | **0%** |

**Why the optimizer does not operate the battery:**

1. **Conversion losses** (≈0.04 kWh/day on aggressive cycles) add grid energy.
2. **Cyclic SOC** requires net zero stored-energy change; arbitrage cannot leave “free” energy in the pack.
3. Illustrative **peak/off-peak spreads** (up to 4/16 INR/kWh in high scenario) are **insufficient** vs 10% round-trip loss for these medoid shapes.
4. **No demand charges** — reducing peak kW does not add a separate monetary term.

### 16.8 Engineering interpretation

Experiment 037 shows that **SLP-based characterization supports structured energy-management questions**: (i) which pattern groups face higher **relative** ToD exposure; (ii) whether BESS **could** theoretically arbitrage under stated physics. The **negative/null economic outcome** is a valid engineering result: peak shaving (Exp 035) and bill reduction (Exp 037) decouple when only **energy** prices apply.

### 16.9 Limitations

Illustrative tariffs only; two medoids for BESS economics; no demand charges; no network/tariff reality; hypothetical load-shift not behavioural; **not** population-wide savings claims.

### 16.10 Conclusion (Chapter 16)

Experiment 037 **applies** validated SLP groups to ToD exposure and BESS procurement analysis without claiming guaranteed bill savings. It completes the narrative: **profiles → temporal structure → tariff exposure → storage economics**.

### Prior BESS peak-shaving context (Experiments 033–035)

Separate from tariff cost, medoid **peak reduction** at 5 kWh / 2 kW: group 0 **13.3%** (cyclic rule) / **26.7%** (MILP peak objective); group 1 **51.2%** / **58.3%** (MILP). These are **physical grid-import peak** metrics, not Exp 037 energy bills.

## 17. Limitations (project-wide)

Incomplete synopsis geographies; clusters ≠ tariff classes; illustrative tariff and BESS economics; forecasting cohort ≠ CEEW population. See traceability matrix and Exp 037 `limitations.md`.

## 18. Conclusion

The project delivers: **(A)** credible SLP construction and **out-of-sample validation** (Experiment 036); **(B)** transparent **SLP-informed SVR evaluation** with strong persistence baselines; **(C)** supplementary **ToD/BESS energy-management analysis** grounded in the same profiles (Experiment 037). **Standard Load Profiles provide a structured representation that supports forecasting research, temporal demand analysis, and evaluation of storage strategies under explicit assumptions**—without implying universal economic benefit.

## 19. Future scope

Geographic or labelled splits; richer SLP encodings; CER/GoiEner ingestion at synopsis scale; causal BESS dispatch coupled to forecasts; per-meter SVR.

## 20. References

`references/bibliography.md`; Experiment 023 literature pack.

## Appendices

- **A:** Figure and claim index — `05_figure_and_evidence_index.md`
- **B:** Tables — `tables/`
- **C:** Experiment 036 split assignments — `results/forecasting/experiment_036/split_assignments/`
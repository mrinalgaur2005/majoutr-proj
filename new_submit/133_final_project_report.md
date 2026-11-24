# Final Project Report

## Title page information

**Title:** Standard Load Profile-Based Characterization and SVR-Based Short-Term Electricity Load Forecasting

**Subtitle:** Daily load-profile construction, out-of-sample SLP validation, SLP-informed SVR evaluation, and supplementary ToD / BESS studies

**Degree:** B.Tech, Electrical Engineering (Major Project)

**Institution:** [Insert institution name]

**Student name(s):** [Insert name(s)]

**Guide:** [Insert guide name]

**Academic year:** 2025–26

---

## Abstract

Electricity consumption is heterogeneous across meters and days. This project develops **Standard Load Profile (SLP)** representations from 15-minute smart-meter data, validates their **descriptive usefulness** through rigorous out-of-sample testing, and evaluates **SLP-informed support-vector regression (SVR)** against strong forecasting baselines. On the CEEW Mathura–Bareilly dataset (84 meters, 43,555 complete daily profiles), peak-normalized K=2 clustering identifies two recurring **daily pattern regimes** (not verified consumer categories). **Experiment 036** shows that training-frozen centroids assign held-out meter-days to groups with distinguishable load factor, energy, peakiness, and diurnal structure (13/13 metrics: median Benjamini–Hochberg q < 0.05; median Cliff's δ up to 0.98 for load factor; centroid stability correlation ≈ 0.983). Forecasting evaluation on a corrected Norwegian residential cohort (1,136 households) yields test macro MAE **persistence 0.4361**, **SVR tuned 0.4457**, **SVR+SLP features 0.4537**—**comparable performance** with **limited incremental benefit** from the tested SLP encodings. Supplementary ToD analysis (Experiment 032) and audited BESS simulations on representative physical days (Experiments 033–035) demonstrate downstream applications. The original Ireland–Spain residential/agricultural synopsis comparison was not completed at full protocol scale; traceability is documented without altering stored metrics or the synopsis PDF.

**Keywords:** standard load profiles, load characterization, clustering, support vector regression, short-term forecasting, smart metering, time-of-day analysis, battery energy storage

---

## 1. Introduction

Distribution planning and demand response depend on understanding **how** electricity is consumed across the day, not only **how much**. Standard Load Profiles compress high-dimensional daily curves into interpretable patterns. Machine-learning forecasters such as SVR can ingest calendar, lag, and profile-derived features—but whether SLP information **helps prediction** is an empirical question distinct from whether SLPs **describe** consumption well.

This project therefore pursues two linked contributions: **(A)** SLP-based load characterization and **(B)** SLP-informed SVR forecasting evaluation.

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
| O5 | ToD / BESS as supplementary applications | Supporting |

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

## 15. Supplementary: Time-of-Day analysis

Experiment 032: peak timing distributions, weekend/weekday stacks, cluster-conditional ToD statistics—links profile regimes to **when** demand occurs.

## 16. Supplementary: BESS applications

Behind-the-meter 5 kWh / 2 kW simulation on physical medoid meter-days (BR29, MH31); rule, LP, MILP dispatch; energy accounting per Experiments 034–035. Medoid peak reductions at baseline sizing: cluster 0 **13.3%** (cyclic rule) / **26.7%** (MILP); cluster 1 **51.2%** / **58.3%**. Illustrative only—not population-wide or network claims.

## 17. Limitations

Incomplete synopsis geographies; clusters ≠ tariff classes; BESS not field-validated; no network/tariff models; GoiEner pilot scale; forecasting cohort ≠ CEEW population.

## 18. Conclusion

The project delivers credible **SLP construction**, **in-sample and out-of-sample characterization** (Experiment 036), and a full **SLP-informed SVR investigation** with preserved metrics. Load characterization—including frozen-centroid assignment to unseen meters—is the strongest demonstrated engineering thread. Forecasting evaluation shows **comparable** SVR/SLP performance versus persistence, with **limited** demonstrated improvement from tested profile features.

## 19. Future scope

Geographic or labelled splits; richer SLP encodings; CER/GoiEner ingestion at synopsis scale; causal BESS dispatch coupled to forecasts; per-meter SVR.

## 20. References

`references/bibliography.md`; Experiment 023 literature pack.

## Appendices

- **A:** Figure and claim index — `05_figure_and_evidence_index.md`
- **B:** Tables — `tables/`
- **C:** Experiment 036 split assignments — `results/forecasting/experiment_036/split_assignments/`
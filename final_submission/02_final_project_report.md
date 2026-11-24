# Final Project Report

## Title page information

**Title:** Short-Term Electrical Load Forecasting, Time-of-Day Characterisation, and Battery Energy Storage Simulation Using Smart-Meter Data

**Degree:** B.Tech, Electrical Engineering (Major Project)

**Institution:** [Insert institution name]

**Student name(s):** [Insert name(s)]

**Guide:** [Insert guide name]

**Academic year:** 2025–26

**Repository:** `majou-proj` (Experiments 001–035)

---

## Abstract

This project examines whether recurring load-profile information from smart-meter data improves short-term forecasting, and how representative load shapes inform time-of-day (ToD) analysis and behind-the-meter battery energy storage system (BESS) peak shaving. A CEEW Mathura–Bareilly dataset (84 meters, 15-minute derived demand, 2019–2021) provides load profiling, K=2 peak-normalized clustering, ToD statistics, and a validated BESS simulation on physical kW profiles. A parallel Norwegian residential cohort (Experiments 030–031) implements a leakage-safe forecasting benchmark after data-quality correction; **persistence** is the frozen baseline (test macro MAE **0.4361**), and support-vector regression (SVR) with standard load profile (SLP) features does not outperform persistence. BESS results on representative medoid meter-days show **13.27%** (rule, cyclic on cluster 0) and **26.69%** (mixed-integer programme, cluster 0) peak reduction, versus **51.17%** / **58.32%** on a spikier cluster 1 medoid, with conversion losses **~0.03–0.12 kWh/day** (not the defective Experiment 033 `loss_kwh` field). The original Ireland–Spain dual-category synopsis is **not** fully completed; an alternative evidence chain is documented with explicit limitations.

**Keywords:** smart metering, load profiling, clustering, SVR, persistence, time-of-day, BESS, MILP, energy balance

---

## 1. Introduction

Distribution utilities face rising peak demand and greater variability from electrification. High-resolution smart-meter data enable load profiling, short-horizon forecasting, and consumer-side flexibility studies. This project combines statistical profiling, machine-learning forecasting benchmarks, and a physically consistent BESS dispatch model on real smart-meter observations.

## 2. Background and motivation

Recurring diurnal patterns motivate SLP-based features. Support-vector regression offers nonlinear mapping from lag and calendar features. Storage can shave local peaks if dispatch respects state-of-charge (SOC) and efficiency limits. The work follows the engineering chain: **profiles → forecast → ToD → storage application**.

## 3. Problem statement

Given 15-minute consumer demand, (i) discover dominant daily shape regimes, (ii) compare forecasting models with rigorous baselines, (iii) characterise ToD and peak behaviour, and (iv) quantify behind-the-meter peak shaving with verified energy accounting.

## 4. Original objectives

The unchanged synopsis (`Major Project Synopsis SVR LoadForecasting.pdf`) targets residential (Ireland/CER) and agricultural (Spain/GoiEner) categories, SVR with category SLPs, persistence/ARIMA baselines, MAPE reporting, ToD analysis, and storage/microgrid extensions. See `01_synopsis_traceability.md`.

## 5. Literature review

Experiment 023 verified nine peer references on load forecasting, SVR, and standard profiles (`results/literature_review/experiment_023/`). SVR+SLP is established in literature but not guaranteed to dominate simple baselines on every cohort.

## 6. Dataset descriptions

### 6.1 CEEW Mathura–Bareilly

- **Meters:** 84; **interval:** 15 minutes (from 3-minute `t_kWh`).
- **Period:** largely 2019-05-01 to 2021-10-31.
- **Daily profiles:** 43,555 complete 96-slot days (Exp 032).
- **Definition:** `load_kw = interval_energy_kWh / 0.25 h`.
- **Limitations:** no consumer category field; timezone unverified.

### 6.2 Norwegian residential (forecasting track)

- Used after CER/GoiEner access gates (Experiments 026–031).
- Cleaned demand matrix (Experiment 030); 1136 households in baseline zoo (Experiment 031).

### 6.3 GoiEner / CER (synopsis track)

- Audited in Experiment 019; **not** full ingestion at synopsis scale.

## 7. Data preprocessing and quality assurance

Duplicate 15-minute bins removed; completeness rules for 96 slots; energy residual checks \(|\\sum load\\cdot0.25 - E_{day}| < 0.5\) kWh for BESS inputs. Norwegian track: memmap corruption found and fixed in Experiment 030 (DEC-030).

## 8. Load profile characterisation

Mean daily energy similar weekday/weekend (~8.12 vs 8.17 kWh). Mean load factor **0.312**; mean peak-to-average **4.76** (Exp 032).

## 9. Clustering methodology

K-means on peak-normalized 96-point shapes; **K=2** selected for engineering interpretation. Cluster 0: 19,075 days, mean daily energy **10.93 kWh**, LF **0.467**, P2A **2.25**. Cluster 1: 23,562 days, **6.19 kWh**, LF **0.199**, P2A **6.79**. Clusters describe **shape/magnitude regimes**, not verified “residential/agricultural” labels (DEC research_log).

## 10. Short-term load forecasting methodology

Chronological train/validation/test splits; macro mean absolute error (MAE) over households; SVR with calendar and lag features; SLP-derived features in Norwegian tracks; binding protocol Experiment 024 (approved, execution contingent on data gates).

## 11. Forecasting baseline comparisons

Experiment 031 test macro MAE (kW normalised scale): **persistence 0.4361**, SVR tuned **0.4457**, SVR F0 **0.4537**, ridge **0.4641**, seasonal-naive 24h **0.5900**. Frozen baseline: **persistence** (`frozen_baseline_configuration.json`).

## 12. SVR performance analysis

SVR is implemented and tuned but **does not establish superiority** over persistence on corrected Norwegian data. Possible factors: high short-horizon persistence, weak incremental value of SLP features after data cleaning, and regime mix. Negative result reported honestly.

## 13. Time-of-Day analysis

Experiment 032: peak timing distributions, weekend vs weekday stacks, load-factor and P2A histograms, cluster centroids. Supports planning **shape** differences between clusters without tariff savings.

## 14. Battery energy storage system model

Behind-the-meter: grid import \(g_t = \\max(l_t - p^{dis}_t + p^{ch}_t, 0)\) (no export in primary scenarios).

**Parameters (illustrative 5 kWh / 2 kW medoid runs):** round-trip efficiency 90%, \(\eta_c=\eta_d=\sqrt{0.9}\), SOC window 10–90%, initial SOC 50%, \(\Delta t = 0.25\) h.

SOC dynamics:
\[
SOC_{t+1} = SOC_t + \frac{p^{ch}_t \Delta t \eta_c}{E_{cap}} - \frac{p^{dis}_t \Delta t}{E_{cap}\eta_d}
\]

## 15. Rule-based dispatch

Threshold = 75th percentile of daily load; discharge when load exceeds threshold; charge in valleys if grid import stays below threshold. **Procedural** exclusivity (no simultaneous charge/discharge in code path). Often **non-cyclic** SOC (cluster 0 medoid ends at SOC **0.90**).

## 16. Linear programming (relaxed) optimisation

Experiment 033: minimise peak grid import with full-day foresight; cyclic SOC equality end constraints. Formulation allows **\(p^{ch}_t + p^{dis}_t \le P_{max}\)** — exclusivity **not** guaranteed. In **36/320** scenarios implicit negative grid import is **clipped**, breaking clipped energy balance.

## 17. Mixed-integer linear programming (MILP)

Experiment 035: binary \(z_t\) enforces charge **or** discharge; explicit no-export constraints; SciPy `milp` (HiGHS). **Exclusivity mathematically guaranteed**; medoid peaks match relaxed LP when curtail is zero.

## 18. Battery energy accounting

Conversion loss (audit definition):
\[
E_{conv} = E^{grid}_{ch}(1-\eta_c) + E^{bat}_{dis}\left(\frac{1}{\eta_d}-1\right)
\]

Stored energy change:
\[
\Delta E_{stored} = E_{cap}(SOC_T - SOC_0) = E_{ch,stor} - E_{dis,rem}
\]

Unclipped balance (always valid):
\[
E_{grid,unc} - E_{load} = E^{grid}_{ch} - E^{bat}_{dis}
\]

**Do not** use Experiment 033 `loss_kwh` (= \(E_{ch}-E_{dis}+\max(0,E_{ch}-E_{dis})\)).

## 19. Results and discussion

### 19.1 BESS medoids (5 kWh / 2 kW)

| Cluster | Meter–date | Rule peak ↓ | MILP peak ↓ | Conv. loss (MILP) kWh |
|---------|------------|---------------|-------------|------------------------|
| 0 | BR29 2020-09-06 | **13.27%** (cyclic rule) | **26.69%** | 0.123 |
| 1 | MH31 2019-11-07 | **51.17%** (non-cyclic) | **58.32%** | 0.053 |

`rule_offline_cyclic` achieves SOC closure on cluster 0 only; **infeasible** on cluster 1 under tested constraints (final SOC **≈0.567**).

### 19.2 Sensitivity

Rule-based medoid heatmaps flat across capacity/power (physical saturation). LP/MILP show capacity dependence on cluster 0 (~20% at 1 kWh to ~27% from 2 kWh upward).

### 19.3 Forecasting

Persistence remains strongest baseline after corrected Norwegian ingest.

## 20. Engineering implications

- Distinct load-shape clusters justify **different** storage dispatch strategies (spiky cluster → larger relative peak cuts).
- MILP provides a **defensible** offline benchmark with cyclic SOC and exclusivity.
- Forecasting for operations should not assume SVR dominance without re-benchmarking per cohort.

## 21. Limitations

- Representative **two medoid days**, not population-wide BESS performance.
- No transformer ratings, voltage, or tariffs.
- Ireland–Spain synopsis categories **not** fully replicated.
- Relaxed LP can **curtail** energy; must report unclipped vs clipped accounting.

## 22. Conclusions

The project delivers a reproducible smart-meter analytics pipeline, honest forecasting benchmarks, ToD characterisation, and an audited BESS model. The synopsis hypothesis that SVR+SLP beats persistence is **not supported** on the Norwegian evidence; BESS peak shaving is **demonstrated** on physical CEEW profiles with rigorous Experiment 034–035 accounting.

## 23. Future scope

- CER residential ingestion if access granted.
- Full GoiEner CNAE-01 extract with documented units.
- Multi-day BESS Monte Carlo over eligible meter-days.
- Couple forecasts to causal (non-foresight) dispatch.

## 24. References

See `references/bibliography.md` and Experiment 023 literature pack.

## Appendix A — Figure list

See `05_figure_and_evidence_index.md`.

## Appendix B — Tables

`tables/final_bess_medoid_comparison.csv`, `tables/norwegian_baseline_mae.md`.
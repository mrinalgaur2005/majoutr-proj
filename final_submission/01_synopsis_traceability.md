# Synopsis traceability matrix

**Source synopsis:** `Major Project Synopsis SVR LoadForecasting.pdf` (preserved unchanged).  
**Structured requirements audit:** `results/dataset_audit/experiment_019/synopsis_alignment.csv` (Exp 019).

**Evidence chain actually completed:** CEEW Mathura–Bareilly (profiling, clustering, ToD, BESS) + Norwegian residential cohort (forecasting audit 024–031). This is an **alternative** to the Ireland (CER) / Spain (GoiEner) dual-track in the synopsis text.

---

## 1. Residential smart-meter category (Ireland / CER)

| Field | Detail |
|-------|--------|
| **Original objective** | Residential consumer load profiling and forecasting with verified category labels. |
| **Work undertaken** | CER desk audit, access procedure, schema from manifest (Exp 019, 023); Norwegian **residential** cohort used as partial substitute (Exp 026–031). |
| **Experiments** | 019, 023, 025–031 |
| **Evidence** | CER `PENDING_ACCESS`; Norwegian 1136 HH macro test MAE persistence **0.4361** (Exp 031). |
| **Status** | **Not demonstrated** for Ireland/CER. **Partially demonstrated** on Norwegian open residential data. |
| **Limitations** | Geography, tariff, and meter population differ from synopsis. |
| **Presentation** | State CER as critical path; show Norwegian audit as *methodology* validation only. |

## 2. Agricultural smart-meter category (Spain / GoiEner)

| Field | Detail |
|-------|--------|
| **Original objective** | Agricultural category SLP and SVR forecasting. |
| **Work undertaken** | GoiEner CNAE-01 audit; 15-profile pilot (Exp 019–021); units/semantics gaps documented. |
| **Experiments** | 019–021, 032 (15 GoiEner shapes, not physical kW) |
| **Evidence** | `n_cnae_01=100` in metadata; **15** profiles on disk; pilot evaluated vs baselines (Exp 020–021). |
| **Status** | **Partially demonstrated** (audit + pilot only). |
| **Limitations** | Not full 100-profile study; hourly native resolution; no verified tariff segment. |
| **Presentation** | Show CNAE counts figure; do not claim ag forecasting superiority. |

## 3. SVR with standard load profile (SLP) features

| Field | Detail |
|-------|--------|
| **Original objective** | SVR enhanced by category-specific SLP-derived features. |
| **Work undertaken** | SLP feature designs on CEEW (012–018 frozen); binding Exp 024 protocol; Norwegian SVR±SLP tracks 028–030. |
| **Experiments** | 012–018 (CEEW), 024–030 (Norway), 031 (baseline zoo) |
| **Evidence** | Exp 031: test macro MAE — persistence **0.4361**, SVR tuned **0.4457**, SVR F0 **0.4537**; validation rule recorded in `frozen_baseline_configuration.json`. |
| **Status** | **Partially demonstrated** (full pipeline implemented and evaluated). |
| **Limitations** | CEEW lacks category labels; Norwegian evaluation shows **limited incremental benefit** from tested SLP encodings (see Exp 031 table). |
| **Presentation** | One slide: methodology + macro MAE comparison (comparable band). |

## 4. Baselines (persistence, seasonal naive, ARIMA)

| Field | Detail |
|-------|--------|
| **Original objective** | Rigorous baselines per synopsis. |
| **Work undertaken** | Full baseline zoo Exp 031; persistence frozen. |
| **Experiments** | 012–016, 031 |
| **Evidence** | `frozen_baseline_configuration.json`; validation persistence MAE **0.4349**. |
| **Status** | **Demonstrated** (Norwegian track). CEEW track frozen earlier. |
| **Limitations** | ARIMA not primary headline in final Norwegian cohort. |
| **Presentation** | Bar chart `exp031_test_macro_mae.png`. |

## 5. MAPE &lt; 8% performance target

| Field | Detail |
|-------|--------|
| **Original objective** | Report MAPE below 8% where applicable. |
| **Work undertaken** | MAPE reported in pilots; MAE/WAPE used for model selection (protocol v2). |
| **Experiments** | 020–021, 024 design |
| **Evidence** | Ag pilot MAPE ≫ 8%; Norwegian scale uses MAE. |
| **Status** | **Not demonstrated** at synopsis target. |
| **Limitations** | Sparse zeros, scale, horizon mix. |
| **Presentation** | Mention as synopsis reporting target, not achieved claim. |

## 6. Standard load profiles (category-specific)

| Field | Detail |
|-------|--------|
| **Original objective** | Build/use SLPs for residential and agricultural categories. |
| **Work undertaken** | CEEW cluster centroids (shape); Norwegian category SLP search (Exp 030); GoiEner profiles audit; **out-of-sample SLP validation (Exp 036)**. |
| **Experiments** | 001–010, 030, 032, **036** |
| **Evidence** | K=2 peak-normalized CEEW clusters; Norwegian SLP heatmaps Exp 030; Exp 036 held-out assignment (13/13 metrics BH q<0.05 median). |
| **Status** | **Partially demonstrated** — shapes and **out-of-sample descriptive assignment yes**; **verified dual-category SLPs no**. |
| **Limitations** | Clusters are **not** residential/agricultural labels; Exp 036 uses random meter splits. |
| **Presentation** | Cluster profiles + Exp 036 centroids / held-out bands. |

## 7. Time-of-Day (ToD) / demand analysis

| Field | Detail |
|-------|--------|
| **Original objective** | ToD characterization for planning. |
| **Work undertaken** | Exp 032 full CEEW ToD statistics, peak timing, weekend/weekday. |
| **Experiments** | 032 |
| **Evidence** | 84 meters, 43,555 days; mean load factor **0.312**; mean P2A **4.76**; K=2 regimes. |
| **Status** | **Demonstrated** on CEEW. |
| **Limitations** | No tariff ToD savings. |
| **Presentation** | Mean daily + peak-to-average figures. |

## 8. BESS / storage / microgrid application

| Field | Detail |
|-------|--------|
| **Original objective** | BESS or microgrid stability study downstream of forecasts. |
| **Work undertaken** | Behind-meter BESS peak shaving Exp 033–035; microgrid UC design-only in protocol. |
| **Experiments** | 033, 034, 035 |
| **Evidence** | Medoids BR29 / MH31; MILP peaks **26.69%** (C0), **58.32%** (C1); cyclic rule C0 feasible, C1 infeasible. |
| **Status** | **Partially demonstrated** (simulation on representative days). |
| **Limitations** | No network model, tariffs, or population-wide claims. |
| **Presentation** | Before/after + dispatch comparison bar chart. |

## 9. Ireland–Spain comparative study

| Field | Detail |
|-------|--------|
| **Original objective** | Cross-country comparison in synopsis narrative. |
| **Work undertaken** | Dataset audits only; no joint Ireland–Spain model training. |
| **Experiments** | 019, 022, 023 |
| **Evidence** | `synopsis_compliance_matrix.csv`; readiness files. |
| **Status** | **Not demonstrated**. |
| **Limitations** | CER access; GoiEner archive incompleteness. |
| **Presentation** | One limitation slide; traceability table. |

## 10. Short-term load forecasting (generic)

| Field | Detail |
|-------|--------|
| **Original objective** | Short-horizon forecast for distribution planning. |
| **Work undertaken** | CEEW experiments 012–018; Norwegian 024–031 at scale. |
| **Experiments** | 012–018, 030–031 |
| **Evidence** | Persistence strongest; corrected data pipeline Exp 030. |
| **Status** | **Partially demonstrated** (rigorous evaluation; **inconclusive / limited** SLP advantage in tested configs). |
| **Limitations** | Two dataset contexts; not unified model. |
| **Presentation** | Workflow slide + baseline comparison. |

## 11. Clustering / load-profile discovery

| Field | Detail |
|-------|--------|
| **Original objective** | Extract recurring load shapes. |
| **Work undertaken** | K-means K=2–6; final K=2 peak normalization; **Experiment 036 out-of-sample validation**. |
| **Experiments** | 001–010, 032, **036** |
| **Evidence** | In-sample: cluster 0 **19,063** days, LF ≈ 0.467; cluster 1 **23,574** days, LF ≈ 0.199 (recomputed in Exp 036). Held-out: median Cliff's δ LF **0.98**; centroid corr **0.983**. |
| **Status** | **Demonstrated** (in-sample + out-of-sample descriptive validation). |
| **Limitations** | Shape clusters ≠ consumer class; not geographic holdout. |
| **Presentation** | `exp032_cluster_profiles.png` + `exp036_*` figures. |

## 12. Out-of-sample SLP characterization (project extension)

| Field | Detail |
|-------|--------|
| **Original objective** | Not stated verbatim in synopsis PDF (extension aligned with SLP methodology). |
| **Work undertaken** | Grouped meter splits; frozen centroids; held-out statistics. |
| **Experiments** | **036** |
| **Evidence** | `experiment_036_summary.json`; reproducibility `stats_match: true`. |
| **Status** | **Demonstrated** for descriptive assignment on CEEW. |
| **Limitations** | Does not prove forecasting gain or consumer taxonomy. |
| **Presentation** | Dedicated slides 9–12 in final presentation. |

## Summary counts

| Classification | Count (of 12 traced objectives) |
|----------------|----------------------------------|
| Demonstrated | 4 |
| Partially demonstrated | 5 |
| Not demonstrated | 3 |

## How to explain in viva

“We preserved the original synopsis PDF and built a **documented alternative chain** when CER/GoiEner gates blocked the dual-category experiment. The **central story** is **SLP-based load characterization** (including **Experiment 036** out-of-sample validation) and **SLP-informed SVR evaluation** with honest baselines. ToD and BESS are **supporting** applications on characterized profiles.”
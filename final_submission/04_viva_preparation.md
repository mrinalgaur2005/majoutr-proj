# Viva preparation (60+ questions)

Spoken answers should follow `CLAUDE.md` and `DOCUMENTATION_STYLE_GUIDE.md`: name the analysis (characterization, forecasting comparison, tariff exposure, storage economics), not an experiment index, and do not centre the project on battery dispatch. The notes below retain technical traceability for the speaker.

Each item: **Short answer** (oral) + **Technical detail** + **Evidence**.

---

## A. Project overview and motivation

**Q1. What is the project about?**  
Short: **SLP-based load characterization** and **SLP-informed SVR short-term forecasting** on smart-meter data.  
Detail: Contribution A—profile construction, clustering, **Experiment 036 out-of-sample validation**; Contribution B—SVR±SLP vs baselines (Norway); ToD/BESS supplementary.  
Evidence: `00_README.md`, `02_final_project_report.md`, Exp 001–036.

**Q2. What problem does BESS address here?**  
Short: Reduces **consumer grid-import peak** on representative days.  
Detail: Behind-the-meter dispatch only; no network model.  
Evidence: Exp 033–035 medoid tables.

**Q3. Why smart meters?**  
Short: 15-minute resolution reveals peaks and shapes.  
Detail: CEEW 84 meters, 43,555 complete daily profiles.  
Evidence: Exp 032 summary.

**Q4. Did you achieve the original synopsis?**  
Short: **Partially**—alternative evidence chain.  
Detail: Ireland–Spain dual category **not demonstrated**; see traceability matrix.  
Evidence: `01_synopsis_traceability.md`.

**Q5. What is the main positive engineering outcome?**  
Short: **Validated SLP characterization pipeline** including **out-of-sample assignment** (Exp 036) plus transparent **SVR forecasting evaluation** (Exp 031).  
Evidence: `experiment_036_summary.json`, Exp 031 macro MAE table.

---

## B. Electrical load profiles

**Q6. Define load factor.**  
Short: Mean demand / peak demand.  
Detail: CEEW mean LF **0.312**; cluster 0 **0.467**, cluster 1 **0.199**.  
Evidence: Exp 032.

**Q7. Define peak-to-average ratio.**  
Short: Peak kW / mean kW.  
Detail: Mean P2A **4.76**; cluster 1 spikier (**6.79**).  
Evidence: Exp 032.

**Q8. What is a daily load profile?**  
Short: 96 × 15-min **kW** values per meter-day.  
Evidence: `daily_profiles.parquet`.

**Q9. Units of `load_kw`?**  
Short: **kW** (power), from kWh/0.25 h.  
Evidence: Exp 032 readiness JSON.

**Q10. Why not normalised profiles for BESS sizing?**  
Short: Centroids are **shape** only.  
Detail: BESS uses physical medoid days (Exp 033 medoids).  
Evidence: Exp 032 `bess_representative_profiles.json` disclaimer.

---

## C. Dataset and preprocessing

**Q11. How many CEEW meters?**  
Short: **84**.  
Evidence: Exp 032.

**Q12. Time range?**  
Short: ~May 2019 – Oct 2021.  
Evidence: README §3.

**Q13. What is a “complete day”?**  
Short: 96 intervals, completeness ≥ 98%, energy check.  
Evidence: Exp 033 prep.

**Q14. Norwegian data role?**  
Short: Forecasting benchmark after CEEW gates on CER.  
Evidence: DEC-017, Exp 026–031.

**Q15. Why was Experiment 030 needed?**  
Short: Fix corrupted demand matrix / ingest bugs.  
Evidence: Exp 030 report.

---

## D. Clustering

**Q16. Why K=2?**  
Short: Stable shape split; engineering interpretability.  
Detail: Not sole statistical optimum for all K.  
Evidence: Clustering audit 001–010.

**Q17. Why peak normalization?**  
Short: Separate **shape** from magnitude for clustering.  
Evidence: `cluster_centroids.csv`.

**Q18. Are clusters residential vs agricultural?**  
Short: **No.**  
Detail: DEC research_log; no category labels.  
Evidence: `01_synopsis_traceability.md`.

**Q19. Cluster 0 vs 1 in plain terms?**  
Short: C0 flatter/higher energy; C1 spikier/lower energy.  
Evidence: Exp 032 cluster summaries.

**Q20. How were BESS medoids chosen?**  
Short: Minimum shape distance to centroid on **physical** days.  
Evidence: Exp 033 representative selection.

**Q20a. What is Experiment 036?**  
Short: Out-of-sample test that **frozen training SLPs** assign held-out meter-days to distinguishable consumption groups.  
Evidence: `results/forecasting/experiment_036/results.md`.

**Q20b. Why grouped meter splits?**  
Short: Prevents the same meter appearing in train and test (leakage).  
Detail: 58 train / 26 test meters × 5 seeds.  
Evidence: `split_assignments/split_seed_*.json`, `audit_report.json`.

**Q20c. What is Cliff's delta?**  
Short: Nonparametric effect size from Mann–Whitney pairs; e.g. median δ **0.98** for load factor on held-out data.  
Evidence: `tables/heldout_group_statistics.csv`.

**Q20d. Does Exp 036 prove forecasting improvement?**  
Short: **No**—descriptive validation only.  
Evidence: Report §10 vs §13.

**Q20e. Silhouette and ARI in context?**  
Short: Silhouette ≈ **0.242** (K=2 peak); seed ARI ≥ **0.999** in-sample; cross-split centroid corr ≈ **0.983**.  
Evidence: `verified_context.json`.

---

## E. Short-term load forecasting

**Q21. Forecast horizon?**  
Short: Protocol-defined short-term (Exp 024); Norwegian hourly steps.  
Evidence: `forecasting_protocol_v2.md`.

**Q22. Primary metric?**  
Short: **MAE** (macro over households).  
Evidence: Exp 031.

**Q23. Train/validation/test?**  
Short: Chronological 70/15/15 style per protocol.  
Evidence: Exp 024 approved protocol.

**Q24. What is persistence?**  
Short: Forecast = previous observed value / recent history.  
Evidence: Exp 031 frozen baseline.

**Q25. Is forecasting complete on CEEW?**  
Short: **Frozen** at Exp 018; not final thesis headline.  
Evidence: README.

---

## F. SVR and machine learning

**Q26. Why SVR?**  
Short: Synopsis specified SVR for nonlinear mapping.  
Evidence: Synopsis PDF.

**Q27. SVR test MAE?**  
Short: **~0.446** tuned vs **0.436** persistence — **similar scale**.  
Evidence: Exp 031 summary.

**Q28. Did tuning help?**  
Short: Slightly vs untuned SVR, not vs persistence.  
Evidence: Exp 031.

**Q29. Overfitting risk?**  
Short: Val/test macro used; household-level scatter checked.  
Evidence: `exp031_pers_vs_svr_scatter.png`.

**Q30. Would more data fix SVR?**  
Short: Unclear; not tested—honest limitation.  
Evidence: Future scope in report.

---

## G. Persistence and baselines

**Q31. How did SVR+SLP compare to persistence?**  
Short: **Comparable macro MAE** (~0.436 vs ~0.446–0.454 on Norwegian test).  
Detail: Strong lag persistence; tested SLP encodings showed **limited incremental benefit**; full zoo in Exp 031.  
Evidence: `tables/norwegian_baseline_mae.md`.

**Q32. Was SLP consistently beneficial?**  
Short: **Not consistently** in evaluated configurations; some ablations show local MAE movement (CEEW 010–012).  
Evidence: Exp 030–031; historical experiment reports unchanged.

**Q33. What is frozen baseline?**  
Short: **Persistence** locked in JSON for future work.  
Evidence: `frozen_baseline_configuration.json`.

**Q34. Seasonal naive performance?**  
Short: Worse (~0.59 test MAE).  
Evidence: Exp 031.

**Q35. Compare MAE to peak reduction?**  
Short: Different problems—forecast error kW vs BESS peak %.  
Evidence: Report §18 vs §19.

---

## H. Time-of-Day analysis

**Q36. What ToD metrics did you compute?**  
Short: Peak timing, weekday/weekend, LF, P2A.  
Evidence: Exp 032 figures.

**Q37. Tariff ToD savings?**  
Short: **Not calculated**—no tariff.  
Evidence: Exp 033 limitations.

**Q38. Weekend vs weekday energy?**  
Short: Similar means (~8.12 vs 8.17 kWh).  
Evidence: Exp 032 JSON.

**Q39. How does ToD link to BESS?**  
Short: Informs representative **shapes** and thresholds.  
Evidence: Exp 032 → 033.

**Q40. GoiEner ToD?**  
Short: 15 profiles only; units undocumented.  
Evidence: Exp 032.

---

## I. Battery energy storage

**Q41. Battery size in main example?**  
Short: **5 kWh**, **2 kW**.  
Evidence: Exp 035 comparison table.

**Q42. Round-trip efficiency?**  
Short: **90%** (\(\sqrt{0.9}\) per direction).  
Evidence: Exp 033 battery_model.

**Q43. BESS medoid meters?**  
Short: **BR29** (C0), **MH31** (C1).  
Evidence: Exp 033 summary.

**Q44. Peak reduction cluster 0 MILP?**  
Short: **26.69%**.  
Evidence: Exp 035 CSV.

**Q45. Peak reduction cluster 1 MILP?**  
Short: **58.32%**.  
Evidence: Exp 035 CSV.

**Q46. Population-wide BESS claim?**  
Short: **No**—representative days only.  
Evidence: Exp 035 limitations.

---

## J. Battery SOC and efficiency

**Q47. Why is cyclic SOC important?**  
Short: Fair energy comparison; no hidden stored energy.  
Evidence: Exp 034–035.

**Q48. Rule dispatch final SOC cluster 0?**  
Short: **0.90** (non-cyclic).  
Evidence: Exp 035 table.

**Q49. Why cluster 1 cyclic rule infeasible?**  
Short: Cannot restore 50% SOC without violating threshold/no-export.  
Detail: Final SOC **~0.567** after offline rule.  
Evidence: `cyclic_soc_validation.md`.

**Q50. What is rule_offline_cyclic?**  
Short: Charge budget capped to peak-shave need + restoration.  
Evidence: Exp 035; works on C0 medoid.

**Q51. SOC limits?**  
Short: 10% min, 90% max.  
Evidence: Battery params.

---

## K. Rule-based dispatch

**Q52. Rule threshold?**  
Short: 75th percentile of daily load.  
Evidence: Exp 033.

**Q53. Simultaneous charge/discharge in rule?**  
Short: **Prevented** in code logic.  
Evidence: Exp 034 rule audit.

**Q54. Why rule peak % flat in sensitivity heatmap?**  
Short: Shave needs little energy; saturated by threshold logic.  
Evidence: Exp 034 sensitivity audit.

**Q55. Rule vs MILP on C0?**  
Short: **13.27%** vs **26.69%** peak reduction.  
Evidence: Exp 035.

---

## L. LP and MILP

**Q56. What does Exp 033 LP minimise?**  
Short: **Peak** grid import (offline full-day knowledge).  
Evidence: Exp 033 formulation.

**Q57. LP vs MILP difference?**  
Short: LP relaxed sum-power bound; MILP **binary exclusivity**.  
Evidence: Exp 035 lp_exclusivity doc.

**Q58. Why binary variables for exclusivity?**  
Short: Continuous LP can mathematically allow both >0; binaries forbid.  
Evidence: Big-M vs `scipy.optimize.milp`.

**Q59. What is curtailment in LP?**  
Short: Negative implicit export clipped to zero (**36** scenarios).  
Evidence: Exp 035 energy audit.

**Q60. Does MILP match relaxed LP on medoids?**  
Short: **Yes** on peaks when no curtail.  
Evidence: Exp 035 comparison.

**Q61. Is MILP real-time implementable?**  
Short: **Offline benchmark** only (full-day foresight).  
Evidence: Exp 033 limitations.

---

## M. Results and engineering limitations

**Q62. Conversion loss magnitude?**  
Short: ~**0.03–0.12 kWh/day** on medoids (audit formula).  
Evidence: Exp 035 table; not Exp 033 `loss_kwh`.

**Q63. Transformer relief?**  
Short: **Not claimed**—no network data.  
Evidence: Traceability + limitations.

**Q64. Voltage improvement?**  
Short: **Not claimed**.  
Evidence: Same.

**Q65. Bill savings?**  
Short: **Illustrative ToD only (Exp 037)** — **no** positive BESS procurement savings on medoids; **not** real consumer bills.  
Evidence: `experiment_037_summary.json`, `145_exp037_results.md`.

**Q66. 320-scenario audit meaning?**  
Short: Parameter sweep verified; unclipped identity holds.  
Evidence: Exp 035 `energy_balance_all_scenarios.csv`.

---

## N. Synopsis and completion

**Q67. What is demonstrated vs partial?**  
Short: 4 demonstrated, 5 partial, 3 not (12 objectives including Exp 036).  
Evidence: `01_synopsis_traceability.md`.

**Q68. CER status?**  
Short: **Pending access**; package prepared Exp 023.  
Evidence: CER_ACCESS_PROCEDURE.md.

**Q69. GoiEner status?**  
Short: Audit + 15-profile pilot; not full synopsis.  
Evidence: Exp 019–021.

**Q70. What would you do with six more months?**  
Short: CER ingest; multi-day BESS; causal dispatch; revisit SLP with new categories.  
Evidence: Report future scope.

**Q71. Strongest slide in presentation?**  
Short: **Experiment 036 held-out validation** (slides 9–12) and **forecasting MAE comparison** (slide 14).  
Evidence: `03_final_presentation.md`.

**Q72. Biggest mistake avoided?**  
Short: Exp 030 data audit before trusting SVR gains; Exp 034 before using `loss_kwh`.  
Evidence: DEC registers.

---

## O. Experiment 037 — SLP, ToD tariffs, and BESS economics

**Q73. Why is ToD analysis connected to SLP characterization?**  
Short: SLPs summarize **when** energy is consumed; ToD tariffs price intervals differently — same tariff, different shapes → different bills.  
Evidence: Report §16.2; Exp 032 + 037.

**Q74. What is a Time-of-Day tariff?**  
Short: Energy price \(\pi_t\) varies by clock time; bill = \(\sum_t P_t \Delta t \pi_t\).  
Evidence: `configs/experiment_037_tariff.json`.

**Q75. Off-peak, shoulder, peak?**  
Short: Illustrative moderate spread: **₹5 / ₹8 / ₹12** per kWh on defined 15-min slot windows.  
Evidence: Exp 037 tariff figure; **not** real utility tariffs.

**Q76. Why do SLP groups differ in tariff exposure?**  
Short: Different diurnal energy shares in expensive periods (e.g. group 1 medoid **+18.6%** ToD vs flat vs group 0 **+0.6%**).  
Evidence: `stage_a_tariff_bills.csv`.

**Q77. How is a ToD bill calculated?**  
Short: Multiply grid import (here: load without BESS) by interval price; sum over 96 slots.  
Evidence: `run_experiment_037.py` procurement_cost.

**Q78. Why can BESS charge off-peak?**  
Short: Lower \(\pi_t\); physics allows charging if SOC and power limits permit.  
Evidence: Exp 037 Stage B; Exp 035 constraints.

**Q79. How does efficiency affect arbitrage?**  
Short: Round-trip **90%** means extra grid energy for same delivered load — must overcome price spread.  
Evidence: `bess_physics.py`; Exp 037 results §16.7.

**Q80. What is cyclic SOC?**  
Short: Final SOC = initial (**50%**); no “free” stored energy across the day.  
Evidence: Exp 035 MILP; Exp 037.

**Q81. Why no battery operation in Exp 037 results?**  
Short: Cost-minimizing dispatch **worse** than no-BESS after losses + cycling → **`no_bess_optimal`** safeguard (₹0 savings).  
Evidence: `experiment_037_summary.json`.

**Q82. Peak reduction vs bill savings?**  
Short: Exp 035 reduces **peak kW**; Exp 037 **energy** bill unchanged without demand charges.  
Evidence: Report §16.7–16.8.

**Q83. Why illustrative tariffs?**  
Short: **No** actual tariff dataset in repository; sensitivity analysis only.  
Evidence: `tariff_assumptions.md`, status `illustrative_sensitivity_only`.

**Q84. Can Exp 037 prove real consumer savings?**  
Short: **No** — medoids, illustrative prices, no demand charges.  
Evidence: `limitations.md`.

**Q85. How would demand charges change results?**  
Short: Peak reduction (Exp 035) could gain **monetary** value if \(\pi^{demand}\) applied — **not modelled** in Exp 037.  
Evidence: Report §16.7 item 4.

**Q86. How does SLP link forecasting and energy management?**  
Short: Same profile construction; **different questions** — predict next step (SVR) vs bill/storage (037).  
Evidence: `07_slp_research_framework.md`.
# Final evaluation presentation (~12–15 minutes)

**Format:** 18 slides. **Audience:** Electrical engineering faculty.

---

## Slide 1 — Title

**Title:** Standard Load Profile-Based Characterization and SVR-Based Short-Term Electricity Load Forecasting

**Bullets:** [Student], [Guide], B.Tech EE • CEEW + Norwegian evaluation cohort • Experiments 001–036

**Figure:** None

---

## Slide 2 — Electricity consumption heterogeneity

**Bullets:** Different daily shapes, peaks, load factors, and ToD energy splits • Smart meters (15-min) enable profile analysis

**Figure:** `figures/exp032_ceew_mean_daily.png`

---

## Slide 3 — Research problem

**Bullets:** Two linked questions: (A) Can SLPs represent recurring patterns? (B) Can SLPs inform SVR forecasting?

**Figure:** None

---

## Slide 4 — Research objectives

**Bullets:** Profile construction → clustering → **out-of-sample validation (Exp 036)** → SLP-informed SVR vs baselines • ToD/BESS: supporting only

**Figure:** None

---

## Slide 5 — Datasets

**Bullets:** **CEEW:** 84 m, 43,555 days • **Norway:** 1,136 HH forecasting audit • GoiEner/CER: synopsis audits only

**Figure:** None

**Notes:** CEEW has no ag/res labels.

---

## Slide 6 — Preprocessing & daily profiles

**Bullets:** 96 slots/day • QA: completeness, energy residual • `load_kw` in kW

**Figure:** None

---

## Slide 7 — SLP generation (K=2)

**Bullets:** Peak-normalized k-means • Two shape regimes • LF ≈ 0.47 vs 0.20 • **Not** residential vs agricultural

**Figure:** `figures/exp032_cluster_profiles.png`

---

## Slide 8 — In-sample clustering quality

**Bullets:** Silhouette ≈ 0.24 • Seed ARI ≥ 0.999 • Stable shape templates

**Figure:** Same as slide 7 or repo clustering audit figure

---

## Slide 9 — Experiment 036: methodology

**Bullets:** 5 × 70/30 **meter** splits (58/26) • Train-only centroids • Frozen assignment on held-out days • No leakage

**Figure:** `figures/exp036_train_centroids.png`

---

## Slide 10 — Held-out profile validation

**Bullets:** Assign unseen meter-days to nearest SLP • Groups differ on **unnormalized** kWh/kW metrics

**Figure:** `figures/exp036_heldout_bands.png`

---

## Slide 11 — Statistical separation (held-out)

**Bullets:** 13/13 metrics: median BH q < 0.05 • Cliff's δ: LF **0.98**, energy **0.29**, peak slot modest

**Figure:** `figures/exp036_load_factor.png` and/or `figures/exp036_cliffs_delta_summary.png`

---

## Slide 12 — Stability across splits

**Bullets:** Centroid shape correlation ≈ **0.983** • Disjoint meters verified all splits • Reproducible (`stats_match: true`)

**Figure:** `figures/exp036_cross_split_stability.png`

---

## Slide 13 — SVR + SLP forecasting framework

**Bullets:** Leakage-safe SLP distances • Chronological splits • Macro MAE over households

**Figure:** `figures/exp031_pers_vs_svr_scatter.png`

---

## Slide 14 — Forecasting evaluation

**Bullets:** Persistence **0.436** vs SVR **~0.446–0.454** test MAE • **Comparable** — limited SLP increment • Exp 036 ≠ forecasting claim

**Figure:** `figures/exp031_test_macro_mae.png`

---

## Slide 15 — Interpretation

**Bullets:** SLPs **describe** patterns well (Exp 036) • Predictive benefit **not proven** in tested encodings • Both findings coexist

**Figure:** None

---

## Slide 16 — Supplementary: ToD

**Bullets:** Peak timing & P2A distributions (Exp 032) • Informs representative BESS days

**Figure:** `figures/exp032_peak_to_avg.png`

---

## Slide 17 — Supplementary: BESS (brief)

**Bullets:** 5 kWh / 2 kW medoid simulation • MILP > rule on peak % • Not central project scope

**Figure:** `figures/exp035_dispatch_comparison.png`

---

## Slide 18 — Limitations, synopsis traceability & conclusion

**Bullets:** Ireland–Spain dual category **not completed** • Clusters = pattern regimes • **Demonstrated:** SLP characterization + out-of-sample validation + SVR evaluation pipeline • Questions welcome

**Figure:** Optional `figures/exp034_conversion_loss.png` (audit rigour)

**Notes:** Point to `01_synopsis_traceability.md`.
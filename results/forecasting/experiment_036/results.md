# Experiment 036 — Out-of-sample SLP characterization

## 1. Research question

Can standard load profiles (SLPs) learned from a subset of CEEW meters characterize distinct daily electricity consumption patterns in previously unseen meters?

## 2. Motivation

The project uses peak-normalized daily load-profile clustering (K=2) as a structured descriptor for short-term forecasting experiments. This experiment provides **independent, out-of-sample** evidence that frozen training centroids assign held-out meter-days to groups with distinguishable **non-shape** consumption statistics.

## 3. Dataset

- Source: audited `data/processed/daily_profiles.parquet` (CEEW Mathura–Bareilly, 15-minute intervals).
- **84 meters**, **43,555** complete meter-days (96-slot profiles, existing completeness and energy-balance filters).
- Verified in-sample context (recomputed): K=2 peak silhouette ≈ **0.242**; seed-to-seed ARI **≥ 0.999**; cluster day counts 19,063 / 23,574; mean daily energy **10.93 / 6.20 kWh**; load factor **0.47 / 0.20** (pattern groups, not verified consumer categories).

## 4. Methodology

- **Grouped split:** 70% meters train / 30% test; five seeds `1042–1046`; no meter appears in both partitions within a split.
- **SLP construction:** peak normalization \(P_t / \max_t P_t\); K=2 KMeans (`n_init=20`) on **training days only**; test days assigned by nearest Euclidean distance to frozen centroids.
- **Characteristics on held-out days** (unnormalized kWh/kW): daily energy, mean load, load factor, peak-to-average, peak slot (circular hour summary), morning/afternoon/evening energy and fractional contributions (Exp 032 slot windows), intra-day std and CV.
- **Statistics:** Mann–Whitney U, Cliff's δ, Benjamini–Hochberg FDR across metrics per split; medians reported across splits.
- **Stability:** pairwise Pearson correlation of matched centroid curves across splits (Hungarian label matching).

## 5. Leakage prevention

- Centroids and cluster count fit **only** on training meter-days.
- Per-day peak normalization uses **that day's** profile only.
- Audit: all five splits `disjoint_meters: true` (58 train / 26 test meters each).
- Reproducibility: duplicate run `--verify-repro` → identical stats hash (`metrics/reproducibility_check.json`).

## 6. Split summary

| Seed | Train meters | Test meters | Train days | Test days | Test group 0 | Test group 1 |
|------|-------------|-------------|------------|-----------|--------------|--------------|
| 1042 | 58 | 26 | 30,130 | 12,507 | 6,149 | 6,358 |
| 1043 | 58 | 26 | 28,898 | 13,739 | 8,153 | 5,586 |
| 1044 | 58 | 26 | 29,431 | 13,206 | 6,161 | 7,045 |
| 1045 | 58 | 26 | 30,413 | 12,224 | 5,353 | 6,871 |
| 1046 | 58 | 26 | 28,367 | 14,270 | 6,642 | 7,628 |

Train/test meter lists: `split_assignments/split_seed_*.json`.

## 7. Statistical results (held-out, median across splits)

| Metric | Median Cliff's δ | Interpretation |
|--------|------------------|----------------|
| load_factor | +0.98 | Strong separation |
| peak_to_avg | −0.98 | Strong (inverse of LF) |
| intra_day_cv | −0.70 | Moderate–strong |
| daily_energy_kwh | +0.29 | Moderate |
| mean_load_kw | +0.29 | Moderate |
| afternoon_frac | −0.40 | Moderate |
| evening_energy_kwh | +0.22 | Small–moderate |
| morning_energy_kwh | +0.20 | Small–moderate |
| peak_slot | +0.11 | Small (shape timing) |
| intra_day_std_kw | −0.03 | Negligible |

**13/13** metrics show median BH-adjusted **q < 0.05** across splits (`tables/heldout_group_statistics.csv`). Effect sizes support practical separation for load factor, peak-to-average, and intra-day variability; peak hour differences are statistically detectable but modest in δ.

Example (split 1042): group 0 higher energy (~10.1 vs 5.4 kWh/day), higher load factor (~0.47 vs 0.20), later circular mean peak hour (~17.6 h vs ~11.4 h).

## 8. Cross-split stability

- Mean pairwise centroid correlation (both groups): **0.983** (`tables/cross_split_centroid_stability.csv`).
- Representative SLP shapes are stable across random meter partitions; group labels may permute between runs.

## 9. Figures and tables

Figures: `figures/exp036_*.png` (centroids, held-out profiles, bands, energy/LF/PTA/peak hour, period fractions, Cliff's δ summary, cross-split stability).

Tables: `tables/split_counts.csv`, `heldout_group_statistics.csv`, `cross_split_centroid_stability.csv`.

## 10. Interpretation

**Evidence supports the research question:** training-derived K=2 peak-normalized SLPs assign held-out meter-days to two groups that differ consistently in energy magnitude, load factor, peakiness, and diurnal structure. This validates SLPs as a **descriptive** representation of heterogeneous daily patterns.

Cluster membership does **not** establish consumer identity or universal categories—only recurring **daily pattern regimes** within this audited sample.

## 11. Limitations

See `limitations.md`. Geographic stratification not enforced; shape clustering can partially align with magnitude; single K=2 design.

## 12. Conclusion

Out-of-sample assignment to frozen SLP centroids is feasible and yields statistically and practically distinguishable consumption characteristics on held-out CEEW meters, with high cross-split centroid stability.

## 13. Reproducibility

```bash
.venv/bin/python scripts/run_experiment_036.py
.venv/bin/python scripts/run_experiment_036.py --verify-repro
```

Config: `experiment_config.json`.
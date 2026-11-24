# CEEW Mathura–Bareilly Smart Meter Research

Human-readable experiment diary for the real CEEW pipeline. Synthetic forecast scripts (`run_all_experiments.py`, `phase_*.py`) are a separate track and are not used for the numbers below.

## 1. Research Objective

"Does incorporating recurring load-profile information extracted from high-frequency smart-meter data improve short-term load forecasting compared with conventional temporal/aggregate forecasting approaches in the CEEW Mathura–Bareilly setting?"

This is a hypothesis. Clustering is complete. CEEW forecasting experiments 012–018 are frozen. Experiment 019 audited external category-labelled datasets for the **original synopsis** (SVR + SLP + residential/agricultural categories). Experiment 018 on unlabeled CEEW does **not** replace that synopsis track (DEC-017).

## 2. Project Status

| Stage | Status | Notes |
|------|--------|-------|
| Raw data acquisition | COMPLETE | Harvard Dataverse files under `data/raw/ceew_mathura_bareilly/` |
| Data audit | COMPLETE | 21,845,497 rows; 84 meters |
| 15-min aggregation | COMPLETE | Complete 5-point bins only |
| Daily profiles | COMPLETE | 43,555 full 96-slot days |
| Normalization | COMPLETE | Peak and energy both retained |
| Initial clustering | COMPLETE | K-means, K=2–6, both norms |
| Final clustering audit | COMPLETE | Coverage, location, meter-level, temporal, magnitude |
| Duplicate-timestamp check | COMPLETE | Exact copies inside the Bareilly 2020 file |
| Forecasting 012–016 | COMPLETE | Shrinkage pooled gain is small and concentrated; no new selection rule |
| Forecasting audit (017) | COMPLETE | PASSED WITH UNRESOLVED LIMITATIONS; baseline frozen |
| External dataset audit (019) | COMPLETE | GoiEner CNAE + CER docs + EnergyBench catalog |
| Synopsis SVR+SLP (020) | PARTIAL | Agriculture pilot n=15 local; CER pending |
| Experiment 020A audit | COMPLETE | Reproduce 020; SLP ablation; saved predictions |
| Experiment 020B integrity | COMPLETE | Alignment, flag sensitivity, SLP audit |
| Experiment 021 failure audit | COMPLETE | GoiEner semantics; SVR vs persistence diagnosis |
| Experiment 022 roadmap | COMPLETE | Protocol v2, compliance matrix, access gates |
| Experiment 023 deps & literature | COMPLETE | CER package, GoiEner query, lit review (9 papers) |
| Experiment 024 design audit | COMPLETE | Protocol v2.1 final (PROPOSED); execution blocked on gates |
| Experiment 024A protocol audit | COMPLETE | Timestamp/SLP causality fixes PROPOSED; DST blocked |
| Experiment 024B approval audit | COMPLETE | Approval candidate; design-ready; execution blocked |
| Experiment 024C estimand audit | COMPLETE | P1/P2/P3; final approval candidate |
| Experiment 024 protocol approval | COMPLETE | Binding protocol APPROVED; execution NOT READY |
| Experiment 025 public-data path | COMPLETE | CER closed; GoiEner QC; Norwegian metadata acquired |
| Experiment 026 Norwegian ingest | COMPLETE | demand.csv audited; pilot ingest; Exp024 not authorized |
| ToD | NOT STARTED | |
| BESS | NOT STARTED | |

## 3. Dataset

- Source: Agrawal, Mani, Jain, and Ganesan, CEEW; Harvard Dataverse DOI `10.7910/DVN/GOCHJH`
- Raw rows: 21,845,497 (Bareilly 13,946,703; Mathura 7,898,794)
- Meters: 84 (Bareilly 46, Mathura 38)
- Dates: Bareilly 2019-05-09 to 2021-10-31; Mathura 2019-05-01 to 2021-02-20
- Sampling: 3-minute records of `t_kWh` (interval energy), voltage, current, frequency
- Derived 3-minute average power: `load_kw = t_kWh / 0.05`
- Timestamps are timezone-naive. No consumer-category, feeder, or weather fields.
- Zeros in `t_kWh`: 3,550,039. No negative values in measured fields. No 3-minute loads above 50 kW.

## 4. Repository Structure

- `data/raw/ceew_mathura_bareilly/` — untouched source files
- `data/interim/ceew_15min_bins.parquet` — 15-minute bins
- `data/processed/daily_profiles.parquet` — 96-slot daily profiles plus metadata
- `src/` — loader, aggregation, profiles, clustering, figures
- `scripts/run_ceew_foundation.py` — foundation pipeline
- `scripts/final_clustering_audit.py` — audit diagnostics
- `configs/ceew_foundation.json` — K, seeds, completeness rules
- `results/data_audit/` — meter quality and coverage diagnosis
- `results/clustering/` — metrics, stability, assignments, audit tables
- `results/figures/` — PNG/PDF/SVG figures and `FIGURE_INDEX.md`
- `research_log.md` — formal scientific record
- `README.md` — this diary

# Reproduction Commands

Foundation (audit, 15-min, profiles, clustering, figures):

```bash
python3 scripts/run_ceew_foundation.py
```

Faster rerun after those outputs exist:

```bash
CEEW_SKIP_AUDIT=1 CEEW_SKIP_AGG=1 python3 scripts/run_ceew_foundation.py
```

Final clustering audit:

```bash
python3 scripts/final_clustering_audit.py
```

Duplicate diagnosis and deduplicated bins:

```bash
python3 scripts/diagnose_duplicate_timestamps.py
python3 scripts/duplicate_sensitivity.py
```

Forecasting, using the saved supervised table when it already exists:

```bash
OMP_NUM_THREADS=1 nice -n 15 python3 scripts/run_ceew_forecasting.py
```

Configuration: K = 2, 3, 4, 5, 6; K-means `n_init=20`; stability seeds 0–9; silhouette subsample 10,000 with seed 42; a day is valid only with 96 complete 15-minute bins.

# Experiment timeline

### Experiment 001 — Data Audit

Date: 2026-09-23

Script: `scripts/run_ceew_foundation.py` (uses `src/data/audit_extended.py`)

Command: `python3 scripts/run_ceew_foundation.py`

Input: raw CEEW files

Output: `results/data_audit/meter_quality.csv`, `location_summary.csv`, `audit_summary.json`

Objective: Quantify coverage, gaps, zeros, and extremes before any profile is built.

Method: Chunked read. Expected observations = closed 3-minute grid from each meter’s first to last timestamp. Coverage uses row counts, not unique timestamps.

Results: 84 meters; mean coverage 79.68%; median 82.18%. Duplicate timestamps inside a single file chunk: 0. Extreme loads >50 kW: 0.

Validation: Row totals match the earlier `results/ceew/dataset_audit.json` (21,845,497; 84 meters).

Problems: Three Bareilly meters later showed coverage above 100% (Experiment 006).

Fix: Not changed in this experiment. Diagnosis is Experiment 006.

Research implication: Missingness is absent timestamps, not null cells.

Decision: Keep the original coverage formula. Do not treat zeros as missing.

### Experiment 002 — 15-Minute Aggregation

Date: 2026-09-23

Script: `src/preprocessing/aggregate_15min.py` via `scripts/run_ceew_foundation.py`

Command: `python3 scripts/run_ceew_foundation.py`

Input: 3-minute `t_kWh`

Output: `data/interim/ceew_15min_bins.parquet`, `results/bin_stats.json`

Objective: Build average kW on a 15-minute grid without filling gaps.

Method: A bin is complete only with five unique timestamps spanning 12 minutes. Energy is the sum of `t_kWh`. Power is that sum divided by 0.25 h. Incomplete bins stay missing.

Results: 4,279,109 bin rows; 4,188,438 complete; 90,671 incomplete. Malformed timestamps: 0. Off 3-minute boundary: 0.

Validation: Complete-bin power equals energy/0.25 by construction.

Problems: None that changed the rule.

Fix: None.

Research implication: Downstream days cannot be invented from partial bins.

Decision: No interpolation. No 4-of-5 repair.

### Experiment 003 — Daily Profiles

Date: 2026-09-23

Script: `src/profiles/daily_profiles.py`

Command: `python3 scripts/run_ceew_foundation.py`

Input: 15-minute bins

Output: `data/processed/daily_profiles.parquet`, `results/profiles/daily_profile_summary.csv`

Objective: One 96-point load vector per meter-day, with energy, peak, and calendar metadata.

Method: Keep a day only when all 96 slots are non-null. Days with at least 92 observed slots are counted (43,588) and not filled.

Results: 44,610 meter-days with any observed slot; 43,555 fully complete; 918 of those have zero energy.

Validation: Profile length is 96. Clustering later drops the 918 zero-energy days (42,637 profiles).

Problems: None.

Fix: None.

Research implication: The clustering unit is a meter-day, not a household.

Decision: 100% completeness is the main definition.

### Experiment 004 — Normalization

Date: 2026-09-23

Script: `src/profiles/normalize.py`

Command: `python3 scripts/run_ceew_foundation.py`

Input: 42,637 positive-energy profiles

Output: `results/profiles/normalization_summary.json`

Objective: Compare peak scaling and daily-energy scaling before choosing a clustering representation.

Method: Peak = `P_t / max(P)`. Energy = `P_t / sum(P)`. Both matrices are clustered. Daily-mean scaling is a positive multiple of energy scaling on a full day, so it is not a third experiment.

Results: Mean within-profile variance is 0.0509 (peak) and 0.000128 (energy). Lower energy variance is expected because each profile sums to 1; it is not evidence of a better clustering space.

Validation: Zero-energy days cannot be scaled and are excluded from both.

Problems: A provisional preference for energy normalization was written before comparing validity indices.

Fix: Experiment 006 reopens that preference. Both representations stay in the results.

Research implication: Peak keeps spike contrast. Energy forces a composition (shape shares) and removes daily magnitude.

Decision: OPEN. See DEC-006.

### Experiment 005 — Initial Clustering

Date: 2026-09-23

Script: `src/clustering/kmeans_profiles.py`

Command: `python3 scripts/run_ceew_foundation.py`

Input: Peak- and energy-normalized meter-day profiles

Output: `results/clustering/cluster_metrics.csv`, `cluster_stability.csv`, `cluster_summary.csv`, `cluster_assignments.parquet`, `cluster_location_composition.csv`

Objective: Score K = 2…6 without assuming two consumer classes.

Method: K-means, Euclidean, `n_init=20`, seeds 0–9. Reported partition is seed 0. Silhouette uses one 10,000-row subsample (seed 42). Davies–Bouldin and Calinski–Harabasz use all 42,637 profiles. Stability is adjusted Rand index of seeds 1–9 against seed 0.

Results (silhouette / Davies–Bouldin / Calinski–Harabasz):

Peak: K2 0.242 / 1.589 / 15908; K3 0.145 / 2.196 / 10634; K4 0.142 / 2.236 / 8441; K5 0.104 / 2.450 / 6899; K6 0.101 / 2.544 / 5900.

Energy: K2 0.152 / 3.277 / 2788; K3 0.130 / 3.400 / 2141; K4 0.032 / 3.212 / 1908; K5 0.032 / 2.967 / 1732; K6 0.024 / 2.901 / 1589.

Initialization ARI is high for every K (minimum 0.962 at peak K=6). That is initialization stability, not temporal stability.

Validation: Cluster sizes in `cluster_metrics.csv` match `cluster_summary.csv`.

Problems: First plotting pass failed on a `city`/`city_x` merge (ISSUE-001). Research-log finalization then failed because the summary JSON was missing (ISSUE-002).

Fix: Merge on `profile_index` only. Write `bin_stats.json`. Re-run with cached audit and bins.

Research implication: Internal indices favor K=2, more clearly under peak normalization. Separation is moderate (silhouette 0.24), not sharp.

Decision: K=2 is the leading candidate, not a locked model. No Residential/Agricultural labels.

### Experiment 006 — Final Clustering Audit

Date: 2026-09-23

Script: `scripts/final_clustering_audit.py`

Command: `python3 scripts/final_clustering_audit.py`

Input: Processed profiles, cluster assignments, raw rows for BR49–BR51

Output: `coverage_over_100_diagnosis.csv`, `meter_level_metrics.csv`, `location_cramers_v_k2.csv`, `magnitude_vs_shape_k2.csv`, `temporal_stability_k2.csv`, diagnostic figures

Objective: Test whether the K=2 meter-day result is an artifact of magnitude, city, time, or the coverage formula.

Method and results are in the sections below (coverage, location, meter-level, magnitude, temporal stability). Forecasting was not run.

Validation: Cramér’s V uses the K=2 assignment tables. Temporal ARI compares an early-fit model’s labels on the late half with a K-means refit on that late half.

Problems: The first audit run hit the same city-column merge (ISSUE-003).

Fix: Drop profile city from the merge; assignments already carry city. Re-ran the script successfully.

Research implication: Meter-day K=2 is defensible as a recurring daily-state split. It is not a clean household typology, and energy normalization is not supported as the better clustering metric.

Decision: Main published clustering unit remains the meter-day. Normalization stays open. See DEC-007 through DEC-011.

# Preprocessing Decisions

| Decision | Choice | Reason | Leakage Risk | Status |
|----------|--------|--------|--------------|--------|
| 15-min aggregation | Sum of five `t_kWh` values / 0.25 h | Matches interval energy, not a mean of kWh | Safe | FINAL |
| Missing bins | Left missing | Avoids invented load | Safe | FINAL |
| Complete day | 96/96 slots | No filled profiles | Safe | FINAL |
| Interpolation | None | Global splines use future points | A spline would be leaky; not used | FINAL |
| Zero values | Kept | Measured zeros are not proof of a gap | Safe | FINAL |
| Outliers | Reported, not dropped | A full-sample threshold would leak into a later forecast split | Safe because unused | FINAL |

No decision in this table has been superseded.

# Research Decisions

### DEC-001 — Missing data

Decision: Absent timestamps are missing. Zeros stay in the series. Incomplete 15-minute bins and incomplete days are dropped, not filled.

Evidence: Null counts in raw columns are zero; 3,550,039 zero-energy intervals exist.

Status: FINAL

### DEC-002 — Clustering unit

Decision: Main clusters are fit on meter-days.

Evidence: The research question is about recurring daily profiles used later as forecast context. A meter median answers a different question (Experiment 006).

Status: FINAL for this milestone. Meter-level results are sensitivity only.

### DEC-003 — Joint cities

Decision: Mathura and Bareilly are clustered together.

Evidence: Cramér’s V for K=2 is 0.048 (peak) and 0.037 (energy). City shares inside clusters stay near the overall Bareilly share of 0.619.

Status: FINAL for unsupervised discovery. A later forecast split must still be temporal.

### DEC-004 — No consumer-class names

Decision: Labels are Cluster 0, 1, … only.

Evidence: The files have no consumer category. The CEEW readme describes urban households.

Status: FINAL

### DEC-005 — K search

Decision: Report K=2…6. Do not lock K because one index is largest.

Evidence: Silhouette, Davies–Bouldin, and Calinski–Harabasz all prefer K=2 on both norms, but silhouette is only moderate and K=3 remains interpretable in `cluster_summary.csv`.

Status: PROVISIONAL. K=2 is the leading candidate.

### DEC-006 — Normalization

Decision: Do not treat energy normalization as selected.

Previous: Energy normalization was marked provisional because the scientific target is shape and a single spike can dominate peak scaling.

Evidence from Experiment 005–006: Peak has higher silhouette (0.242 vs 0.152), lower Davies–Bouldin (1.59 vs 3.28), much higher Calinski–Harabasz, and higher temporal ARI (0.830 vs 0.619). Energy variance is lower because profiles sum to 1, which does not mean the clusters are better. Meter-level energy K=2 collapses to 77 vs 6 meters.

Status: OPEN

### DEC-007 — Coverage formula

Decision: Do not rewrite `coverage_percent` in `meter_quality.csv`.

Evidence: Values above 100% are row counts over a span, caused by repeated timestamps across year files. Unique-timestamp coverage for those meters is below 100%.

Status: FINAL until a versioned coverage definition is reviewed by a human.

### DEC-008 — Magnitude vs shape

Decision: Describe K=2 as a joint magnitude-and-shape split, not as high-energy vs low-energy alone.

Evidence: Peak Cluster 0 mean energy 10.93 kWh and load factor 0.47; Cluster 1 mean energy 6.19 kWh and load factor 0.20, with a higher mean peak (1.33 vs 1.03 kW).

Status: FINAL for the current K=2 peak partition.

### DEC-009 — Forecasting protocol (design only)

Decision: Future SLP features must be fit on history strictly before the forecast origin, and must not use the same day’s slots after the origin.

Status: PROVISIONAL design. Not implemented.

# Problems Encountered

### ISSUE-001 — City column collision in cluster plots

Problem: Merging assignments to profiles duplicated `city` as `city_x`.

Detected during: First foundation run, figure stage, after clustering had already been fit.

Cause: Assignments already store `city`.

Fix: `src/visualization/foundation_figures.py` merges on `profile_index` and drops the extra city column.

Files changed: `src/visualization/foundation_figures.py`

Validation: Later `CEEW_SKIP_AUDIT=1 CEEW_SKIP_AGG=1 python3 scripts/run_ceew_foundation.py` completed.

Impact on previous results: Metrics files from the failed run were kept; figures were regenerated.

Results rerun: YES

### ISSUE-002 — Research log finalizer missing summary JSON

Problem: `finalize_research_log.py` exited because `foundation_pipeline_summary.json` did not exist.

Detected during: Background resume after ISSUE-001.

Cause: The pipeline writes that JSON only after figures succeed.

Fix: Write `results/bin_stats.json` during aggregation; create the summary from existing outputs; make the finalizer tolerate a missing malformed-timestamp field.

Files changed: `scripts/run_ceew_foundation.py`, `scripts/finalize_research_log.py`

Validation: Log contains the executive summary and matches `cluster_metrics.csv`.

Impact on previous results: None on cluster numbers.

Results rerun: YES for documentation; clustering outputs were already on disk.

### ISSUE-003 — Same city collision in the audit script

Problem: `final_clustering_audit.py` failed while building the city contingency table.

Detected during: Experiment 006, first execution.

Cause: Same merge as ISSUE-001.

Fix: Merge only energy, peak, load factor, and peak slot.

Files changed: `scripts/final_clustering_audit.py`

Validation: Second run wrote Cramér’s V, meter-level metrics, and temporal ARI.

Impact on previous results: None. Coverage and meter-level tables from the partial first run were recomputed.

Results rerun: YES

# Threats to Validity

**Naive timestamps.** Issue: no timezone field. Why it matters: peak hour could shift if clocks are not local civil time. Mitigation: store timestamps as recorded. Remaining concern: unresolved.

**Long gaps.** Issue: some meters have multi-day gaps (`max_gap_minutes` in `meter_quality.csv`). Why it matters: complete days over-represent well-observed periods. Mitigation: incomplete days are excluded rather than filled. Remaining concern: the sample is not a balanced panel.

**Coverage definition.** Issue: row-based coverage exceeds 100% for BR49, BR50, and BR51. Why it matters: a reader may think the grid math is wrong. Mitigation: diagnosis table; formula not silently changed. Remaining concern: year-file overlap is not deduplicated in the 15-minute sum. If the same timestamp is stored twice with the same `t_kWh`, the bin sum would double-count. This needs human review before forecasting (see coverage section).

**Meter-day weighting.** Issue: a meter with more complete days dominates K-means. Why it matters: clusters can reflect observation effort. Mitigation: meter-level sensitivity. Remaining concern: the main fit is still day-weighted.

**Location confounding.** Issue: joint clustering could rediscover city. Why it matters: an SLP feature might be a location dummy. Mitigation: Cramér’s V ≈ 0.04–0.05. Remaining concern: weak, not zero.

**Moderate silhouette.** Issue: 0.24 (peak) and 0.15 (energy). Why it matters: clusters overlap. Mitigation: report the index; do not claim discrete consumer types. Remaining concern: a forecast gain could be small.

**Normalization sensitivity.** Issue: peak and energy are different geometries. Mitigation: both are saved. Remaining concern: DEC-006 is open.

**Temporal leakage (future).** Issue: fitting clusters on all dates and then forecasting inside that span leaks. Mitigation: protocol below is not yet coded. Remaining concern: current labels are descriptive, not features.

**Initialization vs time.** Issue: seed ARI near 1 does not mean the pattern persists. Mitigation: early/late experiment. Remaining concern: one median split only.

# Coverage above 100%

`meter_quality.csv` defines coverage as `100 * row_count / expected_3min_slots` between the first and last timestamp. Within each file chunk, duplicate timestamps are zero, so the audit printed `duplicate_timestamps = 0`.

A global check of BR49, BR50, and BR51 shows exact repeated timestamps across files. Each repeated stamp appears twice. Unique-timestamp coverage is below 100%:

| Meter | Rows | Unique timestamps | Expected slots | Row coverage % | Unique coverage % |
|-------|-----:|------------------:|---------------:|---------------:|------------------:|
| BR49 | 382,908 | 369,120 | 376,800 | 101.62 | 97.96 |
| BR50 | 450,240 | 294,240 | 322,560 | 139.58 | 91.22 |
| BR51 | 532,320 | 360,960 | 369,120 | 144.21 | 97.79 |

Intervals on the unique timeline are 3 minutes, plus a few longer gaps (about 1,443, 2,883, or 4,323 minutes). The series is not sampled faster than 3 minutes. The formula was not edited.

# Magnitude versus shape

K=2 does not only separate high daily energy from low daily energy.

Under peak normalization, Cluster 0 (19,075 days, 44.7%) has higher mean energy (10.93 kWh), higher load factor (0.47), and a lower mean peak (1.03 kW). Cluster 1 (23,562 days, 55.3%) has lower energy (6.19 kWh), low load factor (0.20), and a higher mean peak (1.33 kW). Median peak hour is 14.25 vs 11.5. The split is a flatter, higher-energy day versus a peakier, lower-energy day.

Energy normalization tells the same story with swapped cluster ids: Cluster 1 is the higher-energy, higher-load-factor group (9.77 kWh, load factor 0.38).

# Meter-day versus meter-level

Meter-level sensitivity uses the median normalized day for each meter with at least 14 complete positive-energy days (83 meters).

Peak K=2 silhouette is 0.365 with sizes 37 and 46. Energy K=2 silhouette is 0.557 but sizes are 77 and 6, so the high score is a small-cluster artifact.

Meter-day clustering is the defensible main analysis: it describes recurring daily states. It is not, by itself, a household archetype model. Meter-level peak K=2 is a useful sensitivity and is more balanced than meter-level energy K=2.

# Location confounding

Overall Bareilly share of clustered days: 0.619.

K=2 Cramér’s V: 0.048 (peak), 0.037 (energy). Cluster Bareilly shares stay between about 0.60 and 0.65. Clustering is not strongly location-driven. City is not a consumer category.

# Temporal stability

Cutoff: median profile date 2020-05-21 (21,313 early days, 21,324 late days).

K-means is fit on the early half (K=2). Late days are labeled with that model and compared with a fresh K-means fit on the late half.

Adjusted Rand index: 0.830 (peak), 0.619 (energy). Peak structure is substantially persistent. Energy structure is only partly persistent. This is not the same statistic as the multi-seed ARI in Experiment 005.

# Leakage-safe SLP protocol (not implemented)

1. Declare a forecast origin time `t` on a 15-minute grid.
2. Fit normalization statistics and K-means only on complete meter-days whose date is strictly before the calendar date of `t`.
3. Do not use any slot at or after `t`, including later slots of the same day, as clustering input or as a feature at `t`.
4. For a history day, the feature may be the cluster id or the distance to centroids computed from that past day only.
5. For the current day at time `t`, an SLP feature may use only slots before `t` (for example, overnight slots if `t` is in the morning) or the previous day’s full profile. It must not use the completed current-day vector.
6. Refit or freeze centroids on a rolling past window. Do not reuse the all-period labels in `cluster_assignments.parquet` as model features.
7. Keep Mathura and Bareilly in one fit only if the training window is the same past window for both. Do not retune K on the test period.

# Current Findings

- 21,845,497 raw rows, 84 meters, 42,637 clustered meter-days.
- Internal indices and initialization stability are strongest at K=2, especially for peak normalization.
- Silhouette remains moderate.
- K=2 mixes magnitude and shape (load factor and peak level), not energy alone.
- City association is weak (Cramér’s V < 0.05).
- Peak K=2 centroids persist into the later half of the sample (ARI 0.83). Energy persistence is weaker (ARI 0.62).
- Row coverage above 100% on three meters is duplicate timestamps across files, not a finer sampling rate.
- No forecast accuracy claim exists.

# Open Questions

1. Is peak or energy normalization more appropriate once leakage-safe forecast features are defined?
2. Should a meter-level model be a second feature, or only a sensitivity?
3. Is the small residual location association worth a stratified check inside a forecast model?
4. Does temporal stability hold for other cutoffs than 2020-05-21, and for K=3?
5. After removing cross-file duplicate timestamps, do 15-minute energies for BR49–BR51 change enough to move cluster membership?
6. Which past-only SLP encoding (previous-day cluster, distance to past centroids, or partial-day shape) should be the first forecast feature?

# Result File Index

| File | Purpose | Generated By | Important Fields |
|------|---------|--------------|------------------|
| `results/data_audit/meter_quality.csv` | Per-meter audit | foundation script | coverage, gaps, complete days |
| `results/data_audit/coverage_over_100_diagnosis.csv` | Duplicate-timestamp diagnosis | audit script | unique vs row coverage |
| `results/bin_stats.json` | 15-min completeness | foundation script | complete and incomplete bins |
| `results/profiles/normalization_summary.json` | Profile counts and variances | foundation script | clustering N |
| `results/clustering/cluster_metrics.csv` | Validity indices | foundation script | silhouette, DB, CH, sizes |
| `results/clustering/cluster_stability.csv` | Seed ARI | foundation script | mean, std, min ARI |
| `results/clustering/cluster_summary.csv` | Cluster descriptors | foundation script | energy, peaks, load factor |
| `results/clustering/meter_level_metrics.csv` | One profile per meter | audit script | silhouette, sizes |
| `results/clustering/location_cramers_v_k2.csv` | City association | audit script | Cramér’s V |
| `results/clustering/temporal_stability_k2.csv` | Early/late ARI | audit script | cutoff, ARI |
| `results/figures/FIGURE_INDEX.md` | Figure catalog | written with the audit | path, experiment |

# Figures to use in a paper or slides

### FIG-001 — Per-meter coverage

Path: `results/figures/data_quality/coverage_histogram.png`

Purpose: Show that coverage is uneven.

What it shows: Histogram of row-based coverage.

Key observation: Centered near 80%, with a right tail above 100% explained in Experiment 006.

Experiment: 001

Interpretation: Do not describe the panel as complete.

Use in paper/PPT: YES

### FIG-005 / FIG-006 — Metrics versus K

Paths: `results/figures/clustering/metrics_vs_k_peak.png`, `metrics_vs_k_energy.png`

Purpose: Compare K without hiding disagreement.

What it shows: Silhouette, Davies–Bouldin, and Calinski–Harabasz.

Key observation: K=2 leads on both norms; energy silhouette collapses after K=3.

Experiment: 005

Interpretation: K=2 is the leading candidate. Separation is moderate.

Use in paper/PPT: YES

### FIG-009 — Peak versus energy centroids

Path: `results/figures/normalization/peak_vs_energy_centroids_k2.png`

Purpose: Show the two geometries.

Key observation: Both norms separate a flatter curve from a more peaked curve. Axis scales differ because energy profiles sum to 1.

Experiment: 006

Interpretation: Do not pick a norm from variance.

Use in paper/PPT: YES

### FIG-011 — Temporal stability

Path: `results/figures/diagnostics/temporal_stability_k2_peak.png`

Purpose: Early centroids versus late days assigned by those centroids.

Key observation: Peak K=2 shape remains visible after 2020-05-21 (ARI 0.83).

Experiment: 006

Interpretation: Initialization stability and temporal stability are different, and both are acceptable for peak K=2.

Use in paper/PPT: YES

# Forecasting Phase

## Experiment 007 — Duplicate timestamps

Date: 2026-09-23

Command: `python3 scripts/diagnose_duplicate_timestamps.py` then `python3 scripts/duplicate_sensitivity.py`

The 341,148 repeated timestamps on BR49, BR50, and BR51 are exact copies of energy, voltage, current, and frequency. Every repeat is inside `CEEW - Smart meter data Bareilly 2020.csv`, not a conflict between year files. The earlier “across year files” note was wrong.

The original 15-minute rule requires exactly five rows. Extra copies made `raw_rows > 5`, so those bins were dropped rather than double-counted. On days that were already complete, mean absolute daily-energy change after deduplication is 0, and peak K=2 adjusted Rand index versus the old labels is 1.0. Deduplication does recover additional complete bins (BR50: 27,648 to 58,848).

### DEC-010 — Duplicate timestamps

Decision: Keep the first copy of each meter-timestamp inside a source file. Forecasting uses `data/interim/ceew_15min_bins_dedup.parquet`. The original bin file and the clustering outputs are unchanged.

Status: FINAL

## Experiment 008 — Forecast representation

Peak and energy distances to K=2 centroids, and peak K=3 distances, were all built from days before the evaluation window. Both representations were kept. The test does not select a winner for forecasting, because neither SLP variant beats persistence.

Status: OPEN (DEC-006 remains open)

## Experiment 009 — Chronological setup

Target: 15-minute average kW at time t+H. Primary horizon H=1. Also H=2, 4, and 8.

| Split | Dates | Rows |
|-------|-------|-----:|
| Train | 2019-05-02 through 2020-06-30 | 2,109,423 |
| Validation | 2020-07-01 through 2020-12-31 | 891,056 |
| Test | 2021-01-02 through 2021-10-31 | 829,864 |

Mathura’s test coverage ends on 2021-02-20. Bareilly continues through 2021-10-31. A common-window subgroup stops at 2021-02-20. No random split. No all-period cluster labels.

Centroids for validation rows are fit on days before 2020-07-01. Centroids for test rows are fit on days before 2021-01-01. Yesterday’s complete profile, or the latest complete day before the forecast date, is the only profile input.

## Experiment 010–012 — Baselines, SLP, comparison

Command: `python3 scripts/run_ceew_forecasting.py`

SVR: RBF, `gamma=scale`, C=100, epsilon=0.2. Chosen by validation MAE of the lag+cyclic model on a 1,932-row train sample and a 3,950-row validation sample. The test models are fit on 2,000 rows drawn from train+validation, with an equal meter share and a preference for later rows. The scaler is fit on those rows only.

Test MAE (kW), H=1, n=829,864:

| Model | MAE | RMSE | WAPE | R² |
|-------|----:|-----:|-----:|---:|
| Persistence | 0.108 | 0.271 | 0.288 | 0.723 |
| Seasonal naive (same slot yesterday) | 0.220 | 0.454 | 0.588 | 0.220 |
| SVR lag | 0.229 | 0.383 | 0.613 | 0.443 |
| SVR lag + cyclic | 0.557 | 0.675 | 1.490 | −0.724 |
| SVR lag + peak SLP | 0.247 | 0.407 | 0.662 | 0.373 |
| SVR lag + cyclic + peak SLP | 0.518 | 0.629 | 1.388 | −0.496 |
| SVR lag + cyclic + energy SLP | 0.570 | 0.680 | 1.526 | −0.750 |
| SVR lag + cyclic + peak K=3 | 0.546 | 0.644 | 1.461 | −0.570 |

MAPE is reported only where absolute load is at least 0.05 kW (656,291 of 829,864 points). Zeros stay in MAE, RMSE, WAPE, and R².

Adding peak-K=2 SLP distances lowers lag+cyclic MAE from 0.557 to 0.518 (6.8%). A paired Wilcoxon test on every 8th absolute-error pair (n=103,733) gives p ≈ 0. That comparison is not the scientific claim. Persistence MAE is 0.108. Every SVR, with or without SLP, is worse than persistence. Lag alone (0.229) is close to seasonal naive and better than any SLP model. Energy SLP and K=3 SLP are worse than peak-K=2 SLP, and all three lose to persistence at H=1, 2, 4, and 8. The same ordering holds for Mathura, Bareilly, weekdays, weekends, and the common window through 2021-02-20.

### ISSUE-004 — Pooled SVR sample is not a competent baseline

Problem: One RBF-SVR fit on 2,000 mixed-meter rows does not learn the series. Lag+cyclic test R² is negative.

Detected during: Experiment 012.

Cause: The training cap was introduced so the laptop would not run out of memory. Validation tuning on 4,000 rows selected C=100, which does not transfer to the full test set.

Fix: Not yet. The run was kept. A later experiment needs a per-meter or larger, still leakage-safe, model before any SLP gain can be claimed.

Impact on previous results: Clustering results are untouched.

Results rerun: NO

# Current Findings

Add these forecasting findings to the clustering findings above:

- Exact duplicate timestamps do not change the daily profiles that entered the original clustering.
- On the 2021 test set, persistence is the best measured forecast (MAE 0.108 kW).
- The leakage-safe SLP feature does not improve on persistence or on lag-only SVR.
- It does reduce error relative to the weak lag+cyclic SVR. That is not evidence that recurring profiles improve forecasting.

# Open Questions

7. Can a per-meter model, still fit only on past data, beat persistence before SLP is added?
8. Was C=100 an artifact of tuning on 4,000 pooled rows?

# Experiment 013 — Per-meter conventional forecasting baseline

Date: 2026-09-23

Command: `OMP_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_013.py`

This addresses ISSUE-004. Experiment 012’s pooled 2,000-row SVR is not sufficient evidence for a forecasting claim. No SLP feature is included here.

Hypothesis: a model fit separately on each meter, using only lags available at time t, can match or beat persistence on the 2021 test set.

Data: `data/interim/ceew_15min_bins_dedup.parquet`. Horizon: next 15-minute load. Split unchanged: train before 2020-07-01, validation through 2020-12-31, test from 2021-01-01. Mathura still ends earlier. Common window through 2021-02-20 is reported separately.

Features: `lag_k = load(t-k+1)`, so `lag_1 = load(t)`, for k in {1, 2, 4, 8, 12, 24, 48, 96}. Cyclic terms use the slot of the target interval, which is known from the clock: sin/cos of slot/96, sin/cos of weekday/7, and a weekend flag. Seasonal naive is `load(t-96)`, as specified for this experiment. That is one step earlier than Experiment 012’s same-clock-time-yesterday rule.

Eligibility: at least 1,344 usable training rows, 288 validation rows, and 288 test rows. 68 of 84 meters qualify (36 Bareilly, 32 Mathura). The other 16 are listed in `per_meter_eligibility.csv` and are not dropped silently.

Scaler: fit on that meter’s training rows while tuning; refit on train+validation before the single test evaluation. Ridge alphas {0.1, 1, 10, 100}. SVR uses C in {1, 10, 100}, epsilon in {0.05, 0.2}, gamma `scale`, and at most the latest 1,500 training rows. Test rows are never sampled.

Competency rule, fixed before looking at a “win”: micro MAE ≤ 1.02 × persistence, macro median MAE ≤ 1.05 × persistence, and neither city worse than persistence by more than 10% MAE.

Micro test MAE (kW), n=835,410:

| Model | MAE | RMSE | R² |
|-------|----:|-----:|---:|
| Persistence | 0.107 | 0.271 | 0.723 |
| Ridge lag | 0.117 | 0.250 | 0.763 |
| Ridge lag+cyclic | 0.117 | 0.250 | 0.763 |
| SVR lag | 0.196 | 0.407 | 0.372 |
| Seasonal naive | 0.222 | 0.457 | 0.208 |

Ridge lag is 8.9% worse than persistence on micro MAE, 9.2% worse in Mathura, and 8.8% worse in Bareilly. Macro median MAE is 0.055 (persistence) versus 0.062 (ridge lag). Ridge MAE is better on only 5 of 68 meters. Ridge RMSE is better on 66 of 68 meters, so the loss is not uniform across error definitions. Under the MAE rule above, no learned model is competitive.

Median training autocorrelation is 0.845 at lag 1, 0.716 at lag 2, and 0.540 at lag 96. Adjacent 15-minute loads are highly correlated, which is why persistence is hard to beat on absolute error. Near-zero intervals are where ridge is weakest (MAE 0.060 versus persistence 0.029).

Decision: persistence remains the strongest conventional baseline under the tested formulation. Experiment 014 tests load-change Ridge instead of SLP; see below.

# Experiment 014 — Load-change (residual) forecasting

Date: 2026-09-23

Command: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_014.py`

Research question: is Experiment 013’s gap to persistence caused by predicting a highly persistent load level? Target `ΔP(t+1)=P(t+1)−P(t)`; reconstructed forecast `P(t)+Δ̂`. Zero-change must equal persistence on load — verified (`max |diff| = 0`).

Same data, splits, eligibility (68/84 meters), and Ridge alpha grid as Experiment 013. Validation MAE on the **delta** target selects alpha. No SLP, ToD, or BESS.

Micro reconstructed-load MAE (kW), n=835,410:

| Model | MAE | RMSE | R² |
|-------|----:|-----:|---:|
| Zero-change (= persistence) | 0.107 | 0.271 | 0.723 |
| Ridge delta lags | 0.111 | 0.262 | 0.740 |
| Ridge delta + cyclic | 0.111 | 0.262 | 0.740 |
| Ridge both | 0.117 | 0.250 | 0.764 |
| Ridge load lags | 0.117 | 0.250 | 0.763 |

Best full-sample model is still persistence. Ridge delta is ~3.1% worse on micro MAE (Bareilly −3.1%, Mathura −2.7%). Macro median MAE: persistence 0.055 vs ridge delta 0.058. Ridge wins on MAE for 5–6 of 68 meters. Wilcoxon (every 8th test row): no improvement over persistence (p=1.0 for all ridge variants).

RMSE again favors ridge (e.g. ridge both 0.250 vs 0.271 persistence). MAE remains the decision metric (DEC-011).

Movement tertiles of `|ΔP|` (cuts from training only): mean MAE on **large** moves — persistence 0.261, ridge delta 0.245, ridge both 0.224. On **small** moves persistence wins (0.0037 vs 0.016 ridge delta). Case **B**: do not add SLP; any residual skill is localized to large movements, not the full test sample.

Horizons H=2,4,8 (zero-change vs ridge delta on reconstructed load): mean MAE slightly favors ridge at H=4 and H=8; H=2 is essentially tied. H=1 remains the primary decision horizon.

Outputs: `results/forecasting/experiment_014/`, `results/forecasting/predictions/experiment_014/test_predictions.parquet`, figures `exp014_*` (FIG-035–044).

# Experiment 015 — Leakage-free change-aware forecasts

Date: 2026-09-30

Command: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_015.py`

Runtime: about 19 seconds. Eligible meters: 68 of 84. Test rows: 835,410. Same splits and eligibility as Experiments 013 and 014. Zero-change matched persistence exactly. Ridge delta MAE matched Experiment 014 to numerical noise (0.11078440005251777).

Question: can a rule that uses only information available at time t improve full-sample MAE over persistence?

Candidates, each justified before the run:

- Ridge delta, reproduced from Experiment 014. For a one-step horizon this target is the persistence residual, so a second residual model was not added.
- Calendar-cycle Ridge was not refit. Experiment 014 already scored it worse than Ridge delta.
- Shrinkage `Δ̂ = λ Δ̂_ridge` with λ in {0, 0.25, 0.5, 0.75, 1}, chosen by validation MAE. Per meter, and one λ pooled across meters.
- A gate on the latest observed `|ΔP(t)|`, using a training percentile in {50, 75, 90} chosen on validation. The future change is not an input.
- Huber regression on the same delta lags, because Ridge optimizes squared error.

Validation micro MAE (n=820,913), which selected the model: shrink_meter 0.1007, Huber 0.1008, shrink_global 0.1009, persistence 0.1013, gate 0.1014, Ridge delta 0.1042. The selected forecast is per-meter shrinkage. Global λ was 0.25. Per meter, λ was 0 for 32 meters, 0.25 for 26, 0.50 for 8, 0.75 for 1, and 1 for 1. No Huber fit failed.

Test micro metrics (kW), n=835,410:

| Model | MAE | vs persistence | RMSE | R² |
|-------|----:|---------------:|-----:|---:|
| Persistence / zero-change | 0.10745 | — | 0.27055 | 0.723 |
| Shrink per meter | 0.10701 | −0.41% | 0.26611 | 0.732 |
| Shrink global (λ=0.25) | 0.10705 | −0.37% | 0.26664 | 0.731 |
| Huber delta | 0.10719 | −0.23% | 0.26491 | 0.734 |
| Gate on recent \|ΔP\| | 0.10789 | +0.41% | 0.26515 | 0.734 |
| Ridge delta | 0.11078 | +3.11% | 0.26211 | 0.740 |

City micro MAE, persistence vs shrink_meter: Bareilly 0.11185 vs 0.11141; Mathura 0.06714 vs 0.06667. The common window through 2021-02-20 moves the same way (0.09602 vs 0.09549).

Macro median MAE: persistence 0.05486, shrink_meter 0.05572, shrink_global 0.05491, Huber 0.05640, gate 0.05540, Ridge delta 0.05821. The pooled gain does not show up as a better median meter.

Meter-level paired MAE (the inferential unit; 15-minute rows are not treated as independent):

| Model | Better | Worse | Tie | Median difference (kW) | 95% bootstrap CI | Wilcoxon p |
|-------|-------:|------:|----:|-----------------------:|-----------------:|-----------:|
| Shrink per meter | 26 | 10 | 32 | 0 | [−0.00000008, 0] | 0.00082 |
| Shrink global | 34 | 34 | 0 | ≈ 0 | includes 0 | 0.11 |
| Huber | 28 | 40 | 0 | +0.00004 | includes 0 | 0.97 |
| Gate | 35 | 33 | 0 | ≈ 0 | includes 0 | 0.71 |
| Ridge delta | 5 | 63 | 0 | +0.00214 | excludes 0 | < 0.001 |

The shrink_meter Wilcoxon p-value is small because ties are dropped and the remaining 36 meters favor shrinkage 26 to 10. The median difference is still zero, and 32 meters are exactly persistence because validation chose λ=0.

The Experiment 013 competency band (micro MAE within 2% of persistence, median within 5%, neither city worse by more than 10%) is met by shrink_meter, and the pooled MAE is slightly lower. That band was a “not clearly worse” screen. It is not a meter-wide improvement.

Retrospective `|ΔP(t+1)|` tertiles, labeled as diagnostics only: high-move micro MAE is persistence 0.271, Ridge delta 0.257, shrink_meter 0.266. Low-move MAE is persistence 0.0044, shrink_meter 0.0078, Ridge delta 0.0199. Shrinkage sits between persistence and Ridge. It does not win both regimes. Weekday, weekend, peak, and off-peak pooled MAE all move by a few ten-thousandths of a kilowatt in the same direction as the full sample.

Outputs: `results/forecasting/experiment_015/`, `results/forecasting/predictions/experiment_015/test_predictions.parquet`, figures `exp015_*` (FIG-045–051).

# Experiment 016 — Diagnosing when shrinkage helps

Date: 2026-09-30

Command: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_016.py`

Runtime: about 6 seconds. This experiment does not refit Ridge. It audits `results/forecasting/experiment_015/` and `predictions/experiment_015/test_predictions.parquet`. Experiment 013 metrics live in `results/forecasting/`, not in an `experiment_013/` folder.

Question: can information available at forecast time explain the nonzero shrinkage weights, and can that information choose between persistence and shrinkage without seeing the test set?

MAE difference = model MAE − persistence MAE. Negative means the model is better.

The saved Experiment 015 predictions reproduce the reference metrics (absolute MAE difference below 10⁻¹⁶): persistence 0.107447 / 0.270548, per-meter shrinkage 0.107011 / 0.266110, global λ=0.25 shrinkage 0.107047 / 0.266642, Ridge delta 0.110784 / 0.262107. All 68 meters and 835,410 test rows match. A per-meter MAE weighted by test-row count equals the pooled MAE. λ=0 on 32 meters, and those test forecasts tie persistence exactly.

Of the 36 meters with λ>0, 26 still improve on the test set and 10 get worse. None of those 36 tie. Validation cannot select a shrinkage forecast worse than persistence, because λ=0 is inside the grid. So “validation helped” and “λ>0” are the same event.

The pooled MAE gain is about 0.000436 kW (−0.41%). The median meter difference is 0. The mean meter difference is −0.000327 kW. A bootstrap that resamples the 68 meters (seed 16, 2000 draws) puts the pooled difference in [−0.000699, −0.000195] kW and the median difference in a interval that reaches 0. The pooled dip is stable under meter resampling. It is not a shift of the typical meter.

Five Bareilly meters (BR24, BR11, BR04, BR36, BR51) account for 64% of the net pooled gain. Ten meters account for 85%. λ=0 meters contribute nothing, by construction.

Bareilly: 23 meters with λ>0, 13 with λ=0. Pooled MAE 0.11185 versus 0.11141. Median difference 0. Mathura: 13 versus 19. Pooled MAE 0.06714 versus 0.06667. The Mathura meter-bootstrap interval for the pooled difference touches zero. Median difference 0 in both cities.

Meters that received λ>0 have larger training mean absolute changes (median 0.097 kW versus 0.046 kW). Spearman correlation with λ is 0.33 (p=0.007) for that feature. Mean load and the standard deviation of the change move in the same direction. These are associations with the validation choice, on 68 correlated features, not a confirmed mechanism. The same features’ correlations with the test MAE difference are retrospective and were not used to pick a rule.

Rules scored only on validation pooled MAE:

| Rule | Validation MAE | Meters using shrinkage |
|------|---------------:|-----------------------:|
| Always per-meter shrinkage | 0.10070 | 68 |
| Shrink if training \|ΔP\| ≥ median | 0.10081 | 34 |
| Shrink only in Bareilly | 0.10092 | 36 |
| Shrink if training \|ΔP\| ≥ 75th percentile | 0.10103 | 17 |
| Shrink only in Mathura | 0.10112 | 32 |
| Shrink if training \|ΔP\| ≥ 90th percentile | 0.10117 | 7 |
| Always persistence | 0.10134 | 0 |

The frozen rule is “always use the Experiment 015 per-meter shrinkage.” Every simpler screen was worse on validation, so none of them was scored as an alternative test model. On the test set that rule is the Experiment 015 forecast: MAE 0.10701, RMSE 0.26611, median meter difference 0. The step-level gate from Experiment 015 was not retuned.

Wilcoxon on the 68 paired meter differences: p=0.00082 if exact ties are dropped, p=0.0024 if they are kept (Pratt). Dropping the 32 λ=0 ties makes the test describe only the 36 meters that were allowed to move. With 68 meters, a small pooled effect can be stable without being large or typical.

One implementation miss was corrected before the successful run: the first training-feature mask did not require the same lag completeness as Experiment 015, so the mean absolute change did not match. The script now uses that mask and stops if the match fails.

Outputs: `results/forecasting/experiment_016/`, `results/forecasting/predictions/experiment_016/test_predictions.parquet`, figures `exp016_*` (FIG-052–061).

# Experiment 017 — Temporal integrity and forecast evaluation audit

Date: 2026-11-24

Command: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_017.py`

**Final status: AUDIT PASSED WITH UNRESOLVED LIMITATIONS**

Why: before any SLP test (Experiment 018), we needed to verify that Experiments 013–016 use a defensible chronological split, that features are available at forecast time, and that reported baselines reproduce from saved predictions.

**Inspected:** `scripts/run_experiment_013.py` through `016.py`, `data/interim/ceew_15min_bins_dedup.parquet`, CEEW ReadMe, `results/forecasting/experiment_015/` and `016/`, and prediction parquets. A discrepancy table is in `results/forecasting/experiment_017/methodology_discrepancies.csv`.

**017A timestamps:** Bins are timezone-naive. No duplicate complete `(meter, bin)` pairs. Adjacent complete bins are 15 minutes apart except at gaps (sampled anomalies saved). CEEW documentation does **not** establish IST vs UTC — this remains **unresolved**.

**017B splits:** Same origin rule as code: train origins `2019-01-01 ≤ t < 2020-07-01`, validation `2020-07-01 ≤ t < 2021-01-01`, test `t ≥ 2021-01-01`; target at `t+15m`. All 68 eligible meters match Experiment 015 eligibility. Origins are strictly ordered and split-disjoint.

**017C leakage:** Per-meter λ, Ridge α, gate τ, scaler refit, and Experiment 016 rule use validation only for selection; test is scoring-only. Retrospective movement tertiles and all-period cluster labels are not model inputs. See `leakage_audit.csv`.

**017D reproduction:** All four baseline micro metrics match saved CSVs to numerical tolerance. Zero-change = persistence. Weighted per-meter MAE equals pooled MAE. Experiment 016 rule predictions = Experiment 015 shrinkage.

**017E freeze:** `frozen_baseline_specification.md`, checksum manifest, and copies under `experiment_017/frozen_artifacts/`.

**017F:** `experiment_018_slp_protocol.md` (design only; peak-normalization track primary; stricter success criteria including **median** meter MAE).

**Figures:** `exp017_*` (FIG-062–068 in `FIGURE_INDEX.md`).

# Experiment 018 — Leakage-safe SLP forecasting

Date: 2026-11-24

**Conclusion C:** causal daily-profile features do not improve H=1 MAE. Do not claim an SLP forecasting benefit.

**Commands:**

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_018.py
python3 scripts/finalize_experiment_018.py
```

Runtime ~4.6 min (training) + ~7 s (finalize). Script: `scripts/run_experiment_018.py`.

**Question:** Does peak-normalized K=2 centroid distance (and optional trailing seven-day correlation) on completed daily profiles, fit causally before each forecast origin, beat persistence and frozen Experiment 015 shrinkage?

**Method:** Same 68 meters and 835,410 test rows as Experiments 013–017. Population K-means (K=2) on historical peak-normalized profiles with `date <` origin day; per meter, distance from the latest completed profile to the nearest centroid; Ridge on load change with delta lags + calendar. Validation picks among `ridge_delta_cyclic`, `ridge_delta_cyclic_slp`, and `ridge_delta_cyclic_slp_corr`. Frozen 015/013 test predictions merged without refit. Negative control: Gaussian noise scaled from training SLP distances (seed 18).

**Pre-implementation:** `experiment_018/preimplementation/` (load units, leakage reconciliation, frozen SLP definition).

**Test micro MAE (kW):**

| Model | MAE |
|-------|-----:|
| frozen_shrink_015 | 0.107011 |
| persistence | 0.107447 |
| ridge_delta_cyclic + SLP (selected) | 0.111347 |
| ridge_delta_cyclic (no SLP) | 0.111346 |
| frozen ridge_lag_cyclic (013) | 0.117321 |

Median per-meter MAE: persistence 0.05486; selected SLP model 0.06093. **4** meters improved, **64** worse (Wilcoxon p≈2×10⁻¹⁰, Pratt ties kept). None of the predeclared success criteria pass.

**Leakage:** future-profile injection self-test passed; split audit matches Experiment 017; Experiment 015 prediction SHA unchanged.

**Limitations:** timezone still unresolved (017); energy-normalization sensitivity not run; validation predictions not saved as parquet in v1 (validation MAE logged in `experiment_018_model_selection.csv`).

**Figures:** `exp018_*` (FIG-069–080 in `FIGURE_INDEX.md`).

**Outputs:** `results/forecasting/experiment_018/`, `results/forecasting/predictions/experiment_018/test_predictions.parquet`.

**DEC-016:** Persistence remains the MAE reference. Frozen shrink_015 stays the best learned pooled baseline. SLP is implemented leakage-safely but rejected for forecasting.

# Experiment 019 — External category-labelled dataset feasibility audit

Date: 2026-11-24

**Command:** `python3 scripts/run_experiment_019.py`

**Why:** CEEW has no verified residential/agricultural labels. The original project synopsis requires category-specific SLP + **SVR**, persistence, ARIMA, and MAPE/RMSE/R². Experiment 018 tested one Ridge-based SLP design on unlabeled CEEW only — it does **not** invalidate the synopsis on labelled external data (**DEC-017**).

**Accessed:** GoiEner Zenodo v7.1 (`metadata_public.csv`, `README.txt`, selective extract from `profiles_part01.tar.zst`). **CER:** ISSDA request documented (`PENDING_ACCESS`). **EnergyBench:** catalog snapshot only (no full download).

**Findings:** 28,900 GoiEner profiles with two-digit **CNAE** division; **100** in division **01** (agriculture-related activity). No verified residential label in GoiEner public metadata. CER documents **Residential/SME** utility codes (agriculture not listed). Individual GoiEner profiles are **hourly** with `cons` and imputation `flag` columns.

**Recommendation:** Multi-track Experiment 020 — GoiEner (CNAE categories) + CER residential when obtained; frozen CEEW supplementary.

**Outputs:** `results/dataset_audit/experiment_019/`, figures `results/figures/dataset_019/exp019_*` (FIG-081–086).

# Experiment 020 — Category-labelled SLP + SVR (partial)

Date: 2026-11-24

**Local-only resume (no new downloads):**

```bash
python3 scripts/run_experiment_020_audit.py          # default: --no-download
python3 scripts/run_experiment_020_forecast.py       # Track A pilot after audit
```

Use `scripts/run_experiment_020_audit.py --allow-download` only when ~8+ GB disk is free (fetches parts 02–06).

**Audit:** 15/100 CNAE-01 profiles available from `profiles_part01.tar.zst` only; 85 require archives not on disk. CER **PENDING_ACCESS**. Gates allow **agriculture-only pilot**; two-category synopsis **not complete**.

**Forecast pilot (Track A):** SVR ± category SLP, persistence, seasonal lag-24, ARIMA(1,0,1) on hourly `cons`. See `results/forecasting/experiment_020/experiment_020_report.md`.

**Not claimed:** residential category, MAPE &lt; 8% synopsis target (pilot MAPE ≫ 8%), ToD/BESS.

# Experiment 020A — Forecast audit and SLP ablation

Date: 2026-11-24

**Command:** `python3 scripts/run_experiment_020a.py` (no downloads; ~10 min)

**Purpose:** Reproduce Experiment 020 metrics from re-run forecasts; save test predictions; paired SVR±SLP ablation; MAPE zero/near-zero sensitivity; data-quality notes. Does **not** modify `results/forecasting/experiment_020/`.

**Findings:** 25/25 pooled macro fields match 020. Persistence best mean MAE (213.5). SLP improves mean MAPE vs no-SLP (reproduces 020) and lowers MAE on 10/15 profiles, but Wilcoxon p≈0.073; no learned model beats persistence on mean MAE. Synopsis MAPE &lt; 8% not meaningful for zero-heavy hourly `cons`.

**Outputs:** `results/forecasting/experiment_020a/experiment_020a_report.md`, `predictions/test_predictions.parquet`, figures `exp020a_*` (FIG-087–094).

# Experiment 020B — Evaluation integrity and imputation sensitivity

Date: 2026-11-24

**Command:** `python3 scripts/run_experiment_020b.py` (~2 min; uses 020A predictions only)

**Purpose:** Verify timestamp alignment; reconcile macro vs micro metrics; operational `flag` sensitivity; paired SLP ablation with bootstrap (seed 202); category-SLP leakage audit. No model retuning; no downloads.

**Findings:** 020A predictions already fully aligned (53,244 test points × 5 models). Exp 020 macro metrics used mixed-origin pairing vs aligned micro (persistence MAE 213.5 vs 192.8). SLP mean ΔMAE −2.07, Wilcoxon p=0.073, bootstrap CI crosses zero — **class B** (small uncertain SLP gain). Flag=1 semantics ambiguous in GoiEner README; sensitivity uses operational tiers. Persistence still best. Do not expand to 85 profiles (**DEC-020**).

**Outputs:** `results/forecasting/experiment_020b/experiment_020b_report.md`, `predictions/aligned_test_predictions.parquet`, figures `exp020b_*` (FIG-095–106).

# Experiment 021 — GoiEner semantics and forecasting failure audit

Date: 2026-11-24

**Command:** `python3 scripts/run_experiment_021.py` (~2.5 min; read-only on 020/020A/020B; no model training)

**Purpose:** Verify GoiEner semantics, target alignment, reproduce 020B metrics, diagnose why SVR/SLP lose to persistence; SLP and extreme-event audits.

**Findings:** 020B micro MAE **reproduced**. Metadata 28900 / CNAE-01 **100** / local **15** confirmed. `cons` units undocumented; flag ambiguous. Persistence valid H=1 benchmark. SVR **over-smooths** (var ratio ~0.59, negative bias). **Class B** — valid results, inadequate model/feature design. SLP leak-free but weak. Do not scale to 85 profiles (**DEC-021**). Next step: protocol revision (design) or CER — not implemented here.

**Outputs:** `results/forecasting/experiment_021/experiment_021_report.md`, audits + `profile_quality_audit.csv`, figures FIG-107–121.

# Experiment 022 — Protocol revision and completion roadmap

Date: 2026-11-24

**Command:** `python3 scripts/run_experiment_022.py` (design audit only; no training, no downloads)

**Purpose:** Synopsis compliance matrix, dataset suitability, forecasting protocol v2, SLP controlled-design spec, ToD/BESS feasibility, contribution assessment, phased roadmap, go/no-go for GoiEner expansion.

**Findings:** Dual-category synopsis **BLOCKED** on CER (critical path). Ag track **PARTIAL**; do **not** extract 85 GoiEner profiles until `cons`/`flag` documented and protocol v2 gates met. SLP benefit **not defensible** for publication from 020–021 alone. MAPE&lt;8% = synopsis reporting only; **MAE/WAPE** for selection. **DEC-022**.

**Outputs:** `results/forecasting/experiment_022/` (`forecasting_protocol_v2.md`, `synopsis_compliance_matrix.csv`, `project_completion_roadmap.md`, etc.).

# Experiment 023 — CER prep, GoiEner query, literature review

Date: 2026-11-24

**Command:** `python3 scripts/run_experiment_023.py`

**Purpose:** Prepare CER/ISSDA application package; draft GoiEner semantics query; structured literature review (9 verified DOIs); protocol v2 audit → v2.1; synopsis audit; proposed Experiment 024 design. **No** auto-submit, **no** downloads, **no** training.

**Findings:** SVR+SLP **not novel** as a method; **MODERATE** gap for dual-category leakage-safe evaluation. CER **critical path** for residential synopsis. GoiEner expansion still **NO-GO** until publisher clarification. **DEC-023**.

**Outputs:** `results/dataset_access/experiment_023/`, `results/literature_review/experiment_023/`, `results/dataset_audit/experiment_023/`, `results/forecasting/experiment_023/`, figures FIG-122–124.

# Experiment 024 — Final experimental design audit (design-only)

Date: 2026-11-24

**Command:** `python3 scripts/run_experiment_024_design.py`

**Purpose:** Finalize dual-track protocol (GoiEner ag + CER residential), SLP F0–F2, stats/regime plans, execution stages, and validation checklist. **No** training, downloads, or submissions.

**Status:** **DESIGN_READY_WITH_BLOCKERS** — CER access and GoiEner semantics gates; protocol v2.1 final awaits **DEC-024-01** approval.

**Outputs:** `results/forecasting/experiment_024/` (`experiment_024_final_design.md`, `forecasting_protocol_v2_1_final.md`, …), figures FIG-125–131.

# Experiment 024A — Protocol integrity and temporal leakage audit (design-only)

Date: 2026-11-24

**Command:** `python3 scripts/run_experiment_024a.py` (synthetic tests: `results/forecasting/experiment_024a/test_timestamp_alignment.py`)

**Purpose:** Audit H=1, SLP calendar slot, F1 cross-profile causality, seasonal-naive indexing, splits. **No** training, downloads, or submissions. **Did not overwrite** `forecasting_protocol_v2_1_final.md`.

**Findings:** Cross-profile F1 leakage **demonstrated** (Test I). **Proposed:** `slot_target` for SLP; causal F1 at `t_origin`; timestamp-based H=1 and seasonal naive. DST/timezone templates **BLOCKED**. Revised protocol: `protocol_v2_1_final_proposed_revision.md` (**PROPOSED — NOT APPROVED**, DEC-024A-01).

**Tests:** 10/10 automated pass; Test J DST blocked.

# Experiment 024B — Final protocol approval audit (design-only)

Date: 2026-11-24

**Command:** `python3 scripts/run_experiment_024b.py` (tests: `results/forecasting/experiment_024b/test_information_eligibility.py`)

**Purpose:** Resolve forecast issuance/information-set semantics (Issue A) and duplicate/common-eligibility rules (Issue B). **No** training, downloads, or submissions.

**Decisions (PROPOSED):** `t_available=t_timestamp` assumption; F1/F2 strict `< t_origin`; rolling primary; Strategy A common mask; conflict dup exclusion (replaces keep-first).

**Output:** `protocol_v2_1_approval_candidate.md` (**AWAITING HUMAN APPROVAL**, DEC-024B-01). **Design-level** `protocol_ready_for_approval: true`; **execution** still blocked.

**Tests:** 16/16 pass (024B); 024A suite unchanged.

# Experiment 024C — Final approval and estimand consistency (design-only)

Date: 2026-11-24

**Command:** `python3 scripts/run_experiment_024c.py` (tests: `results/forecasting/experiment_024c/test_evaluation_populations.py`)

**Purpose:** Split **P1** (six-model) vs **P2** (SVR/SLP primary estimand); clarify idealized zero-latency rolling setting; consolidated `protocol_v2_1_final_approval_candidate.md`. **No** training/downloads/submissions.

**Key finding:** 024B single mask requiring seasonal-naive for all models is **amended** — **P2** is primary for synopsis SLP hypothesis without SN requirement; **P1** for full six-model tableau.

**Tests:** 13/13 pass. **DEC-024C-01** replaces **DEC-024B-01** for human approval review.

# Experiment 024 — Protocol approval and design freeze

Date: 2026-11-24

**Human approval recorded:** DEC-024C-01, DEC-024C-02, DEC-024C-03 **APPROVED**.

**Binding protocol:** `results/forecasting/experiment_024c/protocol_v2_1_final_approval_candidate.md` (status: APPROVED — BINDING).

**Design:** P1 six-model / P2 SLP-primary / P3 diagnostic; rolling causal F1/F2; timestamp H=1; idealized `t_issue=t_origin`, `t_available=t_timestamp`.

**Execution:** **NOT READY** — GoiEner metadata partial; CER access not granted. **No** `run_experiment_024.py`; **no** training.

**Artifacts:** `approved_protocol_freeze.md`, `execution_readiness_assessment.md`, `stage_0_dataset_readiness_plan.md`, `implementation_architecture.md`, `project_status.md`.

**Next phase:** Stage 0 metadata resolution (manual CER submit + GoiEner query).

# Experiment 025 — Public dataset-only execution path

Date: 2026-11-24

**Command:** `python3 scripts/run_experiment_025.py`

**Constraint (DEC-025-01):** Only directly downloadable public data — **no** CER application, **no** GoiEner author email.

**Executed:** Dataset inventory/eligibility; **15 GoiEner CNAE-01 QC** (`goiener_15profile_qc.csv`); downloaded Norwegian residential **`households.csv`** (Zenodo 7856848).

**Not executed:** Binding Experiment 024 forecasting (metadata gates); full `demand.csv` download (~363 MB — next step).

**Outputs:** `results/forecasting/experiment_025/`

# Experiment 026 — Norwegian residential ingestion and readiness

Date: 2026-11-24

**Command:** `python3 scripts/run_experiment_026.py`

**Executed:** Downloaded **demand.csv** (362,648,777 B; MD5 verified); schema/timestamp/consumption audits; household join (**1,136** `Demand_data=Yes`); pilot parquet (5 HH); GoiEner descriptive CSV. **No forecasting.**

**Readiness:** AUDITED — partial P2 feasibility; **Exp 024 residential track not authorized** (interval/TZ/DST semantics open).

**Outputs:** `results/forecasting/experiment_026/`, `data/external/norwegian_residential/processed/pilot_demand.parquet`

# Next Step

**Priority:** Human authorization for residential forecasting after resolving **Hour/timestamp semantics + TZ/DST** (DEC-026-03). Optional: full Norwegian per-household coverage scan; GoiEner exploratory only.

## Experiment 027 (2026-11-24)

Norwegian temporal semantics + full P2 eligibility audit. See `results/forecasting/experiment_027/`.

## Experiment 028 (2026-11-24)

Exploratory Norwegian SVR±SLP dual-timestamp study. `results/forecasting/experiment_028/`.

## Experiment 029 (2026-11-24)

Audit of Exp 028 SLP/metrics. See `results/forecasting/experiment_029/` and `new_submit/`.

## Experiment 030 (2026-11-24)

Corrected Norwegian SVR±SLP after Exp 029 audit.

## Experiment 031 (2026-11-24)

Norwegian residential baseline audit; frozen baseline selection.

## Experiment 032 (2026-11-24)

CEEW ToD analysis; BESS input profiles.

## Experiment 033 (2026-11-24)

CEEW BESS peak-shaving demonstration.

## Experiment 034 (2026-11-24)

BESS simulation audit and validated results (`results/forecasting/experiment_034/`).

## Experiment 035 (2026-11-24)

Final BESS validation and project consolidation.

## Final submission pack (2026-11-24)

Experimental phase closed (001–035). Evaluation materials: `final_submission/` (report, presentation, viva, traceability). Indexed in `new_submit/131_*` … `136_*`. Original synopsis PDF unchanged.

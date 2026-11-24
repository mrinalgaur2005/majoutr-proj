# Research Experiment Log

## Project

Research-oriented experimental pipeline for CEEW Mathura–Bareilly high-frequency smart-meter data: data audit, causal preprocessing, 15-minute aggregation, daily load profiles, normalization analysis, and clustering through validation. Forecasting and downstream applications are explicitly out of scope for this milestone.

## Research Question

"Does incorporating recurring load-profile information extracted from high-frequency smart-meter data improve short-term load forecasting compared with conventional temporal/aggregate forecasting approaches in the CEEW Mathura–Bareilly setting?"

(Research question unchanged; clustering milestone prepares profile representations for later forecast comparison.)

## Current Milestone

CEEW data foundation + daily load profiles + clustering

## Environment

- Python version: 3.12.3
- pandas 3.0.5, numpy 2.5.3 (see `results/foundation_pipeline_summary.json`)
- OS: Linux-6.14.0-37-generic-x86_64-with-glibc2.39
- Execution date/time: 2026-09-23T08:28:09.544961+00:00

## Repository State Before Experiment

**Present and reused:**

- Raw CEEW files: `data/raw/ceew_mathura_bareilly/` (Harvard Dataverse, untouched)
- Loader: `src/data/ceew_loader.py` (chunked read, `interval_energy_kwh`, derived `load_kw`)
- Prior audit outputs preserved: `results/ceew/dataset_audit.json`, `results/ceew/per_meter_coverage.csv`
- Legacy script (not used as main path): `scripts/prepare_ceew_15min.py` (meter-median unit of analysis)

**Synthetic / forecasting stack (not used on CEEW):**

- `phase_1_processing.py`, `run_all_experiments.py`, `svr_feature_engineering_tuning.py`, phases 3–5
- Prior synthetic results under `results/` (e.g. `final_metrics.csv`) — not deleted

**Conflicts documented:**

| Component | Issue | Action |
|-----------|--------|--------|
| `phase_1_processing.py` | Mean resample, bidirectional cubic spline, min-max norm, K=2, Residential/Agricultural labels | Not used on CEEW |
| `prepare_ceew_15min.py` | Clusters one median profile per meter (≥14 complete days), not meter-days | Not main clustering unit |
| `README.md` | Previously described repo as synthetic-only | Updated after milestone |

## Dataset

- **Source:** Agrawal et al., Harvard Dataverse DOI `10.7910/DVN/GOCHJH`
- **Paths:** `data/raw/ceew_mathura_bareilly/*.csv`, `*.tab`, `CEEW -  ReadMe.txt`
- **Meters / locations:** 84 meters; Bareilly (`BR*`), Mathura (`MH*`)
- **Date ranges (from prior audit):** Bareilly 2019-05-09 – 2021-10-31; Mathura 2019-05-01 – 2021-02-20
- **Sampling:** 3-minute intervals per README (`t_kWh` per interval)
- **Columns:** timestamp, meter, interval energy (`t_kWh`), voltage, current, frequency
- **Units:** Interval energy in kWh per 3-min record; `load_kw = t_kWh / 0.05` (average kW over 3 min)
- **Uncertainties:** Naive timestamps (no timezone field); urban household meters per documentation — no verified consumer-category labels

## Preprocessing leakage classification (main path)

| Operation | Leakage |
|-----------|---------|
| Complete-bin 15-min sum of `t_kWh` / 0.25 h | **Safe** (uses only timestamps in bin) |
| Exclude incomplete 15-min bins | **Safe** |
| Require 96 complete bins per day | **Safe** (listwise complete days) |
| No global interpolation | **Safe** |
| Zeros retained as measured values | **Safe** |
| Joint clustering on all profile days | **Safe** for unsupervised shape discovery; **not** safe if same labels later used in training without temporal split (forecast milestone) |
| Global outlier dropping by full-sample threshold | **Not applied** (would be leaky for temporal forecast if reused) |

## Steps 1–5

See Executive Summary and step sections at end of this file. Reproduce with `python scripts/run_ceew_foundation.py`.

---

---

---

# Executive Summary

## Dataset Used

- 21,845,497 raw 3-minute rows, 84 meters
- Rows by city: {'Bareilly': 13946703, 'Mathura': 7898794}
- Raw file checksums: see `results/data_audit/audit_summary.json`

## Data Quality Findings

- Nulls in core fields: {'interval_energy_kwh': 0, 'voltage_v': 0, 'current_a': 0, 'frequency_hz': 0, 'load_kw': 0}
- Negatives: {'interval_energy_kwh': 0, 'voltage_v': 0, 'current_a': 0, 'frequency_hz': 0, 'load_kw': 0}
- Zero interval energy rows: 3550039
- Extreme load rows (>50.0 kW): 0
- Mean per-meter coverage %: 79.68 (median 82.18)
- 15-min bins complete / total: 4188438 / 4279109
- Malformed timestamps: 0; off 3-min boundary: 0

## Preprocessing Decisions

- 15-min power: sum(`t_kWh`) / 0.25 h only when bin has exactly 5 unique 3-min points spanning 12 minutes
- Daily profile: 96 complete 15-min slots; no imputation
- Clustering input: meter-day profiles with positive daily energy

## Missing Data Strategy

- Missing timestamps → incomplete bins → NaN load; incomplete days excluded from profiles
- Zeros are valid measurements, not treated as missing

## Number of Valid Profiles

- Meter-days total (any completeness): 44610
- 100% complete meter-days: 43555
- ≥95% slots (sensitivity count only): 43588
- Profiles used in clustering (non-zero energy): 42637
- All-zero complete days excluded: 918

## Normalization Experiments

- **Peak:** P_t / max(P_t); mean row variance = 0.050927
- **Energy (sum):** P_t / sum(P_t); mean row variance = 0.000128
- Both representations clustered for K=2..6; no single metric used to declare winner

## Clustering Algorithms

- K-Means (sklearn), Euclidean, n_init=20, seeds=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
- Joint clustering across Mathura and Bareilly meter-days

## K Values Tested

[2, 3, 4, 5, 6]

## Clustering Metrics

**Energy normalization:**

- K=2: silhouette(subsample)=0.1522, DB=3.2768, CH=2787.8, sizes=[16177, 26460]
- K=3: silhouette(subsample)=0.1300, DB=3.4004, CH=2141.1, sizes=[26038, 5466, 11133]
- K=4: silhouette(subsample)=0.0316, DB=3.2121, CH=1907.7, sizes=[18662, 2893, 4504, 16578]
- K=5: silhouette(subsample)=0.0316, DB=2.9670, CH=1731.9, sizes=[2663, 16256, 18344, 2615, 2759]
- K=6: silhouette(subsample)=0.0245, DB=2.9007, CH=1588.5, sizes=[2443, 12381, 2471, 4401, 2472, 18469]

**Peak normalization:**

- K=2: silhouette(subsample)=0.2424, DB=1.5893, CH=15908.2, sizes=[19075, 23562]
- K=3: silhouette(subsample)=0.1455, DB=2.1958, CH=10634.2, sizes=[15685, 16232, 10720]
- K=4: silhouette(subsample)=0.1423, DB=2.2358, CH=8440.6, sizes=[7019, 15396, 12360, 7862]
- K=5: silhouette(subsample)=0.1036, DB=2.4499, CH=6898.8, sizes=[7131, 12417, 4651, 11232, 7206]
- K=6: silhouette(subsample)=0.1013, DB=2.5438, CH=5900.3, sizes=[3996, 6986, 7594, 11372, 5892, 6797]

Silhouette computed on subsample n=10000 (seed 42).

## Stability Results

**Energy:**

- K=2: ARI mean=0.9979, std=0.0013, min=0.9948
- K=3: ARI mean=0.9905, std=0.0067, min=0.9848
- K=4: ARI mean=0.9941, std=0.0014, min=0.9916
- K=5: ARI mean=0.9962, std=0.0010, min=0.9946
- K=6: ARI mean=0.9935, std=0.0039, min=0.9900

**Peak:**

- K=2: ARI mean=0.9993, std=0.0005, min=0.9989
- K=3: ARI mean=0.9941, std=0.0024, min=0.9895
- K=4: ARI mean=0.9989, std=0.0010, min=0.9969
- K=5: ARI mean=0.9939, std=0.0044, min=0.9869
- K=6: ARI mean=0.9814, std=0.0102, min=0.9618

## Selected / Candidate K

- Best silhouette (subsample) under **energy** norm: K=2 (score=0.1522)
- Best silhouette (subsample) under **peak** norm: K=2 (score=0.2424)
- Metrics may disagree across indices and normalizations; no final K forced here.

## Cluster Characteristics

See `results/clustering/cluster_summary.csv`. Sample (energy norm, K=3 if present):

```
 cluster  n_profiles  pct_profiles  mean_daily_energy_kwh  mean_peak_load_kw  mean_peak_slot  mean_load_factor  morning_strength_kw  daytime_strength_kw  evening_strength_kw  overnight_strength_kw  profile_flatness  k normalization
       0       26038     61.069025                9.80531           1.142236       53.740072          0.383894             0.312016             0.333096             0.395728               0.530867          0.254406  3        energy
       1        5466     12.819851                5.04531           1.480695       38.435053          0.154424             0.392735             0.203905             0.206725               0.126677          0.535209  3        energy
       2       11133     26.111124                6.41657           1.180224       55.478577          0.247412             0.208804             0.369073             0.325454               0.171321          0.356871  3        energy
```

## Mathura vs Bareilly Findings

```
    city  n_profiles  n_meters  mean_daily_energy_kwh  mean_peak_load_kw  median_peak_slot
Bareilly       26395        46               8.357323           1.175845              54.0
 Mathura       16242        38               8.233743           1.227559              43.0
```

Location composition per cluster: `results/clustering/cluster_location_composition.csv`

## Potential Problems / Threats to Validity

- Naive timestamp timezone
- Long outage gaps (per-meter max gap minutes in meter_quality.csv)
- Joint clustering may encode location-specific shapes
- Silhouette on subsample is approximate for large N

## Decisions Requiring Human Review

- Confirm energy vs peak normalization for forecast-stage SLP features
- Choose candidate K after reviewing metrics, stability, and interpretability

## Next Recommended Step

Chronological train/validation/test split and persistence / seasonal-naive / SVR baselines (out of scope for this milestone).

---

## Step 1 — Data Audit (numerical)

- Meters: 84
- Total rows: 21845497
- Per-meter table: `results/data_audit/meter_quality.csv`
- Location summary: `results/data_audit/location_summary.csv`

## Step 2 — Preprocessing

See leakage table above and `results/foundation_pipeline_summary.json` bin_stats.

## Step 3 — Daily Profile Construction

- Valid 96-slot profiles for clustering: 42637
- Based on **average kW** per 15-min bin (not normalized energy shape alone)

## Step 4 — Normalization

Primary **provisional** choice for later forecasting: daily-energy normalization (shape-focused; peak norm sensitive to single-slot spikes).

## Step 5 — Clustering

Outputs under `results/clustering/`.

---

## Experiment 006 — Final clustering audit (formal)

Date: 2026-09-23. Command: `python3 scripts/final_clustering_audit.py`. No forecast model was fit.

### Assumptions

- Meter-day K-means labels from seed 0 are the descriptive partition.
- Coverage in `meter_quality.csv` remains row-based. The diagnosis does not replace it.
- Temporal split uses the median profile date (2020-05-21), not a pre-registered calendar date.
- Cramér’s V is computed on the K=2 city × cluster table only.
- Meter-level profiles are medians of already day-normalized vectors, restricted to meters with at least 14 positive-energy complete days (83 meters).

### Leakage

Operations in this audit are descriptive of the full sample. They are not valid as forecast features. A leakage-safe protocol is specified in README.md (DEC-009) and is not implemented. Using `cluster_assignments.parquet` inside a model trained on the same dates would be definitely leaky.

### Numerical results

Coverage above 100% (row formula unchanged):

- BR49: 382,908 rows, 369,120 unique timestamps, unique coverage 97.96%, 13,788 duplicated timestamps.
- BR50: 450,240 rows, 294,240 unique timestamps, unique coverage 91.22%, 156,000 duplicated timestamps.
- BR51: 532,320 rows, 360,960 unique timestamps, unique coverage 97.79%, 171,360 duplicated timestamps.

Within-chunk duplicate counts in the original audit are 0 because repeats sit across files. Sampling on the unique clock is still 3 minutes.

Location, K=2: Cramér’s V = 0.0482 (peak) and 0.0366 (energy). Overall Bareilly share = 0.619. Not a location partition.

Magnitude and shape, peak K=2: Cluster 0 mean energy 10.93 kWh, load factor 0.467, mean peak 1.03 kW (n=19,075). Cluster 1 mean energy 6.19 kWh, load factor 0.199, mean peak 1.33 kW (n=23,562). Conclusion: both level and shape.

Meter-level silhouette: peak K=2 is 0.365 (sizes 37 and 46). Energy K=2 is 0.557 (sizes 77 and 6). The energy score is not evidence of a balanced household typology.

Temporal ARI, early model versus late refit: peak 0.830, energy 0.619. Multi-seed ARI from Experiment 005 remains a different quantity (all ≥ 0.962).

### Supported conclusions

- K=2 is the strongest internal-validity candidate on both normalizations. It is not uniquely identified as the scientific model, because silhouette is moderate and K=3 still has a readable size pattern.
- Peak normalization is better behaved on silhouette, Davies–Bouldin, Calinski–Harabasz, temporal ARI, and meter-level balance.
- The earlier provisional choice of energy normalization is not confirmed. Decision status: OPEN.
- Meter-day clustering describes recurring daily states. It should not be described as a household archetype model.
- Clusters are not strongly location-driven and must not be named residential, agricultural, or commercial.

### Threats added by this audit

Cross-file duplicate timestamps may have been summed into 15-minute energy for BR49–BR51. If the paired rows carry the same `t_kWh`, those bins are inflated. The effect on cluster membership was not re-estimated. This is unresolved.

## Experiment 007 — Duplicate timestamps

Command: `python3 scripts/diagnose_duplicate_timestamps.py`.

341,148 duplicated timestamps. All measurement fields match exactly (energy difference 0). All repeats are inside the Bareilly 2020 file only. The earlier cross-file interpretation is rejected.

Sensitivity command: `python3 scripts/duplicate_sensitivity.py`.

Matched complete days have mean absolute daily-energy difference 0. Peak K=2 ARI between the original labels and labels after replacing those days is 1.0. Deduplication increases complete bins because the five-row rule had been rejecting bins that contained an extra copy. Forecasting uses the deduplicated bin file. Original clustering files were not overwritten.

DEC-010: keep the first exact copy. Status: FINAL.

## Experiments 008–012 — Leakage-safe forecast test

These results are forecasting results. They do not change the descriptive clustering results.

Hypothesis: previous-day distance to historical centroids reduces 15-minute-ahead error beyond lag and cyclic features.

Method: target is load at t+H. Train ends 2020-06-30 (2,109,423 rows). Validation ends 2020-12-31 (891,056). Test is 2021-01-02 to 2021-10-31 (829,864). Centroids are fit only on days before the split being scored. All-period cluster assignments are not features. SVR is RBF, C=100, epsilon=0.2, gamma=scale, scaler fit on a 2,000-row train+validation sample.

H=1 test MAE (kW): persistence 0.108, seasonal naive 0.220, lag 0.229, lag+cyclic 0.557, lag+peak SLP 0.247, lag+cyclic+peak SLP 0.518, lag+cyclic+energy SLP 0.570, lag+cyclic+peak K=3 0.546.

Wilcoxon on paired absolute errors, lag+cyclic+SLP versus lag+cyclic: MAE reduction 6.85%, n=103,733 (every 8th pair), p-value reported as 0 in `statistical_tests.csv`. Persistence remains better than both by a large margin. The same pattern holds at H=2, 4, and 8 and in the city, weekday, and peak subgroups.

Decision: do not claim that SLP improves forecasting. The pooled SVR is not a competent baseline (ISSUE-004). DEC-006 stays OPEN.

## Experiment 013 — Per-meter conventional baseline

Command: `python3 scripts/run_experiment_013.py`

Hypothesis: independent per-meter lag models can match persistence. SLP was not tested.

Assumptions: `lag_1 = load(t)` when the target is `load(t+1)`. Seasonal naive is `load(t-96)`. A meter needs 1,344 / 288 / 288 usable train / validation / test rows. SVR training uses only the latest 1,500 rows. The competency rule uses MAE, not RMSE.

Results, micro, n=835,410 eligible-meter test rows, 68 meters: persistence MAE 0.107, RMSE 0.271, R² 0.723. Ridge lag MAE 0.117, RMSE 0.250, R² 0.763. Ridge lag+cyclic MAE 0.117. SVR lag MAE 0.196. Seasonal naive MAE 0.222.

Macro median MAE: persistence 0.055, ridge lag 0.062, ridge lag+cyclic 0.064, SVR 0.083. Ridge MAE wins on 5/68 meters. Ridge RMSE wins on 66/68.

City micro MAE: Bareilly persistence 0.112 vs ridge 0.122; Mathura persistence 0.067 vs ridge 0.073.

Median autocorrelation in the training window: lag 1 = 0.845, lag 2 = 0.716, lag 4 = 0.600, lag 8 = 0.480, lag 96 = 0.540.

Decision: persistence remains the strongest conventional baseline on MAE. The pooled Experiment 012 SVR is retired as a primary baseline. SLP ablation is not run. DEC-011: do not treat ridge or per-meter SVR as the forecasting baseline until a model matches persistence on the primary MAE criterion.

## Experiment 014 — Load-change forecasting

Command: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_014.py`

Hypothesis: predicting `ΔP(t+1)=P(t+1)-P(t)` and reconstructing `P(t)+Δ̂` beats persistence on reconstructed-load MAE when level forecasting failed in Experiment 013.

Method: same deduplicated bins, splits, eligibility (68 meters), and Ridge alphas as Experiment 013. Models: zero-change, Ridge on delta lags, Ridge on load lags, Ridge on both, Ridge on delta lags plus calendar cycles. No SLP. Validation MAE on the delta target selects alpha. Reconstructed-load MAE uses the Experiment 013 competency rule. Movement tertiles of `|ΔP|` from training rows only. Horizons H=2,4,8 reported for zero-change and ridge delta.

Verification: `zero_change` reconstructed load equals `P(t)` with max absolute difference 0.0 (persistence equivalence).

Results, micro reconstructed load, n=835,410: zero-change MAE 0.107, RMSE 0.271, R² 0.723. Ridge delta MAE 0.111, RMSE 0.262, R² 0.740. Ridge both MAE 0.117, RMSE 0.250, R² 0.764. City micro MAE (zero-change / ridge delta): Bareilly 0.112 / 0.115; Mathura 0.067 / 0.069.

Macro median MAE: zero-change 0.055, ridge delta 0.058, ridge both 0.061. Meters with lower MAE than persistence: ridge delta 5/68, ridge both 6/68.

Movement tertile mean MAE (reconstructed load): low |ΔP| persistence 0.0037 vs ridge delta 0.016; high |ΔP| persistence 0.261 vs ridge delta 0.245 vs ridge both 0.224.

Wilcoxon signed-rank on paired absolute errors (stride 8): ridge variants not better than persistence (p=1.0).

Decision case B: competency rule not met on the full sample. Do not add SLP. Residual ridge skill appears only in the large-movement tertile. RMSE improvements without MAE gains mirror Experiment 013; MAE stays the primary metric.

DEC-012: load-change Ridge does not replace persistence as the baseline. SLP ablation remains blocked.

Note on the Experiment 014 Wilcoxon: the test used every 8th 15-minute row with alternative “greater.” Those rows are serially dependent, so the p-values are not treated as confirmatory. Experiment 015 moves inference to the meter.

## Experiment 015 — Change-aware forecasts (plan)

Date: 2026-09-30.

Research question: can a leakage-free rule that uses only information available at time t combine persistence and a load-change model so that full-sample MAE improves on persistence?

Hypothesis: Ridge delta loses MAE on small changes and gains on large ones. A validation-chosen shrinkage toward zero change, or a gate on the latest observed `|ΔP(t)|`, can keep the large-change gains without using the future change. A Huber fit on the same lags tests whether squared loss, rather than the delta target, caused the MAE loss.

Dataset and splits: `data/interim/ceew_15min_bins_dedup.parquet`. Train origins before 2020-07-01, validation origins before 2021-01-01, test origins from 2021-01-01. Eligibility 1,344 / 288 / 288 usable rows, same as Experiments 013 and 014.

Target: `ΔP(t+1)=P(t+1)−P(t)`. Reconstructed load `P(t)+Δ̂`. This equals the one-step persistence residual; that formulation is not run as a second model.

Not re-tested: Ridge on load lags, Ridge on both, and Ridge delta plus calendar cycles (Experiment 014). No SLP.

Leakage controls: scalers and thresholds from training rows; hyperparameters from validation MAE; test untouched until the final scores. Retrospective `|ΔP(t+1)|` tertiles are diagnostic only.

Command: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_015.py`

Results: filled after the run.

## Experiment 015 — Change-aware forecasts (results)

Date: 2026-09-30. Runtime about 19 seconds. Script: `scripts/run_experiment_015.py`.

Sanity checks: zero-change reconstruction equals `P(t)` (max abs diff 0). `P(t+1)−P(t)` matches the stored delta (max abs diff 0). No duplicate meter-bin rows in the complete deduplicated file. Ridge delta test MAE 0.11078440005251777 matches Experiment 014 (absolute difference ~1e-16). 68 eligible meters, 835,410 test rows, same timestamps for every model. Huber failures: none. Ineligible meters remain in `per_meter_eligibility.csv` with reason `below_minimum_usable_rows`.

Validation micro MAE, used for selection: shrink_meter 0.100698, huber_delta 0.100775, shrink_global 0.100868, zero_change 0.101341, gate_recent 0.101449, ridge_delta 0.104245 (n=820,913). Selected model: shrink_meter. Pooled λ for shrink_global: 0.25. Per-meter λ counts: 0 → 32, 0.25 → 26, 0.50 → 8, 0.75 → 1, 1 → 1.

Test micro MAE / RMSE / R²: zero_change 0.107447 / 0.270548 / 0.722892; shrink_meter 0.107011 / 0.266110 / 0.731909; shrink_global 0.107047 / 0.266642 / 0.730837; huber_delta 0.107195 / 0.264907 / 0.734327; gate_recent 0.107888 / 0.265149 / 0.733843; ridge_delta 0.110784 / 0.262107 / 0.739913.

Absolute MAE change versus persistence: shrink_meter −0.000436 kW (−0.41%), shrink_global −0.000400 kW (−0.37%), huber −0.000252 kW (−0.23%), gate +0.000441 kW (+0.41%), ridge_delta +0.003337 kW (+3.11%).

Macro median MAE: zero_change 0.054859, shrink_global 0.054914, gate 0.055400, shrink_meter 0.055724, huber 0.056397, ridge_delta 0.058205.

Meter-level Wilcoxon on paired MAE differences (n=68, ties dropped by the test): shrink_meter 26 better, 10 worse, 32 tied, median difference 0, two-sided p=0.00082. shrink_global 34/34, p=0.11. The 32 ties are the meters whose validation rule set λ=0.

Retrospective high-`|ΔP|` micro MAE: persistence 0.271, ridge_delta 0.257, shrink_meter 0.266. Retrospective low-`|ΔP|` micro MAE: persistence 0.0044, shrink_meter 0.0078, ridge_delta 0.0199. These cuts use the realized future change and were not used to choose λ or the gate.

Decision: DEC-013. A leakage-free shrinkage of the Experiment 014 Ridge delta forecast lowers pooled test MAE by about 0.4% and keeps that direction from validation to test. It does not lower the median meter’s MAE. The Experiment 013 competency band is met only because that band allows the median to be up to 5% worse. That is not a sufficient reason to add SLP. Persistence stays the baseline. ToD and BESS were not started.

What was not tested: SLP, ToD, BESS, calendar-cycle Ridge, load-lag Ridge, horizons other than H=1.

## Experiment 016 — When shrinkage helps (plan)

Date: 2026-09-30.

Research question: can forecast-time information explain the 36 nonzero λ assignments from Experiment 015, and can a rule using only that information choose between persistence and shrinkage without seeing the test set?

Method: audit saved Experiment 015 files rather than refitting. Sign convention: MAE difference = model − persistence. Candidate rules, chosen by validation pooled MAE only: always persistence, always per-meter shrinkage, one city only, or training mean `|ΔP|` at or above the 50/75/90 percentile across meters. Test associations are retrospective. Meter is the inferential unit. Seed 16.

Command: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_016.py`

## Experiment 016 — When shrinkage helps (results)

Date: 2026-09-30. Runtime about 6 seconds. Script: `scripts/run_experiment_016.py`.

Baseline check: recomputed test MAE/RMSE from `predictions/experiment_015/test_predictions.parquet` match the saved micro metrics to < 10⁻¹⁶. Persistence 0.107447/0.270548, shrink_meter 0.107011/0.266110, shrink_global 0.107047/0.266642, ridge_delta 0.110784/0.262107. n=835,410. Eligible meters=68. Weighted per-meter MAE equals the pooled MAE. No duplicate meter-time keys. λ=0 implies a test tie on all 32 such meters.

Counts: λ>0 on 36 meters; test helped 26, hurt 10, tied 0. Median test MAE difference 0. Mean −0.000327 kW. Pooled difference −0.000436 kW (−0.41%). Meter bootstrap (seed 16, 2000 resamples of meters): pooled difference 95% interval [−0.000699, −0.000195]; median interval reaches 0.

Concentration: the five largest negative contributions (BR24, BR11, BR04, BR36, BR51), all Bareilly, are 64% of the net pooled gain. Ten meters are 85%. λ=0 meters contribute 0.

City: Bareilly λ>0 / λ=0 = 23/13, pooled MAE 0.111847 vs 0.111415, median difference 0. Mathura 13/19, pooled 0.067143 vs 0.066672, median 0. Mathura pooled bootstrap interval includes values at or above zero.

Exploratory association, validation λ only: median training mean `|ΔP|` is 0.097 kW when λ>0 and 0.046 kW when λ=0. Spearman with λ is 0.33 (p=0.007). Mean load and change standard deviation are correlated with the same split. This is not treated as a confirmed mechanism. Retrospective Spearman of training mean `|ΔP|` with test MAE difference is −0.37 and was not used for selection.

Validation pooled MAE of the prespecified rules: always shrink 0.100698 (68 meters), `|ΔP|` ≥ p50 0.100814 (34), Bareilly only 0.100922 (36), `|ΔP|` ≥ p75 0.101032 (17), Mathura only 0.101117 (32), `|ΔP|` ≥ p90 0.101175 (7), always persistence 0.101341. Frozen rule: always_shrink_meter. Its test MAE and median meter difference are those of Experiment 015. No other rule was evaluated on the test set.

Wilcoxon, all 68 meters: p=0.00082 dropping ties, p=0.00243 keeping ties (Pratt). The drop-ties test ignores the 32 meters whose forecast is persistence.

Deviation: the first run aborted because the training-feature mask omitted Experiment 015’s lag-completeness filter. The successful run uses that filter and asserts agreement with the saved training mean `|ΔP|`.

DEC-014: no forecast-time screen in the prespecified set beats using the validation-chosen λ, including λ=0. That policy’s pooled MAE gain is small and concentrated. It does not move the median meter. Do not add SLP, ToD, or BESS on this evidence. Persistence remains the baseline.

What was not tested: new model classes, a retuned step-level gate, SLP, ToD, BESS.

## Experiment 017 — Temporal integrity and forecast evaluation audit

Date: 2026-11-24. Command: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_017.py`. Runtime ~7 s. Script: `scripts/run_experiment_017.py`. No new models.

Objective: verify timestamp semantics, split boundaries, feature leakage, and baseline reproducibility before Experiment 018 (SLP).

017A: timezone-naive `datetime64` bins; zero duplicate complete `(meter_id, bin)`; 15-minute median spacing on all meters. CEEW ReadMe does not specify timezone — UNRESOLVED (do not assume IST/UTC).

017B: origin split matches 013–016 code; 68 eligible meters; eligibility file matches audit for all 84 meters; disjoint train/val/test origin sets; H=1 target at `t+15m`.

017C: validation-only selection for α, λ, gate, 016 rule; no confirmed leakage in the forecasting pipeline; movement tertiles and all-period clusters excluded from inputs.

017D: recomputed test MAE/RMSE match Experiment 015 micro metrics (tolerance 1e-6); n=835,410; zero-change = P(t); 016 rule = 015 shrinkage.

017E: frozen baseline spec, metrics, SHA-256 manifest, artifact copies in `experiment_017/frozen_artifacts/`.

017F: `experiment_018_slp_protocol.md` written; not implemented.

Discrepancies: `methodology_discrepancies.csv` (Experiment 012 `dataset_split.json` test start vs 013–016; eligibility `train_rows` vs `usable_*`).

Audit status: **AUDIT PASSED WITH UNRESOLVED LIMITATIONS** (timestamp zone unresolved).

DEC-015: the 013–016 chronological evaluation protocol is adequate to proceed to a leakage-safe SLP ablation under `experiment_018_slp_protocol.md`, provided SLP features respect pre-origin history only and success is judged on MAE including median per-meter improvement, not pooled gain alone.

What was not tested in 017: SLP, ToD, BESS, Experiment 018 implementation.

## Experiment 018 — Leakage-safe SLP forecasting

Date: 2026-11-24. Commands: `python3 scripts/run_experiment_018.py`; `python3 scripts/finalize_experiment_018.py`. Runtime ~278 s training + ~7 s finalize.

Research question: does causal recurring daily load-profile information improve 15-minute-ahead load forecasting beyond conventional lags/calendar and frozen Experiment 015 shrinkage?

Hypotheses: null — SLP features do not yield meaningful MAE improvement across eligible meters; alternative — historical profile shape generalizes (not assumed).

Data: `ceew_15min_bins_dedup.parquet`; 68 meters; 835,410 test rows; identical origin splits as Experiment 017.

SLP features (peak-normalized, K=2): for each forecast origin, fit population centroids using completed profiles with `date <` origin calendar day; take the meter’s latest completed profile before t; use Euclidean distance to nearest centroid (primary) and nearest centroid index (diagnostic); optional trailing seven-day median-profile correlation (ablation arm). No all-period cluster labels. Automated injection test: adding a future profile does not change historical features.

Models: Ridge on `ΔP` with delta lags + calendar (same as Experiment 014 family); ablations ± SLP distance, ± correlation, noise control (seed 18, training-scaled). Comparators merged from frozen Experiment 015 (persistence, shrink_meter) and 013 (`ridge_lag_cyclic`) without refit. α and SLP variant chosen on validation pooled load MAE only; primary test model = `ridge_delta_cyclic_slp` (lowest validation MAE among three ridge variants).

Test results (micro MAE kW): persistence 0.107447; frozen shrink_015 0.107011; ridge_delta_cyclic 0.111346; primary SLP 0.111347; frozen 013 ridge 0.117321. Median per-meter MAE: persistence 0.054859; primary SLP 0.060928. Meters improved / worse / tied vs persistence: 4 / 64 / 0. Wilcoxon signed-rank (Pratt, 68 meters): p=2.01×10⁻¹⁰. Meter bootstrap median difference 95% CI [0.00193, 0.00408] kW (seed 18, 2000 draws). City micro MAE: both Bareilly and Mathura worse than persistence for the SLP ridge family.

Ablation: SLP distance and correlation change micro MAE by ≲10⁻⁵ kW versus no-SLP ridge; noise control matches SLP arms — no evidence of real SLP signal.

Predeclared success criteria: **all failed** (including median-meter and 1.02× persistence rule). Formal conclusion **C** — no meaningful forecasting improvement.

DEC-016: leakage-safe SLP features are implementable but do not improve MAE versus persistence or frozen shrink_015. Do not add ToD, BESS, or tariff work on an SLP benefit claim. Persistence remains the MAE reference.

Limitations: timezone unresolved (017); energy-normalization sensitivity not executed; validation prediction parquet not saved (validation MAE in `experiment_018_model_selection.csv`).

What was not tested: ToD, BESS, test-tuned K or normalization, all-period cluster assignment as input.

## Experiment 019 — External category-labelled dataset feasibility audit

Date: 2026-11-24. Command: `python3 scripts/run_experiment_019.py`. Runtime ~66 s. No forecasting.

Motivation: Original project synopsis requires residential and agricultural **verified** consumer categories, SVR with SLP-derived features, persistence and ARIMA baselines, MAPE/RMSE/R², and downstream ToD/microgrid applications. CEEW Mathura–Bareilly has **no** ag/res labels and remains the frozen supplementary India track. Experiment 018 (Ridge+centroid SLP on unlabeled CEEW) does not test the synopsis hypothesis (DEC-017).

Datasets investigated:

- **GoiEner v7.1** (Zenodo 10.5281/zenodo.22313409, CC-BY-4.0): 28,900 series; public metadata = `id` + two-digit CNAE division. CNAE division **01**: n=100. Individual profiles (pre-imputation) are **hourly** with multivariate columns (`cons`, `self`, `gen`, `flag`, …). Audit used selective extract from `profiles_part01.tar.zst` (IDs 00001–05291) due to disk limits. No verified residential/domestic CNAE label in public metadata.
- **CER ISSDA** (10.7929/ISSDA/BX59EU): **PENDING_ACCESS**. Documented 30-minute kWh intervals; allocation Residential/SME/Other — **no agriculture category**.
- **EnergyBench** (HuggingFace ai-iot/EnergyBench, CC-4.0): catalog snapshot; building-use Residential/Commercial labels are **not** CNAE or CER codes; synthetic partitions excluded from tier-1 eligibility.

Synopsis alignment: agricultural category **supported** on GoiEner (CNAE 01); residential **partial** (CER pending); **multi-dataset** design required for both synopsis categories. Native GoiEner forecasting horizon: **hourly** (do not upsample to 15 min). Weather not in GoiEner v7.1 public metadata.

DEC-017: Continue the original synopsis on external labelled data; preserve CEEW Experiments 001–018; do not claim Experiment 018 disproves SLP in general.

Deliverables: `results/dataset_audit/experiment_019/`, `experiment_020_protocol.md`, figures FIG-081–086.

What was not tested in 019: Experiment 020 model training, ToD, BESS, CER row-level audit.

## Experiment 020 — Category-labelled SLP + SVR (partial, local-only)

Date: 2026-11-24. Commands: `python3 scripts/run_experiment_020_audit.py` (default no download); `python3 scripts/run_experiment_020_forecast.py`.

Audit: 15/100 CNAE-01 profiles from local `profiles_part01.tar.zst` only; mapping for 85 others `ARCHIVE_NOT_ON_DISK`. CER checklist `cer_access_checklist.md` — PENDING_ACCESS.

Forecast Track A pilot: hourly `cons`, 70/15/15 chronological, category hour-of-week SLP (train-only), models persistence / lag-24 / ARIMA(1,0,1) / SVR / SVR+SLP. Pooled mean MAPE: persistence 258%, SVR+SLP 1010%, SVR 1050% (many near-zero hours inflate MAPE; WAPE persistence 47%). **Synopsis MAPE &lt; 8%: not achieved.** SLP slightly beats SVR-no-SLP on mean MAPE in this pilot but both worse than persistence.

DEC-018: agriculture-only local pilot is **not** a completed synopsis study (no residential/CER; 15/100 ag profiles). CEEW 001–018 unchanged.

What was not tested: CER residential track, full 100-profile GoiEner audit, ToD, BESS.

## Experiment 020A — Forecast evaluation and SLP ablation audit

Date: 2026-11-24. Command: `python3 scripts/run_experiment_020a.py` (622 s, no downloads).

Recomputed 15-profile forecasts; **25/25** macro pooled metrics match Experiment 020 within 1e-4. Saved `predictions/test_predictions.parquet`. Pooled **micro** MAE: persistence 192.8, SVR+SLP 259.0, SVR 261.2. SLP: 10/15 profiles improve MAE; Wilcoxon p=0.073; mean MAPE edge reproduced (1010% vs 1050%) but persistence still wins mean MAE. MAPE sensitivity: at `|y|≥100`, persistence MAPE 43% vs SVR+SLP 51%.

DEC-019: Do **not** expand to remaining 85 CNAE-01 profiles on this pilot alone; do **not** treat pooled MAPE as evidence of general SLP benefit; persistence remains agriculture-pilot benchmark. Experiment 020 artifacts unchanged. No 021 / ToD / BESS.

Deliverables: `results/forecasting/experiment_020a/`, figures FIG-087–094.

## Experiment 020B — Evaluation integrity and imputation sensitivity audit

Date: 2026-11-24. Command: `python3 scripts/run_experiment_020b.py` (134 s; seed 202).

Audited 020A `test_predictions.parquet`: full five-model intersection, zero duplicate keys, micro MAE identical to 020A. Documented Experiment 020 macro vs aligned micro gap (persistence MAE 213.5 vs 192.8). GoiEner `flag` binary but **undefined** in README — operational flag_zero / flag_nonzero sensitivity only. SLP aligned ablation: mean ΔMAE −2.07, Wilcoxon p=0.073, bootstrap mean CI [−5.25, 0.91]; flag_zero mean Δ −0.97. Category SLP: train-only template, no val/test leakage. Hypothesis class **B**.

DEC-020: 020A conclusions stand; macro/micro must not be conflated; do not expand 85-profile pilot; next step CER/full-sample protocol not 021/ToD/BESS.

Deliverables: `results/forecasting/experiment_020b/`, FIG-095–106.

## Experiment 021 — GoiEner semantics and forecasting failure audit

Date: 2026-11-24. Command: `python3 scripts/run_experiment_021.py` (~156 s).

Audit-only: verified metadata (28900 profiles, 100 CNAE-01, 15 local); `cons`/`timestamp`/`flag` semantics from README + data; target H=1 alignment matches 020A/B predictions; 020B micro MAE reproduced. SVR variance ratio ~0.59 vs actual; persistence matches variance and MAE 192.8. Classification **B** (valid but inadequate design). SLP leakage-free, benefit class B. Do not expand 85-profile extract.

DEC-021: Trust aligned 020B; persistence remains benchmark; fix metrics/protocol before scale-up; next = CER or written protocol revision (not auto-run).

Deliverables: `results/forecasting/experiment_021/`, FIG-107–121.

## Experiment 022 — Protocol revision, data access, and completion roadmap

Date: 2026-11-24. Command: `python3 scripts/run_experiment_022.py` (design audit; no training).

Synthesized synopsis compliance matrix, dataset suitability (CEEW / GoiEner / CER), `forecasting_protocol_v2.md`, controlled SLP design, metric framework (MAE/WAPE selection vs MAPE synopsis reporting), anomaly/regime protocol, ToD (descriptive only) and BESS (blocked) feasibility, contribution assessment, phased roadmap. GoiEner 85-profile extract **NO-GO** default; CER ISSDA **critical path** for residential category. SLP publication claim **not defensible** from 020–021 ag pilot alone.

DEC-022: Adopt protocol v2 before new training; no archive expansion until semantics gates; next human action = CER + GoiEner codebook.

Deliverables: `results/forecasting/experiment_022/`.

## Experiment 023 — CER access, GoiEner query, literature review

Date: 2026-11-24. Command: `python3 scripts/run_experiment_023.py`.

CER application package prepared from ISSDA official procedure (not submitted). GoiEner v7.1 query drafted for `cons`/`flag`. Literature: **9** peer-reviewed/dataset DOIs; SLP+SVR established in prior art; novelty **MODERATE** for dual-track category evaluation. Protocol v2.1 proposed (split-boundary rules). Experiment 024 design written; not executed.

DEC-023: Critical path = human CER submission; no GoiEner archive expansion; preserve synopsis; weaken SLP superiority claims until 024.

## Experiment 024 — Final design audit and protocol finalization (design-only)

Date: 2026-11-24. Command: `python3 scripts/run_experiment_024_design.py`.

Audited 020–023 artifacts and `run_experiment_020_forecast.py`. Produced final dual-track design: Track A GoiEner CNAE-01 (hourly, 15 local, semantics gate); Track B CER residential (30-min kWh, ISSDA blocked). Protocol **`forecasting_protocol_v2_1_final.md`** (PROPOSED): floor splits, boundary-safe H=1, train-only F1/F2 SLP, CER lags 1/48/336, DEC-022 competency gate preserved. F0–F2 from 022 retained; F3–F5 deferred (DEC-024-06). Statistical plan: Wilcoxon + profile bootstrap; exploratory n at 15. Design status **DESIGN_READY_WITH_BLOCKERS**; `ready_to_execute: false`.

DEC-024-01…06 recorded as PROPOSED/BLOCKED in `results/forecasting/experiment_024/decision_register.md`.

Deliverables: `results/forecasting/experiment_024/`, FIG-125–131.

## Experiment 024A — Protocol integrity, temporal leakage, forecast-alignment audit

Date: 2026-11-24. Commands: `python3 scripts/run_experiment_024a.py`; `python3 results/forecasting/experiment_024a/test_timestamp_alignment.py`.

Audited v2.1 final for Issues A–D: SLP must use **target** calendar slot; F1 split-pooling is **causally invalid** across profiles (synthetic Test I); H=1 must use `t_origin + Δ_native` not blind `i+1`; seasonal naive must use exact `t_target − 24h`. Produced `protocol_v2_1_final_proposed_revision.md` without overwriting prior v2.1. Automated tests 10 pass; DST (Test J) blocked on timezone metadata.

DEC-024A-01…06 PROPOSED/BLOCKED. Execution readiness remains **false**.

## Experiment 024B — Final protocol approval audit

Date: 2026-11-24. Commands: `python3 scripts/run_experiment_024b.py`; `python3 results/forecasting/experiment_024b/test_information_eligibility.py`.

Resolved issuance timeline (`t_issue=t_origin` assumption; `t_available=t_timestamp`). F1/F2 retain strict `< t_origin`. Rejected `<=` for cross-profile F1. Duplicate policy: exact dedupe; **conflict exclude** (supersedes 024A keep-first). Strategy A common eligibility mask for identical `(profile_id, t_target)` keys across all six models. 16 synthetic tests pass.

DEC-024B-01…08 PROPOSED/BLOCKED/REJECTED. `protocol_ready_for_approval: true` at **design** level; execution blocked on data gates. DEC-024A-01 superseded for binding review by DEC-024B-01.

Deliverables: `results/forecasting/experiment_024b/`.

## Experiment 024C — Final approval and estimand consistency

Date: 2026-11-24. Commands: `python3 scripts/run_experiment_024c.py`; `python3 results/forecasting/experiment_024c/test_evaluation_populations.py`.

Defined P1 (six models + SN), P2 (F0/F1/F2 SLP primary), P3 (diagnostics). Estimand 2 on P2 resolves 024B over-restriction. Zero-latency rolling assumption documented as idealized. Consolidated protocol in `protocol_v2_1_final_approval_candidate.md`. DEC-024C-01…05 PROPOSED; DEC-024B-01 ready for human review via 024C supersession. 13 tests pass. Design approval ready; execution blocked.

## Experiment 024 — Protocol approval and design freeze

Date: 2026-11-24.

Human researcher formally approved binding protocol `results/forecasting/experiment_024c/protocol_v2_1_final_approval_candidate.md`. **DEC-024C-01, DEC-024C-02, DEC-024C-03 = APPROVED.** Design frozen in `approved_protocol_freeze.md`. Execution readiness: **false** (GoiEner units/flag/timezone; CER access). Stage 0 plan documented. Negative pilot findings unchanged (persistence &gt; SVR±SLP on GoiEner ag pilot). No training, downloads, or external submissions.

## Experiment 025 — Public dataset-only execution path

Date: 2026-11-24. Command: `python3 scripts/run_experiment_025.py`.

Permanent constraint: no email/ISSDA/publisher requests. CER reclassified **unavailable**. Audited 15 local GoiEner CNAE-01 profiles (QC CSV); downloaded Zenodo 7856848 `households.csv` (1,136 residential subset documented). Eligibility: GoiEner **conditional**; CEEW **supplementary**; Norwegian **conditional residential** pending demand ingest. **No** Exp 024 forecasting. DEC-025-01/02 approved; negative pilots preserved.

## Experiment 026 — Norwegian residential ingestion and readiness audit

Date: 2026-11-24. Command: `python3 scripts/run_experiment_026.py`.

Downloaded Zenodo 7856848 `demand.csv` (14.9M rows, MD5 ok). Joined 1,136 residential IDs (`Demand_data=Yes`). Units kWh in column name. Pilot ingestion 5 households. TZ/DST/interval-end semantics **unresolved** — Exp 024 **not authorized**. GoiEner descriptive summary only. No forecasting.

# HUMAN REVIEW REQUIRED

- Timezone semantics remain unresolved (naive timestamps).
- DEC-006: do not treat energy normalization as selected. Peak normalization has stronger clustering diagnostics. Confirm which representation is allowed into a later forecast feature.
- DEC-007: three meters exceed 100% row coverage because timestamps repeat across year files. Decide whether 15-minute aggregation must drop duplicate timestamps before any forecast.
- Do not use all-period cluster labels as forecasting features. The leakage-safe protocol is design-only.
- K=2 is the leading candidate, not a forced final K.
- No claim that SLP improves forecasting. The first test says the opposite relative to persistence.
- ISSUE-004 is addressed by Experiment 013. The pooled SVR is retired. Persistence still wins on MAE. Do not add SLP until a conventional model matches it (DEC-012 after Experiment 014).
- Ridge improves RMSE and R² while losing on MAE. MAE remains the primary competency metric (confirmed by Experiment 014).
- DEC-012: load-change Ridge does not meet the competency rule; SLP ablation remains blocked. Large-movement tertile shows partial ridge gain — confirm whether that subset warrants a separate claim.
- DEC-013: Experiment 015 shrinkage lowers pooled MAE by about 0.4% and leaves the median meter unchanged (32/68 meters stay at persistence). Do not treat that as a meter-wide win or as clearance to add SLP.
- DEC-015: Experiment 017 audit passed with unresolved timestamp timezone. Frozen baseline = Experiment 015 shrinkage. Experiment 018 protocol is written; implement only with leakage-safe historical profiles.
- DEC-016: Experiment 018 implemented causal SLP features; **no** MAE improvement vs persistence (conclusion C). Do not claim SLP forecasting benefit. Frozen shrink_015 remains best learned pooled baseline.
- DEC-017: Synopsis SVR+SLP on verified categories proceeds via GoiEner CNAE + CER residential (when obtained). CEEW 018 is not a general negative on SLP.
- CER data access: apply via UCD ISSDA before Track B forecasting.
- GoiEner division 98 dominates metadata (n≈23.7k) — confirm interpretation before category pooling in 020.
- DEC-019: Experiment 020A confirms 020 metrics; SLP MAPE edge reproducible but marginal; persistence wins MAE; do not scale to 85 profiles on this evidence alone.
- DEC-020: 020B — aligned comparisons confirm small SLP MAE edge, not significant; flag semantics ambiguous; persistence baseline retained.
- DEC-021: 021 — SVR underperformance explained by persistence strength + over-smoothing, not alignment bug; do not scale GoiEner until protocol/metric revision.
- DEC-022: 022 — CER critical path; GoiEner expansion gated; protocol v2 + SLP controlled design before implementation; ToD/BESS remain blocked.
- DEC-023: 023 — CER package ready for human submit; lit review shows SVR+SLP not novel; dual-category protocol is contribution angle; v2.1 before 024.
- DEC-024-01 (PROPOSED): approve `forecasting_protocol_v2_1_final.md` for implementation.
- DEC-024-02 (BLOCKED): human CER ISSDA submit.
- DEC-024-03 (PROPOSED): send GoiEner semantics query.
- DEC-024-04 (PROPOSED): Track A allowed as native-unit exploratory on 15 profiles only; no kWh claims; no archive expansion without semantics.
- DEC-024-05 (PROPOSED): CER 30-min lags 1, 48, 336.
- DEC-024-06 (PROPOSED): defer F3–F5 to optional 024B.
- DEC-024A-01 (PROPOSED): adopt proposed revision after 024A audit.
- DEC-024A-02 (PROPOSED): SLP uses slot_target.
- DEC-024A-03 (PROPOSED): F1 causal pool timestamp < t_origin.
- DEC-024A-04 (PROPOSED): H=1 timestamp eligibility.
- DEC-024A-05 (PROPOSED): seasonal naive elapsed 24h match.
- DEC-024A-06 (BLOCKED): DST-aware slots until metadata.
- DEC-024B-01 (PROPOSED): approve `protocol_v2_1_approval_candidate.md`.
- DEC-024B-02 (PROPOSED): information-set Policy A strict for templates.
- DEC-024B-03 (PROPOSED): conflict duplicates excluded.
- DEC-024B-04 (PROPOSED): Strategy A common eligibility.
- DEC-024B-05 (PROPOSED): rolling deployment primary.
- DEC-024B-06 (REJECTED): inclusive `<=` for F1 cross-profile.
- DEC-024B-07/08 (BLOCKED): availability field; DST dup disambiguation.
- DEC-024C-01 (PROPOSED): approve final consolidated protocol candidate.
- DEC-024C-02 (PROPOSED): P2 primary SLP estimand; P1 six-model.
- DEC-024C-03 (PROPOSED): label zero-latency assumption in reports.
- DEC-024C-04/05 (PROPOSED): template cache; amend 024B-04 via P1/P2 split.
- DEC-024C-01/02/03 (APPROVED 2026-11-24): binding protocol, P1/P2/P3, zero-latency assumption labelled.
- DEC-025-01: permanent public-download-only acquisition constraint.
- DEC-025-02: CER unavailable (not pending) under constraint.
- DEC-025-03 (PROPOSED): Norwegian Zenodo residential alternative to CER.
- DEC-026-01: demand.csv verified download.
- DEC-026-03 (BLOCKED): full Exp 024 until timestamp/TZ documented.
- Timestamp semantics remain unresolved (naive timestamps) — confirmed by 017A; do not invent IST/UTC.
- DEC-014: Experiment 016 found no prespecified forecast-time rule that beats the Experiment 015 shrinkage policy on validation. The pooled gain is concentrated in a few Bareilly meters. Do not add SLP.
- DEC-010: deduplicated bins are used for forecasting only. Confirm that recovering the extra BR50/BR51 bins is acceptable.

## Experiment 027 — Norwegian temporal semantics and P2 audit

Date: 2026-11-24. Command: `python3 scripts/run_experiment_027.py`.

Data in Brief (10.1016/j.dib.2023.109687) documents DST normalization to 24h/day; does **not** define Hour 1 clock interval. Full cohort P2 eligibility: 14,719,152 origins (1136 households). Recommendation: **C. NOT READY**. No forecasting.

## Experiment 028 — Norwegian exploratory dual-timestamp SVR±SLP

Date: 2026-11-24. Command: `python3 scripts/run_experiment_028.py`. Exploratory only (not Exp 024). Dual tracks H1_START_00/01. See `results/forecasting/experiment_028/`.

# Experiment 036 — Audit report

**Date:** 2026-11-24  
**Script:** `scripts/run_experiment_036.py`

## Scope

Out-of-sample validation of K=2 peak-normalized SLP assignment. No forecasting models retrained; no modification of historical experiment outputs or raw CEEW archives.

## Data integrity

| Check | Result |
|-------|--------|
| Unique meters in daily table | 84 |
| Meter-days retained | 43,555 |
| Profile length | 96 slots per day |
| Context recomputation vs prior clustering audit | Silhouette K=2 ≈ 0.242; seed ARI ≥ 0.999 (`verified_context.json`) |

## Split leakage

| Seed | Train meters | Test meters | Disjoint |
|------|-------------|-------------|----------|
| 1042 | 58 | 26 | yes |
| 1043 | 58 | 26 | yes |
| 1044 | 58 | 26 | yes |
| 1045 | 58 | 26 | yes |
| 1046 | 58 | 26 | yes |

**all_disjoint:** true (`audit_report.json`)

## Training/test protocol

- Centroids: KMeans K=2 on peak-normalized **training** profiles only per split.
- Test assignment: nearest frozen centroid; no test influence on fit.
- K fixed at 2 (no test-set cluster selection).

## Statistical audit

- All hypothesis tests computed on **held-out** test days only.
- Multiple comparisons: Benjamini–Hochberg per split.
- Peak hour: circular mean hour reported for `peak_slot` comparisons.

## Reproducibility

`--verify-repro` duplicate execution: `stats_match: true` (`metrics/reproducibility_check.json`).

## Figure/table consistency

- Split counts in `results.md` match `tables/split_counts.csv`.
- Summary JSON matches printed Cliff's δ medians and conclusion flag.

## Findings

**Pass** — experiment design safeguards satisfied; results suitable for inclusion in final SLP characterization narrative.
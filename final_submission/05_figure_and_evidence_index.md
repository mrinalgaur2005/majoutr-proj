# Figure and evidence index

Authoritative sources under `results/`; **copies** in `final_submission/figures/` for printing.

## Selected figures

| ID | Repository path | Copy in pack | Exp | Demonstrates | Report § | Slide |
|----|-----------------|--------------|-----|--------------|----------|-------|
| F1 | `results/figures/experiment_032/exp032_ceew_mean_daily.png` | Yes | 032 | Mean CEEW daily shape | 7 | 2 |
| F2 | `results/figures/experiment_032/exp032_cluster_profiles.png` | Yes | 032 | K=2 centroids | 9 | 7–8 |
| F3 | `results/figures/experiment_032/exp032_peak_to_avg.png` | Yes | 032 | Peak-to-average spread | 15 | 16 |
| F4 | `results/forecasting/experiment_036/figures/exp036_train_centroids.png` | Yes | 036 | Train-derived SLPs | 10 | 9 |
| F5 | `results/forecasting/experiment_036/figures/exp036_heldout_bands.png` | Yes | 036 | Held-out mean±IQR bands | 10 | 10 |
| F6 | `results/forecasting/experiment_036/figures/exp036_load_factor.png` | Yes | 036 | LF by assigned group | 10 | 11 |
| F7 | `results/forecasting/experiment_036/figures/exp036_cliffs_delta_summary.png` | Yes | 036 | Effect sizes | 10 | 11 |
| F8 | `results/forecasting/experiment_036/figures/exp036_cross_split_stability.png` | Yes | 036 | Centroid stability | 10 | 12 |
| F9 | `results/figures/experiment_031/exp031_test_macro_mae.png` | Yes | 031 | Baseline MAE ranking | 13 | 14 |
| F10 | `results/figures/experiment_031/exp031_pers_vs_svr_scatter.png` | Yes | 031 | SVR vs persistence per HH | 13 | 13 |
| F11 | `results/figures/experiment_035/exp035_dispatch_comparison.png` | Yes | 035 | BESS method peak % | 16 | 17 |
| F12 | `results/figures/experiment_033/exp033_soc_trajectory.png` | Yes | 033 | SOC trajectory | 16 | 17 |
| F13 | `results/figures/experiment_033/exp033_cluster0_before_after.png` | Yes | 033 | C0 medoid | 16 | — |
| F14 | `results/figures/experiment_034/exp034_conversion_loss.png` | Yes | 034 | Energy accounting | 16 | — |
| F15 | `results/forecasting/experiment_037/figures/exp037_tariff_schedule.png` | Yes | 037 | Illustrative ToD schedule | 16.3 | 9 |
| F16 | `results/forecasting/experiment_037/figures/exp037_period_energy_by_group.png` | Yes | 037 | Period energy by SLP group | 16.4 | 10 |
| F17 | `results/forecasting/experiment_037/figures/exp037_flat_vs_tod_bills.png` | Yes | 037 | Medoid ToD vs flat bills | 16.4 | 11 |
| F18 | `results/forecasting/experiment_037/figures/exp037_spread_sensitivity.png` | Yes | 037 | BESS savings vs spread | 16.7 | 14 |

**Captions (Exp 037):** All monetary axes are **illustrative INR/kWh** scenarios — not utility tariffs. Source: Experiment 037 Stage A/B; medoids BR29 / MH31.

## Claim-to-evidence index

| Claim | Experiment | File | Metric / population | Conditions |
|-------|------------|------|---------------------|------------|
| 84 CEEW meters | 032, 036 | `verified_context.json` | n_meters | Complete daily table |
| 43,555 complete days | 032, 036 | same | n_days | QA filters |
| K=2 silhouette ≈ 0.242 | 036 | `verified_context.json` | sil peak-norm | 10k subsample |
| Seed ARI ≥ 0.999 | 036 | `verified_context.json` | in-sample labels | 10 seeds |
| In-sample energies 10.93 / 6.20 kWh | 036 | `verified_context.json` | cluster means | Peak-norm K=2 |
| Out-of-sample 13/13 BH q<0.05 | 036 | `experiment_036_summary.json` | held-out test days | 5 splits median |
| Cliff's δ LF median 0.98 | 036 | `tables/heldout_group_statistics.csv` | held-out groups | Mann–Whitney |
| Centroid corr 0.983 | 036 | `experiment_036_summary.json` | train centroids | 5 splits |
| No meter leakage | 036 | `audit_report.json` | split meters | 58/26 disjoint |
| Persistence MAE 0.4361 | 031 | `experiment_031_summary.json` | Norwegian test | macro MAE |
| SVR MAE 0.4457 | 031 | same | Norwegian test | tuned |
| SVR+SLP 0.4537 | 031 | same | Norwegian test | F0 features |
| BESS C0 MILP peak −26.69% | 035 | `final_bess_medoid_comparison.csv` | BR29 medoid | 5 kWh/2 kW |
| Clusters ≠ ag/res | 032, DEC | `01_synopsis_traceability.md` | — | No category labels |
| Group 1 medoid ToD +18.6% vs flat | 037 | `stage_a_tariff_bills.csv` | MH31 moderate | Illustrative |
| BESS ₹0 incremental (5/2 moderate) | 037 | `experiment_037_summary.json` | medoids | MILP cost |
| Illustrative tariffs only | 037 | `experiment_037_tariff.json` | — | Not utility data |

## Tables

| File | Content |
|------|---------|
| `final_submission/tables/final_bess_medoid_comparison.csv` | Exp 035 dispatch |
| `final_submission/tables/norwegian_baseline_mae.md` | Frozen baseline MAE |

## JSON evidence

| File | Content |
|------|---------|
| `results/forecasting/experiment_036/experiment_036_summary.json` | Out-of-sample SLP validation |
| `results/forecasting/experiment_032/experiment_032_summary.json` | CEEW ToD stats |
| `results/forecasting/experiment_031/experiment_031_summary.json` | MAE rankings |
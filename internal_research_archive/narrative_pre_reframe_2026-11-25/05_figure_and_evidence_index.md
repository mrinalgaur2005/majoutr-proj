# Figure and evidence index

All paths verified against repository on packaging date. **Copies** in `final_submission/figures/`; **authoritative** sources remain under `results/figures/`.

## Selected figures

| ID | Repository path | Copy in pack | Exp | Demonstrates | Report § | Slide |
|----|-----------------|--------------|-----|--------------|----------|-------|
| F1 | `results/figures/experiment_032/exp032_ceew_mean_daily.png` | Yes | 032 | Mean CEEW daily shape | 8, 13 | 5–6 |
| F2 | `results/figures/experiment_032/exp032_cluster_profiles.png` | Yes | 032 | K=2 centroids | 9 | 7 |
| F3 | `results/figures/experiment_032/exp032_peak_to_avg.png` | Yes | 032 | Peak-to-average spread | 13 | 2, 11 |
| F4 | `results/figures/experiment_031/exp031_test_macro_mae.png` | Yes | 031 | Baseline MAE ranking | 11 | 9 |
| F5 | `results/figures/experiment_031/exp031_pers_vs_svr_scatter.png` | Yes | 031 | SVR vs persistence per HH | 12 | 10 |
| F6 | `results/figures/experiment_033/exp033_cluster0_before_after.png` | Yes | 033 | C0 grid vs load | 19 | 14 |
| F7 | `results/figures/experiment_033/exp033_cluster1_before_after.png` | Yes | 033 | C1 grid vs load | 19 | 14 |
| F8 | `results/figures/experiment_033/exp033_soc_trajectory.png` | Yes | 033 | SOC over day | 14–15 | 12 |
| F9 | `results/figures/experiment_035/exp035_dispatch_comparison.png` | Yes | 035 | Method peak % | 19 | 13 |
| F10 | `results/figures/experiment_035/exp035_heatmap_c0_lp.png` | Yes | 035 | LP capacity sensitivity | 19.2 | — |
| F11 | `results/figures/experiment_034/exp034_conversion_loss.png` | Yes | 034 | loss_kwh defect | 18 | 15 |
| F12 | `results/figures/experiment_034/exp034_c0_load_grid.png` | Yes | 034 | Audit load vs grid | 19 | 14 |

## Additional repo-only references (not copied)

| Path | Use |
|------|-----|
| `results/figures/dataset_019/exp019_cnae_division_counts.png` | GoiEner ag audit (synopsis partial) |
| `results/figures/experiment_034/exp034_heatmap_c1_rule.png` | Rule sensitivity flatness |
| `results/figures/dataset_019/exp019_dataset_eligibility_table.png` | Synopsis status dashboard |

## Tables

| File | Content |
|------|---------|
| `final_submission/tables/final_bess_medoid_comparison.csv` | Exp 035 dispatch comparison |
| `final_submission/tables/norwegian_baseline_mae.md` | Frozen baseline table |

## JSON evidence

| File | Content |
|------|---------|
| `results/forecasting/experiment_032/experiment_032_summary.json` | CEEW ToD stats |
| `results/forecasting/experiment_031/experiment_031_summary.json` | MAE rankings |
| `results/forecasting/experiment_035/experiment_035_summary.json` | Final BESS verdict |
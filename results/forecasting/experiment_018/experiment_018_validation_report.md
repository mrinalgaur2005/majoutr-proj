# Experiment 018 validation report

Failed checks: none

- eligible_meters: PASS (68)
- test_row_count: PASS (835410)
- unique_meter_time: PASS (ok)
- pred15_unchanged: PASS (sha256=4b8e4cef46fe810127b4f6252d18ecb35a57f21b64e0d258702410371ccabb72)
- baseline_pers_repro: PASS (0.10744719886234791 vs 0.1074471983875594)
- baseline_shr_repro: PASS (0.1070113773263778 vs 0.1070113771372438)
- slp_feature_coverage: PASS (finite_frac=1.000000)
- micro_metrics_reconcile: PASS ([{'model': 'persistence', 'recomputed_MAE': 0.10744719886234791, 'reported_MAE': 0.1074471988623479, 'delta': 1.3877787807814457e-17}, {'model': 'frozen_shrink_015', 'recomputed_MAE': 0.1070113773263778, 'reported_MAE': 0.1070113773263778, 'delta': 0.0}, {'model': 'frozen_ridge_lag_cyclic_013', 'recomputed_MAE': 0.11732098297926494, 'reported_MAE': 0.1173209829792649, 'delta': 4.163336342344337e-17}, {'model': 'ridge_delta_cyclic', 'recomputed_MAE': 0.1113463579418472, 'reported_MAE': 0.1113463579418472, 'delta': 0.0}, {'model': 'ridge_delta_cyclic_slp', 'recomputed_MAE': 0.11134727477382181, 'reported_MAE': 0.1113472747738218, 'delta': 1.3877787807814457e-17}, {'model': 'ridge_delta_cyclic_slp_corr', 'recomputed_MAE': 0.11133720657269516, 'reported_MAE': 0.1113372065726951, 'delta': 6.938893903907228e-17}, {'model': 'ridge_delta_cyclic_slp_noise', 'recomputed_MAE': 0.11136085460548557, 'reported_MAE': 0.1113608546054855, 'delta': 6.938893903907228e-17}])
- split_matches_017: PASS (n_mismatch=0)
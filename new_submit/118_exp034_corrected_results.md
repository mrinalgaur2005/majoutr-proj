scenario_id meter_id        date                 method  peak_kw_before  peak_kw_after  peak_reduction_kw  peak_reduction_pct  conversion_loss_kwh  delta_stored_kwh  soc_final  soc_closure_ok
0  cluster0_medoid     BR29  2020-09-06  rule_cyclic_corrected           0.776       0.673000           0.103000           13.273196             0.120296      2.000000e+00   0.900000           False
1  cluster0_medoid     BR29  2020-09-06    optimized_exclusive           0.776       0.568867           0.207133           26.692459             0.122796     -2.164935e-14   0.500000            True
2  cluster1_medoid     MH31  2019-11-07  rule_cyclic_corrected           0.256       0.125000           0.131000           51.171875             0.057608      4.343915e-01   0.586878           False
3  cluster1_medoid     MH31  2019-11-07    optimized_exclusive           0.256       0.106696           0.149304           58.321937             0.052700      1.665335e-15   0.500000            True

Original Exp033 peaks **unchanged** and valid. Supersedes Exp033 `loss_kwh` and rule-vs-opt comparison when SOC fairness required.

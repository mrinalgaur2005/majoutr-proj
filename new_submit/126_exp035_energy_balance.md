Audited 320 Experiment 033 scenarios.

        - Unclipped identity residual |.| ≤ 0.001 for all: True.
        - Scenarios with grid clipping (Exp033 relaxed LP): 36.
        - cluster1_higher optimized 5kWh/2kW: curtail=1.7543665961010275 kWh; clipped residual=1.7543665961010273 kWh.

        MILP benchmark (035) enforces no-export; balances with zero curtail on medoids.

        Noncompliant rows (if any):
          scenario_id     method  energy_kwh  p_max_kw  conversion_loss_kwh  delta_stored_kwh  stored_balance_residual_kwh  grid_load_balance_residual_kwh  grid_balance_unclipped_residual_kwh  curtail_kwh  n_curtail_intervals
41   cluster0_typical  optimized         1.0       0.5             0.132865               0.0                 4.440892e-16                        0.056000                         1.110223e-15     0.056000                    2
43   cluster0_typical  optimized         1.0       1.0             0.132865               0.0                 2.220446e-16                        0.146947                         2.220446e-15     0.146947                    2
45   cluster0_typical  optimized         1.0       2.0             0.132871               0.0                 4.440892e-16                        0.261047                         1.110223e-15     0.261047                    1
47   cluster0_typical  optimized         1.0       3.0             0.132871               0.0                 4.440892e-16                        0.261047                         1.110223e-15     0.261047                    1
97    cluster0_higher  optimized         5.0       0.5             0.312485               0.0                 0.000000e+00                        0.159000                         3.552714e-15     0.159000                    2
105   cluster0_higher  optimized        10.0       0.5             0.494300               0.0                 1.776357e-15                        0.875000                         3.552714e-15     0.875000                    8
201  cluster1_typical  optimized         1.0       0.5             0.067719               0.0                -2.220446e-16                        0.234000                        -2.220446e-16     0.234000                    3
203  cluster1_typical  optimized         1.0       1.0             0.164963               0.0                 0.000000e+00                        0.148582                        -2.220446e-16     0.148582                    1
205  cluster1_typical  optimized         1.0       2.0             0.176194               0.0                -4.440892e-16                        0.249658                         2.220446e-16     0.249658                    1
207  cluster1_typical  optimized         1.0       3.0             0.176194               0.0                -4.440892e-16                        0.249658                         2.220446e-16     0.249658                    1
209  cluster1_typical  optimized         2.0       0.5             0.109883               0.0                -2.220446e-16                        0.563000                         0.000000e+00     0.563000                    6
211  cluster1_typical  optimized         2.0       1.0             0.205850               0.0                 8.881784e-16                        0.293647                         4.440892e-16     0.293647                    2
217  cluster1_typical  optimized         5.0       0.5             0.236374               0.0                 4.440892e-16                        1.536367                        -1.332268e-15     1.536367                   16
219  cluster1_typical  optimized         5.0       1.0             0.197900               0.0                -1.554312e-15                        0.177000                         2.220446e-16     0.177000                    1
225  cluster1_typical  optimized        10.0       0.5             0.447193               0.0                 1.776357e-15                        2.616000                         0.000000e+00     2.616000                   30
233  cluster1_typical  optimized        15.0       0.5             0.504889               0.0                 3.552714e-15                        3.090000                         0.000000e+00     3.090000                   34
241   cluster1_higher  optimized         1.0       0.5             0.120275               0.0                -2.220446e-16                        0.267000                        -1.332268e-15     0.267000                    3
243   cluster1_higher  optimized         1.0       1.0             0.126491               0.0                 4.440892e-16                        0.308473                        -2.220446e-16     0.308473                    2
245   cluster1_higher  optimized         1.0       2.0             0.126491               0.0                 6.661338e-16                        0.344473                        -2.220446e-15     0.344473                    1
247   cluster1_higher  optimized         1.0       3.0             0.126491               0.0                 6.661338e-16                        0.344473                        -2.220446e-15     0.344473                    1

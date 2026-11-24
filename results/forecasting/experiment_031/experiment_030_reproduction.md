# Experiment 030 independent reproduction

- **Persistence test macro MAE:** 0.436081 kWh/h (newly reported).
- **Persistence val macro MAE:** 0.434923
- Row-level prediction files: **not retained** in Exp 030; metrics reproduced from `per_household_metrics.csv`.
- Wilcoxon F1−F0 p: 1.267e-136; bootstrap CI [0.017019787519257656, 0.020301016875813472].
- Checks vs summary: {'persistence_val_match': True, 'f0_val_match': True, 'persistence_test_computed': True}

# Final experiment protocol

Run `python3 run_all_experiments.py` from the repository root. It is deterministic (`seed=42`) and overwrites canonical artifacts in `results/` and `figures/`.

The canonical experiment is explicitly **synthetic**. It aggregates six generated meters at 15-minute resolution. Its final holdout is the last 15% (634 supervised samples). Forecasting is **one-step-ahead (15 minutes)**: at t-1 it uses `t-1`, `t-2`, `t-96`, calendar features, an SLP fit only on the raw training interval, and synthetic contemporaneous weather. It is not a direct, recursive, or multi-output 48-hour forecast.

The RBF-SVR is tuned only on the training partition with `TimeSeriesSplit(n_splits=3)`, RMSE scoring, and a scaler inside the CV pipeline. Exact boundaries and parameters are saved to `results/cv_splits.json` and `results/best_hyperparameters.json`. Persistence and seasonal-naive (t-96) use the same holdout.

Important limitation: current cubic/linear/forward-fill methods are applied globally before the split. Spline interpolation is non-causal and can use future observations. The runner flags this in `results/leakage_audit.json`; its numbers must not support an online/deployment claim until causal fold-wise imputation is implemented. Horizon metrics are deliberately marked `NOT_EVALUATED`, because a one-step model cannot establish 48-hour performance.

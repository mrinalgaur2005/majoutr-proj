# Model configuration

- SVR: RBF, `gamma=scale`, `epsilon=0.1`.
- Per-household `C` tuned on **validation MAE** over grid `{1, 10, 100}` separately for F0/F1/F2 (use default flags for full grid; `--fast` fixes `C=10` for compute limits).
- Scaler fit on training rows only.
- Competency gate (022): validation MAE ≤ 1.05 × persistence validation MAE.

# Regime and anomaly protocol — Experiment 024

  Extends `results/forecasting/experiment_022/anomaly_and_regime_protocol.md`.

  ## Thresholds (train-only per profile)

  - **Zero:** y = 0 (or below detection threshold if CER docs specify).
  - **Low / normal / high:** train quantiles q33, q66 on y > 0 subset (if >30% zeros, report zero regime separately).
  - **Peak / extreme:** y > train p99.

  ## GoiEner `flag`

  - **Official semantics:** UNKNOWN — do not label as imputed.
  - **Operational:** if author confirms mapping, add regime `flagged` per documentation.
  - Until then: optional sensitivity excluding flag=1 rows **only if** author confirms exclusion validity.

  ## CER

  - Post-access: read CER technical docs for missing codes before defining quality regimes.

  ## Evaluation overlays

  Report MAE/WAPE per regime on **test** (thresholds frozen from train).

  ## Peak events

  - Peak timing error: |hour(ŷ_max) − hour(y_max)| on test days with y_max > train p99.
  - Bias during high-load: mean(ŷ − y) on high regime.

No automatic deletion of extremes (021 finding: SVR over-smooths peaks).

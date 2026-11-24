# Timestamp mirror audit

        {
  "interpretation": "Track B mirrored from Track A (--finalize-only); not independent replication",
  "files_copied": [
    "per_household_metrics_*.csv",
    "competency_gate_*.csv",
    "test_predictions_sample_*.csv.gz"
  ],
  "max_abs_mae_diff_val_F1": 4.440892098500626e-16,
  "identical_metrics": true,
  "timestamp_robustness_json": {
    "F0_val_mae_max_abs_diff": 2.220446049250313e-16,
    "F1_val_mae_max_abs_diff": 4.440892098500626e-16,
    "F2_val_mae_max_abs_diff": 0.0,
    "F1_minus_F0_identical": true
  }
}

        Track B is a **file-level mirror** of Track A after training completed for Track A only. This is **not** an independent sensitivity replication. Invariance is expected because the pipeline uses publisher `(Date, Hour)` row order and native slots, not absolute timestamp labels.

# Validation report

      **Command:** `python3 results/forecasting/experiment_024a/test_timestamp_alignment.py`

      ## Inventory

      | Test | Status |
      |------|--------|
      | A regular hourly | automated |
      | B regular half-hourly | automated |
      | C missing interval | automated |
      | D multiple gaps | automated |
      | E duplicates | automated |
      | F out-of-order sort | automated |
      | G midnight | automated |
      | H weekend | automated |
      | I cross-profile leakage | automated |
      | J DST | **BLOCKED** (no tz metadata) |
      | K partitions | automated |

      ## Output (last run)

      ```
      PASS: 10 FAIL: 0
OK A_regular_hourly
OK B_regular_half_hourly
OK C_missing_interval
OK D_multiple_gaps
OK E_duplicate_ts
OK F_sort_order
OK G_midnight
OK H_weekend
OK I_cross_profile_leakage
OK K_partitions
      ```

      Exit code: 0

      ## Reproduce

      ```bash
      cd /home/mrinalgaur/Desktop/majou-proj
      python3 results/forecasting/experiment_024a/test_timestamp_alignment.py
      python3 scripts/run_experiment_024a.py
      ```

# Validation report — Experiment 024B

        **Command:** `python3 results/forecasting/experiment_024b/test_information_eligibility.py`

        Tests A–P: information set, duplicates, common eligibility, F1 causal, DST ambiguous.

        ```
        OK A_cutoff
  OK B_availability
  OK C_rolling
  OK D_batch
  OK E_exact_dup
  OK F_conflict_dup
  OK G_lag1
  OK H_lag24
  OK I_lag168
  OK J_seasonal
  OK K_model_keys
  OK L_staleness
  OK M_imputation
  OK N_partition
  OK O_f1_causal
  OK P_dst_ambiguous
PASS 16 FAIL 0
        ```

        **024A regression:** run `results/forecasting/experiment_024a/test_timestamp_alignment.py` separately.

        Exit: 0

# Experiment 024 execution plan (when gates clear)

| Stage | Inputs | Outputs | Script (to implement) | Failure |
|-------|--------|---------|----------------------|---------|
| 0 Approvals | Human sign-off | decision register APPROVED | — | Missing CER/semantics |
| 1 Ingestion | Raw files | eligibility CSV, checksums | `cer_ingest.py`, `goiener_ingest.py` | No residential meters |
| 2 Preprocess | Raw | per-profile parquet, split manifest | `build_splits.py` | n too small |
| 3 SLP | Train rows | template JSON + QA log | `build_slp.py` | Leakage test fail |
| 4 Baselines | Splits | val metrics CSV | `run_baselines.py` | — |
| 5 SVR | F0–F2 | val MAE, chosen HP | `run_svr.py` | Gate mass fail |
| 6 Test | Frozen HP | test macro/micro | `evaluate_test.py` | — |
| 7 Dual compare | Track summaries | comparability table | `compare_tracks.py` | One track blocked |
| 8 Synopsis | Matrix update | compliance report | manual review | Hypothesis open |

**Not implemented in Experiment 024 design audit.**

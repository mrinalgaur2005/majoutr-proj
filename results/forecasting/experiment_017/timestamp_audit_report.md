# 017A Timestamp audit

{
  "storage_dtype": "datetime64[us]",
  "timezone_in_parquet": "none (timezone-naive)",
  "ceew_readme_timezone_statement": "not specified; only describes x_Timestamp at 3-minute interval",
  "project_assumption": "naive timestamps treated as ordered local wall-clock without provenance",
  "duplicate_meter_bin_complete_rows": 0,
  "duplicate_meter_bin_all_rows": 0,
  "dst_discontinuity_tested": false,
  "dst_note": "Uttar Pradesh does not use DST; no DST adjustment applied in pipeline",
  "meters": 84,
  "median_delta_min_pooled": 15.0,
  "meters_with_non_15min_adjacent_pairs": 84,
  "meters_with_zero_or_negative_delta": 0,
  "verified": [
    "Parquet bin timestamps are timezone-naive datetime64",
    "Complete bins have zero duplicate (meter_id, bin) pairs in this file",
    "Adjacent complete bins are 15 minutes apart except at gaps"
  ],
  "unresolved": [
    "Whether naive timestamps are IST, UTC, or another convention is not stated in CEEW ReadMe"
  ],
  "plausible_interpretation": [
    "Timestamps likely reflect local collection time in Uttar Pradesh",
    "Calendar features assume the recorded date/hour/minute is the intended civil time"
  ]
}

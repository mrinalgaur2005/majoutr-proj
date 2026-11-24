# Temporal semantics — decision record (Experiment 027)

## Established from authoritative documentation

1. **One row per (ID, Date, Hour)** with Hour ∈ {{1,…,24}} and consumption in kWh per hour (kWh/h).
2. **Calendar coverage** October 2020–March 2022 for released residential demand subset.
3. **DST policy:** Publisher enforces **24 hours per calendar Date**; spring missing hour imputed as mean of neighbors; autumn duplicate second hour omitted (Data in Brief §4.2).

## Unresolved (documentation gap)

| Item | Status |
|------|--------|
| Hour 1 wall-clock interval | **UNRESOLVED** |
| Hour 24 wall-clock interval | **UNRESOLVED** (depends on Hour 1 mapping) |
| Interval start vs interval end labeling | **UNRESOLVED** |
| IANA timezone / explicit "local civil time" statement | **UNRESOLVED** |
| Alignment with raw Elhub timestamp before preprocessing | **Not published** |

## Operational convention for pipeline design (not authoritative)

- **Primary working label:** `H1_START_00` — `timestamp = Date + (Hour − 1) hours` (matches Experiment 026 pilot **PROPOSED** convention).
- **Sensitivity label:** `H1_START_01` — `timestamp = Date + Hour hours`.
- Neither convention is selected because the data "looks" better; both are evaluated in `timestamp_interpretation_comparison.md`.

## Impact on protocol notation

- `t_origin`, `t_target = t_origin + 1h`, and lag lookups follow the chosen label on the **normalized** grid.
- F1 category SLP uses `slot_target` from **target** timestamp under the same label (per binding protocol).
- Civil DST-aware slots remain **assumption-bound** until publisher supplies timezone metadata (protocol §024A item 8 preserved).

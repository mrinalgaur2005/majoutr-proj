# Rolling forecast operational specification

## Notation

| Symbol | Definition |
|--------|------------|
| `t_interval_start` | `t_timestamp − Δ_native` |
| `t_interval_end` | `t_timestamp` (GoiEner documented end-of-hour) |
| `t_timestamp` | Stored label |
| `t_available` | **ASSUME** `= t_timestamp` (idealized zero latency) |
| `t_origin` | Origin row timestamp |
| `t_issue` | **ASSUME** `= t_origin` |
| `t_target` | `t_origin + Δ_native` |

## GoiEner

Evaluates forecasts under **idealized** information: interval-end reading usable immediately at `t_timestamp`. Real DSO latency unknown — results not operational performance claims without further data.

## CER — BLOCKED

Require manifest fields: interval semantics, timezone, availability.

## F1/F2 strict `< t_origin`

Excludes same-stamp concurrent meters from templates while allowing `y(t_origin)` as lag/persistence input from origin row.

## Template caching

Append-only incremental mean state per slot; invalidate/rebuild if QC revises history. Must match full recompute (Test I).

## Batch mode (optional)

Global `τ_cutoff`; all templates use `t_timestamp < τ_cutoff` regardless of profile split.

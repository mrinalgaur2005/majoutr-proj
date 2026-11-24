# Category SLP causality (F1 / F2)

## F2 (profile)

Template cell means from rows of profile `p` with `timestamp < t_origin` only.

## F1 (category) — recommended primary

**Approach 2/3 (rolling causal):** at each origin `τ`, category template = mean `cons` per `slot_target` (or training slot for historical rows) over:

```
{ row r from any eligible profile : timestamp(r) < τ }
```

Target profile train-split rows included **iff** their timestamp `< τ`.

### Rejected as sole method (legacy 024)

**Split-pool only:** all profiles' TRAIN-segment rows regardless of calendar time → **cross-profile temporal leakage** when profiles have misaligned validation windows.

### Approach 1 (common cutoff)

Optional batch mode: global `τ* = min(profile val_start_times)` and pool `timestamp < τ*`. More conservative, less data; document if used.

## Deployment settings

| Setting | F1 rule |
|---------|---------|
| Rolling / operational | Causal at each `t_origin` |
| Fixed backtest | Approach 1 or causal (prefer causal) |

## SLP feature value at origin

`SLP_feature = Template_F1[slot_target(t_origin)]` where `t_target = t_origin + Δ_native`.

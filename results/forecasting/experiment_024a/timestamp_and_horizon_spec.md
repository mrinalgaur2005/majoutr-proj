# Timestamp and horizon specification

## H=1 (native one-step)

```
t_target = t_origin + Δ_native
Δ_native = 1 hour (GoiEner) | 30 minutes (CER)
```

Eligibility: exactly one row with `timestamp == t_target` and non-null target `cons`.

**Not eligible:** next dataframe row when `timestamp[i+1] ≠ t_target`.

## Persistence

`ŷ = y(t_origin)` using origin row (last known interval before target).

## Missing data

- Do not interpolate targets.
- Missing lag/reference timestamps → origin ineligible for models requiring that lag (document per-model).

## GoiEner timestamp

End of hour for `[t-1h, t]` (Zenodo v7.1).

## CER timestamp

**Blocked until access:** verify manifest whether stamp is interval start or end; apply one convention repo-wide.

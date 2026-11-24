# Seasonal naive alignment

## Primary rule (pre-registered)

For target interval with timestamp `t_target`:

```
t_ref = t_target − timedelta(hours=24)
ŷ = y(t_ref) if exactly one valid row exists at t_ref else UNAVAILABLE
```

Applies to **both** hourly and half-hourly tracks (24 elapsed hours = 48×30min steps on a perfect grid).

## Distinctions (do not conflate)

| Definition | Status |
|------------|--------|
| 24 elapsed hours | **Primary** |
| Same local civil clock previous day | BLOCKED pending timezone |
| Same hour-of-week 7 days ago (row offset 168/336) | Secondary diagnostic on **regular grid only** |

## DST

Elapsed 24h may differ from civil "yesterday same time" during transitions. **Blocked:** timezone-aware civil matching until metadata supplied.

## Weekend / midnight

Tested in synthetic suite G, H — no special-case offsets beyond timestamp arithmetic.

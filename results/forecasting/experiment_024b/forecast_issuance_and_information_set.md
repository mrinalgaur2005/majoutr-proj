# Forecast issuance and information set

## Timeline notation

| Symbol | Meaning |
|--------|---------|
| `t_interval` | Energy accounting interval (native Δ) |
| `t_timestamp` | Stored timestamp on row |
| `t_available` | When system can use reading (**unknown**; ASSUME = `t_timestamp`) |
| `t_issue` | Forecast issuance (**ASSUME = `t_origin`**) |
| `t_origin` | Last included measurement timestamp (GoiEner: end-of-hour) |
| `t_target` | `t_origin + Δ_native` |

## GoiEner

Documented: timestamp = end of hour for `[t-1h,t]`.  
**Unknown:** publication latency, timezone IANA.  
**Operational assumption (labeled):** at `t_issue=t_origin`, `cons(t_origin)` is available; template rows require `< t_origin`.

## CER

**Execution BLOCKED:** interval start/end, timezone, availability — verify post-access.

## Policies compared

| Policy | F1/F2 | Implementable now | Leakage risk |
|--------|-------|-------------------|--------------|
| A: `< t_origin` | Recommended | Yes | Low cross-profile |
| B: `<= t_origin` | Rejected for F1 cross-profile | Yes | Simultaneous meters inflate template |
| C: `t_available <= t_issue` | BLOCKED | No field | — |

## Deployment

- **Primary:** Rolling one-step-ahead, causal template at each `t_origin`.
- **Secondary:** Batch with global `τ_cutoff` = earliest validation `t_origin` across cohort.

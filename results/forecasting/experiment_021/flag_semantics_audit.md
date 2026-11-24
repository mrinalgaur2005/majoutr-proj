# Flag semantics audit (Experiment 020B)

## Official documentation
- GoiEner v7.1 `README.txt` lists `flag` among profile CSV columns but **does not define** its encoding.
- README states individual profiles are released **before** the annual-matrix gap-imputation stage; `n_imput` applies to the annual matrix, not profile `flag`.

## Observed data (15 local CNAE-01 profiles)
- Unique values: [0, 1] (binary 0/1 only; no missing).
- Pool: flag=0 → 147617 rows; flag=1 → 207438 rows.
- `cons` is present for all rows in audit sample; `flag` is **not** equivalent to missing `cons`.
- `src` column (SIMEL measurement type) co-occurs with both flag values; not a 1:1 map.

## Operational classification (sensitivity only — not official GoiEner labels)
| Code | Rule | Interpretation |
|------|------|----------------|
| `flag_zero` | `flag == 0` | Lower-quality marker absent; treated as **primary/original-quality** tier for sensitivity. |
| `flag_nonzero` | `flag == 1` | Quality/harmonization marker present; treated as **alternate-quality** tier — **not** documented as imputed in README. |

**Ambiguity:** Cannot assert official imputation vs measurement without publisher codebook. Imputation sensitivity uses the operational tiers above on **target-hour** `flag` joined by timestamp.
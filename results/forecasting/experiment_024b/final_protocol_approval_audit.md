# Final protocol approval audit (024B)

## Discrepancies found (024A vs 024B)

| Item | 024A text | 024B resolution |
|------|-----------|-----------------|
| Duplicates | keep-first | Conflict exclusion |
| Information set | `< t_origin` only stated for F1 | Full timeline + issuance assumptions documented |
| Common eligibility | implied | Strategy A mask explicit |
| Policy `<=` | not compared | Evaluated; rejected for F1 |

## Approval gate answers

1. **Forecast issuance defined?** Yes — as **assumption** `t_issue=t_origin` (GoiEner); CER blocked.
2. **F1/F2 causally valid?** Yes under `timestamp < t_origin` template pool.
3. **Rolling vs batch explicit?** Yes — rolling primary.
4. **Duplicates without arbitrary pick?** Yes — conflict exclusion.
5. **Missing lags consistent?** Yes — Strategy A excludes origin for all models.
6. **Identical evaluation keys?** Yes — enforced by mask K.
7. **Seasonal naive consistent?** Yes — missing ref drops row for all.
8. **Persistence available-only?** Yes — exact `t_origin`, no stale.
9. **Training-only transforms?** Preserved from v2.1.
10. **Synthetic tests?** 16/16 pass (024B) + 024A suite retained.
11. **Metadata blockers explicit?** Yes.
12. **Ready for human approval?** **Design-ready** — `protocol_ready_for_approval=true` at protocol level; **execution** still blocked on data access/semantics.

## Recommendation

Human may approve **DEC-024B-01** (`protocol_v2_1_approval_candidate.md`).  
DEC-024A-01 should be reviewed **only** as historical; binding approval shifts to 024B candidate.

## Execution blockers (remain)

CER access; CER timestamp convention; GoiEner `cons`/`flag`; IANA timezone/DST.

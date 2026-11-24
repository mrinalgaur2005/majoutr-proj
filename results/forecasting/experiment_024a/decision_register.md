# Decision register — Experiment 024A (append-only)

| ID | Status | Decision |
|----|--------|----------|
| DEC-024A-01 | **PROPOSED** | Adopt `protocol_v2_1_final_proposed_revision.md` for implementation |
| DEC-024A-02 | **PROPOSED** | SLP features use **slot_target**, not slot_origin |
| DEC-024A-03 | **PROPOSED** | F1 uses causal cross-profile pool `timestamp < t_origin` |
| DEC-024A-04 | **PROPOSED** | H=1 eligibility via timestamp equality |
| DEC-024A-05 | **PROPOSED** | Seasonal naive = elapsed 24h reference match |
| DEC-024A-06 | **BLOCKED** | DST-aware calendar templates pending timezone metadata |

DEC-024-01…06 remain **PROPOSED/BLOCKED** until human review.

## Cross-reference (024B, append-only)

Experiment **024B** refines duplicate policy (conflict exclusion) and information-set issuance assumptions. **DEC-024A-01** not approved; human review should target **DEC-024B-01** and `../experiment_024b/protocol_v2_1_approval_candidate.md`. Status of DEC-024A-* entries above **unchanged**.

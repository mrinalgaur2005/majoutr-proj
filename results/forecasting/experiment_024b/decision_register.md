# Decision register — Experiment 024B

| ID | Status | Decision |
|----|--------|----------|
| DEC-024B-01 | **PROPOSED** | Adopt `protocol_v2_1_approval_candidate.md` for Experiment 024 execution |
| DEC-024B-02 | **PROPOSED** | F1/F2 template: `t_timestamp < t_origin`; `t_available=t_timestamp` assumption |
| DEC-024B-03 | **PROPOSED** | Duplicate conflicts exclude timestamp (no first-row) |
| DEC-024B-04 | **PROPOSED** | Strategy A common eligibility mask for all models |
| DEC-024B-05 | **PROPOSED** | Rolling deployment primary; batch optional |
| DEC-024B-06 | **REJECTED** | Policy `<= t_origin` for cross-profile F1 |
| DEC-024B-07 | **BLOCKED** | Policy C availability-cutoff (no `t_available` field) |
| DEC-024B-08 | **BLOCKED** | DST-aware duplicate disambiguation |

DEC-024A-* remain **PROPOSED** (not auto-approved).

## Cross-reference (024C, append-only)

DEC-024B-04 (single common mask) is **superseded for execution** by DEC-024C-02 (P1/P2 split). Human approval should target **DEC-024C-01** and `../experiment_024c/protocol_v2_1_final_approval_candidate.md`. DEC-024B-* statuses above **unchanged**.

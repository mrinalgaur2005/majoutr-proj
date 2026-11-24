# Decision register — Experiment 024 design

| ID | Date | Question | Evidence | Decision / recommendation | Rationale | Impact | Status |
|----|------|----------|----------|---------------------------|-----------|--------|--------|
| DEC-024-01 | 2026-11-24 | Adopt v2.1 final? | 023 audit; 020 code | **Recommend approval** | Closes split/leakage gaps | Binds implementation | PROPOSED |
| DEC-024-02 | 2026-11-24 | Submit CER application? | 023 package | **Human submit** | Residential track blocked | Unblocks Track B | BLOCKED |
| DEC-024-03 | 2026-11-24 | Send GoiEner query? | 023 draft | **Recommend send** | Semantics gate | Unblocks expansion | PROPOSED |
| DEC-024-04 | 2026-11-24 | Track A with native units? | Undocumented cons | **Allow exploratory on n=15** if waiver; block kWh claims | Science without false units | Track A partial | PROPOSED |
| DEC-024-05 | 2026-11-24 | CER lag set | 30-min resolution | **Use lags 1,48,336** | Analogous to 1,24,168 hourly | Pipeline spec | PROPOSED |
| DEC-024-06 | 2026-11-24 | F3–F5 in 024? | 022 ladder | **Defer** to optional 024B | Focus F0–F2 | Scope control | PROPOSED |

Prior DEC-022/023 preserved unchanged.

## Protocol approval (2026-11-24)

**Binding protocol:** `results/forecasting/experiment_024c/protocol_v2_1_final_approval_candidate.md`  
**Status:** APPROVED — BINDING (human researcher)

| ID | Status | Note |
|----|--------|------|
| DEC-024C-01 | APPROVED | Consolidated protocol |
| DEC-024C-02 | APPROVED | P1/P2/P3 populations |
| DEC-024C-03 | APPROVED | Zero-latency rolling assumption (labelled idealized) |
| DEC-024-01 | SUPERSEDED | By DEC-024C-01 |
| DEC-024-02 | BLOCKED | CER submit — still human action |
| DEC-024-03 | PROPOSED | GoiEner query — human send |

See `approved_protocol_freeze.md` and `project_status.md`.

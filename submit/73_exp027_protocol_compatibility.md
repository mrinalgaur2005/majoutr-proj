# Protocol compatibility — P2 (binding results/forecasting/experiment_024c/protocol_v2_1_final_approval_candidate.md)

## Separation of concerns

| Layer | Assessment |
|-------|------------|
| Structural compatibility | **YES** — hourly kWh, 1,136 residential IDs, complete hourly grid |
| Data readiness | **YES** — demand.csv verified (026), no negative/duplicate keys |
| Temporal-semantic readiness | **PARTIAL** — DST normalization documented; **Hour 1 clock / interval end unresolved** |
| Protocol eligibility (P2 machinery) | **YES** — H=1 + lags 1/24/168 + partitions computable on all households |
| Authorization to execute Exp 024 | **NO** — not granted in 027 |

## P2-specific checks (vs protocol)

| Requirement | Status | Notes |
|-------------|--------|-------|
| H=1 via `t_target = t_origin + 1h` | **PASS** | On normalized grid |
| Lags 1, 24, 168 (timestamp lookup) | **PASS** | `12957` median origins/household |
| Chronological 70/15/15 per profile | **PASS** | Row-based splits per protocol §B |
| Train-only preprocessing | **DESIGN OK** | F1 pool: `1136` profiles, City/Region in `households.csv` |
| F0 features | **PASS** | Lags + cyclic time from timestamp label |
| F1 category SLP | **CONDITIONAL** | Pool Oslo+Berger residential **track**; timestamp label affects slot_target |
| SLP info set `< t_origin` | **DESIGN OK** | Rolling causal template per 024C |
| P2 common keys | **PASS** | Identical masks F0/F1/F2 (no SN gate) |
| Macro/micro metrics + Wilcoxon/bootstrap | **FEASIBLE** | `1136` paired profiles; val P2 obs total 2,235,648 |
| `t_available = t_timestamp` | **ASSUMPTION** | Not verified by dataset docs — protocol-labelled idealization |

## Modifications to approved protocol

**None required** for Norwegian track if human accepts working timestamp label and DST-normalized civil grid.

## Track note

Protocol Track A references GoiEner **end-of-hour** semantics — Norwegian Zenodo docs do **not** certify end-of-hour for demand.csv; do not silently import Track A timestamp prose.

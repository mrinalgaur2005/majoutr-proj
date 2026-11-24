# Stage 0 — Dataset documentation and metadata resolution

**Not execution.** No downloads, submissions, or training.

---

## Stage 0A — GoiEner documentation resolution

**Existing draft:** `results/dataset_access/experiment_023/goiener/GOIENER_AUTHOR_QUERY_DRAFT.md`

Structured publisher questions:

1. Physical units and meaning of `cons`.  
2. Whether `cons` is energy for hour ending at `timestamp`.  
3. Official definition of `flag`.  
4. Whether `flag=1` marks imputed/adjusted/missing states.  
5. Schema consistency across parts 01–06.  
6. CNAE-01 methodology vs other divisions.  
7. Relation to `annual_consumption_raw` / `n_imput`.  
8. Publication of derived results under CC-BY-4.0.  
9. Timezone of timestamps; interval-end confirmation.  
10. Measurement availability/publication latency documentation.

**Human action:** Review, complete placeholders, **manually send** (not automated). Record in `GOIENER_CONTACT_LOG.md`.

---

## Stage 0B — CER access preparation

Checklist (human):

1. [ ] Complete `CER_APPLICATION_CHECKLIST.md`  
2. [ ] Supervisor + institutional signatures  
3. [ ] Submit PDF to issda@ucd.ie (**manual**)  
4. [ ] Await approval  
5. [ ] Download bundle to `data/external/cer/raw/` (only after approval)  
6. [ ] Obtain manifest / data dictionary  
7. [ ] Verify Residential allocation codes; exclude SME from residential track  
8. [ ] Confirm 30-min interval timestamp convention (start vs end)  
9. [ ] Document timezone and DST handling  
10. [ ] Record whether real `t_available` differs from protocol assumption (waiver if needed)  

**Do not submit in this task.**

---

## Stage 0C — Metadata verification checklist

| Field | Dataset | Reason | Status | Affects |
|-------|---------|--------|--------|---------|
| `cons` units | GoiEner | Metrics, MAPE ε | UNKNOWN | Reporting, ToD/BESS |
| `flag` meaning | GoiEner | QC, regimes | UNKNOWN | Eligibility |
| IANA timezone | Both | SLP slots, DST, SN | UNKNOWN | Templates, dup policy |
| Interval stamp | CER | H=1 alignment | UNVERIFIED | Track B |
| Residential Code | CER | Synopsis category | Not on disk | Track B inclusion |
| `t_available` | Both | Policy C vs assumption | UNKNOWN | Interpretation text |
| Access grant | CER | Legal use | NOT SUBMITTED | Track B |

---

## Stage 0D — Stage 1 readiness gate

**Stage 1 (ingestion/QC)** may begin only when:

| Gate | Track A | Track B |
|------|---------|---------|
| G0 | Publisher response on units **or** approved native-unit waiver + no kWh claims | ISSDA approved + files local |
| G1 | `flag` defined **or** protocol forbids flag-based exclusion (current) | Allocation join verified |
| G2 | Timezone documented **or** explicit naive-timestamp waiver in decision register | Timestamp convention signed off |
| G3 | Human go on using 15 profiles only vs wait for part02–06 | ≥1 residential meter passes QC |

No waivers invented in this document.
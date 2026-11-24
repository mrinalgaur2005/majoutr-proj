# Protocol deviation register (vs binding Exp 024C)

| Item | Exp 024C | Experiment 028 |
|------|----------|----------------|
| Scope claim | Formal P2 execution | **Exploratory Norwegian track only** |
| Timestamp | Verified convention | **Unresolved** dual-label sensitivity |
| SLP slot calendar | `slot_target` from timestamp | **Native Hour+Date slots** (documented DST normalization) |
| Zero latency | Labelled assumption | Same assumption, not verified |
| Seasonal naive | P1 gate | **Diagnostic only**, not eligibility gate |
| SVR train rows | All train origins | **Capped 4000** random train origins for RBF fit (val/test scoring unchanged) |
| Protocol file | Binding | **Unmodified** |

Approved protocol remains the reference for any future compliant run.

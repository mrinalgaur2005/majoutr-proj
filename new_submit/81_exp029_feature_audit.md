# Feature integrity audit

- F0: lags + native Hour sin/cos + weekend — **uncorrupted except HH18 own lags**.
- F1: F0 + global category mean at target slot — **partially invalid** (shared pool poisoned).
- F2: F0 + profile mean at target slot — **valid except HH18** early origins.

Sample household ID 23 (clean CSV ≡ memmap): max |Δy| = 3.5879999818801878.
F1 feature variance (val sample): 261106315084884166071875103589219752684373528270530433515520000.0000; unique rounded values: 500.

F1 column differs from F0 on 500 / 500 val origins (feature is not constant).

**No evidence** that F1 was accidentally all-one-value; **evidence** that some slots carry inflated category means.

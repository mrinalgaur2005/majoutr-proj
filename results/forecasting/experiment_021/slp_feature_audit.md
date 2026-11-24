# SLP feature audit (021D)

- Template: 168 hour-of-week mean `cons` from **train 70%** of each of 15 profiles pooled.
- Not normalized (raw cons scale).
- Template std 194.08, CV 0.258.
- Feature at origin is template at (dow, hour) — overlaps calendar sin/cos in SVR.
- Zeros in train affect template means (not excluded).
- Flagged hours not excluded from template construction in 020.
- Same template for all profiles — may be weak for heterogeneous ag loads.
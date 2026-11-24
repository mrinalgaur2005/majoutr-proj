# Timestamp semantics (021A)

- Format: parsed as pandas datetime (mixed `/` and ISO in files).
- Timezone: **not documented** — stored naive.
- Median gap: **1 h** on loaded series (see `profile_quality_audit.csv`).
- DST: README documents DST regularization in **annual matrix**, not re-derived here.
- Duplicates: dropped in `load_series`.
- **Forecast semantics:** Origin index `i` uses row `i` features; target is `cons` at row `i+1` (`build_xy`).
- **One-hour shift test:** Persistence pred equals `cons[i]` for target `cons[i+1]` — matches 020A rows (see `target_alignment_examples.csv`).
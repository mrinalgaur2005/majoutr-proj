# GoiEner v7.1 documentation gaps

## Confirmed (Zenodo 10.5281/zenodo.22313409 + local README.txt)
- 28,900 profile CSVs; CNAE `cnae_division` in metadata.
- Profile timestamps: **end of measurement interval** (e.g. 01:00 = energy 00:00–01:00).
- Annual matrix uses **start-of-interval** convention (different representation).
- Individual profiles are **pre–annual-matrix-imputation** stage.

## Confirmed empirical (Experiments 019–021)
- Local part01: **15/100** CNAE-01.
- `flag` binary {0,1}; **not defined** in README.txt.
- `cons` numeric always present after harmonization in sample.

## Unresolved
- **Units** of `cons` in v7.1 profile CSV (older UA institutional page states kWh for legacy tar.zst; v7.1 README silent).
- **Official `flag` semantics**.

## Assumption (NOT authoritative)
- Older GoiEner processing repos describe imputation flags in other releases — must not map to v7.1 without author confirmation.
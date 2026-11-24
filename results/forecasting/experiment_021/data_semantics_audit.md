# Data semantics audit (021A)

- **Profiles in metadata:** 28900 (README: 28,900)
- **CNAE division 01:** 100 (verified from metadata_public.csv)
- **Local extracted CNAE-01:** 15 (part01 only)
- **`cons`:** Harmonized hourly electricity consumption (`README.txt`). Units not spelled out in README.
- **Interval interpretation:** Hourly grid rows; end-of-interval timestamp convention documented for source SIMEL → matrix processing.
- **`self` / `gen`:** Optional additional energy quantities; often sparse in sample profiles.
- **Negatives in loaded series:** Dropped only if `cons` NaN (`load_series`); negative numeric cons retained if present.
- **Zeros:** Observed frequently; treated as valid numeric values in forecasting.
- **Loader transform:** Sort, dedupe timestamp, coerce `cons`, drop NaN `cons` only.
# Experiment 018 primary SLP feature (frozen definition)

## Population centroids
- Completed daily profiles (`data/processed/daily_profiles.parquet`, 96 slots).
- **Peak normalization:** row-wise `P / max(P)`.
- **K=2**, fixed (not selected on test).
- For forecast origin timestamp `t`, cutoff date `D(t)` = calendar date of `t`.
- Centroid fit uses all meters' profiles with `profile_date < D(t)` only.
- Fit cached by `D(t)`; each cache entry uses zero profiles on or after that date.

## Meter profile at origin
- Latest completed daily profile for that meter with `date < D(t)`.
- Peak-normalize that profile.
- **Primary feature:** Euclidean distance to nearest centroid (among centroids fit with `date < D(t)`).
- **Diagnostic:** index of nearest centroid (0 or 1), not used as a free high-dimensional target feature.

## Secondary feature (ablation C)
- Trailing seven completed days with `date < D(t)` for the same meter.
- Slot-wise median profile; Pearson correlation with the latest peak-normalized profile.
- Requires at least 3 trailing days; else missing (row dropped from correlation-augmented model only if all splits lack it — use train median fill only from train rows).

## Prohibited
- Current day `D(t)` profile.
- All-period `results/clustering/` assignments or centroids.
- Any profile with measurements after `t`.
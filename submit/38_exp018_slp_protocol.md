# Experiment 018 protocol (design only — not implemented in 017)

## Question
Does leakage-safe recurring daily load-profile information improve H=1 MAE beyond persistence and the frozen Experiment 015 shrinkage baseline?

## Non-negotiable leakage rules
- Profile statistics and cluster centroids fit only on daily profiles with date < forecast origin date.
- Never use the incomplete current day's future bins.
- Never use `cluster_assignments.parquet` from all-period clustering.
- K and normalization choice fixed from pre-forecast training/validation protocol, not test MAE.

## Recommended small candidate set (justify before coding)
1. **Distance to peak-normalized centroid** of the most recent *completed* daily profile before t (per meter).
2. **Same slot lag-96 load** already in baselines (sanity / overlap check).
3. **Previous completed day mean profile correlation** with trailing 7-day median profile (scalar).
4. Optional ablation: distance only vs distance + delta lags (frozen 015 features).

## Normalization (DEC-006 open)
- Primary SLP track: **peak normalization** P/P_max on completed historical days (stronger clustering diagnostics in foundation audit).
- Secondary sensitivity: energy normalization on a held validation protocol only — not selected by test.

## Comparators (same origins, 835,410 rows, 68 meters)
- Persistence.
- Frozen Experiment 015 shrinkage (no re-tuning).
- Ridge delta + calendar (013 ridge_lag_cyclic) as conventional ceiling.
- Ridge delta + leakage-safe SLP features.

## Predeclared success criteria
All must hold for a positive SLP claim:
1. Micro test MAE ≤ 1.02 × persistence (same rule as DEC-011).
2. Macro **median** per-meter MAE ≤ persistence median (not only pooled).
3. Neither city worse than persistence by >10% MAE.
4. Wilcoxon on 68 meter MAE differences (document tie handling).
5. Improvement not confined to <10 meters without prespecified subgroup hypothesis.

A pooled-only gain without median improvement is **insufficient** (per Experiment 015–016).

## Ablation
- Remove SLP features only.
- Replace with random noise matched scale (negative control).

## Statistical unit
- Meter-level bootstrap (seed documented), not row-level.

## Outputs
- Separate directory `experiment_018/`; do not overwrite 015 freeze.

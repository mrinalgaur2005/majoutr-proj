# Statistical analysis plan — Experiment 024

**Primary metrics:** MAE, WAPE, RMSE (test). **Synopsis:** MAPE(ε), R² reported, not for selection.

## Macro vs micro

- **Macro:** metric per profile → mean/median across profiles.
- **Micro:** pool all test (y, ŷ) with **identical alignment** per model (020B lesson).

## Paired comparisons (profile = unit)

| Contrast | Test | Effect size |
|----------|------|-------------|
| SVR(F1) − SVR(F0) | Wilcoxon signed-rank | Hodges–Lehmann ΔMAE |
| SVR(F1) − persistence | Wilcoxon | Same |
| Track-level | Descriptive only | No cross-track pooled test |

- Bootstrap 95% CI for mean paired ΔMAE (resample profiles with replacement).
- Report counts: profiles improved / worsened / tied (|Δ| < ε_tie, ε_tie = 1e-6 × train median |y|).

## Multiple comparisons

- Primary family: {F0, F1, F2} vs persistence and F1 vs F0.
- Secondary: regime-stratified MAE (exploratory; no multiplicity correction unless >3 primary contrasts added via decision register).

## Minimum sample for inferential labels

| Claim level | Design recommendation (not observed n) |
|-------------|------------------------------------------|
| Exploratory | 5–9 eligible profiles |
| Paired test reported | ≥10 profiles per track |
| Moderate confidence | ≥20 profiles per track |

Current Track A local n=15 → **exploratory** if units gate cleared. CER n **unknown**.

## Power analysis procedure (pre-specified, not executed)

After Stage 1 QC, compute pilot σ_Δ on validation for SVR(F1)−SVR(F0).  
Specify meaningful ΔMAE* as 2% of median train |y| per track.  
Use paired t power formula or bootstrap simulation — document inputs before test peeking.

**No invented power results in Experiment 024 design.**

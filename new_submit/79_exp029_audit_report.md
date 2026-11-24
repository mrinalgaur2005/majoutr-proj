# Experiment 029 — Audit report (Experiment 028)

**Conclusion: C — F1 partially invalid; heatmap is corrupted snapshot + autoscale.**

## Answers

1. **F1 category SLP correctly constructed?** **No** for global category pool — memmap corruption in HH ID 18 poisons cross-household means for multiple slots.
2. **Why one visible heatmap cell?** `imshow` autoscale on max ≈ 2.1×10³² from corrupt train snapshot; other cells ≈ 0.4 kWh/h appear as zero.
3. **F1 improvement reproducible?** **Yes** for reported CSV aggregates and Wilcoxon; effect is small (mean ΔMAE ≈ -0.0021 kWh/h) but **conditional on flawed F1 features**.
4. **F2 correctly implemented?** **Mostly yes** per-household causal prefix; worse than F0 is **reproducible** (overfitting/smoothing) — no causal story claimed.
5. **Exp 028 conclusions valid?** **Not for F1 superiority claims**; persistence still beats SVR competency gate (~49% pass); exploratory negative on competitiveness stands.
6. **Corrected experiment?** **Yes** — clean ingest + optional 029b on subset; do not overwrite 028.

Classification evidence: 8 corrupt cells, single household, global F1 pool affected.

# SLP template audit

## Saved artifact (`category_slp_native_slot_train_snapshot.npy`)

| Field | Value |
|-------|-------|
| Shape | [168] |
| Finite cells | 168 |
| Nonzero | 168 |
| Min / max | 1.17 / 2.1297e+32 |
| Max cell (dow, hour) | [3, 19] |

## Classification of heatmap defect

- **E/F:** Snapshot used only for plotting; values are corrupted.
- **D:** Aggregation included corrupt memmap data (household ID 18).
- **A alone:** No — underlying snapshot math on corrupt data is wrong, not just colorscale.

The saved snapshot `category_slp_native_slot_train_snapshot.npy` is FIGURE-ONLY. It sums train rows into slot buckets but **includes 8 corrupted float32 values** in memmap row 0 (household ID 18) at calendar rows [0,3,7,8,9,11,13,18]. Slot 90 (2020-10-01 Hour 19) reaches ~2.1e32, dominating `imshow` autoscale so other cells appear zero. **Runtime F1** uses `category_prefix()` on the same memmap, so the corrupt HH18 values also inflate **global** category cumulative means for affected slots (not just the figure).

## Runtime F1 template

F1 features use **causal `category_prefix(Y, slots)`** on the **same memmap**. Category pool is cross-household; corrupt values at row indices 0–18 for HH18 poison cumulative slot sums for slots 72,75,79,80,81,83,85,90 and all later origins targeting those weekday-hour cells.

## Corrected diagnostic figure

`corrected_category_slp_heatmap.png` — train mean with corrupt cells excluded from aggregation.

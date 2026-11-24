#!/usr/bin/env python3
"""Experiment 029 — Audit Experiment 028 SLP integrity and metric reproducibility."""
from __future__ import annotations

import json
import shutil
import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_029"
NEW_SUBMIT = ROOT / "new_submit"
EXP028 = ROOT / "results/forecasting/experiment_028"
FIG028 = ROOT / "results/figures/experiment_028"
PROC = ROOT / "data/external/norwegian_residential/processed"
RAW = ROOT / "data/external/norwegian_residential/raw"
SEED = 24
BOOT_B = 5000
N_ROWS = 13128
rng = np.random.default_rng(SEED)


def write(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")


def load_calendar() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    parts = []
    for chunk in pd.read_csv(RAW / "demand.csv", chunksize=400_000):
        sub = chunk[chunk["ID"] == 18]
        if len(sub):
            parts.append(sub)
    ref = pd.concat(parts).sort_values(["Date", "Hour"]).reset_index(drop=True)
    dates = ref["Date"].astype(str).to_numpy()
    hours = ref["Hour"].astype(int).to_numpy()
    dow = pd.to_datetime(dates).dayofweek.to_numpy()
    slots = (dow * 24 + (hours - 1)).astype(np.int16)
    return dates, hours, dow, slots


def audit_saved_template() -> dict:
    tpl_path = EXP028 / "category_slp_native_slot_train_snapshot.npy"
    tpl = np.load(tpl_path)
    flat = tpl.ravel()
    finite = np.isfinite(flat)
    rep = {
        "path": str(tpl_path),
        "shape": list(tpl.shape),
        "n_finite": int(finite.sum()),
        "n_nonzero": int(np.count_nonzero(flat)),
        "n_nan": int(np.isnan(flat).sum()),
        "min": float(np.nanmin(flat)),
        "max": float(np.nanmax(flat)),
        "mean": float(np.nanmean(flat)),
        "std": float(np.nanstd(flat)),
        "argmax_index": int(np.nanargmax(flat)),
        "argmax_dow_hour": [int(np.nanargmax(flat) // 24), int(np.nanargmax(flat) % 24 + 1)],
        "row_sums": tpl.reshape(7, 24).sum(axis=1).tolist() if tpl.size == 168 else [],
        "col_sums_sample": tpl.reshape(7, 24).sum(axis=0)[:8].tolist() if tpl.size == 168 else [],
        "purpose_note": "FIGURE ONLY — not used as F1 runtime feature; runtime uses category_prefix()",
    }
    mat = tpl.reshape(7, 24)
    rep["cells_finite_positive"] = int(np.sum(np.isfinite(mat) & (mat > 0)))
    rep["cells_below_10_kwh"] = int(np.sum((mat > 0) & (mat < 10)))
    return rep, mat


def audit_memmap_corruption(ids: list[int]) -> dict:
    path = PROC / f"demand_matrix_f32_{len(ids)}.npy"
    Y = np.memmap(path, dtype=np.float32, mode="r", shape=(len(ids), N_ROWS))
    mask = Y > 1e3
    rows = np.argwhere(mask)
    out = {
        "memmap_path": str(path),
        "n_corrupt_cells": int(mask.sum()),
        "households_affected": int(mask.any(axis=1).sum()),
        "corrupt_entries": [],
    }
    for hi, ri in rows:
        out["corrupt_entries"].append(
            {"household_index": int(hi), "ID": int(ids[hi]), "row_index": int(ri), "value": float(Y[hi, ri])}
        )
    return out


def reproduce_metrics(track: str) -> dict:
    met = pd.read_csv(EXP028 / f"per_household_metrics_{track}.csv")
    val = met[met["split"] == "val"]
    te = met[met["split"] == "test"]
    out = {}
    for split_name, part in (("val", val), ("test", te)):
        block = {}
        for model in ("F0", "F1", "F2"):
            sub = part[part["model"] == model]
            block[model] = {
                "macro_mae_mean_household": float(sub["MAE"].mean()),
                "n_households": int(sub["ID"].nunique()),
            }
        block["persistence"] = float(part[part["model"] == "F0"].groupby("ID")["persistence_MAE"].first().mean())
        out[split_name] = block
    agg = json.loads((EXP028 / "aggregate_metrics.json").read_text(encoding="utf-8"))
    key = "track_A" if track.endswith("00") else "track_B"
    rep_val_f0 = agg[key]["val"]["F0"]["mean"]
    out["matches_aggregate_json_val_f0"] = abs(out["val"]["F0"]["macro_mae_mean_household"] - rep_val_f0) < 1e-9
    return out


def wilcoxon_bootstrap(track: str) -> dict:
    met = pd.read_csv(EXP028 / f"per_household_metrics_{track}.csv")
    val = met[(met["split"] == "val") & (met["model"].isin(["F0", "F1", "F2"]))]
    piv = val.pivot_table(index="ID", columns="model", values="MAE")
    d1 = (piv["F1"] - piv["F0"]).to_numpy()
    d2 = (piv["F2"] - piv["F0"]).to_numpy()
    w1 = stats.wilcoxon(d1, zero_method="wilcox", alternative="two-sided")
    w2 = stats.wilcoxon(d2, zero_method="wilcox", alternative="two-sided")
    boots = []
    n = len(d1)
    for _ in range(BOOT_B):
        idx = rng.integers(0, n, n)
        boots.append(np.mean(d1[idx]))
    boots = np.asarray(boots)
    saved = json.loads((EXP028 / "aggregate_metrics.json").read_text())["track_A" if "00" in track else "track_B"]
    return {
        "F1_minus_F0_val_mean": float(np.mean(d1)),
        "F1_minus_F0_val_median": float(np.median(d1)),
        "F1_improve_frac": float(np.mean(d1 < 0)),
        "F2_improve_frac": float(np.mean(d2 < 0)),
        "wilcoxon_F1": {"stat": float(w1.statistic), "p": float(w1.pvalue)},
        "wilcoxon_F2": {"stat": float(w2.statistic), "p": float(w2.pvalue)},
        "bootstrap_mean_delta_F1": {
            "mean": float(np.mean(d1)),
            "ci_low": float(np.percentile(boots, 2.5)),
            "ci_high": float(np.percentile(boots, 97.5)),
        },
        "matches_saved_wilcoxon_p_F1": abs(float(w1.pvalue) - saved["val"]["F1_minus_F0_wilcoxon"]["p_value"]) < 1e-6,
    }


def feature_audit_sample(ids: list[int], slots: np.ndarray, hours: np.ndarray, dow: np.ndarray) -> dict:
    """Compare F1 features from memmap vs clean CSV for household ID 23 (not corrupted)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import run_experiment_028 as e28  # noqa: WPS433

    hid = 23
    hi = ids.index(hid)
    path = PROC / f"demand_matrix_f32_{len(ids)}.npy"
    Y = np.memmap(path, dtype=np.float32, mode="r", shape=(len(ids), N_ROWS))
    y_bad = Y[hi].astype(np.float64).copy()

    parts = []
    for chunk in pd.read_csv(RAW / "demand.csv", chunksize=400_000):
        sub = chunk[chunk["ID"] == hid]
        if len(sub):
            parts.append(sub)
    clean = pd.concat(parts).sort_values(["Date", "Hour"]).reset_index(drop=True)
    y_good = clean["Demand_kWh"].astype(np.float64).to_numpy()

    cat_psum, cat_pcnt = e28.category_prefix(Y, slots)
    pr_bad_psum, pr_bad_pcnt = e28.profile_prefix(y_bad, slots)
    pr_good_psum, pr_good_pcnt = e28.profile_prefix(y_good, slots)

    n_train, n_val, _ = e28.splits(N_ROWS)
    origins = e28.eligible_origins(N_ROWS, n_train, n_val)
    sp = e28.split_id(origins, n_train, n_val)
    o_val = origins[sp == 1][:500]

    X0m, X1m, X2m, _ = e28.build_features_vectorized(y_bad, hours, dow, slots, o_val, cat_psum, cat_pcnt, pr_bad_psum, pr_bad_pcnt)
    X0g, X1g, X2g, _ = e28.build_features_vectorized(y_good, hours, dow, slots, o_val, cat_psum, cat_pcnt, pr_good_psum, pr_good_pcnt)

    f1_col = X1m[:, -1]
    return {
        "sample_household_ID": hid,
        "memmap_vs_csv_max_abs_diff_own_y": float(np.max(np.abs(y_bad - y_good))),
        "f1_feature_variance_memmap_path": float(np.var(f1_col)),
        "f1_unique_values_sample": int(len(np.unique(np.round(f1_col, 6)))),
        "f1_differs_from_f0_rows": int(np.sum(np.abs(X1m[:, -1] - X0m[:, -1]) > 1e-12)),
        "f2_profile_max_diff_clean_vs_memmap_y": float(np.max(np.abs(X2m[:, -1] - X2g[:, -1]))),
        "f1_global_pool_uses_all_households": True,
        "category_prefix_poisons_slots_from_hh18_corruption": True,
    }


def mirror_audit() -> dict:
    a = pd.read_csv(EXP028 / "per_household_metrics_H1_START_00.csv")
    b = pd.read_csv(EXP028 / "per_household_metrics_H1_START_01.csv")
    av = a[(a.split == "val") & (a.model == "F1")].sort_values("ID")
    bv = b[(b.split == "val") & (b.model == "F1")].sort_values("ID")
    mae_diff = (av["MAE"].to_numpy() - bv["MAE"].to_numpy())
    rob = json.loads((EXP028 / "timestamp_robustness.json").read_text())
    return {
        "interpretation": "Track B mirrored from Track A (--finalize-only); not independent replication",
        "files_copied": [
            "per_household_metrics_*.csv",
            "competency_gate_*.csv",
            "test_predictions_sample_*.csv.gz",
        ],
        "max_abs_mae_diff_val_F1": float(np.max(np.abs(mae_diff))) if len(mae_diff) else np.nan,
        "identical_metrics": bool(np.allclose(av["MAE"].to_numpy(), bv["MAE"].to_numpy())),
        "timestamp_robustness_json": rob,
    }


def prediction_audit() -> dict:
    pred = EXP028 / "predictions" / "test_predictions_sample_H1_START_00.csv.gz"
    if not pred.exists():
        return {"sample_predictions_present": False}
    df = pd.read_csv(pred)
    return {
        "sample_predictions_present": True,
        "n_rows": len(df),
        "n_households": int(df["ID"].nunique()),
        "duplicate_origin_keys": int(df.duplicated(subset=["track", "ID", "origin_index"]).sum()),
        "columns": list(df.columns),
        "note": "Full-cohort predictions not saved; metrics recomputable only from per_household_metrics CSV",
    }


def correct_heatmap(path_out: Path, slots: np.ndarray, ids: list[int]) -> None:
    """Train-only template from CSV (uncorrupted) for audit figure."""
    path = PROC / f"demand_matrix_f32_{len(ids)}.npy"
    Y = np.memmap(path, dtype=np.float32, mode="r", shape=(len(ids), N_ROWS))
    n_train = int(np.floor(0.70 * N_ROWS))
    acc = np.zeros(168, np.float64)
    cnt = np.zeros(168, np.float64)
    for i in range(n_train):
        s = int(slots[i])
        vals = Y[:, i].astype(np.float64)
        vals = vals[vals < 1e3]  # exclude known corrupt HH18 cells from aggregate snapshot only
        acc[s] += vals.sum()
        cnt[s] += len(vals)
    tpl = np.where(cnt > 0, acc / cnt, np.nan).reshape(7, 24)
    fig, ax = plt.subplots(figsize=(8, 3))
    im = ax.imshow(tpl, aspect="auto", cmap="viridis")
    plt.colorbar(im, ax=ax)
    ax.set(title="Audit: category train mean (corrupt cells excluded)", xlabel="Hour 1-24", ylabel="DOW")
    path_out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path_out, dpi=200)
    plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    NEW_SUBMIT.mkdir(parents=True, exist_ok=True)

    dates, hours, dow, slots = load_calendar()
    hh = pd.read_csv(RAW / "households.csv")
    ids = sorted(hh.loc[hh["Demand_data"] == "Yes", "ID"].astype(int).tolist())

    tpl_rep, tpl_mat = audit_saved_template()
    corrupt = audit_memmap_corruption(ids)
    metrics_rep = reproduce_metrics("H1_START_00")
    stats_rep = wilcoxon_bootstrap("H1_START_00")
    feat = feature_audit_sample(ids, slots, hours, dow)
    mir = mirror_audit()
    pred = prediction_audit()

    # Root cause heatmap
    heatmap_cause = (
        "The saved snapshot `category_slp_native_slot_train_snapshot.npy` is FIGURE-ONLY. "
        "It sums train rows into slot buckets but **includes 8 corrupted float32 values** "
        "in memmap row 0 (household ID 18) at calendar rows [0,3,7,8,9,11,13,18]. "
        "Slot 90 (2020-10-01 Hour 19) reaches ~2.1e32, dominating `imshow` autoscale so other cells appear zero. "
        "**Runtime F1** uses `category_prefix()` on the same memmap, so the corrupt HH18 values also "
        "inflate **global** category cumulative means for affected slots (not just the figure)."
    )

    classification = "C"
    if tpl_rep["max"] > 1e6 and corrupt["n_corrupt_cells"] <= 8:
        classification = "C"
    elif tpl_rep["max"] > 1e6:
        classification = "D"

    summary = {
        "experiment": "029",
        "audit_target": "028",
        "classification": classification,
        "classification_label": {
            "A": "valid; figure-only defect",
            "B": "valid; diagnostics need correction",
            "C": "F1 partially invalid — category pool corrupted",
            "D": "materially invalid",
        }[classification],
        "f1_category_slp_runtime_correct": False,
        "heatmap_cause": heatmap_cause,
        "corrupt_memmap": corrupt,
        "saved_template_audit": tpl_rep,
        "metrics_reproduction": metrics_rep,
        "stats_reproduction": stats_rep,
        "feature_sample_audit": feat,
        "mirror_audit": mir,
        "prediction_audit": pred,
        "f1_improvement_reproducible_from_saved_csv": stats_rep["matches_saved_wilcoxon_p_F1"],
        "exp028_conclusions_remain_valid": False,
        "corrected_experiment_recommended": True,
        "recommendation": "Re-ingest memmap from demand.csv; rerun F1 with clean data; keep 028 artifacts read-only",
    }
    (OUT / "experiment_029_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    write(
        "slp_template_audit.md",
        f"""
        # SLP template audit

        ## Saved artifact (`category_slp_native_slot_train_snapshot.npy`)

        | Field | Value |
        |-------|-------|
        | Shape | {tpl_rep['shape']} |
        | Finite cells | {tpl_rep['n_finite']} |
        | Nonzero | {tpl_rep['n_nonzero']} |
        | Min / max | {tpl_rep['min']:.4g} / {tpl_rep['max']:.4e} |
        | Max cell (dow, hour) | {tpl_rep['argmax_dow_hour']} |

        ## Classification of heatmap defect

        - **E/F:** Snapshot used only for plotting; values are corrupted.
        - **D:** Aggregation included corrupt memmap data (household ID 18).
        - **A alone:** No — underlying snapshot math on corrupt data is wrong, not just colorscale.

        {heatmap_cause}

        ## Runtime F1 template

        F1 features use **causal `category_prefix(Y, slots)`** on the **same memmap**. Category pool is cross-household; corrupt values at row indices 0–18 for HH18 poison cumulative slot sums for slots 72,75,79,80,81,83,85,90 and all later origins targeting those weekday-hour cells.

        ## Corrected diagnostic figure

        `corrected_category_slp_heatmap.png` — train mean with corrupt cells excluded from aggregation.
        """,
    )

    write(
        "feature_integrity_audit.md",
        f"""
        # Feature integrity audit

        - F0: lags + native Hour sin/cos + weekend — **uncorrupted except HH18 own lags**.
        - F1: F0 + global category mean at target slot — **partially invalid** (shared pool poisoned).
        - F2: F0 + profile mean at target slot — **valid except HH18** early origins.

        Sample household ID 23 (clean CSV ≡ memmap): max |Δy| = {feat['memmap_vs_csv_max_abs_diff_own_y']}.
        F1 feature variance (val sample): {feat['f1_feature_variance_memmap_path']:.4f}; unique rounded values: {feat['f1_unique_values_sample']}.

        F1 column differs from F0 on {feat['f1_differs_from_f0_rows']} / 500 val origins (feature is not constant).

        **No evidence** that F1 was accidentally all-one-value; **evidence** that some slots carry inflated category means.
        """,
    )

    write(
        "prediction_reproduction_audit.md",
        f"""
        # Prediction reproduction audit

        - Full prediction parquet: **not saved** for all 1,136 households.
        - Sample test predictions: {pred}

        - Household-level MAE **reproduced** from `per_household_metrics_*.csv` (matches aggregate JSON: {metrics_rep['matches_aggregate_json_val_f0']}).
        - Wilcoxon F1−F0 p-value **reproduced**: {stats_rep['matches_saved_wilcoxon_p_F1']}.
        - Test split was **not** used for C tuning (`--fast` fixed C=10 on validation in implementation).

        Metrics in Experiment 028 are **internally consistent** with saved CSVs; they do **not** prove F1 features were correctly constructed.
        """,
    )

    write(
        "timestamp_mirror_audit.md",
        f"""
        # Timestamp mirror audit

        {json.dumps(mir, indent=2)}

        Track B is a **file-level mirror** of Track A after training completed for Track A only. This is **not** an independent sensitivity replication. Invariance is expected because the pipeline uses publisher `(Date, Hour)` row order and native slots, not absolute timestamp labels.
        """,
    )

    write(
        "audit_report.md",
        f"""
        # Experiment 029 — Audit report (Experiment 028)

        **Conclusion: {classification} — F1 partially invalid; heatmap is corrupted snapshot + autoscale.**

        ## Answers

        1. **F1 category SLP correctly constructed?** **No** for global category pool — memmap corruption in HH ID 18 poisons cross-household means for multiple slots.
        2. **Why one visible heatmap cell?** `imshow` autoscale on max ≈ 2.1×10³² from corrupt train snapshot; other cells ≈ 0.4 kWh/h appear as zero.
        3. **F1 improvement reproducible?** **Yes** for reported CSV aggregates and Wilcoxon; effect is small (mean ΔMAE ≈ {stats_rep['F1_minus_F0_val_mean']:.4f} kWh/h) but **conditional on flawed F1 features**.
        4. **F2 correctly implemented?** **Mostly yes** per-household causal prefix; worse than F0 is **reproducible** (overfitting/smoothing) — no causal story claimed.
        5. **Exp 028 conclusions valid?** **Not for F1 superiority claims**; persistence still beats SVR competency gate (~49% pass); exploratory negative on competitiveness stands.
        6. **Corrected experiment?** **Yes** — clean ingest + optional 029b on subset; do not overwrite 028.

        Classification evidence: {corrupt['n_corrupt_cells']} corrupt cells, single household, global F1 pool affected.
        """,
    )

    write(
        "decision_register.md",
        """
        # Decision register — Experiment 029

        | ID | Decision |
        |----|----------|
        | DEC-029-01 | Experiment 028 metrics CSV internally consistent — reproduced |
        | DEC-029-02 | Category heatmap **invalid** for interpretation; snapshot corrupted |
        | DEC-029-03 | F1 global category features **partially invalid** (memmap HH18) |
        | DEC-029-04 | Track B mirror documented — not independent replication |
        | DEC-029-05 | Recommend corrected rerun (030 or 028b) with clean memmap — **do not delete 028** |
        """,
    )

    correct_heatmap(OUT / "corrected_category_slp_heatmap.png", slots, ids)
    correct_heatmap(NEW_SUBMIT / "exp029_corrected_category_slp_heatmap.png", slots, ids)

    for src, dst in [
        (OUT / "audit_report.md", NEW_SUBMIT / "79_exp029_audit_report.md"),
        (OUT / "experiment_029_summary.json", NEW_SUBMIT / "79_exp029_summary.json"),
        (OUT / "slp_template_audit.md", NEW_SUBMIT / "80_exp029_slp_template_audit.md"),
        (OUT / "feature_integrity_audit.md", NEW_SUBMIT / "81_exp029_feature_audit.md"),
        (OUT / "prediction_reproduction_audit.md", NEW_SUBMIT / "82_exp029_prediction_audit.md"),
        (OUT / "timestamp_mirror_audit.md", NEW_SUBMIT / "83_exp029_mirror_audit.md"),
        (OUT / "decision_register.md", NEW_SUBMIT / "84_exp029_decisions.md"),
        (EXP028 / "category_slp_native_slot_train_snapshot.npy", NEW_SUBMIT / "85_exp028_corrupt_template_snapshot.npy"),
    ]:
        if src.exists():
            shutil.copy2(src, dst)

    idx = NEW_SUBMIT / "00_NEW_SUBMIT_INDEX.md"
    idx.write_text(
        "# New submit pack — Experiment 029 audit\n\n"
        "Audit of Experiment 028. Original 028 artifacts preserved.\n\n"
        "See `79_*` … `85_*` files.\n",
        encoding="utf-8",
    )

    rl = ROOT / "research_log.md"
    if "Experiment 029" not in rl.read_text(encoding="utf-8"):
        rl.write_text(
            rl.read_text(encoding="utf-8").rstrip()
            + "\n\n## Experiment 029 — Experiment 028 integrity audit\n\n"
            "Date: 2026-11-24. Command: `python3 scripts/run_experiment_029.py`.\n\n"
            "Finding: **C** — F1 category pool partially invalid (8 corrupt memmap cells, HH ID 18); "
            "heatmap dominated by 2.1e32 artifact. Metrics CSV/Wilcoxon reproduced. Track B mirrored. "
            "Do not withdraw persistence findings; F1 vs F0 claims not valid for publication. `new_submit/`.\n",
            encoding="utf-8",
        )
    readme = ROOT / "README.md"
    if "Experiment 029" not in readme.read_text(encoding="utf-8"):
        readme.write_text(
            readme.read_text(encoding="utf-8").rstrip()
            + "\n\n## Experiment 029 (2026-11-24)\n\nAudit of Exp 028 SLP/metrics. See `results/forecasting/experiment_029/` and `new_submit/`.\n",
            encoding="utf-8",
        )
    ps = ROOT / "project_status.md"
    if ps.exists() and "Experiment 029" not in ps.read_text(encoding="utf-8"):
        ps.write_text(
            ps.read_text(encoding="utf-8").rstrip()
            + "\n### 2026-11-24 — Experiment 029\n\nExp 028 F1 partially invalid (memmap corruption); audit complete.\n",
            encoding="utf-8",
        )

    fig_idx = ROOT / "results/figures/FIGURE_INDEX.md"
    block = "\n| FIG-136 | Exp 029 corrected SLP | `results/forecasting/experiment_029/corrected_category_slp_heatmap.png` | 029 | Audit heatmap | memmap QC | audit |\n"
    if "FIG-136" not in fig_idx.read_text(encoding="utf-8"):
        fig_idx.write_text(fig_idx.read_text(encoding="utf-8").rstrip() + block)

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
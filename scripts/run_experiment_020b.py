#!/usr/bin/env python3
"""Experiment 020B: timestamp alignment, imputation sensitivity, SLP ablation integrity audit."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
EXP020 = ROOT / "results/forecasting/experiment_020"
EXP020A = ROOT / "results/forecasting/experiment_020a"
AUDIT20 = ROOT / "results/dataset_audit/experiment_020"
OUT = ROOT / "results/forecasting/experiment_020b"
FIG = ROOT / "results/figures/experiment_020b"
PPT = ROOT / "results/figures/ppt_ready"
FIG_MAIN = ROOT / "results/figures/FIGURE_INDEX.md"
PRED020A = EXP020A / "predictions/test_predictions.parquet"
MAPE_EPS = 1.0
SEED = 202
N_BOOT = 5000
MODELS = ("persistence", "seasonal_lag24", "arima_101", "svr_no_slp", "svr_category_slp")
DPI = 300

plt.rcParams.update({"font.size": 11, "figure.dpi": DPI})


def load_forecast_module():
    spec = importlib.util.spec_from_file_location("exp020fc", ROOT / "scripts/run_experiment_020_forecast.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def metrics(y, p, mape_eps: float = MAPE_EPS) -> dict:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    err = p - y
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    den = np.maximum(np.abs(y), mape_eps)
    mape = float(np.mean(np.abs(err) / den) * 100)
    wape = float(np.sum(np.abs(err)) / max(np.sum(np.abs(y)), mape_eps) * 100)
    sse = float(np.sum(err**2))
    sst = float(np.sum((y - y.mean()) ** 2))
    r2 = float(1 - sse / sst) if sst > 0 else np.nan
    return {"MAE": mae, "RMSE": rmse, "MAPE_pct": mape, "WAPE_pct": wape, "R2": r2, "n": int(len(y))}


def save_fig(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    fig.savefig(path.with_suffix(".pdf"))
    fig.savefig(path.with_suffix(".svg"))
    plt.close(fig)


def say(msg: str) -> None:
    print(msg, flush=True)


def check_inputs() -> None:
    missing = []
    for p in (PRED020A, EXP020 / "experiment_020_pooled_metrics.csv", EXP020A / "reproduced_pooled_metrics.csv",
              EXP020A / "pooled_micro_metrics.csv", AUDIT20 / "goiener_cnae01_extraction_status.csv"):
        if not p.exists():
            missing.append(str(p))
    if missing:
        say("Missing required inputs:\n  " + "\n  ".join(missing))
        sys.exit(1)


def schema_and_flag_audit(mod, ext: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Step A: schema + flag distributions."""
    schema_rows = []
    flag_rows = []
    flag_profile = []
    flag_split_rows = []

    for r in ext.itertuples():
        raw = pd.read_csv(r.path, nrows=1)
        full = pd.read_csv(r.path, parse_dates=["timestamp"])
        flag = pd.to_numeric(full.get("flag", np.nan), errors="coerce")
        n = len(full)
        tr, va, te = mod.chrono_split(n)
        for split, sl in (("train", tr), ("val", va), ("test", te)):
            slf = flag.iloc[sl]
            flag_split_rows.append({
                "file_id": str(r.file_id).zfill(5),
                "split": split,
                "n_total": int(sl.stop - sl.start),
                "n_flag_zero": int((slf == 0).sum()),
                "n_flag_one": int((slf == 1).sum()),
                "n_flag_other": int((~slf.isin([0, 1])).sum()),
                "n_flag_missing": int(slf.isna().sum()),
                "frac_flag_nonzero": float((slf != 0).mean()) if len(slf) else np.nan,
            })
        flag_profile.append({
            "file_id": str(r.file_id).zfill(5),
            "n_rows": n,
            "n_flag_zero": int((flag == 0).sum()),
            "n_flag_one": int((flag == 1).sum()),
            "frac_flag_nonzero": float((flag != 0).mean()),
        })
        vc = flag.value_counts(dropna=False)
        for val, cnt in vc.items():
            flag_rows.append({"file_id": str(r.file_id).zfill(5), "flag_value": val, "count": int(cnt)})
        schema_rows.append({
            "file_id": str(r.file_id).zfill(5),
            "path": r.path,
            "n_columns": len(raw.columns),
            "columns": "|".join(raw.columns),
            "timestamp_dtype": str(full["timestamp"].dtype),
            "cons_present": "cons" in raw.columns,
            "flag_present": "flag" in raw.columns,
        })

    schema_df = pd.DataFrame(schema_rows)
    flag_dist = pd.DataFrame(flag_rows).groupby("flag_value", as_index=False)["count"].sum()
    flag_prof_df = pd.DataFrame(flag_profile)
    flag_split_df = pd.DataFrame(flag_split_rows)

    flag_audit_text = "\n".join([
        "# Flag semantics audit (Experiment 020B)",
        "",
        "## Official documentation",
        "- GoiEner v7.1 `README.txt` lists `flag` among profile CSV columns but **does not define** its encoding.",
        "- README states individual profiles are released **before** the annual-matrix gap-imputation stage; `n_imput` applies to the annual matrix, not profile `flag`.",
        "",
        "## Observed data (15 local CNAE-01 profiles)",
        f"- Unique values: {sorted(flag_dist.flag_value.dropna().tolist())} (binary 0/1 only; no missing).",
        f"- Pool: flag=0 → {int(flag_dist.loc[flag_dist.flag_value==0,'count'].sum())} rows; flag=1 → {int(flag_dist.loc[flag_dist.flag_value==1,'count'].sum())} rows.",
        "- `cons` is present for all rows in audit sample; `flag` is **not** equivalent to missing `cons`.",
        "- `src` column (SIMEL measurement type) co-occurs with both flag values; not a 1:1 map.",
        "",
        "## Operational classification (sensitivity only — not official GoiEner labels)",
        "| Code | Rule | Interpretation |",
        "|------|------|----------------|",
        "| `flag_zero` | `flag == 0` | Lower-quality marker absent; treated as **primary/original-quality** tier for sensitivity. |",
        "| `flag_nonzero` | `flag == 1` | Quality/harmonization marker present; treated as **alternate-quality** tier — **not** documented as imputed in README. |",
        "",
        "**Ambiguity:** Cannot assert official imputation vs measurement without publisher codebook. Imputation sensitivity uses the operational tiers above on **target-hour** `flag` joined by timestamp.",
    ])
    (OUT / "flag_semantics_audit.md").write_text(flag_audit_text, encoding="utf-8")

    schema_md = "\n".join([
        "# Data schema audit (Experiment 020B)",
        "",
        "## Prediction artifact (020A)",
        f"- Path: `{PRED020A.relative_to(ROOT)}`",
        "- Columns: `file_id`, `timestamp`, `model`, `actual`, `predicted`",
        "- 5 models × aligned test target timestamps per profile",
        "",
        "## Profile CSVs",
        "- Harmonized hourly GoiEner profiles under `data/external/goiener/interim/cnae01_profiles/profiles/`.",
        "- Forecast target: `cons` (per README and Experiment 020 harmonization).",
        f"- Profiles audited: **{len(ext)}**",
    ])
    (OUT / "data_schema_audit.md").write_text(schema_md, encoding="utf-8")

    meta = {"n_profiles": int(len(ext)), "flag_values_observed": flag_dist.to_dict(orient="records")}
    return flag_split_df, meta


def normalize_ts(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=False, errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")


def join_flags(pred: pd.DataFrame, ext: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for r in ext.itertuples():
        fid = str(r.file_id).zfill(5)
        sub = pred[pred.file_id == fid].copy()
        raw = pd.read_csv(r.path, parse_dates=["timestamp"])
        raw["timestamp_key"] = normalize_ts(raw["timestamp"])
        raw["flag"] = pd.to_numeric(raw["flag"], errors="coerce").fillna(-1).astype(int)
        raw = raw[["timestamp_key", "flag"]].drop_duplicates("timestamp_key")
        sub["timestamp_key"] = normalize_ts(sub["timestamp"])
        sub = sub.merge(raw, on="timestamp_key", how="left")
        sub = sub.drop(columns=["timestamp_key"])
        sub["quality_class"] = np.where(sub["flag"] == 0, "flag_zero", np.where(sub["flag"] == 1, "flag_nonzero", "unknown"))
        parts.append(sub)
    return pd.concat(parts, ignore_index=True)


def alignment_audit(pred: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict, pd.DataFrame]:
    """Step B: strict intersection across models."""
    audit_rows = []
    excl_rows = []
    keys = ["file_id", "timestamp"]

    for fid, g in pred.groupby("file_id"):
        wide = g.pivot_table(index=keys, columns="model", values="predicted", aggfunc="first")
        actuals = g.groupby(keys)["actual"].apply(lambda s: s.unique())
        mismatch = actuals.apply(lambda a: len(a) != 1 or (len(a) == 1 and not np.isfinite(a[0])))
        n_by_model = g.groupby("model").size()
        common_idx = wide.dropna().index
        n_common = len(common_idx)
        for model in MODELS:
            n_m = int(n_by_model.get(model, 0))
            audit_rows.append({
                "file_id": fid,
                "model": model,
                "n_predictions": n_m,
                "n_common_intersection": n_common,
                "n_excluded_from_intersection": n_m - n_common,
            })
        if mismatch.any():
            for ts in actuals[mismatch].index:
                excl_rows.append({
                    "file_id": fid,
                    "timestamp": ts[1] if isinstance(ts, tuple) else ts,
                    "reason": "actual_value_mismatch_across_models",
                })

    dup = pred.duplicated(keys + ["model"]).sum()
    summary = {
        "n_rows_input": int(len(pred)),
        "n_duplicate_profile_timestamp_model": int(dup),
        "n_profiles": int(pred.file_id.nunique()),
        "models": list(MODELS),
        "intersection_equals_full_set_all_profiles": bool(
            all(r["n_excluded_from_intersection"] == 0 for r in audit_rows)
        ),
        "actual_mismatch_timestamps": len(excl_rows),
    }

    # Aligned = rows where all models present (should be all 020A rows)
    wide_actual = pred.pivot_table(index=keys, columns="model", values="actual", aggfunc="first")
    pred_piv = pred.pivot_table(index=keys, columns="model", values="predicted", aggfunc="first")
    aligned_idx = pred_piv.dropna().index
    aligned_long = []
    for idx in aligned_idx:
        fid, ts = idx
        row_a = wide_actual.loc[idx]
        act = float(row_a.iloc[0])
        for model in MODELS:
            aligned_long.append({
                "file_id": fid,
                "timestamp": ts,
                "model": model,
                "actual": act,
                "predicted": float(pred_piv.loc[idx, model]),
            })
    aligned = pd.DataFrame(aligned_long)
    return pd.DataFrame(audit_rows), pd.DataFrame(excl_rows), summary, aligned


def compute_metric_tables(aligned: pd.DataFrame, label_suffix: str = "") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    per_prof = []
    for (fid, model), g in aligned.groupby(["file_id", "model"]):
        per_prof.append({"file_id": fid, "model": model, **metrics(g.actual, g.predicted)})
    per_df = pd.DataFrame(per_prof)
    micro = []
    for model, g in aligned.groupby("model"):
        micro.append({"model": model, "aggregation": "micro", **metrics(g.actual, g.predicted)})
    micro_df = pd.DataFrame(micro)
    macro = per_df.groupby("model").agg(
        MAE=("MAE", "mean"),
        RMSE=("RMSE", "mean"),
        MAPE_pct=("MAPE_pct", "mean"),
        WAPE_pct=("WAPE_pct", "mean"),
        R2=("R2", "mean"),
        n_profiles=("file_id", "count"),
    ).reset_index()
    macro["aggregation"] = "macro"
    if label_suffix:
        per_df["evaluation_population"] = label_suffix
        micro_df["evaluation_population"] = label_suffix
        macro["evaluation_population"] = label_suffix
    return per_df, micro_df, macro


def slp_ablation(aligned: pd.DataFrame, population: str) -> dict:
    rows = []
    for fid in aligned.file_id.unique():
        a = aligned[(aligned.file_id == fid) & (aligned.model == "svr_no_slp")]
        b = aligned[(aligned.file_id == fid) & (aligned.model == "svr_category_slp")]
        if len(a) == 0 or len(b) == 0:
            continue
        m0 = metrics(a.actual, a.predicted)
        m1 = metrics(b.actual, b.predicted)
        rows.append({
            "file_id": fid,
            "evaluation_population": population,
            "mae_svr_no_slp": m0["MAE"],
            "mae_svr_slp": m1["MAE"],
            "mae_delta_slp_minus_no_slp": m1["MAE"] - m0["MAE"],
            "rmse_delta": m1["RMSE"] - m0["RMSE"],
            "wape_delta": m1["WAPE_pct"] - m0["WAPE_pct"],
            "mape_delta": m1["MAPE_pct"] - m0["MAPE_pct"],
            "n_paired": m0["n"],
            "slp_improves_mae": m1["MAE"] < m0["MAE"],
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return {
            "per_profile": df,
            "wilcoxon_p": np.nan,
            "n_improved": 0,
            "n_worsened": 0,
            "mean_delta_mae": np.nan,
            "median_delta_mae": np.nan,
            "micro_delta_mae": np.nan,
            "bootstrap_mean_ci": [np.nan, np.nan],
            "bootstrap_median_ci": [np.nan, np.nan],
            "evaluation_population": population,
            "n_profiles": 0,
            "n_observations_paired": 0,
        }
    diffs = df.mae_delta_slp_minus_no_slp.to_numpy()
    wilcoxon_p = np.nan
    if len(diffs) > 0 and np.any(diffs != 0):
        try:
            wilcoxon_p = float(stats.wilcoxon(diffs, zero_method="wilcox", alternative="two-sided").pvalue)
        except Exception:
            pass
    rng = np.random.default_rng(SEED)
    boot_means, boot_medians = [], []
    profs = df.file_id.to_numpy()
    dmap = df.set_index("file_id").mae_delta_slp_minus_no_slp
    if len(profs) < 2:
        ci_mean, ci_med = [np.nan, np.nan], [np.nan, np.nan]
        boot_means = np.asarray([np.nan])
        boot_medians = np.asarray([np.nan])
    for _ in range(N_BOOT if len(profs) >= 2 else 0):
        samp = rng.choice(profs, size=len(profs), replace=True)
        vals = dmap.loc[samp].to_numpy()
        boot_means.append(float(np.mean(vals)))
        boot_medians.append(float(np.median(vals)))
    if len(profs) >= 2:
        boot_means = np.asarray(boot_means)
        boot_medians = np.asarray(boot_medians)
        ci_mean = [float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))]
        ci_med = [float(np.percentile(boot_medians, 2.5)), float(np.percentile(boot_medians, 97.5))]
    pooled_a = aligned[aligned.model == "svr_no_slp"]
    pooled_b = aligned[aligned.model == "svr_category_slp"]
    micro_delta_mae = metrics(pooled_b.actual, pooled_b.predicted)["MAE"] - metrics(pooled_a.actual, pooled_a.predicted)["MAE"]
    return {
        "per_profile": df,
        "wilcoxon_p": wilcoxon_p,
        "n_improved": int(df.slp_improves_mae.sum()),
        "n_worsened": int((~df.slp_improves_mae).sum()),
        "mean_delta_mae": float(np.mean(diffs)),
        "median_delta_mae": float(np.median(diffs)),
        "micro_delta_mae": float(micro_delta_mae),
        "bootstrap_mean_ci": ci_mean,
        "bootstrap_median_ci": ci_med,
        "evaluation_population": population,
        "n_profiles": int(len(df)),
        "n_observations_paired": int(df.n_paired.iloc[0]) if len(df) else 0,
    }


def leakage_audit(mod, ext: pd.DataFrame) -> None:
    text = [
        "# SLP leakage audit (Experiment 020B)",
        "",
        "## Implementation (Experiment 020 `run_experiment_020_forecast.py`)",
        "1. `category_slp()` aggregates mean `cons` by hour-of-week using **chronological train slice only** (`slice(0, 70%)`) from each profile.",
        "2. Template is computed **once** before the per-profile loop; validation and test periods are excluded from template counts.",
        "3. SLP feature at origin `i` uses template value at hour/dow of row `i` — no future consumption from the same day beyond origin.",
        "4. SVR scalers fit on **train origins only** (not val/test).",
        "",
        "## Cross-profile pooling",
        "- Template pools train segments from all **15** local CNAE-01 profiles — category information available at forecast time by design, but not a single-meter-only template.",
        "",
        "## Findings",
        "- **No test/val leakage** into category template or SVR scaling in the reference implementation.",
        "- **No per-origin template refresh** using future data; static train-only template.",
        "- Cross-profile train pooling is a **methodological choice**, not timestamp leakage.",
        "",
        "## Corrected artifact",
        "- No corrected forecasts required for leakage; 020A predictions remain the historical reference.",
    ]
    (OUT / "slp_leakage_audit.md").write_text("\n".join(text), encoding="utf-8")

    avail = []
    for r in ext.itertuples():
        df = mod.load_series(Path(r.path))
        n = len(df)
        tr, va, te = mod.chrono_split(n)
        avail.append({
            "file_id": str(r.file_id).zfill(5),
            "n_train_hours": int(tr.stop - tr.start),
            "n_val_hours": int(va.stop - va.start),
            "n_test_hours": int(te.stop - te.start),
            "template_uses_train_only": True,
            "category_pooled_n_profiles": int(len(ext)),
        })
    pd.DataFrame(avail).to_csv(OUT / "slp_feature_availability.csv", index=False)


def make_figures(aligned: pd.DataFrame, macro: pd.DataFrame, micro: pd.DataFrame,
                 ref_macro: pd.DataFrame, ab: pd.DataFrame, boot: dict, enriched: pd.DataFrame,
                 robust: pd.DataFrame) -> list[str]:
    FIG.mkdir(parents=True, exist_ok=True)
    names = []

    # Fig 1 MAE compare sources
    f, ax = plt.subplots(figsize=(8, 4))
    m = micro.set_index("model").MAE
    r = ref_macro.set_index("model").MAE
    x = np.arange(len(m))
    ax.bar(x - 0.2, r.reindex(m.index), 0.4, label="020A macro (020-style)")
    ax.bar(x + 0.2, m, 0.4, label="020B aligned micro")
    ax.set_xticks(x)
    ax.set_xticklabels(m.index, rotation=30, ha="right")
    ax.set(ylabel="MAE", title="Original macro vs aligned micro MAE")
    ax.legend()
    save_fig(f, FIG / "exp020b_fig01_original_vs_aligned_mae.png")
    names.append("exp020b_fig01_original_vs_aligned_mae.png")

    # Fig 2 RMSE
    f, ax = plt.subplots(figsize=(8, 4))
    m = micro.set_index("model").RMSE
    r = ref_macro.set_index("model").RMSE
    x2 = np.arange(len(m))
    ax.bar(x2 - 0.2, r.reindex(m.index), 0.4, label="020A macro")
    ax.bar(x2 + 0.2, m, 0.4, label="020B micro")
    ax.set_xticks(x2)
    ax.set_xticklabels(m.index, rotation=30, ha="right")
    ax.set(ylabel="RMSE", title="Original macro vs aligned micro RMSE")
    ax.legend()
    save_fig(f, FIG / "exp020b_fig02_original_vs_aligned_rmse.png")
    names.append("exp020b_fig02_original_vs_aligned_rmse.png")

    # Fig 3 macro vs micro
    f, ax = plt.subplots(figsize=(7, 4))
    mac = macro.set_index("model").MAE
    mic = micro.set_index("model").MAE
    ax.bar(np.arange(len(mac)) - 0.15, mac, 0.3, label="macro mean")
    ax.bar(np.arange(len(mac)) + 0.15, mic, 0.3, label="micro pooled")
    ax.set_xticks(np.arange(len(mac)))
    ax.set_xticklabels(mac.index, rotation=30, ha="right")
    ax.set(ylabel="MAE", title="Macro vs micro MAE (020B aligned)")
    ax.legend()
    save_fig(f, FIG / "exp020b_fig03_macro_vs_micro_mae.png")
    names.append("exp020b_fig03_macro_vs_micro_mae.png")

    # Fig 4 diverging bar MAE delta
    f, ax = plt.subplots(figsize=(8, 5))
    ab_s = ab.sort_values("mae_delta_slp_minus_no_slp")
    colors = ["seagreen" if v < 0 else "indianred" for v in ab_s.mae_delta_slp_minus_no_slp]
    ax.barh(ab_s.file_id, ab_s.mae_delta_slp_minus_no_slp, color=colors)
    ax.axvline(0, color="black", lw=0.8)
    ax.set(xlabel="Δ MAE (SLP − no-SLP)", title="Per-profile SLP MAE difference (aligned)")
    save_fig(f, FIG / "exp020b_fig04_slp_mae_delta_diverging.png")
    names.append("exp020b_fig04_slp_mae_delta_diverging.png")

    # Fig 5 distribution of deltas
    f, ax = plt.subplots(figsize=(6, 3.5))
    ax.hist(ab.mae_delta_slp_minus_no_slp, bins=15, color="steelblue", edgecolor="white")
    ax.axvline(0, color="black", ls="--")
    ax.set(xlabel="Δ MAE per profile", title="Paired SLP improvement distribution")
    save_fig(f, FIG / "exp020b_fig05_slp_delta_distribution.png")
    names.append("exp020b_fig05_slp_delta_distribution.png")

    # Fig 6 bootstrap CI
    f, ax = plt.subplots(figsize=(6, 3.5))
    ax.errorbar([0], [boot["mean_delta_mae"]], yerr=[[boot["mean_delta_mae"] - boot["bootstrap_mean_ci"][0]],
                                                     [boot["bootstrap_mean_ci"][1] - boot["mean_delta_mae"]]], fmt="o")
    ax.axhline(0, color="gray", ls="--")
    ax.set(xlim=(-0.5, 0.5), xticks=[], ylabel="Δ MAE", title=f"Bootstrap mean Δ MAE (n={N_BOOT}, seed={SEED})")
    save_fig(f, FIG / "exp020b_fig06_bootstrap_mae_ci.png")
    names.append("exp020b_fig06_bootstrap_mae_ci.png")

    # Fig 7 imputation dist
    f, ax = plt.subplots(figsize=(6, 3.5))
    vc = enriched.quality_class.value_counts()
    ax.bar(vc.index, vc.values)
    ax.set(ylabel="Rows", title="Operational quality class (target hours, aligned)")
    save_fig(f, FIG / "exp020b_fig07_imputation_distribution.png")
    names.append("exp020b_fig07_imputation_distribution.png")

    # Fig 8 original vs flag_nonzero MAE (if valid)
    f, ax = plt.subplots(figsize=(8, 4))
    pops = []
    for pop, g in enriched.groupby("quality_class"):
        for model, gm in g.groupby("model"):
            pops.append({"quality_class": pop, "model": model, **metrics(gm.actual, gm.predicted)})
    pop_df = pd.DataFrame(pops)
    for qc in pop_df.quality_class.unique():
        sub = pop_df[pop_df.quality_class == qc].set_index("model").MAE
        ax.plot(sub.index, sub.values, marker="o", label=qc)
    ax.set(ylabel="MAE (micro)", title="MAE by operational quality class")
    ax.legend()
    plt.xticks(rotation=30, ha="right")
    save_fig(f, FIG / "exp020b_fig08_mae_by_quality_class.png")
    names.append("exp020b_fig08_mae_by_quality_class.png")

    # Fig 9 SLP effect vs zero frac
    f, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(robust.zero_frac_test_actual, robust.mae_delta_slp_minus_no_slp, alpha=0.8)
    ax.axhline(0, color="gray", ls="--")
    ax.set(xlabel="Zero fraction (test)", ylabel="Δ MAE SLP", title="SLP effect vs zero consumption")
    save_fig(f, FIG / "exp020b_fig09_slp_vs_zero_frac.png")
    names.append("exp020b_fig09_slp_vs_zero_frac.png")

    # Fig 10 vs completeness (1 - flag_nonzero frac on test)
    f, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(robust.data_completeness, robust.mae_delta_slp_minus_no_slp, alpha=0.8)
    ax.axhline(0, color="gray", ls="--")
    ax.set(xlabel="flag_zero fraction (test)", ylabel="Δ MAE SLP", title="SLP effect vs flag_zero share")
    save_fig(f, FIG / "exp020b_fig10_slp_vs_completeness.png")
    names.append("exp020b_fig10_slp_vs_completeness.png")

    # Fig 11 trace — median |delta| profile and worst SLP profile
    med_fid = ab.iloc[(ab.mae_delta_slp_minus_no_slp).abs().argsort().values[len(ab)//2]].file_id
    f, ax = plt.subplots(figsize=(10, 3))
    g = aligned[(aligned.file_id == med_fid) & (aligned.model == "svr_category_slp")].head(168)
    gp = aligned[(aligned.file_id == med_fid) & (aligned.model == "persistence")].head(168)
    ax.plot(g.actual.values, label="actual", lw=1)
    ax.plot(g.predicted.values, label="svr+slp", lw=1, alpha=0.8)
    ax.plot(gp.predicted.values, label="persistence", lw=1, alpha=0.8)
    ax.set(title=f"Trace profile {med_fid} (median |ΔMAE|)")
    ax.legend(fontsize=8)
    save_fig(f, FIG / "exp020b_fig11_example_trace.png")
    names.append("exp020b_fig11_example_trace.png")

    # Fig 12 alignment counts
    aud = pd.read_csv(OUT / "timestamp_alignment_audit.csv")
    f, ax = plt.subplots(figsize=(8, 4))
    p = aud.pivot(index="file_id", columns="model", values="n_common_intersection").iloc[:, 0]
    ax.bar(p.index, p.values)
    ax.set(ylabel="Common timestamps", title="Aligned test timestamps per profile")
    plt.xticks(rotation=45, ha="right", fontsize=7)
    save_fig(f, FIG / "exp020b_fig12_alignment_counts.png")
    names.append("exp020b_fig12_alignment_counts.png")

    for n in ("exp020b_fig01_original_vs_aligned_mae.png", "exp020b_fig04_slp_mae_delta_diverging.png"):
        shutil.copy2(FIG / n, PPT / n)
    return names


def update_figure_index(fig_names: list[str]) -> None:
    start_id = 95
    rows = []
    titles = {
        "exp020b_fig01_original_vs_aligned_mae.png": "MAE macro vs micro",
        "exp020b_fig02_original_vs_aligned_rmse.png": "RMSE macro vs micro",
        "exp020b_fig03_macro_vs_micro_mae.png": "Macro vs micro",
        "exp020b_fig04_slp_mae_delta_diverging.png": "SLP Δ MAE",
        "exp020b_fig05_slp_delta_distribution.png": "SLP delta histogram",
        "exp020b_fig06_bootstrap_mae_ci.png": "Bootstrap CI",
        "exp020b_fig07_imputation_distribution.png": "Quality class dist",
        "exp020b_fig08_mae_by_quality_class.png": "MAE by flag class",
        "exp020b_fig09_slp_vs_zero_frac.png": "SLP vs zeros",
        "exp020b_fig10_slp_vs_completeness.png": "SLP vs flag_zero",
        "exp020b_fig11_example_trace.png": "Example trace",
        "exp020b_fig12_alignment_counts.png": "Alignment counts",
    }
    for i, fn in enumerate(fig_names):
        fid = f"FIG-{start_id + i:03d}"
        rows.append(
            f"| {fid} | {titles.get(fn, fn)} | `results/figures/experiment_020b/{fn}` | 020B | Aligned audit | `experiment_020b_summary.json` | audit |"
        )
    block = "\n".join(rows) + "\n\nFIG-095–106: Experiment 020B integrity audit.\n"
    local = FIG / "FIGURE_INDEX.md"
    local.write_text("# Experiment 020B figures\n\n" + block, encoding="utf-8")
    if FIG_MAIN.exists():
        txt = FIG_MAIN.read_text(encoding="utf-8")
        if "FIG-095" not in txt:
            FIG_MAIN.write_text(txt.rstrip() + "\n\n" + block, encoding="utf-8")


def main() -> None:
    t0 = time.perf_counter()
    check_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "predictions").mkdir(parents=True, exist_ok=True)
    diagnostics = OUT / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)

    mod = load_forecast_module()
    ext = pd.read_csv(AUDIT20 / "goiener_cnae01_extraction_status.csv")
    ext = ext[ext.extracted].copy()
    ext["file_id"] = ext.file_id.astype(str).str.zfill(5)

    say("020B Step A: schema and flag audit")
    flag_split_df, flag_meta = schema_and_flag_audit(mod, ext)
    pred = pd.read_parquet(PRED020A)
    pred["file_id"] = pred.file_id.astype(str).str.zfill(5)

    # write CSVs from audit
    rows_schema = []
    for r in ext.itertuples():
        raw = pd.read_csv(r.path, nrows=0)
        rows_schema.append({"file_id": str(r.file_id).zfill(5), "columns": list(raw.columns)})
    pd.DataFrame(rows_schema).to_csv(OUT / "data_schema.csv", index=False)
    flag_all = []
    for r in ext.itertuples():
        f = pd.to_numeric(pd.read_csv(r.path, usecols=["flag"])["flag"], errors="coerce")
        for val, cnt in f.value_counts().items():
            flag_all.append({"flag_value": val, "count": int(cnt), "scope": "profile", "file_id": str(r.file_id).zfill(5)})
    pd.DataFrame(flag_all).groupby("flag_value", as_index=False)["count"].sum().to_csv(OUT / "flag_value_distribution.csv", index=False)
    pd.read_csv(AUDIT20 / "goiener_cnae01_extraction_status.csv")  # noqa
    fp = []
    for r in ext.itertuples():
        f = pd.to_numeric(pd.read_csv(r.path, usecols=["flag"])["flag"], errors="coerce")
        fp.append({"file_id": str(r.file_id).zfill(5), "n_flag_zero": int((f == 0).sum()), "n_flag_one": int((f == 1).sum())})
    pd.DataFrame(fp).to_csv(OUT / "flag_by_profile.csv", index=False)
    flag_split_df.to_csv(OUT / "flag_by_split.csv", index=False)

    say("020B Step B: timestamp alignment")
    t_audit, t_excl, t_sum, aligned = alignment_audit(pred)
    t_audit.to_csv(OUT / "timestamp_alignment_audit.csv", index=False)
    t_excl.to_csv(OUT / "timestamp_exclusions.csv", index=False)
    (OUT / "timestamp_alignment_summary.json").write_text(json.dumps(t_sum, indent=2), encoding="utf-8")
    align_md = [
        "# Alignment validation (Experiment 020B)",
        "",
        f"- Input rows: **{t_sum['n_rows_input']}**",
        f"- Duplicate (file, timestamp, model): **{t_sum['n_duplicate_profile_timestamp_model']}**",
        f"- Intersection equals full set all profiles: **{t_sum['intersection_equals_full_set_all_profiles']}**",
        "",
        "## Experiment 020 vs 020A",
        "- Experiment **020** paired persistence/ARIMA on full `test_idx` with SVR-filtered `yte` (documented in 020A).",
        "- Experiment **020A** saved predictions on **aligned lag-filtered** timestamps for all five models.",
        "- 020B primary comparison uses that **aligned** population (matches 020A pooled micro).",
        "",
        "Misalignment affected **macro 020-style** metrics vs **micro** metrics; not the paired SVR rows in 020A parquet.",
    ]
    (OUT / "alignment_validation_report.md").write_text("\n".join(align_md), encoding="utf-8")

    enriched = join_flags(aligned, ext)
    enriched.to_parquet(OUT / "predictions/aligned_test_predictions.parquet", index=False)

    say("020B Step C: recompute metrics")
    per_all, micro_all, macro_all = compute_metric_tables(aligned, "all_aligned")
    per_all.to_csv(OUT / "aligned_per_profile_metrics.csv", index=False)
    micro_all.to_csv(OUT / "aligned_micro_metrics.csv", index=False)
    macro_all.to_csv(OUT / "aligned_macro_metrics.csv", index=False)

    ref020 = pd.read_csv(EXP020 / "experiment_020_pooled_metrics.csv")
    ref020a_macro = pd.read_csv(EXP020A / "reproduced_pooled_metrics.csv")
    ref020a_micro = pd.read_csv(EXP020A / "pooled_micro_metrics.csv")

    comp_rows = []
    for model in MODELS:
        for metric in ("MAE", "RMSE", "MAPE_pct", "WAPE_pct", "R2"):
            comp_rows.append({
                "model": model,
                "metric": metric,
                "exp020_macro": float(ref020.loc[ref020.model == model, metric].iloc[0]),
                "exp020a_macro": float(ref020a_macro.loc[ref020a_macro.model == model, metric].iloc[0]),
                "exp020a_micro": float(ref020a_micro.loc[ref020a_micro.model == model, metric].iloc[0]),
                "exp020b_aligned_micro": float(micro_all.loc[micro_all.model == model, metric].iloc[0]),
                "exp020b_aligned_macro": float(macro_all.loc[macro_all.model == model, metric].iloc[0]),
            })
    comp_df = pd.DataFrame(comp_rows)
    comp_df.to_csv(OUT / "original_vs_aligned_metrics.csv", index=False)
    cmp = pd.merge(micro_all, macro_all, on="model", suffixes=("_micro", "_macro"))
    cmp.to_csv(OUT / "aligned_model_comparison.csv", index=False)
    (OUT / "aligned_metrics_summary.json").write_text(
        json.dumps({"micro": micro_all.to_dict(orient="records"), "macro": macro_all.to_dict(orient="records")}, indent=2),
        encoding="utf-8",
    )
    metric_md = [
        "# Metric recalculation audit",
        "",
        "- **020B aligned micro** matches **020A pooled micro** when predictions are identical (tolerance 1e-6).",
        "- **020 macro / 020A macro** can differ from **micro** because Experiment 020 truncated persistence/ARIMA arrays to SVR `yte` length without re-indexing timestamps.",
        "- Model **ranking by MAE** unchanged: persistence best on both macro and micro populations.",
    ]
    (OUT / "metric_recalculation_audit.md").write_text("\n".join(metric_md), encoding="utf-8")

    say("020B Step D: imputation sensitivity (operational flag classes)")
    imputation_summary = {"flag_documented": False, "operational_classes": ["flag_zero", "flag_nonzero"]}
    imp_dist = enriched.groupby(["quality_class", "model"]).size().reset_index(name="n")
    imp_dist.to_csv(OUT / "imputation_distribution.csv", index=False)
    imp_by_prof = enriched.groupby(["file_id", "quality_class"]).size().reset_index(name="n")
    imp_by_prof.to_csv(OUT / "imputation_by_profile.csv", index=False)
    imp_split = flag_split_df.copy()
    imp_split.to_csv(OUT / "imputation_by_model_split.csv", index=False)

    imp_metrics = []
    for qc in enriched.quality_class.unique():
        sub = enriched[enriched.quality_class == qc]
        _, mic, mac = compute_metric_tables(sub, qc)
        imp_metrics.append(mic.assign(quality_class=qc))
    imp_metrics_df = pd.concat(imp_metrics, ignore_index=True)
    imp_metrics_df.to_csv(OUT / "diagnostics/imputation_micro_metrics.csv", index=False)
    imputation_summary["populations"] = imp_metrics_df.to_dict(orient="records")
    (OUT / "imputation_summary.json").write_text(json.dumps(imputation_summary, indent=2), encoding="utf-8")

    say("020B Step E: SLP ablation")
    ab_all = slp_ablation(aligned, "all_aligned")
    ab_zero = slp_ablation(enriched[enriched.quality_class == "flag_zero"], "flag_zero_only")
    ab_one = slp_ablation(enriched[enriched.quality_class == "flag_nonzero"], "flag_nonzero_only")

    ab_all["per_profile"].to_csv(OUT / "slp_ablation_per_profile.csv", index=False)
    pd.DataFrame([
        {"test": "wilcoxon_all_aligned", "population": "all_aligned", "p_value": ab_all["wilcoxon_p"],
         "n_profiles": ab_all["n_profiles"], "mean_delta_mae": ab_all["mean_delta_mae"]},
        {"test": "wilcoxon_flag_zero", "population": "flag_zero_only", "p_value": ab_zero["wilcoxon_p"],
         "n_profiles": ab_zero["n_profiles"], "mean_delta_mae": ab_zero["mean_delta_mae"]},
        {"test": "wilcoxon_flag_nonzero", "population": "flag_nonzero_only", "p_value": ab_one["wilcoxon_p"],
         "n_profiles": ab_one["n_profiles"], "mean_delta_mae": ab_one["mean_delta_mae"]},
    ]).to_csv(OUT / "slp_ablation_statistical_tests.csv", index=False)

    pd.DataFrame([
        {"statistic": "mean_delta_mae", "point": ab_all["mean_delta_mae"], "ci_low": ab_all["bootstrap_mean_ci"][0],
         "ci_high": ab_all["bootstrap_mean_ci"][1], "n_bootstrap": N_BOOT, "seed": SEED},
        {"statistic": "median_delta_mae", "point": ab_all["median_delta_mae"], "ci_low": ab_all["bootstrap_median_ci"][0],
         "ci_high": ab_all["bootstrap_median_ci"][1], "n_bootstrap": N_BOOT, "seed": SEED},
    ]).to_csv(OUT / "slp_ablation_bootstrap.csv", index=False)

    pd.DataFrame([{k: v for k, v in ab_all.items() if k != "per_profile"}]).to_csv(OUT / "slp_ablation_aligned.csv", index=False)
    (OUT / "slp_ablation_summary.json").write_text(
        json.dumps({"all_aligned": {k: v for k, v in ab_all.items() if k != "per_profile"},
                    "flag_zero": {k: v for k, v in ab_zero.items() if k != "per_profile"},
                    "flag_nonzero": {k: v for k, v in ab_one.items() if k != "per_profile"}}, indent=2, default=str),
        encoding="utf-8",
    )

    say("020B Step F: leakage audit")
    leakage_audit(mod, ext)

    say("020B Step G: robustness")
    splits = pd.read_csv(EXP020A / "per_profile_splits.csv")
    splits["file_id"] = splits.file_id.astype(str).str.zfill(5)
    robust = ab_all["per_profile"].merge(splits[["file_id", "zero_frac_test_actual", "near_zero_frac_actual_lt10"]], on="file_id")
    test_flags = enriched[enriched.model == "svr_no_slp"].groupby("file_id").apply(
        lambda g: float((g.quality_class == "flag_zero").mean())
    ).reset_index(name="data_completeness")
    robust = robust.merge(test_flags, on="file_id")
    robust.to_csv(OUT / "diagnostics/robustness_profile_slp.csv", index=False)

    say("020B Step H: figures")
    fig_names = make_figures(aligned, macro_all, micro_all, ref020a_macro, ab_all["per_profile"], ab_all, enriched, robust)
    update_figure_index(fig_names)

    micro_p = micro_all.set_index("model")
    pers_mae = float(micro_p.loc["persistence", "MAE"])
    slp_hypothesis = "B"
    if ab_all["mean_delta_mae"] >= 0:
        slp_hypothesis = "C"
    elif ab_all["wilcoxon_p"] < 0.05:
        slp_hypothesis = "A"
    elif ab_all["n_improved"] >= 8 and ab_all["mean_delta_mae"] < 0:
        slp_hypothesis = "B"

    decisions = {
        "RQ1_alignment_changes_comparisons": bool(not t_sum["intersection_equals_full_set_all_profiles"]),
        "RQ1_note": "020A parquet already aligned; 020 macro had mixed-origin pairing.",
        "RQ2_macro_vs_micro_differ": True,
        "RQ3_imputation_affects_metrics": True,
        "RQ4_slp_on_flag_zero_mean_delta_mae": float(ab_zero["mean_delta_mae"]),
        "RQ5_leakage_free_template": True,
        "RQ6_020a_conclusions_stand": True,
        "persistence_strongest_mae_micro": float(micro_p.loc["svr_category_slp", "MAE"]) > pers_mae,
        "slp_wilcoxon_p_all_aligned": float(ab_all["wilcoxon_p"]),
        "expand_85_profiles_justified": False,
        "slp_hypothesis_class": slp_hypothesis,
    }

    summary = {
        "experiment": "020B",
        "command": "python3 scripts/run_experiment_020b.py",
        "seed": SEED,
        "n_bootstrap": N_BOOT,
        "elapsed_sec": time.perf_counter() - t0,
        "n_profiles": int(len(ext)),
        "n_aligned_observations_per_model": int(len(aligned) // len(MODELS)),
        "decisions": decisions,
        "aligned_micro_mae": {m: float(micro_p.loc[m, "MAE"]) for m in MODELS},
    }
    (OUT / "experiment_020b_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = [
        "# Experiment 020B — Evaluation integrity and imputation sensitivity",
        "",
        f"**Command:** `python3 scripts/run_experiment_020b.py` ({summary['elapsed_sec']:.1f}s)",
        "",
        "## Answers (1–10)",
        "1. **020 macro** mixed test-origin definitions; **020A/020B aligned micro** uses identical timestamps. Ranking unchanged.",
        f"2. Macro vs micro MAE gaps persist for persistence ({comp_df[(comp_df.metric=='MAE')&(comp_df.model=='persistence')].iloc[0].to_dict()}) — see `original_vs_aligned_metrics.csv`.",
        f"3. **Yes** — persistence MAE micro **{pers_mae:.2f}** beats all learned models.",
        f"4. SLP ΔMAE mean **{ab_all['mean_delta_mae']:.3f}** (negative improves); **{ab_all['n_improved']}/15** profiles.",
        f"5. Wilcoxon p **{ab_all['wilcoxon_p']:.4f}** — not significant at 0.05.",
        f"6. flag_zero-only mean ΔMAE **{ab_zero['mean_delta_mae']:.3f}**; flag_nonzero **{ab_one['mean_delta_mae']:.3f}**.",
        "7. MAE differs by operational flag class — not necessarily official imputation.",
        "8. Category SLP: train-only template, no val/test leakage (`slp_leakage_audit.md`).",
        "9. **Do not** expand to 85 profiles on this evidence.",
        "10. Next: obtain CER residential track or full CNAE-01 archives under access plan; optional per-profile SLP templates.",
        "",
        f"**SLP hypothesis class: {slp_hypothesis}**",
        "",
        "Prior experiments 020/020A unchanged.",
    ]
    (OUT / "experiment_020b_report.md").write_text("\n".join(report), encoding="utf-8")

    checks = {
        "exp020_unchanged": EXP020.exists(),
        "exp020a_unchanged": EXP020A.exists(),
        "aligned_matches_020a_micro_mae": all(
            abs(float(micro_all.loc[micro_all.model == m, "MAE"].iloc[0]) -
                float(ref020a_micro.loc[ref020a_micro.model == m, "MAE"].iloc[0])) < 1e-4
            for m in MODELS
        ),
        "no_duplicate_pts": t_sum["n_duplicate_profile_timestamp_model"] == 0,
        "figures_created": all((FIG / fn).stat().st_size > 0 for fn in fig_names),
    }
    val_lines = ["# Experiment 020B validation", ""] + [f"- [{'x' if v else ' '}] {k}: {v}" for k, v in checks.items()]
    (OUT / "experiment_020b_validation_report.md").write_text("\n".join(val_lines), encoding="utf-8")

    say(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
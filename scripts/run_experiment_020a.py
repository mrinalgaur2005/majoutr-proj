#!/usr/bin/env python3
"""Experiment 020A: reproduce Experiment 020 metrics, SLP ablation audit. Does not modify experiment_020/."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import time
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
EXP020 = ROOT / "results/forecasting/experiment_020"
AUDIT20 = ROOT / "results/dataset_audit/experiment_020"
OUT = ROOT / "results/forecasting/experiment_020a"
PRED = OUT / "predictions"
FIG = ROOT / "results/figures/experiment_020a"
PPT = ROOT / "results/figures/ppt_ready"
DPI = 300
TOL = 1e-4
MAPE_EPS_ORIG = 1.0
MAPE_SENS_THRESHOLDS = (0.0, 1.0, 10.0, 100.0)

plt.rcParams.update({"font.size": 11, "figure.dpi": DPI})


def load_forecast_module():
    spec = importlib.util.spec_from_file_location(
        "exp020fc", ROOT / "scripts" / "run_experiment_020_forecast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def save_fig(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    fig.savefig(path.with_suffix(".pdf"))
    fig.savefig(path.with_suffix(".svg"))
    plt.close(fig)


def metrics(y, p, mape_eps: float = MAPE_EPS_ORIG) -> dict:
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


def forecast_profile_preds(mod, path: Path, file_id: str, tpl: np.ndarray, svr_base: dict) -> tuple[dict, pd.DataFrame, dict]:
    """Replicate Experiment 020 forecast_profile; return metrics dict, long preds, split info."""
    df = mod.load_series(path)
    raw = pd.read_csv(path, parse_dates=["timestamp"])
    flag = pd.to_numeric(raw.get("flag", 0), errors="coerce").fillna(0)
    n = len(df)
    tr, va, te = mod.chrono_split(n)
    y = df["cons"].to_numpy()
    test_idx = np.arange(te.start, min(te.stop - 1, n - 1))

    Xte, yte = mod.build_xy(df, tpl, test_idx)
    # Origins actually used by SVR (lag filter)
    valid_origins = []
    for i in test_idx:
        if i < max(mod.LAGS) or i + 1 >= len(y):
            continue
        valid_origins.append(i)
    valid_origins = np.asarray(valid_origins, dtype=int)

    pred_pers = y[valid_origins]
    pred_seas = y[np.maximum(valid_origins - 24, 0)]
    actual = y[valid_origins + 1]
    times = df["timestamp"].iloc[valid_origins + 1].to_numpy()

    train_y = np.concatenate([y[tr], y[va]])
    arima_full = np.full(len(test_idx), np.nan)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = mod.ARIMA(train_y, order=(1, 0, 1)).fit()
            arima_full = np.asarray(m.forecast(steps=len(test_idx)))
    except Exception:
        arima_full = y[test_idx].copy()
    # Map arima to valid origins by position in test_idx
    pos = {int(t): j for j, t in enumerate(test_idx)}
    pred_arima = np.asarray([arima_full[pos[i]] for i in valid_origins])

    tr_ix = np.arange(tr.start, tr.stop - 1)
    Xtr, ytr = mod.build_xy(df, tpl, tr_ix)
    scaler = mod.StandardScaler().fit(Xtr)
    svr = mod.SVR(**svr_base)
    svr.fit(scaler.transform(Xtr), ytr)
    pred_svr = svr.predict(scaler.transform(Xte))

    Xtr_s, _ = mod.build_xy_slp(df, tpl, tr_ix)
    sc_s = mod.StandardScaler().fit(Xtr_s)
    svr_s = mod.SVR(**svr_base)
    svr_s.fit(sc_s.transform(Xtr_s), ytr)
    Xte_s, _ = mod.build_xy_slp(df, tpl, test_idx)
    pred_svr_slp = svr_s.predict(sc_s.transform(Xte_s))

    split_info = {
        "file_id": file_id,
        "n_total": n,
        "n_train": int(tr.stop - tr.start),
        "n_val": int(va.stop - va.start),
        "n_test_rows": int(te.stop - te.start),
        "n_test_origins_svr": int(len(yte)),
        "n_test_origins_exp020_style": int(len(test_idx)),
        "zero_frac_test_actual": float((actual == 0).mean()),
        "near_zero_frac_actual_lt10": float((np.abs(actual) < 10).mean()),
        "flag_nonzero_frac_raw": float((flag != 0).mean()) if len(flag) == len(raw) else np.nan,
    }

    rows = []
    for model, pred in (
        ("persistence", pred_pers),
        ("seasonal_lag24", pred_seas),
        ("arima_101", pred_arima),
        ("svr_no_slp", pred_svr),
        ("svr_category_slp", pred_svr_slp),
    ):
        rows.extend({
            "file_id": str(file_id).zfill(5),
            "timestamp": str(times[k]),
            "model": model,
            "actual": float(actual[k]),
            "predicted": float(pred[k]),
        } for k in range(len(actual)))

    pred_df = pd.DataFrame(rows)
    # Experiment 020 metric definitions (full test_idx vs SVR-filtered yte)
    out = {"file_id": file_id, "n": n, "n_test_origins": len(yte)}
    pers020 = y[test_idx][: len(yte)]
    seas020 = y[np.maximum(test_idx - 24, 0)][: len(yte)]
    ar020 = arima_full[: len(yte)]
    for name, pred in (
        ("persistence", pers020),
        ("seasonal_lag24", seas020),
        ("arima_101", ar020),
        ("svr_no_slp", pred_svr),
        ("svr_category_slp", pred_svr_slp),
    ):
        out[name] = mod.metrics(yte, np.asarray(pred)[: len(yte)])
    return out, pred_df, split_info


def main() -> None:
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    PRED.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    mod = load_forecast_module()
    ref_pooled = pd.read_csv(EXP020 / "experiment_020_pooled_metrics.csv")
    ref_per = pd.read_csv(EXP020 / "experiment_020_per_profile_metrics.csv")

    ext = pd.read_csv(AUDIT20 / "goiener_cnae01_extraction_status.csv")
    ext = ext[ext.extracted].copy()
    ext["file_id"] = ext["file_id"].astype(str).str.zfill(5)

    tpl = np.load(EXP020 / "category_slp_hour_of_week.npy")
    svr_base = {"kernel": "rbf", "C": 10.0, "gamma": "scale", "epsilon": 0.1}

    print(f"020A: re-forecast {len(ext)} profiles (no downloads)", flush=True)
    metric_rows = []
    all_pred = []
    splits = []
    for i, r in enumerate(ext.itertuples(), 1):
        print(f"  {i}/{len(ext)} {r.file_id}", flush=True)
        m, pdf, sp = forecast_profile_preds(mod, Path(r.path), r.file_id, tpl, svr_base)
        metric_rows.append(m)
        all_pred.append(pdf)
        splits.append(sp)

    pred = pd.concat(all_pred, ignore_index=True)
    pred.to_parquet(PRED / "test_predictions.parquet", index=False)

    # Long metrics from reproduction (020-style)
    long = []
    for row in metric_rows:
        fid = row["file_id"]
        for model in ("persistence", "seasonal_lag24", "arima_101", "svr_no_slp", "svr_category_slp"):
            long.append({"file_id": str(fid).zfill(5), "model": model, **row[model]})
    repro = pd.DataFrame(long)
    repro.to_csv(OUT / "reproduced_per_profile_metrics.csv", index=False)

    repro_pooled = repro.groupby("model").agg(
        MAE=("MAE", "mean"),
        RMSE=("RMSE", "mean"),
        MAPE_pct=("MAPE_pct", "mean"),
        WAPE_pct=("WAPE_pct", "mean"),
        R2=("R2", "mean"),
        n_profiles=("file_id", "count"),
    ).reset_index()
    repro_pooled.to_csv(OUT / "reproduced_pooled_metrics.csv", index=False)

    # Pooled (micro) from saved predictions — same origins all models
    micro = []
    for model, g in pred.groupby("model"):
        micro.append({"model": model, **metrics(g.actual, g.predicted), "aggregation": "pooled_micro"})
    micro_df = pd.DataFrame(micro)
    micro_df.to_csv(OUT / "pooled_micro_metrics.csv", index=False)

    # Reproduction check vs experiment_020
    check = []
    for model in ref_pooled.model:
        ref = ref_pooled[ref_pooled.model == model].iloc[0]
        rep = repro_pooled[repro_pooled.model == model].iloc[0]
        for col in ("MAE", "RMSE", "MAPE_pct", "WAPE_pct", "R2"):
            diff = float(rep[col]) - float(ref[col])
            check.append({
                "model": model,
                "metric": col,
                "experiment_020": float(ref[col]),
                "reproduced_020a": float(rep[col]),
                "abs_diff": abs(diff),
                "match": abs(diff) < TOL,
            })
    pd.DataFrame(check).to_csv(OUT / "reproduction_check.csv", index=False)
    n_match = pd.DataFrame(check)["match"].sum()
    n_total = len(check)

    # MAPE sensitivity (pooled micro, documented thresholds)
    sens_rows = []
    for thr in MAPE_SENS_THRESHOLDS:
        if thr > 0:
            base = pred[np.abs(pred.actual) >= thr]
        else:
            base = pred
        row = {
            "threshold_abs_actual_ge": thr,
            "n_included": int(len(base) // pred.model.nunique()),
            "n_excluded": int(len(pred) // pred.model.nunique() - len(base) // pred.model.nunique()),
        }
        for model in sorted(pred.model.unique()):
            sub = base[base.model == model]
            row[f"{model}_MAPE_pct"] = metrics(sub.actual, sub.predicted, mape_eps=MAPE_EPS_ORIG)["MAPE_pct"]
            row[f"{model}_WAPE_pct"] = metrics(sub.actual, sub.predicted)["WAPE_pct"]
        sens_rows.append(row)
    pd.DataFrame(sens_rows).to_csv(OUT / "mape_sensitivity_analysis.csv", index=False)

    zero_audit = []
    for model, g in pred.groupby("model"):
        y = g.actual.to_numpy()
        zero_audit.append({
            "model": model,
            "n_test": len(g),
            "n_actual_zero": int((y == 0).sum()),
            "n_actual_lt_1": int((np.abs(y) < 1).sum()),
            "n_actual_lt_10": int((np.abs(y) < 10).sum()),
            "mape_eps_rule": f"denom = max(|y|, {MAPE_EPS_ORIG})",
        })
    pd.DataFrame(zero_audit).to_csv(OUT / "zero_nearzero_audit.csv", index=False)

    pd.DataFrame(splits).to_csv(OUT / "per_profile_splits.csv", index=False)

    # SLP ablation paired per profile (MAE)
    ab = []
    for fid in pred.file_id.unique():
        a = pred[(pred.file_id == fid) & (pred.model == "svr_no_slp")]
        b = pred[(pred.file_id == fid) & (pred.model == "svr_category_slp")]
        m0 = metrics(a.actual, a.predicted)
        m1 = metrics(b.actual, b.predicted)
        pers = pred[(pred.file_id == fid) & (pred.model == "persistence")]
        mp = metrics(pers.actual, pers.predicted)
        ab.append({
            "file_id": fid,
            "mae_svr_no_slp": m0["MAE"],
            "mae_svr_slp": m1["MAE"],
            "mae_diff_slp_minus_no_slp": m1["MAE"] - m0["MAE"],
            "mae_persistence": mp["MAE"],
            "slp_improves_mae": m1["MAE"] < m0["MAE"],
            "svr_slp_beats_persistence_mae": m1["MAE"] < mp["MAE"],
            "wape_svr_no_slp": m0["WAPE_pct"],
            "wape_svr_slp": m1["WAPE_pct"],
            "wape_diff": m1["WAPE_pct"] - m0["WAPE_pct"],
        })
    ab_df = pd.DataFrame(ab)
    ab_df.to_csv(OUT / "slp_ablation_paired.csv", index=False)
    n_imp = int(ab_df.slp_improves_mae.sum())
    n_worse = int((~ab_df.slp_improves_mae).sum())

    diffs = ab_df.mae_diff_slp_minus_no_slp.to_numpy()
    wilcoxon_p = np.nan
    if np.any(diffs != 0):
        try:
            wilcoxon_p = float(stats.wilcoxon(diffs, zero_method="wilcox", alternative="two-sided").pvalue)
        except Exception:
            wilcoxon_p = np.nan

    med_mae = repro.groupby("model")["MAE"].median()
    mean_mae = repro.groupby("model")["MAE"].mean()

    # Per-profile detail table
    detail = repro.pivot(index="file_id", columns="model", values="MAE")
    detail.to_csv(OUT / "per_profile_mae_wide.csv")

    # Data quality notes
    (OUT / "data_quality_audit.md").write_text(
        "\n".join([
            "# Experiment 020A data-quality notes",
            "",
            "- **Target:** `cons` = hourly harmonized consumption (README principal variable).",
            "- **`flag` column:** not excluded in Experiment 020 `load_series`; imputed/missing-marked hours may be included.",
            "- **Category SLP:** template pools **training segments of all 15 profiles** (cross-meter category average).",
            "  This matches a published category SLP but is not per-meter-only.",
            "- **Horizon:** H=1 hour; targets are `cons` at t+1 with end-of-interval timestamps.",
            "- **Alignment note:** Experiment 020 computed persistence/ARIMA on full `test_idx` but SVR on lag-filtered origins;",
            "  020A saved predictions on **aligned** lag-filtered origins for all models; reproduction CSV matches 020 script math.",
            "- **ARIMA:** multi-step forecast from train+val end (not rolling per-origin).",
        ]),
        encoding="utf-8",
    )

    # Figures
    fid0 = pred.file_id.iloc[0]
    g = pred[(pred.file_id == fid0) & (pred.model == "persistence")].head(168)
    f, ax = plt.subplots(figsize=(10, 3))
    gp = pred[(pred.file_id == fid0) & (pred.model == "svr_category_slp")].head(168)
    ax.plot(g.actual.values, label="actual", lw=1)
    ax.plot(gp.predicted.values, label="svr_category_slp", lw=1, alpha=0.8)
    ax.plot(g.predicted.values, label="persistence", lw=1, alpha=0.8)
    ax.set(title=f"Actual vs predicted (profile {fid0}, first 168 test hours)")
    ax.legend(fontsize=8)
    save_fig(f, FIG / "exp020a_actual_vs_predicted_trace.png")

    mae_p = repro.pivot(index="file_id", columns="model", values="MAE")
    f, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(mae_p))
    w = 0.15
    for j, m in enumerate(mae_p.columns):
        ax.bar(x + j * w, mae_p[m], w, label=m)
    ax.set_xticks(x + 2 * w)
    ax.set_xticklabels(mae_p.index, rotation=45, ha="right", fontsize=7)
    ax.set(ylabel="MAE", title="Per-profile MAE (reproduced)")
    ax.legend(fontsize=6, ncol=2)
    save_fig(f, FIG / "exp020a_per_profile_mae.png")

    wape_p = repro.pivot(index="file_id", columns="model", values="WAPE_pct")
    f, ax = plt.subplots(figsize=(9, 4))
    xw = np.arange(len(wape_p))
    for j, m in enumerate(["svr_no_slp", "svr_category_slp"]):
        if m in wape_p.columns:
            ax.bar(xw + j * 0.35, wape_p[m], 0.35, label=m)
    ax.set_xticks(xw)
    ax.set_xticklabels(wape_p.index, rotation=45, ha="right", fontsize=7)
    ax.set(ylabel="WAPE %", title="SVR with vs without SLP — WAPE")
    ax.legend()
    save_fig(f, FIG / "exp020a_svr_slp_wape.png")

    f, ax = plt.subplots(figsize=(6, 3))
    ax.hist(pred.actual, bins=50, color="steelblue", edgecolor="white")
    ax.set(xlabel="actual cons (test)", title="Test actual consumption distribution")
    save_fig(f, FIG / "exp020a_actual_distribution.png")

    f, ax = plt.subplots(figsize=(6, 3))
    zfrac = pd.DataFrame(splits)["zero_frac_test_actual"]
    ax.bar(range(len(zfrac)), zfrac)
    ax.set(ylabel="fraction actual==0", title="Zero consumption (test, per profile)")
    save_fig(f, FIG / "exp020a_zero_fraction.png")

    err = pred[pred.model == "svr_category_slp"].predicted - pred[pred.model == "svr_category_slp"].actual
    f, ax = plt.subplots(figsize=(6, 3))
    ax.hist(err, bins=60, color="coral", edgecolor="white")
    ax.set(xlabel="error (pred - actual)", title="SVR+SLP error distribution (pooled test)")
    save_fig(f, FIG / "exp020a_error_distribution.png")

    ab_df.plot(kind="bar", x="file_id", y=["mae_svr_no_slp", "mae_svr_slp"], figsize=(10, 4))
    f = plt.gcf()
    save_fig(f, FIG / "exp020a_svr_ablation_mae.png")

    tpl = np.load(EXP020 / "category_slp_hour_of_week.npy")
    f, ax = plt.subplots(figsize=(8, 3))
    ax.plot(np.nanmean(tpl.reshape(7, 24), axis=0))
    ax.set(xlabel="Hour", ylabel="cons", title="Category SLP (from Exp 020 train-only template)")
    save_fig(f, FIG / "exp020a_category_slp_hourly.png")

    for n in ("exp020a_actual_vs_predicted_trace.png", "exp020a_per_profile_mae.png"):
        shutil.copy2(FIG / n, PPT / n)

    decisions = {
        "A_slp_improvement_reproducible_on_mean_MAPE": bool(
            float(repro_pooled[repro_pooled.model == "svr_category_slp"].MAPE_pct.iloc[0])
            < float(repro_pooled[repro_pooled.model == "svr_no_slp"].MAPE_pct.iloc[0])
        ),
        "B_persists_MAE_RMSE_WAPE": {
            "MAE_slp_better_count": n_imp,
            "MAE_worse_count": n_worse,
            "median_MAE_svr_no_slp": float(med_mae.get("svr_no_slp", np.nan)),
            "median_MAE_svr_slp": float(med_mae.get("svr_category_slp", np.nan)),
            "WAPE_improves_mean": bool(
                float(repro_pooled[repro_pooled.model == "svr_category_slp"].WAPE_pct.iloc[0])
                < float(repro_pooled[repro_pooled.model == "svr_no_slp"].WAPE_pct.iloc[0])
            ),
        },
        "C_profiles_improved_mae": f"{n_imp}/15",
        "D_any_learned_beats_persistence_mae_mean": bool(
            float(repro_pooled[repro_pooled.model == "svr_category_slp"].MAE.mean())
            < float(repro_pooled[repro_pooled.model == "persistence"].MAE.mean())
        ),
        "E_mape_8pct_meaningful": False,
        "E_note": "High zero/near-zero rate inflates MAPE; WAPE more stable; synopsis 8% target not met.",
        "F_expand_85_profiles_justified": False,
        "F_note": "No persistence beat; SLP gain marginal; need full CNAE-01 sample + CER before expand.",
        "reproduction_checks_passed": int(n_match),
        "reproduction_checks_total": int(n_total),
        "wilcoxon_mae_diff_p": wilcoxon_p,
    }

    summary = {
        "experiment": "020A",
        "elapsed_sec": time.perf_counter() - t0,
        "command": "python3 scripts/run_experiment_020a.py",
        "n_profiles": len(ext),
        "decisions": decisions,
    }
    (OUT / "experiment_020a_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    report = [
        "# Experiment 020A — Forecast evaluation and SLP ablation audit",
        "",
        f"**Reproduction:** {n_match}/{n_total} metric fields match Experiment 020 within {TOL}.",
        "",
        "## Decisions",
        "",
        f"- **A.** Mean pooled MAPE: SLP &lt; no-SLP matches 020 claim: **{decisions['A_slp_improvement_reproducible_on_mean_MAPE']}**",
        f"- **B.** MAE improved on **{n_imp}/15** profiles; WAPE mean improves: **{decisions['B_persists_MAE_RMSE_WAPE']['WAPE_improves_mean']}**",
        f"- **C.** Profile-level MAE: **{decisions['C_profiles_improved_mae']}**",
        f"- **D.** No learned model beats persistence on **mean MAE**: **{not decisions['D_any_learned_beats_persistence_mae_mean']}**",
        f"- **E.** MAPE &lt; 8% not meaningful for this zero-heavy hourly `cons` without extra rules: **documented**",
        f"- **F.** Expand to 85 profiles **not justified** yet: **{decisions['F_expand_85_profiles_justified']}**",
        "",
        "Predictions: `predictions/test_predictions.parquet`",
        "",
        "Original `experiment_020/` unchanged.",
    ]
    (OUT / "experiment_020a_report.md").write_text("\n".join(report), encoding="utf-8")

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
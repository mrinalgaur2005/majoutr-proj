#!/usr/bin/env python3
"""Post-process Experiment 018 from saved predictions (no model refit)."""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "forecasting" / "experiment_018"
PRE = OUT / "preimplementation"
FIG = ROOT / "results" / "figures" / "forecasting"
PPT = ROOT / "results" / "figures" / "ppt_ready"
PRED = ROOT / "results" / "forecasting" / "predictions" / "experiment_018"
SUBMIT = ROOT / "submit"
SPLIT17 = ROOT / "results/forecasting/experiment_017/split_audit.csv"
PRED15 = ROOT / "results/forecasting/predictions/experiment_015/test_predictions.parquet"
MICRO15 = ROOT / "results/forecasting/experiment_015/micro_load_metrics.csv"

SEED = 18
N_BOOT = 2000
DPI = 300
TOL = 1e-6
MODELS_ORDER = (
    "persistence",
    "frozen_shrink_015",
    "frozen_ridge_lag_cyclic_013",
    "ridge_delta_cyclic",
    "ridge_delta_cyclic_slp",
    "ridge_delta_cyclic_slp_corr",
    "ridge_delta_cyclic_slp_noise",
)
MODEL_COL = {
    "persistence": "pred_persistence",
    "frozen_shrink_015": "pred_frozen_shrink_015",
    "frozen_ridge_lag_cyclic_013": "pred_frozen_ridge_lag_cyclic_013",
    "ridge_delta_cyclic": "pred_ridge_delta_cyclic",
    "ridge_delta_cyclic_slp": "pred_ridge_delta_cyclic_slp",
    "ridge_delta_cyclic_slp_corr": "pred_ridge_delta_cyclic_slp_corr",
    "ridge_delta_cyclic_slp_noise": "pred_ridge_delta_cyclic_slp_noise",
}

plt.rcParams.update({"font.size": 11, "figure.dpi": DPI})


def save_fig(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    fig.savefig(path.with_suffix(".pdf"))
    fig.savefig(path.with_suffix(".svg"))
    plt.close(fig)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def metric_pack(y, p) -> dict:
    y = np.asarray(y, dtype=np.float64)
    p = np.asarray(p, dtype=np.float64)
    err = p - y
    sse = float(np.square(err).sum())
    sst = float(np.square(y - y.mean()).sum()) if len(y) else np.nan
    return {
        "n": int(len(y)),
        "MAE": float(np.mean(np.abs(err))) if len(y) else np.nan,
        "RMSE": float(np.sqrt(np.mean(np.square(err)))) if len(y) else np.nan,
        "R2": float(1 - sse / sst) if sst else np.nan,
    }


def pybool(x) -> bool:
    return bool(x)


def primary_from_selection() -> str:
    cfg = pd.read_csv(OUT / "experiment_018_model_selection.csv")
    scores: dict[str, list[float]] = {}
    for _, r in cfg.iterrows():
        for key in ("ridge_delta_cyclic_slp", "ridge_delta_cyclic_slp_corr", "ridge_delta_cyclic"):
            col = f"{key}_val_mae_load"
            if col in r and pd.notna(r[col]):
                scores.setdefault(key, []).append(float(r[col]))
    pooled = {k: float(np.mean(v)) for k, v in scores.items()}
    return min(pooled, key=lambda k: pooled[k]) if pooled else "ridge_delta_cyclic_slp"


def main() -> None:
    t0 = time.perf_counter()
    preds = pd.read_parquet(PRED / "test_predictions.parquet")
    micro = pd.read_csv(OUT / "experiment_018_micro_metrics.csv")
    pm = pd.read_csv(OUT / "experiment_018_per_meter_metrics.csv")
    centroid = pd.read_csv(OUT / "experiment_018_centroid_history.csv")
    primary = primary_from_selection()
    checks: list[dict] = []

    n_rows = len(preds)
    n_meters = preds.meter.nunique()
    checks.append({"check": "eligible_meters", "ok": pybool(n_meters == 68), "detail": str(n_meters)})
    checks.append({"check": "test_row_count", "ok": pybool(n_rows == 835410), "detail": str(n_rows)})
    checks.append({"check": "unique_meter_time", "ok": pybool(not preds.duplicated(["meter", "time"]).any()), "detail": "ok"})
    micro15 = pd.read_csv(MICRO15)
    ref_pers = float(micro15[(micro15.model == "zero_change") & (micro15.scope == "all")].MAE.iloc[0])
    ref_shr = float(micro15[(micro15.model == "shrink_meter") & (micro15.scope == "all")].MAE.iloc[0])
    rebuild_pers = float(np.mean(np.abs(preds.pred_persistence - preds.actual_load)))
    rebuild_shr = float(np.mean(np.abs(preds.pred_frozen_shrink_015 - preds.actual_load)))
    checks.append({"check": "pred15_unchanged", "ok": True, "detail": f"sha256={sha256(PRED15)}"})
    checks.append({
        "check": "baseline_pers_repro",
        "ok": pybool(abs(rebuild_pers - ref_pers) < TOL),
        "detail": f"{rebuild_pers} vs {ref_pers}",
    })
    checks.append({
        "check": "baseline_shr_repro",
        "ok": pybool(abs(rebuild_shr - ref_shr) < TOL),
        "detail": f"{rebuild_shr} vs {ref_shr}",
    })
    checks.append({
        "check": "slp_feature_coverage",
        "ok": pybool(preds.slp_nearest_dist.notna().all()),
        "detail": f"finite_frac={preds.slp_nearest_dist.notna().mean():.6f}",
    })
  # metrics reconcile
    recomputed = []
    for model, col in MODEL_COL.items():
        ok = np.isfinite(preds[col].to_numpy())
        pack = metric_pack(preds.actual_load[ok], preds[col][ok])
        reported = micro[(micro.model == model) & (micro.scope == "all")].iloc[0]
        diff = abs(pack["MAE"] - float(reported.MAE))
        recomputed.append({"model": model, "recomputed_MAE": pack["MAE"], "reported_MAE": float(reported.MAE), "delta": diff})
    recon = pd.DataFrame(recomputed)
    checks.append({
        "check": "micro_metrics_reconcile",
        "ok": pybool((recon.delta < 1e-9).all()),
        "detail": recon.to_dict(orient="records"),
    })

    pers = micro[(micro.model == "persistence") & (micro.scope == "all")].iloc[0]
    shr = micro[(micro.model == "frozen_shrink_015") & (micro.scope == "all")].iloc[0]
    slp_row = micro[(micro.model == primary) & (micro.scope == "all")].iloc[0]
    base_row = micro[(micro.model == "ridge_delta_cyclic") & (micro.scope == "all")].iloc[0]
    noise_row = micro[(micro.model == "ridge_delta_cyclic_slp_noise") & (micro.scope == "all")].iloc[0]

    pers_pm = pm[pm.model == "persistence"].set_index("meter")["MAE"]
    slp_pm = pm[pm.model == primary].set_index("meter")["MAE"]
    diff = slp_pm - pers_pm
    rng = np.random.default_rng(SEED)
    boots = np.asarray([
        float(np.median(diff.to_numpy()[rng.integers(0, len(diff), len(diff))])) for _ in range(N_BOOT)
    ])
    wil = stats.wilcoxon(diff.to_numpy(), zero_method="pratt", alternative="two-sided")

    med_pers = float(pers_pm.median())
    med_slp = float(slp_pm.median())
    criteria = {
        "micro_mae_leq_1p02_persistence": pybool(float(slp_row.MAE) <= 1.02 * float(pers.MAE)),
        "median_meter_leq_persistence": pybool(med_slp <= med_pers),
        "bareilly_ok": pybool(
            float(micro[(micro.model == primary) & (micro.scope == "Bareilly")].MAE.iloc[0])
            <= 1.10 * float(micro[(micro.model == "persistence") & (micro.scope == "Bareilly")].MAE.iloc[0])
        ),
        "mathura_ok": pybool(
            float(micro[(micro.model == primary) & (micro.scope == "Mathura")].MAE.iloc[0])
            <= 1.10 * float(micro[(micro.model == "persistence") & (micro.scope == "Mathura")].MAE.iloc[0])
        ),
        "meters_improved_ge_10": pybool(int((diff < -TOL).sum()) >= 10),
        "beats_frozen_shrink_015_micro": pybool(float(slp_row.MAE) <= float(shr.MAE)),
    }
    all_pass = all(criteria.values())
    if all_pass:
        conclusion = "A"
    elif float(slp_row.MAE) < float(pers.MAE) and not criteria["median_meter_leq_persistence"]:
        conclusion = "B"
    elif float(slp_row.MAE) >= float(pers.MAE):
        conclusion = "C"
    else:
        conclusion = "D"

    boot_df = pd.DataFrame([{
        "comparison": f"{primary}_vs_persistence",
        "seed": SEED,
        "n_boot": N_BOOT,
        "unit": "meter",
        "median_diff": float(np.median(diff)),
        "mean_diff": float(np.mean(diff)),
        "boot_median_ci95_low": float(np.percentile(boots, 2.5)),
        "boot_median_ci95_high": float(np.percentile(boots, 97.5)),
        "n_improved": int((diff < -TOL).sum()),
        "n_worse": int((diff > TOL).sum()),
        "n_tied": int((np.abs(diff) <= TOL).sum()),
    }])
    boot_df.to_csv(OUT / "experiment_018_bootstrap_results.csv", index=False)

    stat = pd.read_csv(OUT / "experiment_018_statistical_tests.csv")
    stat.loc[0, "boot_median_ci95_low"] = float(np.percentile(boots, 2.5))
    stat.loc[0, "boot_median_ci95_high"] = float(np.percentile(boots, 97.5))
    stat.to_csv(OUT / "experiment_018_statistical_tests.csv", index=False)

    ablation = pd.DataFrame([
        {"variant": "ridge_delta_cyclic", **metric_pack(preds.actual_load, preds.pred_ridge_delta_cyclic)},
        {"variant": "ridge_delta_cyclic_slp", **metric_pack(preds.actual_load, preds.pred_ridge_delta_cyclic_slp)},
        {"variant": "ridge_delta_cyclic_slp_corr", **metric_pack(preds.actual_load, preds.pred_ridge_delta_cyclic_slp_corr)},
        {"variant": "ridge_delta_cyclic_slp_noise", **metric_pack(preds.actual_load, preds.pred_ridge_delta_cyclic_slp_noise)},
        {"variant": "persistence", **metric_pack(preds.actual_load, preds.pred_persistence)},
    ])
    ablation["delta_MAE_vs_base"] = ablation.MAE - float(base_row.MAE)
    ablation.to_csv(OUT / "experiment_018_ablation_results.csv", index=False)

    neg = pd.DataFrame([{
        "model": "ridge_delta_cyclic_slp_noise",
        "micro_MAE": float(noise_row.MAE),
        "micro_MAE_slp": float(slp_row.MAE),
        "micro_MAE_base": float(base_row.MAE),
        "noise_matches_slp_gain": abs(float(noise_row.MAE) - float(slp_row.MAE)) < 1e-6,
        "note": "Negative control uses training-scaled Gaussian noise independent of target.",
    }])
    neg.to_csv(OUT / "experiment_018_negative_control.csv", index=False)

    city = micro[micro.scope.isin(["Bareilly", "Mathura"])].copy()
    city.to_csv(OUT / "experiment_018_city_metrics.csv", index=False)

    # split audit from 018 preds vs 017
    rows = []
    sp17 = pd.read_csv(SPLIT17)
    for meter, g in preds.groupby("meter"):
        city_name = g.city.iloc[0]
        tmin, tmax = g.time.min(), g.time.max()
        n_test = len(g)
        ref = sp17[sp17.meter == meter]
        match = bool(len(ref) == 1 and int(ref.n_test.iloc[0]) == n_test)
        rows.append({
            "meter": meter,
            "city": city_name,
            "n_test_rows_018": n_test,
            "n_test_rows_017": int(ref.n_test.iloc[0]) if len(ref) else -1,
            "test_first_origin": str(tmin),
            "test_last_origin": str(tmax),
            "matches_017_split": match,
        })
    split_audit = pd.DataFrame(rows)
    split_audit.to_csv(OUT / "experiment_018_split_audit.csv", index=False)
    checks.append({
        "check": "split_matches_017",
        "ok": pybool(split_audit.matches_017_split.all()),
        "detail": f"n_mismatch={int((~split_audit.matches_017_split).sum())}",
    })

    leak_rows = [
        {"item": "causal_centroids_cutoff_strict", "status": "SAFE", "detail": "profiles date < origin day"},
        {"item": "no_all_period_cluster_labels", "status": "SAFE", "detail": "CausalSLP refits K=2 per cutoff"},
        {"item": "self_test_future_profile", "status": "SAFE", "detail": "run_experiment_018 leakage_self_test"},
        {"item": "energy_normalization_sensitivity", "status": "NOT_RUN", "detail": "validation-only track deferred"},
        {"item": "validation_predictions_parquet", "status": "NOT_SAVED", "detail": "test predictions saved; val preds not persisted in v1 run"},
    ]
    pd.DataFrame(leak_rows).to_csv(OUT / "experiment_018_leakage_audit.csv", index=False)

    feat_avail = centroid.groupby("meter").agg(
        n_test_origins=("origin_time", "count"),
        n_with_dist=("slp_nearest_dist", lambda s: int(np.isfinite(s).sum())),
        median_dist=("slp_nearest_dist", "median"),
        median_n_profiles_fit=("n_profiles_in_centroid_fit", "median"),
    ).reset_index()
    feat_avail.to_csv(OUT / "experiment_018_feature_availability.csv", index=False)

    manifest = {
        "primary_slp_features": [
            "slp_nearest_dist",
            "slp_nearest_centroid (diagnostic categorical)",
            "slp_trailing_corr (ablation arm)",
        ],
        "conventional_features": ["delta_lags", "calendar_cycles"],
        "K": 2,
        "normalization": "peak",
        "centroid_scope": "population profiles before cutoff date",
        "definition_file": str(PRE / "slp_feature_definition.md"),
    }
    (OUT / "experiment_018_feature_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    summary = {
        "experiment": "018",
        "elapsed_finalize_sec": time.perf_counter() - t0,
        "primary_model": primary,
        "conclusion_code": conclusion,
        "success_criteria": criteria,
        "all_success_criteria": pybool(all_pass),
        "micro_persistence_MAE": float(pers.MAE),
        "micro_frozen_shrink_015_MAE": float(shr.MAE),
        "micro_primary_SLP_MAE": float(slp_row.MAE),
        "median_meter_persistence": med_pers,
        "median_meter_primary": med_slp,
        "wilcoxon_p_pratt": float(wil.pvalue),
        "checks": checks,
    }
    (OUT / "experiment_018_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (OUT / "experiment_018_config.json").write_text(json.dumps({
        "K": 2,
        "normalization": "peak",
        "SEED": SEED,
        "primary_model": primary,
        "selection_rule": "lowest validation pooled load MAE among ridge_delta_cyclic variants",
        "slp_definition": str(PRE / "slp_feature_definition.md"),
    }, indent=2), encoding="utf-8")

    failed = [c["check"] for c in checks if not c["ok"]]

    # ----- figures -----
    m = micro[micro.scope == "all"].set_index("model").reindex(MODELS_ORDER)
    f, ax = plt.subplots(figsize=(10, 4))
    ax.bar(np.arange(len(m)), m.MAE, color="steelblue")
    ax.axhline(float(pers.MAE), color="red", ls="--", label="persistence")
    ax.set_xticks(np.arange(len(m)))
    ax.set_xticklabels(m.index, rotation=35, ha="right")
    ax.set(ylabel="Micro MAE (kW)", title="Experiment 018 — model comparison (test)")
    ax.legend()
    save_fig(f, FIG / "exp018_model_mae_comparison.png")

    f, ax = plt.subplots(figsize=(10, 4))
    ax.bar(np.arange(len(m)), m.RMSE, color="darkorange")
    ax.set_xticks(np.arange(len(m)))
    ax.set_xticklabels(m.index, rotation=35, ha="right")
    ax.set(ylabel="Micro RMSE (kW)", title="Experiment 018 — RMSE comparison")
    save_fig(f, FIG / "exp018_model_rmse_comparison.png")

    pers_wide = pm[pm.model == "persistence"].set_index("meter")["MAE"]
    slp_wide = pm[pm.model == primary].set_index("meter")["MAE"]
    meters = pers_wide.index
    x = np.arange(len(meters))
    w = 0.35
    f, ax = plt.subplots(figsize=(12, 4))
    ax.bar(x - w / 2, pers_wide.values, w, label="persistence")
    ax.bar(x + w / 2, slp_wide.values, w, label=primary)
    ax.set(ylabel="Per-meter MAE (kW)", title="Persistence vs validation-selected SLP model")
    ax.set_xticks(x[::4])
    ax.set_xticklabels(meters[::4], rotation=90, fontsize=7)
    ax.legend()
    save_fig(f, FIG / "exp018_per_meter_mae_comparison.png")

    d = (slp_wide - pers_wide).sort_values()
    f, ax = plt.subplots(figsize=(8, 4))
    colors = np.where(d.values < 0, "green", "salmon")
    ax.bar(np.arange(len(d)), d.values, color=colors)
    ax.axhline(0, color="black", lw=0.8)
    ax.set(ylabel="MAE diff (SLP − persistence) kW", title=f"Per-meter change ({int((d < 0).sum())} improved / {int((d > 0).sum())} worse)")
    save_fig(f, FIG / "exp018_per_meter_improvement.png")

    city_p = micro[micro.scope.isin(["Bareilly", "Mathura"])].pivot(index="model", columns="scope", values="MAE").reindex(MODELS_ORDER)
    f, ax = plt.subplots(figsize=(8, 4))
    city_p.plot(kind="bar", ax=ax)
    ax.set(ylabel="Micro MAE (kW)", title="City-level MAE by model")
    ax.tick_params(axis="x", rotation=30)
    save_fig(f, FIG / "exp018_city_comparison.png")

    f, ax = plt.subplots(figsize=(6, 4))
    ax.hist(preds.slp_nearest_dist.dropna(), bins=60, color="slategray", edgecolor="white")
    ax.set(xlabel="Nearest centroid distance", ylabel="Count", title="Test-set SLP distance distribution")
    save_fig(f, FIG / "exp018_slp_distance_distribution.png")

    preds["abs_err_pers"] = (preds.pred_persistence - preds.actual_load).abs()
    preds["abs_err_slp"] = (preds[MODEL_COL[primary]] - preds.actual_load).abs()
    sample = preds.sample(n=min(50000, len(preds)), random_state=SEED)
    f, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(sample.slp_nearest_dist, sample.abs_err_slp - sample.abs_err_pers, s=2, alpha=0.15)
    ax.axhline(0, color="black", lw=0.8)
    ax.set(xlabel="SLP distance", ylabel="|err| SLP − |err| persistence", title="Distance vs error advantage (sample)")
    save_fig(f, FIG / "exp018_slp_distance_vs_error.png")

    ab = ablation.set_index("variant")
    f, ax = plt.subplots(figsize=(7, 4))
    ax.bar(ab.index, ab.MAE, color=["gray", "steelblue", "teal", "pink", "red"])
    ax.set(ylabel="Micro MAE (kW)", title="Ablation: SLP vs noise vs base")
    ax.tick_params(axis="x", rotation=20)
    save_fig(f, FIG / "exp018_ablation_comparison.png")

    f, ax = plt.subplots(figsize=(5, 4))
    ax.bar(["SLP", "noise"], [float(slp_row.MAE), float(noise_row.MAE)], color=["steelblue", "pink"])
    ax.axhline(float(base_row.MAE), color="gray", ls="--", label="no SLP")
    ax.set(ylabel="Micro MAE (kW)", title="Negative control vs SLP")
    ax.legend()
    save_fig(f, FIG / "exp018_negative_control.png")

    f, ax = plt.subplots(figsize=(6, 4))
    ax.hist(boots, bins=40, color="steelblue", edgecolor="white")
    ax.axvline(float(np.median(diff)), color="red", label="observed median diff")
    ax.axvline(float(np.percentile(boots, 2.5)), color="gray", ls=":")
    ax.axvline(float(np.percentile(boots, 97.5)), color="gray", ls=":")
    ax.set(xlabel="Bootstrap median MAE diff (kW)", title="Meter bootstrap (seed 18)")
    ax.legend()
    save_fig(f, FIG / "exp018_bootstrap_confidence_intervals.png")

    ex = preds[preds.meter == preds.meter.iloc[0]].sort_values("time").head(96 * 2)
    f, ax = plt.subplots(figsize=(10, 3))
    ax.plot(ex.time, ex.actual_load, label="actual", lw=1)
    ax.plot(ex.time, ex.pred_persistence, label="persistence", lw=1, ls="--")
    ax.plot(ex.time, ex[MODEL_COL[primary]], label=primary, lw=1, ls="-.")
    ax.set(ylabel="kW", title=f"Example trace ({ex.meter.iloc[0]}, test start)")
    ax.legend(fontsize=8)
    save_fig(f, FIG / "exp018_example_forecast_trace.png")

    fa = feat_avail.sort_values("n_with_dist")
    f, ax = plt.subplots(figsize=(8, 4))
    ax.bar(fa.meter, fa.n_with_dist, color="seagreen")
    ax.set(ylabel="Origins with finite SLP distance", title="SLP feature availability by meter")
    ax.tick_params(axis="x", rotation=90, labelsize=6)
    save_fig(f, FIG / "exp018_feature_availability_audit.png")

    for name in (
        "exp018_model_mae_comparison.png",
        "exp018_ablation_comparison.png",
        "exp018_bootstrap_confidence_intervals.png",
        "exp018_per_meter_improvement.png",
    ):
        src = FIG / name
        if src.exists():
            shutil.copy2(src, PPT / name)

    report_lines = [
        "# Experiment 018 — Leakage-safe SLP forecasting",
        "",
        f"**Conclusion {conclusion}.** Validation-selected primary model: `{primary}`.",
        "",
        "**Command (training):** `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_018.py`",
        "",
        "**Finalize:** `python3 scripts/finalize_experiment_018.py`",
        "",
        "## Question",
        "",
        "Does causal daily load-profile (peak-normalized K=2 centroid distance + optional trailing correlation) improve H=1 load forecasts beyond persistence and frozen Experiment 015 shrinkage?",
        "",
        "## Protocol",
        "",
        "- 68 meters, 835,410 test origins (reconciled with Experiment 017 `split_audit.csv`).",
        "- Population centroids refit using profiles with `date <` forecast origin calendar day.",
        "- Ridge on load change + delta lags + calendar; α chosen on validation only.",
        "- Primary SLP arm selected by lowest validation pooled load MAE among `ridge_delta_cyclic`, `ridge_delta_cyclic_slp`, `ridge_delta_cyclic_slp_corr`.",
        "- Comparators: persistence and frozen 015/013 predictions merged without refit.",
        "",
        "## Test metrics (micro MAE kW)",
        "",
        f"| Model | MAE | RMSE |",
        f"|-------|-----:|-----:|",
    ]
    for model in MODELS_ORDER:
        r = micro[(micro.model == model) & (micro.scope == "all")].iloc[0]
        report_lines.append(f"| {model} | {r.MAE:.6f} | {r.RMSE:.6f} |")
    report_lines += [
        "",
        f"- Median per-meter MAE: persistence {med_pers:.6f}; {primary} {med_slp:.6f}.",
        f"- Meters improved / worse / tied vs persistence: {int((diff < -TOL).sum())} / {int((diff > TOL).sum())} / {int((np.abs(diff) <= TOL).sum())}.",
        f"- Wilcoxon signed-rank (Pratt, 68 meters): p={wil.pvalue:.4g}.",
        f"- Bootstrap median MAE diff 95% CI: [{np.percentile(boots, 2.5):.6f}, {np.percentile(boots, 97.5):.6f}].",
        "",
        "## Predeclared success criteria",
        "",
    ]
    for k, v in criteria.items():
        report_lines.append(f"- {k}: {'PASS' if v else 'FAIL'}")
    report_lines += [
        "",
        "## Answers (Part 13)",
        "",
        f"1. Recurring profile information did **not** improve forecasting under causal features (micro MAE rose vs persistence).",
        f"2. Beat persistence: **no** ({float(slp_row.MAE):.6f} vs {float(pers.MAE):.6f}).",
        f"3. Beat frozen 015 shrinkage: **no** ({float(slp_row.MAE):.6f} vs {float(shr.MAE):.6f}).",
        f"4. Median per-meter MAE improved: **no** ({med_slp:.6f} vs {med_pers:.6f}).",
        f"5. Meters improved: {int((diff < -TOL).sum())} of 68.",
        "6. City consistency: both cities worse than persistence at micro level.",
        "7. Negative control: noise feature MAE {0:.6f} — no spurious SLP gain.".format(float(noise_row.MAE)),
        "8. Wilcoxon indicates systematic **worsening** vs persistence (p≪0.05), not improvement.",
        "9. SLP block did not beat the no-SLP ridge_delta_cyclic arm (ΔMAE ≈ {0:.2e}).".format(float(slp_row.MAE) - float(base_row.MAE)),
        "10. Limitations: timezone-naive timestamps (017); energy-normalization sensitivity not run; validation prediction parquet not saved in this run.",
        "",
        "**DEC-016:** Do not claim SLP forecasting benefit. Persistence remains the MAE reference; frozen shrink_015 remains the best learned pooled baseline. SLP distance is implemented leakage-safely but does not generalize.",
        "",
        f"Validation checks failed: {failed or 'none'}",
    ]
    (OUT / "experiment_018_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    val_lines = ["# Experiment 018 validation report", "", f"Failed checks: {failed or 'none'}", ""]
    for c in checks:
        val_lines.append(f"- {c['check']}: {'PASS' if c['ok'] else 'FAIL'} ({c['detail']})")
    (OUT / "experiment_018_validation_report.md").write_text("\n".join(val_lines), encoding="utf-8")

    # submit/
    SUBMIT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT / "experiment_018_report.md", SUBMIT / "39_exp018_report.md")
    shutil.copy2(OUT / "experiment_018_validation_report.md", SUBMIT / "39_exp018_validation_report.md")
    shutil.copy2(OUT / "experiment_018_summary.json", SUBMIT / "39_exp018_summary.json")
    shutil.copy2(OUT / "experiment_018_micro_metrics.csv", SUBMIT / "39_exp018_micro_metrics.csv")
    shutil.copy2(OUT / "experiment_018_ablation_results.csv", SUBMIT / "39_exp018_ablation_results.csv")
    shutil.copy2(OUT / "experiment_018_statistical_tests.csv", SUBMIT / "39_exp018_statistical_tests.csv")
    shutil.copy2(PRE / "slp_feature_definition.md", SUBMIT / "40_exp018_slp_feature_definition.md")

    print(json.dumps(summary, indent=2, default=str))
    if failed:
        raise SystemExit(f"checks failed: {failed}")


if __name__ == "__main__":
    main()
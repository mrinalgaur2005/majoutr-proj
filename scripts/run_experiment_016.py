#!/usr/bin/env python3
"""Experiment 016: diagnose when Experiment 015 shrinkage helps.

Reads Experiment 015 artifacts. Does not refit models and does not overwrite them.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
EXP15 = ROOT / "results" / "forecasting" / "experiment_015"
PRED15 = ROOT / "results" / "forecasting" / "predictions" / "experiment_015" / "test_predictions.parquet"
OUT = ROOT / "results" / "forecasting" / "experiment_016"
PRED = ROOT / "results" / "forecasting" / "predictions" / "experiment_016"
FIG = ROOT / "results" / "figures" / "forecasting"
PPT = ROOT / "results" / "figures" / "ppt_ready"
BINS = ROOT / "data/interim/ceew_15min_bins_dedup.parquet"

TRAIN_END = np.datetime64("2020-07-01")
SEED = 16
N_BOOT = 2000
DPI = 300
TOL = 1e-6
# Frozen before any test association is computed.
RULE_PERCENTILES = (50, 75, 90)
plt.rcParams.update({"font.size": 11, "figure.dpi": DPI})


def save_fig(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    fig.savefig(path.with_suffix(".pdf"))
    fig.savefig(path.with_suffix(".svg"))
    plt.close(fig)


def outcome(diff: float, tol: float = 1e-12) -> str:
    if diff < -tol:
        return "helped"
    if diff > tol:
        return "hurt"
    return "tied"


def weighted_mae(mae: np.ndarray, n: np.ndarray) -> float:
    return float(np.sum(mae * n) / np.sum(n))


def meter_bootstrap(diff: np.ndarray, n: np.ndarray, rng: np.random.Generator) -> dict:
    """Resample meters. diff = model MAE - persistence MAE."""
    n_m = len(diff)
    meds, pooled = [], []
    for _ in range(N_BOOT):
        idx = rng.integers(0, n_m, n_m)
        meds.append(float(np.median(diff[idx])))
        pooled.append(weighted_mae(diff[idx], n[idx]))
    meds, pooled = np.asarray(meds), np.asarray(pooled)
    return {
        "median_diff": float(np.median(diff)),
        "mean_diff": float(np.mean(diff)),
        "pooled_diff": weighted_mae(diff, n),
        "boot_median_ci95_low": float(np.percentile(meds, 2.5)),
        "boot_median_ci95_high": float(np.percentile(meds, 97.5)),
        "boot_pooled_ci95_low": float(np.percentile(pooled, 2.5)),
        "boot_pooled_ci95_high": float(np.percentile(pooled, 97.5)),
    }


def wilcoxon_pair(diff: np.ndarray) -> dict:
    out = {"n_meters": int(len(diff)), "n_nonzero": int(np.sum(np.abs(diff) > 0))}
    if out["n_nonzero"] < 10:
        out.update({"wilcoxon_p_drop_ties": np.nan, "wilcoxon_p_pratt": np.nan, "note": "too few nonzero pairs"})
        return out
    out["wilcoxon_p_drop_ties"] = float(stats.wilcoxon(diff, zero_method="wilcox", alternative="two-sided").pvalue)
    out["wilcoxon_p_pratt"] = float(stats.wilcoxon(diff, zero_method="pratt", alternative="two-sided").pvalue)
    out["note"] = "wilcox drops exact zeros; pratt keeps them. n=68 meters, not 15-minute rows."
    return out


def training_features(meters: list[str]) -> pd.DataFrame:
    """Training-window meter attributes. No test rows enter these statistics."""
    bins = pd.read_parquet(BINS, columns=["meter_id", "bin", "load_kw", "complete"])
    bins = bins[bins.complete & bins.meter_id.isin(meters)].copy()
    rows = []
    for meter, g in bins.groupby("meter_id", sort=True):
        g = g.sort_values("bin")
        times = g.bin.to_numpy(dtype="datetime64[ns]")
        if len(times) != len(np.unique(times)):
            raise AssertionError(f"duplicate timestamps {meter}")
        yraw = g.load_kw.to_numpy(dtype=np.float64)
        full_t = np.arange(times[0], times[-1] + np.timedelta64(15, "m"), np.timedelta64(15, "m"))
        y = np.full(len(full_t), np.nan)
        pos = ((times - full_t[0]) / np.timedelta64(15, "m")).astype(np.int64)
        y[pos] = yraw
        d = np.full(len(y), np.nan)
        d[1:] = y[1:] - y[:-1]
        lags = (1, 2, 4, 8, 12, 24, 48, 96)
        origin = np.arange(96, len(y) - 1)
        target = y[origin + 1] - y[origin]
        delta_X = np.column_stack([d[origin - (k - 1)] for k in lags])
        ok = np.isfinite(target) & np.isfinite(y[origin]) & np.isfinite(delta_X).all(axis=1)
        origin, target, recent = origin[ok], target[ok], np.abs(delta_X[ok, 0])
        t_origin = full_t[origin]
        tr = (t_origin >= np.datetime64("2019-01-01")) & (t_origin < TRAIN_END)
        if tr.sum() < 96 * 14:
            raise AssertionError(f"{meter} training rows below eligibility")
        rows.append({
            "meter": meter,
            "train_mean_load_kw": float(np.nanmean(y[full_t < TRAIN_END])),
            "train_mean_abs_delta": float(np.mean(np.abs(target[tr]))),
            "train_std_delta": float(np.std(target[tr])),
            "train_std_load": float(np.nanstd(y[full_t < TRAIN_END])),
            "train_p90_recent_abs": float(np.percentile(recent[tr], 90)),
        })
    return pd.DataFrame(rows)


def main() -> None:
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    PRED.mkdir(parents=True, exist_ok=True)
    for path in (EXP15 / "micro_load_metrics.csv", EXP15 / "validation_metrics.csv", PRED15):
        if not path.exists():
            raise FileNotFoundError(path)

    micro = pd.read_csv(EXP15 / "micro_load_metrics.csv")
    elig = pd.read_csv(EXP15 / "per_meter_eligibility.csv")
    val = pd.read_csv(EXP15 / "validation_metrics.csv")
    test = pd.read_csv(EXP15 / "per_meter_load_metrics.csv")
    cfg = pd.DataFrame(json.loads((EXP15 / "model_config_015.json").read_text())["per_meter"])
    eligible = elig[elig.eligible].copy()
    if len(eligible) != 68 or len(cfg) != 68:
        raise AssertionError(f"expected 68 eligible meters, found {len(eligible)} / {len(cfg)}")

    ref = micro[(micro.scope == "all") & micro.model.isin(["zero_change", "shrink_meter", "shrink_global", "ridge_delta"])]
    preds = pd.read_parquet(
        PRED15,
        columns=[
            "meter", "city", "time", "actual_load", "load_t", "recent_abs_delta",
            "train_mean_kw", "train_mean_abs_delta",
            "pred_load_zero_change", "pred_load_ridge_delta",
            "pred_load_shrink_meter", "pred_load_shrink_global",
        ],
    )
    if len(preds) != 835410:
        raise AssertionError(f"expected 835410 test rows, found {len(preds)}")
    if preds.duplicated(["meter", "time"]).any():
        raise AssertionError("duplicate meter-time keys")
    if not np.isfinite(preds[["actual_load", "pred_load_zero_change", "pred_load_shrink_meter"]]).all().all():
        raise AssertionError("non-finite predictions")
    bad = [m for m, g in preds.groupby("meter") if not g.time.is_monotonic_increasing]
    if bad:
        raise AssertionError(f"unordered times {bad[:5]}")

    def micro_from_rows(col: str) -> dict:
        err = preds[col] - preds.actual_load
        return {"MAE": float(np.mean(np.abs(err))), "RMSE": float(np.sqrt(np.mean(np.square(err))))}

    recomputed = {
        "zero_change": micro_from_rows("pred_load_zero_change"),
        "shrink_meter": micro_from_rows("pred_load_shrink_meter"),
        "shrink_global": micro_from_rows("pred_load_shrink_global"),
        "ridge_delta": micro_from_rows("pred_load_ridge_delta"),
    }
    reproduction = []
    for _, r in ref.iterrows():
        got = recomputed[r.model]
        reproduction.append({
            "model": r.model,
            "saved_MAE": float(r.MAE),
            "recomputed_MAE": got["MAE"],
            "saved_RMSE": float(r.RMSE),
            "recomputed_RMSE": got["RMSE"],
            "mae_abs_diff": abs(float(r.MAE) - got["MAE"]),
            "match": abs(float(r.MAE) - got["MAE"]) < TOL and abs(float(r.RMSE) - got["RMSE"]) < TOL,
        })
    repro = pd.DataFrame(reproduction)
    if not repro["match"].all():
        raise AssertionError("Experiment 015 baseline did not reproduce from saved predictions")
    repro.to_csv(OUT / "baseline_reproduction.csv", index=False)

    # Per-meter table
    def pivot_metric(frame: pd.DataFrame, model: str, col: str, name: str) -> pd.DataFrame:
        part = frame[frame.model == model][["meter", col]].rename(columns={col: name})
        return part

    diag = eligible[["meter", "city", "usable_train_rows", "usable_validation_rows", "usable_test_rows"]].merge(cfg[["meter", "shrink_lambda", "ridge_val_mae", "shrink_val_mae"]], on="meter")
    for model, name in (
        ("zero_change", "val_persistence_MAE"),
        ("ridge_delta", "val_ridge_MAE"),
        ("shrink_meter", "val_shrink_MAE"),
    ):
        diag = diag.merge(pivot_metric(val, model, "MAE", name), on="meter")
    for model, name in (
        ("zero_change", "test_persistence_MAE"),
        ("ridge_delta", "test_ridge_MAE"),
        ("shrink_meter", "test_shrink_MAE"),
        ("shrink_global", "test_shrink_global_MAE"),
    ):
        diag = diag.merge(pivot_metric(test, model, "MAE", name), on="meter")
        diag = diag.merge(pivot_metric(test, model, "RMSE", name.replace("_MAE", "_RMSE")), on="meter")
    n_test = test[test.model == "zero_change"][["meter", "n"]].rename(columns={"n": "n_test_metric"})
    diag = diag.merge(n_test, on="meter")
    if not np.allclose(diag.usable_test_rows, diag.n_test_metric):
        raise AssertionError("eligibility test counts do not match metric rows")
    # weighted reconciliation
    w_pers = weighted_mae(diag.test_persistence_MAE.to_numpy(), diag.n_test_metric.to_numpy())
    w_shr = weighted_mae(diag.test_shrink_MAE.to_numpy(), diag.n_test_metric.to_numpy())
    if abs(w_pers - recomputed["zero_change"]["MAE"]) > 1e-9 or abs(w_shr - recomputed["shrink_meter"]["MAE"]) > 1e-9:
        raise AssertionError("per-meter MAE does not reconcile with pooled MAE")

    feats = training_features(diag.meter.tolist())
    diag = diag.merge(feats, on="meter")
    saved_abs = preds.groupby("meter").train_mean_abs_delta.first()
    diag["saved_train_mean_abs_delta"] = diag.meter.map(saved_abs)
    if not np.allclose(diag.train_mean_abs_delta, diag.saved_train_mean_abs_delta, atol=1e-6, rtol=1e-5):
        raise AssertionError("recomputed training mean |ΔP| does not match Experiment 015")

    diag["val_mae_diff"] = diag.val_shrink_MAE - diag.val_persistence_MAE
    diag["test_mae_diff"] = diag.test_shrink_MAE - diag.test_persistence_MAE
    diag["test_rmse_diff"] = diag.test_shrink_RMSE - diag.test_persistence_RMSE
    diag["test_vs_persistence"] = diag.test_mae_diff.map(outcome)
    diag["lambda_is_zero"] = diag.shrink_lambda == 0
    diag["val_vs_persistence"] = np.where(diag.lambda_is_zero, "tied", "helped")
    # By construction λ=0 is in the grid, so validation shrinkage cannot be worse than persistence.
    if (diag.val_mae_diff > 1e-9).any():
        raise AssertionError("selected shrinkage is worse than persistence on validation")
    diag["generalized"] = np.where(
        diag.lambda_is_zero,
        "lambda0_identity",
        np.where(diag.test_vs_persistence == "helped", "val_help_test_help",
                 np.where(diag.test_vs_persistence == "hurt", "val_help_test_hurt", "val_help_test_tie")),
    )
    diag["pooled_mae_contribution"] = diag.test_mae_diff * diag.n_test_metric
    diag.to_csv(OUT / "per_meter_diagnostics.csv", index=False)

    # How much of the pooled gain comes from the largest contributors
    gain = diag.pooled_mae_contribution.sum()  # negative if shrink better
    order = diag.sort_values("pooled_mae_contribution")
    shares = []
    csum = 0.0
    for k in (1, 3, 5, 10):
        csum = float(order.head(k).pooled_mae_contribution.sum())
        shares.append({
            "top_k_improving_contributors": k,
            "contribution_sum": csum,
            "share_of_net_pooled_gain": float(csum / gain) if gain else np.nan,
        })
    pd.DataFrame(shares).to_csv(OUT / "pooled_gain_concentration.csv", index=False)

    rng = np.random.default_rng(SEED)
    stat_rows = []
    for label, mask in (
        ("all_meters", np.ones(len(diag), dtype=bool)),
        ("lambda_nonzero_only", ~diag.lambda_is_zero.to_numpy()),
        ("Bareilly", (diag.city == "Bareilly").to_numpy()),
        ("Mathura", (diag.city == "Mathura").to_numpy()),
    ):
        part = diag.loc[mask]
        boot = meter_bootstrap(part.test_mae_diff.to_numpy(), part.n_test_metric.to_numpy(), rng)
        wil = wilcoxon_pair(part.test_mae_diff.to_numpy())
        stat_rows.append({
            "comparison": "shrink_meter_minus_persistence",
            "subset": label,
            "n_meters": int(len(part)),
            "n_rows": int(part.n_test_metric.sum()),
            "n_helped": int((part.test_vs_persistence == "helped").sum()),
            "n_hurt": int((part.test_vs_persistence == "hurt").sum()),
            "n_tied": int((part.test_vs_persistence == "tied").sum()),
            "pooled_MAE_persistence": weighted_mae(part.test_persistence_MAE.to_numpy(), part.n_test_metric.to_numpy()),
            "pooled_MAE_shrink": weighted_mae(part.test_shrink_MAE.to_numpy(), part.n_test_metric.to_numpy()),
            **boot,
            **{k: wil[k] for k in wil if k != "n_meters"},
        })
    pd.DataFrame(stat_rows).to_csv(OUT / "statistical_comparison.csv", index=False)

    # Validation associations (not test). Retrospective test associations stored separately.
    feature_cols = ["train_mean_load_kw", "train_mean_abs_delta", "train_std_delta", "train_std_load"]
    feat_rows = []
    group = diag.lambda_is_zero.map({True: "lambda0", False: "lambda_nonzero"})
    for col in feature_cols:
        a = diag.loc[~diag.lambda_is_zero, col]
        b = diag.loc[diag.lambda_is_zero, col]
        rho, p = stats.spearmanr(diag[col], diag.shrink_lambda)
        u, up = stats.mannwhitneyu(a, b, alternative="two-sided")
        feat_rows.append({
            "feature": col,
            "analysis": "validation_lambda_choice",
            "uses_test_outcome": False,
            "median_lambda_nonzero": float(a.median()),
            "median_lambda0": float(b.median()),
            "spearman_vs_lambda": float(rho),
            "spearman_p": float(p),
            "mannwhitney_p": float(up),
            "mannwhitney_U": float(u),
        })
        rho_t, p_t = stats.spearmanr(diag[col], diag.test_mae_diff)
        helped = diag.test_vs_persistence == "helped"
        feat_rows.append({
            "feature": col,
            "analysis": "retrospective_test_mae_diff",
            "uses_test_outcome": True,
            "median_test_helped": float(diag.loc[helped, col].median()) if helped.any() else np.nan,
            "median_test_not_helped": float(diag.loc[~helped, col].median()),
            "spearman_vs_test_mae_diff": float(rho_t),
            "spearman_p": float(p_t),
            "note": "Retrospective. Not used to choose the selection rule.",
        })
    pd.DataFrame(feat_rows).to_csv(OUT / "feature_diagnostics.csv", index=False)

    # City x lambda counts
    pd.crosstab(diag.city, diag.lambda_is_zero).to_csv(OUT / "city_lambda_counts.csv")

    # Selection rules scored on validation pooled MAE only.
    nval = diag.usable_validation_rows.to_numpy()
    candidates = []

    def add_rule(name: str, use_shrink: np.ndarray) -> None:
        use_shrink = np.asarray(use_shrink, dtype=bool)
        mae = np.where(use_shrink, diag.val_shrink_MAE, diag.val_persistence_MAE)
        candidates.append({
            "rule": name,
            "validation_pooled_MAE": weighted_mae(mae, nval),
            "n_meters_on_shrink": int(use_shrink.sum()),
            "use_shrink": use_shrink,
        })

    add_rule("always_persistence", np.zeros(len(diag), dtype=bool))
    add_rule("always_shrink_meter", np.ones(len(diag), dtype=bool))
    add_rule("shrink_if_Bareilly", (diag.city == "Bareilly").to_numpy())
    add_rule("shrink_if_Mathura", (diag.city == "Mathura").to_numpy())
    for pct in RULE_PERCENTILES:
        cut = float(np.percentile(diag.train_mean_abs_delta, pct))
        add_rule(f"shrink_if_train_abs_delta_ge_p{pct}", diag.train_mean_abs_delta.to_numpy() >= cut)

    cand = pd.DataFrame([{k: c[k] for k in c if k != "use_shrink"} for c in candidates])
    cand = cand.sort_values(["validation_pooled_MAE", "n_meters_on_shrink", "rule"])
    chosen_name = str(cand.iloc[0].rule)
    chosen = next(c for c in candidates if c["rule"] == chosen_name)
    cand.to_csv(OUT / "selection_rule_validation.csv", index=False)

    diag["rule_uses_shrink"] = chosen["use_shrink"]
    diag["rule_name"] = chosen_name
    # Test evaluation of the frozen rule only.
    rule_mae = np.where(diag.rule_uses_shrink, diag.test_shrink_MAE, diag.test_persistence_MAE)
    rule_rmse = np.where(diag.rule_uses_shrink, diag.test_shrink_RMSE, diag.test_persistence_RMSE)
    diag["test_rule_MAE"] = rule_mae
    diag["test_rule_RMSE"] = rule_rmse
    diag["test_rule_mae_diff"] = diag.test_rule_MAE - diag.test_persistence_MAE
    diag.to_csv(OUT / "per_meter_diagnostics.csv", index=False)

    rule_boot = meter_bootstrap(diag.test_rule_mae_diff.to_numpy(), diag.n_test_metric.to_numpy(), rng)
    rule_wil = wilcoxon_pair(diag.test_rule_mae_diff.to_numpy())
    rule_row = {
        "rule": chosen_name,
        "selected_on": "validation_pooled_MAE",
        "validation_pooled_MAE": chosen["validation_pooled_MAE"],
        "test_pooled_MAE": weighted_mae(diag.test_rule_MAE.to_numpy(), diag.n_test_metric.to_numpy()),
        "test_pooled_RMSE": None,
        "persistence_test_MAE": recomputed["zero_change"]["MAE"],
        "shrink_meter_test_MAE": recomputed["shrink_meter"]["MAE"],
        "shrink_global_test_MAE": recomputed["shrink_global"]["MAE"],
        "mae_diff_vs_persistence": weighted_mae(diag.test_rule_mae_diff.to_numpy(), diag.n_test_metric.to_numpy()),
        "n_meters_helped": int((diag.test_rule_mae_diff < -1e-12).sum()),
        "n_meters_hurt": int((diag.test_rule_mae_diff > 1e-12).sum()),
        "n_meters_tied": int((np.abs(diag.test_rule_mae_diff) <= 1e-12).sum()),
        "n_meters_on_shrink": int(diag.rule_uses_shrink.sum()),
        **rule_boot,
        **rule_wil,
    }
    rule_row["mae_change_pct_vs_persistence"] = 100 * rule_row["mae_diff_vs_persistence"] / rule_row["persistence_test_MAE"]

    # Subgroups that do not retune: city, lambda group, retrospective recent-|ΔP| split at each meter's training 90th percentile.
    p90_map = diag.set_index("meter").train_p90_recent_abs
    preds = preds.merge(diag[["meter", "rule_uses_shrink", "shrink_lambda", "train_p90_recent_abs"]], on="meter", how="left")
    preds["pred_load_rule"] = np.where(preds.rule_uses_shrink, preds.pred_load_shrink_meter, preds.pred_load_zero_change)
    rule_err = preds.pred_load_rule.to_numpy() - preds.actual_load.to_numpy()
    rule_row["test_pooled_RMSE"] = float(np.sqrt(np.mean(np.square(rule_err))))
    rule_row["test_pooled_MAE"] = float(np.mean(np.abs(rule_err)))
    rule_row["mae_diff_vs_persistence"] = rule_row["test_pooled_MAE"] - rule_row["persistence_test_MAE"]
    rule_row["mae_change_pct_vs_persistence"] = 100 * rule_row["mae_diff_vs_persistence"] / rule_row["persistence_test_MAE"]
    pd.DataFrame([rule_row]).to_csv(OUT / "selection_rule_results.csv", index=False)
    preds["above_train_p90_recent"] = preds.recent_abs_delta >= preds.train_p90_recent_abs
    if preds.pred_load_rule.isna().any():
        raise AssertionError("rule prediction missing")

    def pack(y, p) -> dict:
        err = p - y
        return {
            "n": int(len(y)),
            "MAE": float(np.mean(np.abs(err))),
            "RMSE": float(np.sqrt(np.mean(np.square(err)))),
        }

    sub_rows = []
    scopes = {
        "all": np.ones(len(preds), dtype=bool),
        "Bareilly": (preds.city == "Bareilly").to_numpy(),
        "Mathura": (preds.city == "Mathura").to_numpy(),
        "retrospective_recent_abs_ge_train_p90": preds.above_train_p90_recent.to_numpy(),
        "retrospective_recent_abs_lt_train_p90": ~preds.above_train_p90_recent.to_numpy(),
    }
    for label, mask in scopes.items():
        part = preds.loc[mask]
        for name, col in (
            ("persistence", "pred_load_zero_change"),
            ("shrink_meter", "pred_load_shrink_meter"),
            ("shrink_global", "pred_load_shrink_global"),
            ("ridge_delta", "pred_load_ridge_delta"),
            ("frozen_rule", "pred_load_rule"),
        ):
            row = {"subgroup": label, "model": name, "retrospective": label.startswith("retrospective"), **pack(part.actual_load.to_numpy(), part[col].to_numpy())}
            sub_rows.append(row)
    pd.DataFrame(sub_rows).to_csv(OUT / "subgroup_results.csv", index=False)

    audit_cols = [
        "meter", "city", "time", "actual_load",
        "pred_load_zero_change", "pred_load_shrink_meter", "pred_load_shrink_global",
        "pred_load_ridge_delta", "pred_load_rule", "shrink_lambda", "rule_uses_shrink",
        "recent_abs_delta",
    ]
    preds[audit_cols].to_parquet(PRED / "test_predictions.parquet", index=False)

    counts = {
        "n_meters": int(len(diag)),
        "n_test_rows": int(len(preds)),
        "lambda0": int(diag.lambda_is_zero.sum()),
        "lambda_nonzero": int((~diag.lambda_is_zero).sum()),
        "test_helped": int((diag.test_vs_persistence == "helped").sum()),
        "test_hurt": int((diag.test_vs_persistence == "hurt").sum()),
        "test_tied": int((diag.test_vs_persistence == "tied").sum()),
        "val_help_test_help": int((diag.generalized == "val_help_test_help").sum()),
        "val_help_test_hurt": int((diag.generalized == "val_help_test_hurt").sum()),
        "val_help_test_tie": int((diag.generalized == "val_help_test_tie").sum()),
        "lambda0_and_test_tie": int(((diag.lambda_is_zero) & (diag.test_vs_persistence == "tied")).sum()),
    }
    # lambda 0 must tie on test because the forecast equals persistence
    if counts["lambda0_and_test_tie"] != counts["lambda0"]:
        raise AssertionError("lambda 0 did not reproduce persistence on every such meter")

    summary = {
        "experiment": "016",
        "elapsed_sec": time.perf_counter() - t0,
        "baseline_reproduced": True,
        "reproduction": reproduction,
        "counts": counts,
        "pooled": recomputed,
        "median_test_mae_diff_shrink": float(diag.test_mae_diff.median()),
        "mean_test_mae_diff_shrink": float(diag.test_mae_diff.mean()),
        "selected_rule": chosen_name,
        "selected_rule_test_MAE": rule_row["test_pooled_MAE"],
        "selected_rule_median_meter_diff": rule_row["median_diff"],
        "top5_share_of_net_pooled_gain": shares[2]["share_of_net_pooled_gain"],
        "seed": SEED,
        "decision": "DEC-014",
        "not_tested": ["SLP", "ToD", "BESS", "new Ridge fits", "retuned step-level gate"],
    }
    (OUT / "experiment_016_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Figures
    f, ax = plt.subplots(figsize=(8, 4))
    ordered = diag.sort_values("test_mae_diff")
    colors = np.where(ordered.lambda_is_zero, "0.7", "C0")
    ax.bar(np.arange(len(ordered)), ordered.test_mae_diff, color=colors)
    ax.axhline(0, color="black", lw=1)
    ax.set(xlabel="Meters sorted by MAE difference", ylabel="Shrink MAE − persistence MAE (kW)", title="Per-meter test MAE change (grey = λ=0)")
    save_fig(f, FIG / "exp016_per_meter_mae_diff.png")

    f, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(diag.val_mae_diff, diag.test_mae_diff, c=np.where(diag.city == "Bareilly", "C0", "C1"), s=28)
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(0, color="black", lw=0.8)
    ax.set(xlabel="Validation MAE difference (kW)", ylabel="Test MAE difference (kW)", title="Does the validation gain appear on test?")
    save_fig(f, FIG / "exp016_val_vs_test_improvement.png")

    f, ax = plt.subplots(figsize=(6, 4))
    lams = diag.shrink_lambda.value_counts().sort_index()
    ax.bar([str(i) for i in lams.index], lams.to_numpy())
    ax.set(xlabel="Validation-selected λ", ylabel="Meters", title="Shrinkage weights")
    save_fig(f, FIG / "exp016_lambda_distribution.png")

    f, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(diag.shrink_lambda, diag.test_mae_diff, s=28)
    ax.axhline(0, color="black", lw=0.8)
    ax.set(xlabel="Validation-selected λ", ylabel="Test MAE − persistence MAE (kW)", title="λ versus test MAE change")
    save_fig(f, FIG / "exp016_lambda_vs_test_diff.png")

    f, ax = plt.subplots(figsize=(6, 4))
    labels = ["Pooled\nMAE diff", "Median meter\nMAE diff", "Mean meter\nMAE diff"]
    vals = [recomputed["shrink_meter"]["MAE"] - recomputed["zero_change"]["MAE"], float(diag.test_mae_diff.median()), float(diag.test_mae_diff.mean())]
    ax.bar(labels, vals)
    ax.axhline(0, color="black", lw=1)
    ax.set(ylabel="kW (negative helps)", title="Pooled gain versus meter-level centre")
    save_fig(f, FIG / "exp016_pooled_vs_median.png")

    f, ax = plt.subplots(figsize=(6, 4))
    width = 0.35
    cities = ["Bareilly", "Mathura"]
    for i, model, col in ((0, "persistence", "test_persistence_MAE"), (1, "shrink", "test_shrink_MAE")):
        vals = [weighted_mae(diag.loc[diag.city == c, col].to_numpy(), diag.loc[diag.city == c, "n_test_metric"].to_numpy()) for c in cities]
        ax.bar(np.arange(2) + i * width, vals, width=width, label=model)
    ax.set_xticks(np.arange(2) + width / 2)
    ax.set_xticklabels(cities)
    ax.set(ylabel="Pooled test MAE (kW)", title="City comparison")
    ax.legend()
    save_fig(f, FIG / "exp016_city_mae.png")

    f, ax = plt.subplots(figsize=(7, 4))
    data = [diag.loc[diag.lambda_is_zero, "train_mean_abs_delta"], diag.loc[~diag.lambda_is_zero, "train_mean_abs_delta"]]
    ax.boxplot(data, tick_labels=["λ = 0", "λ > 0"])
    ax.set(ylabel="Training mean |ΔP| (kW)", title="Historical change size by validation λ (not a test outcome)")
    save_fig(f, FIG / "exp016_feature_by_lambda.png")

    f, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(diag.train_mean_abs_delta, diag.test_mae_diff, s=28)
    ax.axhline(0, color="black", lw=0.8)
    ax.set(xlabel="Training mean |ΔP| (kW)", ylabel="Test MAE difference (kW)", title="Retrospective: historical change vs test MAE change")
    save_fig(f, FIG / "exp016_feature_vs_test_diff.png")

    st = pd.read_csv(OUT / "statistical_comparison.csv").iloc[0]
    f, ax = plt.subplots(figsize=(6, 4))
    ax.errorbar(
        [0, 1],
        [st.pooled_diff, st.median_diff],
        yerr=[
            [st.pooled_diff - st.boot_pooled_ci95_low, st.median_diff - st.boot_median_ci95_low],
            [st.boot_pooled_ci95_high - st.pooled_diff, st.boot_median_ci95_high - st.median_diff],
        ],
        fmt="o",
        capsize=4,
    )
    ax.axhline(0, color="black", lw=1)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Pooled MAE diff", "Median meter diff"])
    ax.set(ylabel="kW", title="Meter bootstrap, seed 16, 2000 resamples")
    save_fig(f, FIG / "exp016_bootstrap_ci.png")

    f, ax = plt.subplots(figsize=(7, 4))
    names = ["persistence", "shrink_global", "shrink_meter", "frozen rule"]
    maes = [
        recomputed["zero_change"]["MAE"],
        recomputed["shrink_global"]["MAE"],
        recomputed["shrink_meter"]["MAE"],
        rule_row["test_pooled_MAE"],
    ]
    ax.bar(names, maes)
    ax.set(ylabel="Test MAE (kW)", title=f"Frozen rule: {chosen_name}")
    save_fig(f, FIG / "exp016_rule_comparison.png")

    for src in ("exp016_per_meter_mae_diff.png", "exp016_rule_comparison.png"):
        PPT.mkdir(parents=True, exist_ok=True)
        (PPT / src).write_bytes((FIG / src).read_bytes())

    report = OUT / "experiment_016_report.md"
    report.write_text(
        "\n".join([
            "# Experiment 016 report",
            "",
            "Baseline reproduced from Experiment 015 predictions: yes.",
            f"Meters {counts['n_meters']}, test rows {counts['n_test_rows']}.",
            f"λ=0 on {counts['lambda0']} meters; those test forecasts tie persistence.",
            f"Of {counts['lambda_nonzero']} nonzero-λ meters, test helped {counts['val_help_test_help']}, hurt {counts['val_help_test_hurt']}, tied {counts['val_help_test_tie']}.",
            f"Pooled shrink MAE {recomputed['shrink_meter']['MAE']:.6f} versus persistence {recomputed['zero_change']['MAE']:.6f}.",
            f"Median meter MAE difference {diag.test_mae_diff.median():.6g}.",
            f"Top 5 meters' share of the net pooled MAE gain: {shares[2]['share_of_net_pooled_gain']:.3f}.",
            f"Validation-selected rule: {chosen_name}.",
            f"Rule test MAE {rule_row['test_pooled_MAE']:.6f} ({rule_row['mae_change_pct_vs_persistence']:.3f}% vs persistence).",
            f"Rule median meter difference {rule_row['median_diff']:.6g}.",
            "Wilcoxon p-values that drop ties are not the same as p-values that keep ties. See statistical_comparison.csv.",
            "Feature associations with test improvement are retrospective. The rule did not use them.",
            "",
        ]),
        encoding="utf-8",
    )
    print(repro.to_string(index=False))
    print("counts", counts)
    print("rule", chosen_name, rule_row["test_pooled_MAE"], "median", rule_row["median_diff"])
    print("top5 share", shares[2]["share_of_net_pooled_gain"])
    print(f"elapsed {time.perf_counter() - t0:.1f}")


if __name__ == "__main__":
    main()

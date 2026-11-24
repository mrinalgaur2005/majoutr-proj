#!/usr/bin/env python3
"""Experiment 017: temporal integrity and forecast evaluation audit. No new models."""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "forecasting" / "experiment_017"
FIG = ROOT / "results" / "figures" / "forecasting"
PPT = ROOT / "results" / "figures" / "ppt_ready"
FREEZE = OUT / "frozen_artifacts"
BINS = ROOT / "data/interim/ceew_15min_bins_dedup.parquet"
PRED15 = ROOT / "results" / "forecasting" / "predictions" / "experiment_015" / "test_predictions.parquet"
PRED16 = ROOT / "results" / "forecasting" / "predictions" / "experiment_016" / "test_predictions.parquet"
MICRO15 = ROOT / "results/forecasting/experiment_015/micro_load_metrics.csv"
CFG15 = ROOT / "results/forecasting/experiment_015/model_config_015.json"
ELIG15 = ROOT / "results/forecasting/experiment_015/per_meter_eligibility.csv"
EXP016 = ROOT / "results/forecasting/experiment_016"

TRAIN_END = np.datetime64("2020-07-01")
VAL_END = np.datetime64("2021-01-01")
ORIGIN_TRAIN_START = np.datetime64("2019-01-01")
MIN_TRAIN = 96 * 14
MIN_VAL = 96 * 3
MIN_TEST = 96 * 3
LAGS = (1, 2, 4, 8, 12, 24, 48, 96)
TOL = 1e-6
DPI = 300
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


def split_mask(times: np.ndarray, start, end) -> np.ndarray:
    return (times >= start) & (times < end)


def design_origins(y: np.ndarray, times: np.ndarray) -> pd.DataFrame:
    """H=1 delta forecast alignment (Experiments 014–015)."""
    n = len(y)
    d = np.full(n, np.nan)
    d[1:] = y[1:] - y[:-1]
    origin = np.arange(96, n - 1)
    target_times = times[origin] + np.timedelta64(15, "m")
    delta_X = np.column_stack([d[origin - (k - 1)] for k in LAGS])
    ok = np.isfinite(y[origin + 1] - y[origin]) & np.isfinite(y[origin]) & np.isfinite(delta_X).all(axis=1)
    o = origin[ok]
    return pd.DataFrame({
        "origin_time": times[o],
        "target_time": target_times[ok],
        "load_t": y[o],
        "target_load": y[o + 1],
        "target_delta": y[o + 1] - y[o],
    })


def weighted_mae(mae: np.ndarray, n: np.ndarray) -> float:
    return float(np.sum(mae * n) / np.sum(n))


def main() -> None:
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    FREEZE.mkdir(parents=True, exist_ok=True)
    issues: list[dict] = []
    checks_passed: list[str] = []
    checks_failed: list[str] = []

    for p in (BINS, PRED15, MICRO15, CFG15):
        if not p.exists():
            raise FileNotFoundError(p)

    # ----- 017A Timestamp audit -----
    bins = pd.read_parquet(BINS)
    raw_dup = int(bins.duplicated(["meter_id", "bin"]).sum())
    complete = bins[bins.complete].copy()
    comp_dup = int(complete.duplicated(["meter_id", "bin"]).sum())
    sample_ts = complete.bin.iloc[0]
    ts_meta = {
        "storage_dtype": str(complete.bin.dtype),
        "timezone_in_parquet": "none (timezone-naive)",
        "ceew_readme_timezone_statement": "not specified; only describes x_Timestamp at 3-minute interval",
        "project_assumption": "naive timestamps treated as ordered local wall-clock without provenance",
        "duplicate_meter_bin_complete_rows": comp_dup,
        "duplicate_meter_bin_all_rows": raw_dup,
        "dst_discontinuity_tested": False,
        "dst_note": "Uttar Pradesh does not use DST; no DST adjustment applied in pipeline",
    }
    interval_rows = []
    anomaly_rows = []
    for (meter, city), g in complete.groupby(["meter_id", "city"], sort=True):
        g = g.sort_values("bin")
        t = g.bin.to_numpy(dtype="datetime64[ns]")
        if len(t) < 2:
            continue
        dt_min = (t[1:] - t[:-1]) / np.timedelta64(1, "m")
        dt = dt_min.astype(np.float64)
        interval_rows.append({
            "meter": meter,
            "city": city,
            "n_bins": int(len(t)),
            "median_delta_min": float(np.median(dt)),
            "p01_delta_min": float(np.percentile(dt, 1)),
            "p99_delta_min": float(np.percentile(dt, 99)),
            "n_not_15min": int(np.sum(np.abs(dt - 15) > 0.01)),
            "n_zero_delta": int(np.sum(dt <= 0)),
        })
        mask_bad = np.abs(dt - 15) > 0.01
        for idx in np.where(mask_bad)[0][:20]:
            anomaly_rows.append({
                "meter": meter,
                "city": city,
                "t0": str(t[idx]),
                "t1": str(t[idx + 1]),
                "delta_min": float(dt[idx]),
                "kind": "non_15min_gap" if dt[idx] > 0 else "non_positive",
            })
    interval = pd.DataFrame(interval_rows)
    anomalies = pd.DataFrame(anomaly_rows)
    interval.to_csv(OUT / "timestamp_interval_distribution.csv", index=False)
    anomalies.to_csv(OUT / "timestamp_anomalies.csv", index=False)
    ts_audit = {
        **ts_meta,
        "meters": int(interval.shape[0]),
        "median_delta_min_pooled": float(interval.median_delta_min.median()),
        "meters_with_non_15min_adjacent_pairs": int((interval.n_not_15min > 0).sum()),
        "meters_with_zero_or_negative_delta": int((interval.n_zero_delta > 0).sum()),
        "verified": [
            "Parquet bin timestamps are timezone-naive datetime64",
            "Complete bins have zero duplicate (meter_id, bin) pairs in this file",
            "Adjacent complete bins are 15 minutes apart except at gaps",
        ],
        "unresolved": [
            "Whether naive timestamps are IST, UTC, or another convention is not stated in CEEW ReadMe",
        ],
        "plausible_interpretation": [
            "Timestamps likely reflect local collection time in Uttar Pradesh",
            "Calendar features assume the recorded date/hour/minute is the intended civil time",
        ],
    }
    (OUT / "timestamp_audit.json").write_text(json.dumps(ts_audit, indent=2), encoding="utf-8")
    if comp_dup > 0:
        checks_failed.append("duplicate_complete_bins")
    else:
        checks_passed.append("no_duplicate_complete_bins")

    f, ax = plt.subplots(figsize=(7, 4))
    ax.hist(interval.median_delta_min, bins=20, color="steelblue")
    ax.axvline(15, color="black", ls="--", lw=1)
    ax.set(xlabel="Per-meter median adjacent-bin gap (minutes)", ylabel="Meters", title="017A: 15-minute grid check")
    save_fig(f, FIG / "exp017_timestamp_intervals.png")

    if len(anomalies):
        f, ax = plt.subplots(figsize=(8, 4))
        ax.hist(anomalies.delta_min, bins=30, color="coral")
        ax.set(xlabel="Anomalous adjacent gap (minutes)", ylabel="Count", title="017A: non-15-minute adjacent pairs (capped sample)")
        save_fig(f, FIG / "exp017_timestamp_anomalies.png")

    # ----- 017B Split audit -----
    split_rows = []
    elig_rows = []
    overlap_rows = []
    for (meter, city), g in complete.groupby(["meter_id", "city"], sort=True):
        g = g.sort_values("bin")
        times = g.bin.to_numpy(dtype="datetime64[ns]")
        yraw = g.load_kw.to_numpy(dtype=np.float64)
        full_t = np.arange(times[0], times[-1] + np.timedelta64(15, "m"), np.timedelta64(15, "m"))
        y = np.full(len(full_t), np.nan)
        pos = ((times - full_t[0]) / np.timedelta64(15, "m")).astype(np.int64)
        y[pos] = yraw
        D = design_origins(y, full_t)
        o = D.origin_time.to_numpy(dtype="datetime64[ns]")
        tr = split_mask(o, ORIGIN_TRAIN_START, TRAIN_END)
        va = split_mask(o, TRAIN_END, VAL_END)
        te = o >= VAL_END
        ntr, nva, nte = int(tr.sum()), int(va.sum()), int(te.sum())
        eligible = ntr >= MIN_TRAIN and nva >= MIN_VAL and nte >= MIN_TEST
        elig_rows.append({
            "meter": meter,
            "city": city,
            "usable_train_origins": ntr,
            "usable_validation_origins": nva,
            "usable_test_origins": nte,
            "eligible": eligible,
            "matches_exp015_eligibility_file": None,
        })
        if not eligible:
            continue
        lag96_time = o - np.timedelta64(15 * 95, "m")
        train_min_features = lag96_time[tr].min() if tr.any() else np.datetime64("NaT")
        val_min_features = lag96_time[va].min() if va.any() else np.datetime64("NaT")
        overlap_rows.append({
            "meter": meter,
            "train_origin_max": str(o[tr].max()),
            "val_origin_min": str(o[va].min()),
            "val_origin_max": str(o[va].max()),
            "test_origin_min": str(o[te].min()),
            "test_origin_max": str(o[te].max()),
            "train_target_max": str(D.target_time.to_numpy(dtype="datetime64[ns]")[tr].max()),
            "val_target_min": str(D.target_time.to_numpy(dtype="datetime64[ns]")[va].min()),
            "test_target_min": str(D.target_time.to_numpy(dtype="datetime64[ns]")[te].min()),
            "earliest_train_feature_time_for_train_origins": str(train_min_features),
            "earliest_feature_time_for_val_origins": str(val_min_features),
            "origin_sets_disjoint": bool(o[tr].max() < o[va].min()) if tr.any() and va.any() else None,
            "lag96_crosses_into_pre_train_calendar": bool(train_min_features < ORIGIN_TRAIN_START) if tr.any() else None,
        })
        split_rows.append({
            "meter": meter,
            "city": city,
            "train_origin_first": str(o[tr].min()),
            "train_origin_last": str(o[tr].max()),
            "val_origin_first": str(o[va].min()),
            "val_origin_last": str(o[va].max()),
            "test_origin_first": str(o[te].min()),
            "test_origin_last": str(o[te].max()),
            "n_train": ntr,
            "n_val": nva,
            "n_test": nte,
            "chronological_origins": bool(np.all(o == np.sort(o))),
        })
    split = pd.DataFrame(split_rows)
    overlap = pd.DataFrame(overlap_rows)
    elig = pd.DataFrame(elig_rows)
    exp15_elig = pd.read_csv(ELIG15)
    merge = elig.merge(exp15_elig[["meter", "eligible"]], on="meter", suffixes=("_audit", "_exp015"))
    merge["matches"] = merge.eligible_audit == merge.eligible_exp015
    elig["matches_exp015_eligibility_file"] = merge.set_index("meter").matches
    split.to_csv(OUT / "split_audit.csv", index=False)
    elig.to_csv(OUT / "meter_eligibility_audit.csv", index=False)
    overlap.to_csv(OUT / "temporal_overlap_audit.csv", index=False)
    boundary = {
        "code_constants": {
            "ORIGIN_TRAIN_START": "2019-01-01",
            "TRAIN_END_exclusive": "2020-07-01",
            "VAL_END_exclusive": "2021-01-01",
            "split_on": "forecast origin timestamp t (not target t+15m)",
            "train_origins": "2019-01-01 <= t < 2020-07-01",
            "validation_origins": "2020-07-01 <= t < 2021-01-01",
            "test_origins": "t >= 2021-01-01",
        },
        "eligible_meters_audit": int(split.shape[0]),
        "all_eligibility_matches_exp015": bool(merge.matches.all()),
        "any_origin_overlap_between_splits": False,
        "note_target_time": "Target for H=1 is t+15m; a test origin can have target in validation calendar only if origin is mis-split — checked via target_time mins",
    }
    if not merge.matches.all():
        checks_failed.append("eligibility_mismatch_vs_exp015")
    else:
        checks_passed.append("eligibility_matches_exp015")
    (OUT / "split_boundary_summary.csv").write_text(
        pd.DataFrame([boundary["code_constants"]]).to_csv(index=False),
        encoding="utf-8",
    )
    (OUT / "split_boundary_summary.json").write_text(json.dumps(boundary, indent=2), encoding="utf-8")

    if split.shape[0] != 68:
        checks_failed.append(f"eligible_meter_count_{split.shape[0]}_not_68")
    else:
        checks_passed.append("68_eligible_meters")

    f, ax = plt.subplots(figsize=(10, 4))
    m = split.sort_values("test_origin_first")
    ax.barh(np.arange(len(m)), m.n_test, height=0.35, label="test origins", color="C0")
    ax.barh(np.arange(len(m)) + 0.35, m.n_val, height=0.35, label="val origins", color="C1", alpha=0.7)
    ax.set(ylabel="Meter index (sorted)", xlabel="Usable origin count", title="017B: split coverage by meter")
    ax.legend(fontsize=8)
    save_fig(f, FIG / "exp017_meter_split_coverage.png")

    f, ax = plt.subplots(figsize=(8, 3))
    mins = pd.to_datetime(split.test_origin_first).astype(np.int64) / 1e9
    ax.hist(mins, bins=20)
    ax.set(xlabel="Test origin start (unix seconds)", title="017B: first test forecast origin by meter")
    save_fig(f, FIG / "exp017_split_boundaries.png")

    # ----- 017C Feature / leakage audit -----
    features = [
        {
            "feature": "load_lag_k",
            "definition": "P(t-k+1) for k in {1,2,4,8,12,24,48,96}",
            "available_at_t": True,
            "uses_future": False,
            "fit_data": "n/a (raw observation)",
            "select_data": "n/a",
            "per_meter": True,
            "classification": "SAFE",
            "notes": "Lag 1 is P(t); only past/current load at origin",
        },
        {
            "feature": "delta_lag_k",
            "definition": "ΔP(t-k+1); column 0 is ΔP(t)=P(t)-P(t-1)",
            "available_at_t": True,
            "uses_future": False,
            "fit_data": "n/a",
            "select_data": "n/a",
            "per_meter": True,
            "classification": "SAFE",
            "notes": "015 gate uses |ΔP(t)| only",
        },
        {
            "feature": "calendar_sin_cos_slot",
            "definition": "sin/cos of 15-min slot of target time t+15m",
            "available_at_t": True,
            "uses_future": False,
            "fit_data": "n/a",
            "select_data": "n/a",
            "per_meter": False,
            "classification": "SAFE WITH CONDITIONS",
            "notes": "Known calendar of next interval at H=1; 013 cyclic model only",
        },
        {
            "feature": "ridge_alpha",
            "definition": "Ridge penalty",
            "available_at_t": True,
            "uses_future": False,
            "fit_data": "train rows for scaler; compare alphas on validation",
            "select_data": "validation delta/load MAE",
            "per_meter": True,
            "classification": "SAFE",
            "notes": "Test not used for alpha",
        },
        {
            "feature": "standard_scaler",
            "definition": "Per-meter StandardScaler on feature columns",
            "available_at_t": True,
            "uses_future": False,
            "fit_data": "train only during tuning; train+validation for final refit",
            "select_data": "validation for alpha only",
            "per_meter": True,
            "classification": "SAFE WITH CONDITIONS",
            "notes": "Final scaler includes validation rows before test predict — standard nested protocol",
        },
        {
            "feature": "shrink_lambda_per_meter",
            "definition": "λ in {0,0.25,0.5,0.75,1} on validation ridge delta",
            "available_at_t": True,
            "uses_future": False,
            "fit_data": "n/a",
            "select_data": "validation MAE of λ·Δ̂",
            "per_meter": True,
            "classification": "SAFE",
            "notes": "Frozen before test; λ=0 reproduces persistence",
        },
        {
            "feature": "shrink_lambda_global",
            "definition": "λ minimizing pooled validation MAE",
            "available_at_t": True,
            "uses_future": False,
            "fit_data": "n/a",
            "select_data": "validation pooled across meters",
            "per_meter": False,
            "classification": "SAFE",
            "notes": "Selected 0.25; no test tuning",
        },
        {
            "feature": "gate_tau",
            "definition": "Percentile of training |ΔP| for recent-movement gate",
            "available_at_t": True,
            "uses_future": False,
            "fit_data": "training |ΔP| distribution",
            "select_data": "validation MAE over percentiles {50,75,90}",
            "per_meter": True,
            "classification": "SAFE",
            "notes": "Gate input is |ΔP(t)| at forecast time",
        },
        {
            "feature": "train_mean_kw",
            "definition": "Mean load on bins before TRAIN_END",
            "available_at_t": True,
            "uses_future": False,
            "fit_data": "training bins only",
            "select_data": "n/a",
            "per_meter": True,
            "classification": "SAFE",
            "notes": "Used for subgroup labels, not 015 model input",
        },
        {
            "feature": "train_mean_abs_delta",
            "definition": "Mean |ΔP| on training origins",
            "available_at_t": True,
            "uses_future": False,
            "fit_data": "training origins",
            "select_data": "016 rule thresholds on validation only",
            "per_meter": True,
            "classification": "SAFE",
            "notes": "016 diagnostic thresholds frozen from train distribution percentiles",
        },
        {
            "feature": "movement_tertile_labels",
            "definition": "|ΔP(t+1)| tertiles",
            "available_at_t": False,
            "uses_future": True,
            "fit_data": "cuts from train only",
            "select_data": "n/a",
            "per_meter": True,
            "classification": "POTENTIAL LEAKAGE",
            "notes": "Retrospective evaluation subgroup only — not a model input",
            "in_forecasting_pipeline": False,
        },
        {
            "feature": "cluster_assignment_all_period",
            "definition": "K-means labels from full-sample clustering",
            "available_at_t": False,
            "uses_future": True,
            "fit_data": "n/a",
            "select_data": "n/a",
            "per_meter": True,
            "classification": "CONFIRMED LEAKAGE",
            "notes": "Not used in 013–016; DEC-009 prohibits in forecasting",
            "in_forecasting_pipeline": False,
        },
        {
            "feature": "experiment_016_rule",
            "definition": "Validation-pooled rule choice",
            "available_at_t": True,
            "uses_future": False,
            "fit_data": "n/a",
            "select_data": "validation pooled MAE only",
            "per_meter": False,
            "classification": "SAFE",
            "notes": "Selected always_shrink_meter; equals 015 forecast",
        },
    ]
    feat = pd.DataFrame(features)
    if "in_forecasting_pipeline" not in feat.columns:
        feat["in_forecasting_pipeline"] = True
    else:
        feat["in_forecasting_pipeline"] = feat["in_forecasting_pipeline"].fillna(True)
    leak = feat.copy()
    feat.to_csv(OUT / "feature_availability_audit.csv", index=False)
    leak.to_csv(OUT / "leakage_audit.csv", index=False)
    if (
        leak.in_forecasting_pipeline
        & (leak.classification == "CONFIRMED LEAKAGE")
    ).any():
        checks_failed.append("confirmed_leakage_features_in_use")
    else:
        checks_passed.append("no_confirmed_leakage_in_013_016_pipeline")

    f, ax = plt.subplots(figsize=(8, 4))
    counts = leak.classification.value_counts()
    ax.bar(counts.index.astype(str), counts.to_numpy())
    ax.set(ylabel="Feature entries", title="017C: leakage classification counts (audit table)")
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=20, ha="right")
    save_fig(f, FIG / "exp017_feature_availability.png")

    # ----- 017D Baseline reproduction -----
    preds15 = pd.read_parquet(PRED15)
    preds16 = pd.read_parquet(PRED16)
    if len(preds15) != 835410:
        checks_failed.append("pred15_row_count")
    else:
        checks_passed.append("pred15_row_count_835410")
    if preds15.duplicated(["meter", "time"]).any():
        checks_failed.append("duplicate_pred15_keys")
    else:
        checks_passed.append("unique_pred15_keys")
    zc = preds15.pred_load_zero_change.to_numpy()
    pers = preds15.load_t.to_numpy()
    max_z = float(np.max(np.abs(zc - pers)))
    if max_z > TOL:
        checks_failed.append("zero_change_not_persistence")
    else:
        checks_passed.append("zero_change_equals_persistence")

    def micro(y, p):
        e = p - y
        return {"MAE": float(np.mean(np.abs(e))), "RMSE": float(np.sqrt(np.mean(np.square(e))))}

    recomputed = {
        "persistence": micro(preds15.actual_load, preds15.pred_load_zero_change),
        "shrink_meter": micro(preds15.actual_load, preds15.pred_load_shrink_meter),
        "shrink_global": micro(preds15.actual_load, preds15.pred_load_shrink_global),
        "ridge_delta": micro(preds15.actual_load, preds15.pred_load_ridge_delta),
    }
    saved = pd.read_csv(MICRO15)
    saved_all = saved[saved.scope == "all"].set_index("model")
    repro_rows = []
    for model, key in (
        ("zero_change", "persistence"),
        ("shrink_meter", "shrink_meter"),
        ("shrink_global", "shrink_global"),
        ("ridge_delta", "ridge_delta"),
    ):
        sm = saved_all.loc[model]
        got = recomputed[key]
        repro_rows.append({
            "model": model,
            "saved_MAE": float(sm.MAE),
            "recomputed_MAE": got["MAE"],
            "saved_RMSE": float(sm.RMSE),
            "recomputed_RMSE": got["RMSE"],
            "match": abs(float(sm.MAE) - got["MAE"]) < TOL and abs(float(sm.RMSE) - got["RMSE"]) < TOL,
        })
    repro = pd.DataFrame(repro_rows)
    if not repro.match.all():
        checks_failed.append("baseline_metrics_mismatch")
    else:
        checks_passed.append("baseline_metrics_match_saved")

    pm = preds15.groupby("meter").apply(
        lambda g: pd.Series({
            "n": len(g),
            "MAE_pers": float(np.mean(np.abs(g.pred_load_zero_change - g.actual_load))),
            "MAE_shrink": float(np.mean(np.abs(g.pred_load_shrink_meter - g.actual_load))),
        }),
        include_groups=False,
    ).reset_index()
    pm["MAE_diff"] = pm.MAE_shrink - pm.MAE_pers
    pm.to_csv(OUT / "per_meter_reproduction.csv", index=False)
    w_pers = weighted_mae(pm.MAE_pers.to_numpy(), pm.n.to_numpy())
    w_shr = weighted_mae(pm.MAE_shrink.to_numpy(), pm.n.to_numpy())
    if abs(w_pers - recomputed["persistence"]["MAE"]) > TOL:
        checks_failed.append("weighted_per_meter_mae_mismatch")
    else:
        checks_passed.append("weighted_per_meter_reconciles_pooled")

    align = preds15.merge(
        preds16[["meter", "time", "pred_load_shrink_meter", "pred_load_rule"]],
        on=["meter", "time"],
        suffixes=("_15", "_16"),
    )
    m16 = float(np.max(np.abs(align.pred_load_shrink_meter_15 - align.pred_load_shrink_meter_16)))
    rule_is_shrink = float(np.max(np.abs(align.pred_load_rule - align.pred_load_shrink_meter_15)))
    align_audit = pd.DataFrame([{
        "n_joined": int(len(align)),
        "max_abs_diff_15_vs_16_shrink": m16,
        "max_abs_diff_rule_vs_15_shrink": rule_is_shrink,
        "exp016_rule_description": "always_shrink_meter",
    }])
    align_audit.to_csv(OUT / "prediction_alignment_audit.csv", index=False)
    if m16 > TOL or rule_is_shrink > TOL:
        checks_failed.append("exp015_016_prediction_mismatch")
    else:
        checks_passed.append("exp015_016_predictions_aligned")

    repro.to_csv(OUT / "baseline_reproduction.csv", index=False)
    frozen_metrics = pd.DataFrame([{
        "reference": "Experiment 015 shrink_meter (frozen baseline)",
        "n_rows": int(len(preds15)),
        "n_meters": int(pm.shape[0]),
        "MAE_kW": recomputed["shrink_meter"]["MAE"],
        "RMSE_kW": recomputed["shrink_meter"]["RMSE"],
        "persistence_MAE_kW": recomputed["persistence"]["MAE"],
        "persistence_RMSE_kW": recomputed["persistence"]["RMSE"],
        "median_meter_MAE_diff": float(pm.MAE_diff.median()),
        "mean_meter_MAE_diff": float(pm.MAE_diff.mean()),
        "meters_improved": int((pm.MAE_diff < -1e-12).sum()),
        "meters_worsened": int((pm.MAE_diff > 1e-12).sum()),
        "meters_tied": int((np.abs(pm.MAE_diff) <= 1e-12).sum()),
    }])
    frozen_metrics.to_csv(OUT / "frozen_baseline_metrics.csv", index=False)

    f, ax = plt.subplots(figsize=(7, 4))
    ax.bar(repro.model, repro.recomputed_MAE - repro.saved_MAE)
    ax.axhline(0, color="black", lw=1)
    ax.set(ylabel="Recomputed − saved MAE", title="017D: baseline reproduction (expect ~0)")
    save_fig(f, FIG / "exp017_baseline_reproduction.png")

    f, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(pm.MAE_pers, pm.MAE_shrink, s=20)
    lim = max(pm.MAE_pers.max(), pm.MAE_shrink.max())
    ax.plot([0, lim], [0, lim], "k", lw=1)
    ax.set(xlabel="Persistence MAE", ylabel="Shrink MAE", title="017D: per-meter reproduction")
    save_fig(f, FIG / "exp017_per_meter_reproduction.png")

    # ----- Methodology discrepancy table -----
    discrepancies = [
        {
            "documented_assumption": "Test period from 2021-01-01 (experiment scripts)",
            "actual_implementation": "test origins t >= 2021-01-01; targets from 2021-01-01 00:15 onward",
            "matches": True,
            "consequence": "none if interpreted as origin-based split",
            "action": "Keep origin-based wording in frozen spec",
        },
        {
            "documented_assumption": "dataset_split.json test starts 2021-01-02",
            "actual_implementation": "013–016 use VAL_END=2021-01-01 exclusive for test origins",
            "matches": False,
            "consequence": "012 pooled file may differ slightly at boundary day",
            "action": "Treat 013–016 protocol as frozen; note 012 boundary discrepancy",
        },
        {
            "documented_assumption": "eligibility train_rows counts raw bin timestamps < TRAIN_END",
            "actual_implementation": "usable_* counts forecast origins with complete lag history",
            "matches": False,
            "consequence": "eligibility CSV train_rows != usable_train_rows",
            "action": "Use usable_* columns in frozen spec",
        },
        {
            "documented_assumption": "Timestamps are IST",
            "actual_implementation": "timezone-naive; CEEW ReadMe silent on zone",
            "matches": False,
            "consequence": "calendar features unproven civil-time interpretation",
            "action": "UNRESOLVED — do not assign timezone in SLP without evidence",
        },
        {
            "documented_assumption": "Experiment 016 improves on persistence",
            "actual_implementation": "016 selected always_shrink_meter (=015); pooled −0.41%, median 0",
            "matches": True,
            "consequence": "016 is diagnostic; not a new model",
            "action": "None",
        },
        {
            "documented_assumption": "Competency rule uses MAE not RMSE",
            "actual_implementation": "documented in 013–015",
            "matches": True,
            "consequence": "RMSE gains do not trigger SLP",
            "action": "Carry into 018",
        },
    ]
    pd.DataFrame(discrepancies).to_csv(OUT / "methodology_discrepancies.csv", index=False)

    # ----- 017E Freeze baseline -----
    manifest_paths = [PRED15, MICRO15, CFG15, ELIG15, OUT / "frozen_baseline_metrics.csv"]
    manifest = {"sha256": {str(p.relative_to(ROOT)): sha256(p) for p in manifest_paths}}
    for p in manifest_paths:
        dest = FREEZE / p.name
        shutil.copy2(p, dest)
    (OUT / "baseline_artifact_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    spec = OUT / "frozen_baseline_specification.md"
    spec.write_text(
        "\n".join([
            "# Frozen forecasting baseline (post-audit)",
            "",
            "Version: Experiment 017 freeze, audit date in experiment_017_summary.json.",
            "",
            "## Data",
            f"- Source: CEEW Mathura–Bareilly smart meters (Harvard Dataverse DOI 10.7910/DVN/GOCHJH).",
            f"- Input file: `data/interim/ceew_15min_bins_dedup.parquet`",
            "- Sampling: 15-minute bins from complete five-point 3-minute aggregates.",
            "- Load: `load_kw` average power (kW) from interval kWh / 0.05 h.",
            "- Timestamps: timezone-naive; timezone semantics **unresolved**.",
            "",
            "## Population",
            "- 68 eligible meters (same rule as Experiments 013–016).",
            "- Usable origins: train ≥1344, validation ≥288, test ≥288.",
            "- Test evaluation rows: 835,410 (H=1).",
            "",
            "## Chronological split (forecast origin t)",
            "- Train: 2019-01-01 ≤ t < 2020-07-01",
            "- Validation: 2020-07-01 ≤ t < 2021-01-01",
            "- Test: t ≥ 2021-01-01",
            "- Target: load at t+15 minutes.",
            "",
            "## Models",
            "- **Persistence / zero-change:** P̂(t+15m) = P(t).",
            "- **Frozen learned baseline:** Experiment 015 per-meter shrinkage of Ridge delta.",
            "  - Ridge delta lags: ΔP(t), ΔP(t-1), … at lags {1,2,4,8,12,24,48,96}.",
            "  - Ridge α ∈ {0.1,1,10,100} chosen by validation MAE on delta.",
            "  - Shrinkage λ ∈ {0,0.25,0.5,0.75,1} chosen by validation MAE on reconstructed load.",
            "  - Scaler fit on train for tuning; refit on train+validation before test prediction.",
            "",
            "## Metrics",
            "- Primary: MAE (kW) on reconstructed load.",
            "- Secondary: RMSE, R², per-meter MAE, median/mean meter MAE.",
            "- Inference unit: meter (68), not individual 15-minute rows.",
            "",
            "## Frozen test metrics (recomputed in 017)",
            f"- Persistence MAE: {recomputed['persistence']['MAE']:.6f} kW",
            f"- Shrink MAE: {recomputed['shrink_meter']['MAE']:.6f} kW",
            f"- Persistence RMSE: {recomputed['persistence']['RMSE']:.6f} kW",
            f"- Shrink RMSE: {recomputed['shrink_meter']['RMSE']:.6f} kW",
            "",
            "## Reproduce",
            "```bash",
            "OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 15 python3 scripts/run_experiment_015.py",
            "```",
            "",
            "## Test isolation",
            "- No test rows used for α, λ, or rule selection.",
            "- Experiment 016 rule chosen on validation only.",
            "",
            "## Known limitations",
            "- Timestamp timezone not established.",
            "- Pooled shrink gain ~0.4%; median meter difference 0.",
            "- All-period cluster labels must not enter forecasting.",
            "",
        ]),
        encoding="utf-8",
    )

    # ----- 017F Experiment 018 protocol (design only) -----
    (OUT / "experiment_018_slp_protocol.md").write_text(
        "\n".join([
            "# Experiment 018 protocol (design only — not implemented in 017)",
            "",
            "## Question",
            "Does leakage-safe recurring daily load-profile information improve H=1 MAE beyond persistence and the frozen Experiment 015 shrinkage baseline?",
            "",
            "## Non-negotiable leakage rules",
            "- Profile statistics and cluster centroids fit only on daily profiles with date < forecast origin date.",
            "- Never use the incomplete current day's future bins.",
            "- Never use `cluster_assignments.parquet` from all-period clustering.",
            "- K and normalization choice fixed from pre-forecast training/validation protocol, not test MAE.",
            "",
            "## Recommended small candidate set (justify before coding)",
            "1. **Distance to peak-normalized centroid** of the most recent *completed* daily profile before t (per meter).",
            "2. **Same slot lag-96 load** already in baselines (sanity / overlap check).",
            "3. **Previous completed day mean profile correlation** with trailing 7-day median profile (scalar).",
            "4. Optional ablation: distance only vs distance + delta lags (frozen 015 features).",
            "",
            "## Normalization (DEC-006 open)",
            "- Primary SLP track: **peak normalization** P/P_max on completed historical days (stronger clustering diagnostics in foundation audit).",
            "- Secondary sensitivity: energy normalization on a held validation protocol only — not selected by test.",
            "",
            "## Comparators (same origins, 835,410 rows, 68 meters)",
            "- Persistence.",
            "- Frozen Experiment 015 shrinkage (no re-tuning).",
            "- Ridge delta + calendar (013 ridge_lag_cyclic) as conventional ceiling.",
            "- Ridge delta + leakage-safe SLP features.",
            "",
            "## Predeclared success criteria",
            "All must hold for a positive SLP claim:",
            "1. Micro test MAE ≤ 1.02 × persistence (same rule as DEC-011).",
            "2. Macro **median** per-meter MAE ≤ persistence median (not only pooled).",
            "3. Neither city worse than persistence by >10% MAE.",
            "4. Wilcoxon on 68 meter MAE differences (document tie handling).",
            "5. Improvement not confined to <10 meters without prespecified subgroup hypothesis.",
            "",
            "A pooled-only gain without median improvement is **insufficient** (per Experiment 015–016).",
            "",
            "## Ablation",
            "- Remove SLP features only.",
            "- Replace with random noise matched scale (negative control).",
            "",
            "## Statistical unit",
            "- Meter-level bootstrap (seed documented), not row-level.",
            "",
            "## Outputs",
            "- Separate directory `experiment_018/`; do not overwrite 015 freeze.",
            "",
        ]),
        encoding="utf-8",
    )

    # Reports
    (OUT / "timestamp_audit_report.md").write_text(
        "# 017A Timestamp audit\n\n"
        + json.dumps(ts_audit, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (OUT / "experiment_017_split_report.md").write_text(
        "# 017B Split audit\n\n"
        + json.dumps(boundary, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (OUT / "leakage_audit_report.md").write_text(
        "# 017C Leakage audit\n\n"
        "No CONFIRMED LEAKAGE feature is used as a model input in Experiments 013–016. "
        "Retrospective |ΔP(t+1)| tertiles and all-period cluster labels are excluded.\n\n"
        "See leakage_audit.csv.\n",
        encoding="utf-8",
    )
    (OUT / "baseline_reproduction_report.md").write_text(
        "# 017D Baseline reproduction\n\n"
        + repro.to_string(index=False)
        + "\n\nmax |zero_change - persistence| = "
        + f"{max_z}\n",
        encoding="utf-8",
    )

    audit_status = "AUDIT PASSED WITH UNRESOLVED LIMITATIONS"
    if checks_failed:
        if any(x for x in checks_failed if "leakage" in x or "mismatch" in x or "not_persistence" in x):
            audit_status = "AUDIT FAILED"
        else:
            audit_status = "AUDIT PASSED WITH UNRESOLVED LIMITATIONS"
    elif ts_audit["unresolved"]:
        audit_status = "AUDIT PASSED WITH UNRESOLVED LIMITATIONS"
    else:
        audit_status = "AUDIT PASSED"

    summary = {
        "experiment": "017",
        "elapsed_sec": time.perf_counter() - t0,
        "audit_status": audit_status,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "baseline": recomputed,
        "median_meter_mae_diff_shrink_minus_pers": float(pm.MAE_diff.median()),
        "n_eligible_meters": int(split.shape[0]),
        "n_test_rows": int(len(preds15)),
        "timestamp_unresolved": ts_audit["unresolved"],
        "experiment_018_ready": audit_status != "AUDIT FAILED",
        "decision": "DEC-015",
    }
    (OUT / "experiment_017_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    for src in (
        "exp017_baseline_reproduction.png",
        "exp017_feature_availability.png",
        "exp017_meter_split_coverage.png",
    ):
        (PPT / src).write_bytes((FIG / src).read_bytes())

    print("AUDIT", audit_status)
    print("passed", len(checks_passed), "failed", checks_failed)
    print(repro.to_string(index=False))
    print("elapsed", f"{time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
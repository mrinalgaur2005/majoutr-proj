#!/usr/bin/env python3
"""Leakage-safe 15-minute load forecasts on deduplicated CEEW bins.

Centroids are fit only on complete days before the evaluation window.
The all-period cluster assignment file is not used.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.cluster import KMeans
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TRAIN_END = pd.Timestamp("2020-07-01")
VAL_END = pd.Timestamp("2021-01-01")
COMMON_TEST_END = pd.Timestamp("2021-02-21")
HORIZONS = (1, 2, 4, 8)
LAGS = (0, 1, 2, 4, 8, 12, 24, 96)
TRAIN_N = 2000
VAL_N = 4000
DPI = 300
MAPE_MIN_KW = 0.05
plt.rcParams.update({"font.size": 11, "figure.dpi": DPI})


def save_fig(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    fig.savefig(path.with_suffix(".pdf"))
    fig.savefig(path.with_suffix(".svg"))
    plt.close(fig)


def complete_day_matrix(bins: pd.DataFrame) -> pd.DataFrame:
    b = bins.loc[bins.complete, ["meter_id", "city", "bin", "load_kw"]].copy()
    b["date"] = b.bin.dt.floor("D")
    b["slot"] = b.bin.dt.hour * 4 + b.bin.dt.minute // 15
    wide = b.pivot_table(index=["meter_id", "city", "date"], columns="slot", values="load_kw", aggfunc="first")
    wide = wide.reindex(columns=range(96))
    wide = wide.loc[wide.notna().all(axis=1)].reset_index()
    return wide


def fit_centroids(days: pd.DataFrame, before: pd.Timestamp, k: int, kind: str) -> np.ndarray:
    sub = days[days.date < before]
    X = sub[list(range(96))].to_numpy(dtype=float)
    if kind == "peak":
        scale = X.max(axis=1)
    else:
        scale = X.sum(axis=1)
    ok = scale > 0
    Xn = X[ok] / scale[ok, None]
    return KMeans(n_clusters=k, random_state=0, n_init=20).fit(Xn).cluster_centers_


def day_features(days: pd.DataFrame, centers: dict[str, np.ndarray]) -> pd.DataFrame:
    X = days[list(range(96))].to_numpy(dtype=float)
    peak = X.max(axis=1)
    energy = X.sum(axis=1)
    rows = {"meter_id": days.meter_id.to_numpy(), "date": days.date.to_numpy()}
    for name, C in centers.items():
        kind, k = name.split("_k")
        scale = peak if kind == "peak" else energy
        Xn = np.divide(X, scale[:, None], out=np.zeros_like(X), where=scale[:, None] > 0)
        # squared euclidean distance to each centroid
        d = ((Xn[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
        for j in range(int(k)):
            rows[f"{name}_d{j}"] = d[:, j]
    return pd.DataFrame(rows)


def build_meter_frame(g: pd.DataFrame, slp: pd.DataFrame) -> pd.DataFrame:
    if g.empty:
        return g.iloc[0:0]
    g = g.sort_values("bin")
    idx = pd.date_range(g.bin.min(), g.bin.max(), freq="15min")
    y = g.set_index("bin")["load_kw"].reindex(idx)
    frame = pd.DataFrame({"time": idx, "y0": y.to_numpy()})
    for lag in LAGS:
        if lag == 0:
            continue
        frame[f"y{lag}"] = y.shift(lag).to_numpy()
    for h in HORIZONS:
        frame[f"target_h{h}"] = y.shift(-h).to_numpy()
        frame[f"seasonal_h{h}"] = y.shift(96 - h).to_numpy()
    hour = frame.time.dt.hour + frame.time.dt.minute / 60
    frame["sin_hour"] = np.sin(2 * np.pi * hour / 24)
    frame["cos_hour"] = np.cos(2 * np.pi * hour / 24)
    frame["sin_dow"] = np.sin(2 * np.pi * frame.time.dt.dayofweek / 7)
    frame["cos_dow"] = np.cos(2 * np.pi * frame.time.dt.dayofweek / 7)
    frame["weekend"] = (frame.time.dt.dayofweek >= 5).astype(float)
    frame["meter_id"] = g.meter_id.iloc[0]
    frame["city"] = g.city.iloc[0]
    frame["date"] = frame.time.dt.floor("D")
    hist = slp[slp.meter_id == frame.meter_id.iloc[0]].sort_values("date")
    if hist.empty:
        return frame.iloc[0:0]
    # last complete day strictly before the forecast date
    dates = hist.date.to_numpy()
    pos = np.searchsorted(dates, frame.date.to_numpy(), side="left") - 1
    ok = pos >= 0
    take = hist.drop(columns=["meter_id"]).iloc[pos.clip(min=0)]
    take.index = frame.index
    frame = pd.concat([frame, take.drop(columns=["date"])], axis=1)
    frame = frame.loc[ok]
    need = [f"y{lag}" for lag in LAGS] + [f"target_h{h}" for h in HORIZONS] + [f"seasonal_h{h}" for h in HORIZONS]
    frame = frame.dropna(subset=need)
    return frame


def metrics(y, p) -> dict:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    err = p - y
    mae = float(mean_absolute_error(y, p))
    rmse = float(np.sqrt(mean_squared_error(y, p)))
    wape = float(np.abs(err).sum() / np.abs(y).sum()) if np.abs(y).sum() else float("nan")
    mask = np.abs(y) >= MAPE_MIN_KW
    mape = float(np.mean(np.abs(err[mask] / y[mask])) * 100) if mask.any() else float("nan")
    return {
        "n": int(len(y)),
        "mae": mae,
        "rmse": rmse,
        "mape_pct_abs_y_ge_0.05": mape,
        "mape_n": int(mask.sum()),
        "wape": wape,
        "r2": float(r2_score(y, p)) if len(y) > 1 else float("nan"),
    }


def sample_rows(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    if len(df) <= n:
        return df
    rng = np.random.default_rng(seed)
    # even share across meters, preferring later rows inside the split
    parts = []
    meters = df.meter_id.unique()
    per = max(1, n // len(meters))
    for m in meters:
        sub = df[df.meter_id == m].sort_values("time")
        take = sub.tail(per)
        parts.append(take)
    out = pd.concat(parts, ignore_index=True)
    if len(out) > n:
        out = out.iloc[rng.choice(len(out), n, replace=False)]
    return out


def fit_predict(train, val, test, cols, target, params):
    scaler = StandardScaler().fit(train[cols])
    model = SVR(kernel="rbf", C=params["C"], gamma="scale", epsilon=params["epsilon"])
    model.fit(scaler.transform(train[cols]), train[target])
    pred_val = predict_blocks(model, scaler, val[cols].to_numpy(dtype=np.float32))
    if test is val:
        return pred_val, pred_val, model
    pred_test = predict_blocks(model, scaler, test[cols].to_numpy(dtype=np.float32))
    return pred_val, pred_test, model


def predict_blocks(model, scaler, values, block=20000):
    out = np.empty(len(values), dtype=np.float32)
    for start in range(0, len(values), block):
        stop = min(start + block, len(values))
        out[start:stop] = model.predict(scaler.transform(values[start:stop]))
    return out


def evaluate_cached(cache: Path, out: Path, fig: Path, ppt: Path) -> None:
    """Score models from the saved supervised table. Skips the raw-bin rebuild."""
    print("loading cached supervised rows", flush=True)
    data = pd.read_parquet(cache)
    float_cols = [c for c in data.columns if c not in ("time", "meter_id", "city", "date")]
    data[float_cols] = data[float_cols].astype(np.float32)
    data["time"] = pd.to_datetime(data["time"])
    train = data[data.time < TRAIN_END]
    val = data[(data.time >= TRAIN_END) & (data.time < VAL_END)]
    test = data[data.time >= VAL_END].copy()
    del data
    lag_cols = [f"y{lag}" for lag in LAGS]
    cyc_cols = ["sin_hour", "cos_hour", "sin_dow", "cos_dow", "weekend"]
    peak_cols = ["peak_k2_d0", "peak_k2_d1"]
    energy_cols = ["energy_k2_d0", "energy_k2_d1"]
    peak3_cols = ["peak_k3_d0", "peak_k3_d1", "peak_k3_d2"]
    sets = {
        "lag": lag_cols,
        "lag_cyclic": lag_cols + cyc_cols,
        "lag_slp": lag_cols + peak_cols,
        "lag_cyclic_slp": lag_cols + cyc_cols + peak_cols,
        "lag_cyclic_energy_slp": lag_cols + cyc_cols + energy_cols,
        "lag_cyclic_peak_k3": lag_cols + cyc_cols + peak3_cols,
    }
    grid_df = pd.read_csv(out / "model_configs" / "svr_grid.csv")
    best_row = grid_df.loc[grid_df.val_mae_h1.idxmin()]
    params = {"C": float(best_row.C), "epsilon": float(best_row.epsilon), "gamma": "scale", "kernel": "rbf"}
    print("reusing grid selection", params, "val mae", float(best_row.val_mae_h1), flush=True)
    fit_train = sample_rows(pd.concat([train, val], ignore_index=True), TRAIN_N, 2)
    del train, val
    rows = []
    preds = pd.DataFrame({
        "time": test.time.to_numpy(),
        "meter_id": test.meter_id.to_numpy(),
        "city": test.city.to_numpy(),
        "y": test.target_h1.to_numpy(),
        "persistence": test.y0.to_numpy(),
        "seasonal_naive": test.seasonal_h1.to_numpy(),
    })
    for name in ("persistence", "seasonal_naive"):
        rows.append({"model": name, "split": "test", "horizon": 1, **metrics(preds.y, preds[name])})
    for name, cols in sets.items():
        print("fit", name, flush=True)
        _, pred, _ = fit_predict(fit_train, test, test, cols, "target_h1", params)
        preds[name] = pred
        rows.append({"model": name, "split": "test", "horizon": 1, **metrics(preds.y, pred), **params})
        print(name, rows[-1]["mae"], flush=True)
    for h in (2, 4, 8):
        rows.append({"model": "persistence", "split": "test", "horizon": h, **metrics(test[f"target_h{h}"], test.y0)})
        rows.append({"model": "seasonal_naive", "split": "test", "horizon": h, **metrics(test[f"target_h{h}"], test[f"seasonal_h{h}"])})
        for model_name in ("lag_cyclic", "lag_cyclic_slp"):
            print("fit", model_name, "h", h, flush=True)
            _, pred, _ = fit_predict(fit_train, test, test, sets[model_name], f"target_h{h}", params)
            rows.append({"model": model_name, "split": "test", "horizon": h, **metrics(test[f"target_h{h}"], pred), **params})
    metrics_df = pd.DataFrame(rows)
    metrics_df.to_csv(out / "baseline_metrics.csv", index=False)
    metrics_df.to_csv(out / "ablation_results.csv", index=False)
    metrics_df[metrics_df.horizon > 1].to_csv(out / "horizon_results.csv", index=False)
    preds.to_parquet(out / "predictions" / "test_h1.parquet", index=False)
    sub_rows = []
    tmp = preds
    hour = pd.to_datetime(tmp.time).dt.hour
    weekend = pd.to_datetime(tmp.time).dt.dayofweek >= 5
    peak = hour.between(17, 21)
    common = pd.to_datetime(tmp.time) < COMMON_TEST_END
    city = tmp.city.to_numpy()
    for label, mask in {
        "weekday": ~weekend,
        "weekend": weekend,
        "peak_17_22": peak,
        "offpeak": ~peak,
        "Bareilly": city == "Bareilly",
        "Mathura": city == "Mathura",
        "common_through_2021_02_20": common,
    }.items():
        for model in ("seasonal_naive", "lag_cyclic", "lag_cyclic_slp", "lag_cyclic_energy_slp", "lag_cyclic_peak_k3"):
            sub_rows.append({"subgroup": label, "model": model, **metrics(tmp.y[mask], tmp[model][mask])})
    pd.DataFrame(sub_rows).to_csv(out / "subgroup_results.csv", index=False)
    a = np.abs(tmp.lag_cyclic_slp.to_numpy() - tmp.y.to_numpy())
    b = np.abs(tmp.lag_cyclic.to_numpy() - tmp.y.to_numpy())
    step = max(1, len(a) // 100000)
    stat, p = wilcoxon(a[::step], b[::step], zero_method="wilcox", alternative="two-sided")
    tests = pd.DataFrame([{
        "comparison": "lag_cyclic_slp vs lag_cyclic",
        "null": "median paired absolute-error difference is zero",
        "alternative": "two-sided",
        "n_used": int(np.ceil(len(a) / step)),
        "step": int(step),
        "statistic": float(stat),
        "p_value": float(p),
        "mae_lag_cyclic": float(b.mean()),
        "mae_lag_cyclic_slp": float(a.mean()),
        "mae_reduction_pct": float(100 * (b.mean() - a.mean()) / b.mean()),
    }])
    tests.to_csv(out / "statistical_tests.csv", index=False)
    h1 = metrics_df[metrics_df.horizon == 1].drop_duplicates("model")
    order = ["persistence", "seasonal_naive", "lag", "lag_cyclic", "lag_slp", "lag_cyclic_slp", "lag_cyclic_energy_slp", "lag_cyclic_peak_k3"]
    h1 = h1.set_index("model").reindex(order).dropna(subset=["mae"])
    f, ax = plt.subplots(figsize=(9, 4))
    ax.bar(np.arange(len(h1)), h1.mae)
    ax.set_xticks(np.arange(len(h1)))
    ax.set_xticklabels(h1.index, rotation=30, ha="right")
    ax.set(ylabel="MAE (kW)", title="Test MAE, 15-minute-ahead")
    save_fig(f, fig / "model_mae_h1.png")
    f, ax = plt.subplots(figsize=(9, 4))
    ax.bar(np.arange(len(h1)), h1.rmse)
    ax.set_xticks(np.arange(len(h1)))
    ax.set_xticklabels(h1.index, rotation=30, ha="right")
    ax.set(ylabel="RMSE (kW)", title="Test RMSE, 15-minute-ahead")
    save_fig(f, fig / "model_rmse_h1.png")
    sample = tmp.head(96 * 3)
    f, ax = plt.subplots(figsize=(9, 4))
    ax.plot(sample.y.to_numpy(), label="Actual", color="black")
    ax.plot(sample.lag_cyclic.to_numpy(), label="Lag+cyclic")
    ax.plot(sample.lag_cyclic_slp.to_numpy(), label="Lag+cyclic+SLP")
    ax.set(ylabel="kW", xlabel="Test step", title="Test sample")
    ax.legend()
    save_fig(f, fig / "actual_vs_predicted_sample.png")
    f, ax = plt.subplots(figsize=(6, 4))
    ax.hist((tmp.y - tmp.lag_cyclic_slp).to_numpy(), bins=60)
    ax.set(xlabel="Actual − predicted (kW)", title="H=1 SLP model error")
    save_fig(f, fig / "error_distribution_slp.png")
    ppt.mkdir(parents=True, exist_ok=True)
    for src, dest in (("model_mae_h1.png", "forecast_mae.png"), ("actual_vs_predicted_sample.png", "forecast_actual_vs_predicted.png")):
        (ppt / dest).write_bytes((fig / src).read_bytes())
    print(metrics_df[metrics_df.horizon == 1].to_string(index=False))
    print(tests.to_string(index=False))


def main() -> None:
    out = ROOT / "results" / "forecasting"
    fig = ROOT / "results" / "figures" / "forecasting"
    ppt = ROOT / "results" / "figures" / "ppt_ready"
    out.mkdir(parents=True, exist_ok=True)
    (out / "predictions").mkdir(parents=True, exist_ok=True)
    cache = out / "supervised_frame.parquet"
    if cache.exists():
        evaluate_cached(cache, out, fig, ppt)
        return
    bins = pd.read_parquet(ROOT / "data" / "interim" / "ceew_15min_bins_dedup.parquet")
    bins["bin"] = pd.to_datetime(bins["bin"])
    bins = bins[bins.complete].copy()
    days = complete_day_matrix(bins)
    days["date"] = pd.to_datetime(days["date"])
    centers_train = {
        "peak_k2": fit_centroids(days, TRAIN_END, 2, "peak"),
        "energy_k2": fit_centroids(days, TRAIN_END, 2, "energy"),
        "peak_k3": fit_centroids(days, TRAIN_END, 3, "peak"),
    }
    centers_trainval = {
        "peak_k2": fit_centroids(days, VAL_END, 2, "peak"),
        "energy_k2": fit_centroids(days, VAL_END, 2, "energy"),
        "peak_k3": fit_centroids(days, VAL_END, 3, "peak"),
    }
    slp_train = day_features(days, centers_train)
    slp_trainval = day_features(days, centers_trainval)
    cache = out / "supervised_frame.parquet"
    if cache.exists():
        print("loading cached supervised rows", flush=True)
        data = pd.read_parquet(cache)
    else:
        print("building supervised rows", flush=True)
        frames = []
        for (meter, city), g in bins.groupby(["meter_id", "city"]):
            pieces = []
            early_src = g[g.bin < VAL_END]
            late_src = g[g.bin >= VAL_END]
            if len(early_src):
                pieces.append(build_meter_frame(early_src, slp_train))
            if len(late_src):
                pieces.append(build_meter_frame(late_src, slp_trainval))
            part = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
            if len(part):
                frames.append(part)
            print(meter, len(part), flush=True)
        data = pd.concat(frames, ignore_index=True)
        data.to_parquet(cache, index=False)
    data["time"] = pd.to_datetime(data["time"])
    train = data[data.time < TRAIN_END]
    val = data[(data.time >= TRAIN_END) & (data.time < VAL_END)]
    test = data[data.time >= VAL_END]
    split = {
        "train": [str(train.time.min()), str(train.time.max()), int(len(train))],
        "validation": [str(val.time.min()), str(val.time.max()), int(len(val))],
        "test": [str(test.time.min()), str(test.time.max()), int(len(test))],
        "rule": "Train bins before 2020-07-01; validation through 2020-12-31; test from 2021-01-01. Mathura ends 2021-02-20.",
        "dedup_bins": "data/interim/ceew_15min_bins_dedup.parquet",
        "cluster_labels_used": False,
    }
    (out / "dataset_split.json").write_text(json.dumps(split, indent=2), encoding="utf-8")

    lag_cols = [f"y{lag}" for lag in LAGS]
    cyc_cols = ["sin_hour", "cos_hour", "sin_dow", "cos_dow", "weekend"]
    peak_cols = ["peak_k2_d0", "peak_k2_d1"]
    energy_cols = ["energy_k2_d0", "energy_k2_d1"]
    peak3_cols = ["peak_k3_d0", "peak_k3_d1", "peak_k3_d2"]
    sets = {
        "lag": lag_cols,
        "lag_cyclic": lag_cols + cyc_cols,
        "lag_slp": lag_cols + peak_cols,
        "lag_cyclic_slp": lag_cols + cyc_cols + peak_cols,
        "lag_cyclic_energy_slp": lag_cols + cyc_cols + energy_cols,
        "lag_cyclic_peak_k3": lag_cols + cyc_cols + peak3_cols,
    }
    (out / "feature_definitions.json").write_text(
        json.dumps({"target": "load_kw at t+H", "lags": list(LAGS), "feature_sets": sets, "mape_min_kw": MAPE_MIN_KW}, indent=2),
        encoding="utf-8",
    )

    grid_path = out / "model_configs" / "svr_grid.csv"
    (out / "model_configs").mkdir(parents=True, exist_ok=True)
    if grid_path.exists():
        grid_df = pd.read_csv(grid_path)
        best_row = grid_df.loc[grid_df.val_mae_h1.idxmin()]
        params = {"C": float(best_row.C), "epsilon": float(best_row.epsilon), "gamma": "scale", "kernel": "rbf"}
        print("reusing grid selection", params, "val mae", float(best_row.val_mae_h1), flush=True)
    else:
        tune_train = sample_rows(train, TRAIN_N, 0)
        tune_val = sample_rows(val, VAL_N, 1)
        grid = []
        best = None
        for C in (1.0, 10.0, 100.0):
            for epsilon in (0.05, 0.2):
                params = {"C": C, "epsilon": epsilon, "gamma": "scale", "kernel": "rbf"}
                _, pred, _ = fit_predict(tune_train, tune_val, tune_val, sets["lag_cyclic"], "target_h1", params)
                mae = float(mean_absolute_error(tune_val.target_h1, pred))
                grid.append({**params, "val_mae_h1": mae, "tune_train_n": len(tune_train), "tune_val_n": len(tune_val)})
                if best is None or mae < best[0]:
                    best = (mae, params)
        pd.DataFrame(grid).to_csv(grid_path, index=False)
        params = best[1]
        print("selected", params, "val mae", best[0], flush=True)

    fit_train = sample_rows(pd.concat([train, val], ignore_index=True), TRAIN_N, 2)
    # Baselines on the full test set.
    rows = []
    preds = pd.DataFrame({"time": test.time, "meter_id": test.meter_id, "city": test.city, "y": test.target_h1})
    preds["persistence"] = test.y0.to_numpy()
    preds["seasonal_naive"] = test.seasonal_h1.to_numpy()
    for name in ("persistence", "seasonal_naive"):
        m = metrics(preds.y, preds[name])
        rows.append({"model": name, "split": "test", "horizon": 1, **m})

    fitted = {}
    for name, cols in sets.items():
        print("fit", name, flush=True)
        _, pred, model = fit_predict(fit_train, test, test, cols, "target_h1", params)
        preds[name] = pred
        m = metrics(preds.y, pred)
        rows.append({"model": name, "split": "test", "horizon": 1, **m, **params})
        fitted[name] = model

    for h in (2, 4, 8):
        rows.append({"model": "persistence", "split": "test", "horizon": h, **metrics(test[f"target_h{h}"], test.y0)})
        rows.append({"model": "seasonal_naive", "split": "test", "horizon": h, **metrics(test[f"target_h{h}"], test[f"seasonal_h{h}"])})
    for h in (2, 4, 8):
        for model_name in ("lag_cyclic", "lag_cyclic_slp"):
            cols = sets[model_name]
            _, pred, _ = fit_predict(fit_train, test, test, cols, f"target_h{h}", params)
            rows.append({"model": model_name, "split": "test", "horizon": h, **metrics(test[f"target_h{h}"], pred), **params})

    metrics_df = pd.DataFrame(rows)
    metrics_df.to_csv(out / "baseline_metrics.csv", index=False)
    preds.to_parquet(out / "predictions" / "test_h1.parquet", index=False)

    # Subgroups on H=1 for lag_cyclic vs lag_cyclic_slp
    sub_rows = []
    tmp = preds.copy()
    tmp["hour"] = tmp.time.dt.hour
    tmp["weekend"] = tmp.time.dt.dayofweek >= 5
    tmp["peak"] = tmp.hour.between(17, 21)
    tmp["common_test"] = tmp.time < COMMON_TEST_END
    for label, mask in {
        "weekday": ~tmp.weekend,
        "weekend": tmp.weekend,
        "peak_17_22": tmp.peak,
        "offpeak": ~tmp.peak,
        "Bareilly": tmp.city == "Bareilly",
        "Mathura": tmp.city == "Mathura",
        "common_through_2021_02_20": tmp.common_test,
    }.items():
        for model in ("seasonal_naive", "lag_cyclic", "lag_cyclic_slp", "lag_cyclic_energy_slp", "lag_cyclic_peak_k3"):
            m = metrics(tmp.loc[mask, "y"], tmp.loc[mask, model])
            sub_rows.append({"subgroup": label, "model": model, **m})
    pd.DataFrame(sub_rows).to_csv(out / "subgroup_results.csv", index=False)

    # Paired test on absolute errors, research model vs lag+cyclic
    a = np.abs(tmp.lag_cyclic_slp - tmp.y)
    b = np.abs(tmp.lag_cyclic - tmp.y)
    # Wilcoxon on a subsample if needed for speed, but compute on all if n < 200000 else every kth
    step = max(1, len(a) // 100000)
    stat, p = wilcoxon(a[::step], b[::step], zero_method="wilcox", alternative="two-sided")
    mae_b = float(b.mean())
    mae_a = float(a.mean())
    tests = pd.DataFrame([{
        "comparison": "lag_cyclic_slp vs lag_cyclic",
        "null": "median paired absolute-error difference is zero",
        "alternative": "two-sided",
        "n_used": int(np.ceil(len(a) / step)),
        "step": step,
        "statistic": float(stat),
        "p_value": float(p),
        "mae_lag_cyclic": mae_b,
        "mae_lag_cyclic_slp": mae_a,
        "mae_reduction_pct": float(100 * (mae_b - mae_a) / mae_b) if mae_b else float("nan"),
    }])
    tests.to_csv(out / "statistical_tests.csv", index=False)

    # Figures
    h1 = metrics_df[metrics_df.horizon == 1].drop_duplicates("model")
    order = ["persistence", "seasonal_naive", "lag", "lag_cyclic", "lag_slp", "lag_cyclic_slp", "lag_cyclic_energy_slp", "lag_cyclic_peak_k3"]
    h1 = h1.set_index("model").reindex(order).dropna(subset=["mae"])
    f, ax = plt.subplots(figsize=(9, 4))
    ax.bar(np.arange(len(h1)), h1.mae)
    ax.set_xticks(np.arange(len(h1)))
    ax.set_xticklabels(h1.index, rotation=30, ha="right")
    ax.set(ylabel="MAE (kW)", title="Test MAE, 15-minute-ahead")
    save_fig(f, fig / "model_mae_h1.png")
    f, ax = plt.subplots(figsize=(9, 4))
    ax.bar(np.arange(len(h1)), h1.rmse)
    ax.set_xticks(np.arange(len(h1)))
    ax.set_xticklabels(h1.index, rotation=30, ha="right")
    ax.set(ylabel="RMSE (kW)", title="Test RMSE, 15-minute-ahead")
    save_fig(f, fig / "model_rmse_h1.png")
    sample = tmp[tmp.meter_id == tmp.meter_id.iloc[0]].sort_values("time").head(96 * 3)
    f, ax = plt.subplots(figsize=(9, 4))
    ax.plot(sample.time, sample.y, label="Actual", color="black")
    ax.plot(sample.time, sample.lag_cyclic, label="Lag+cyclic")
    ax.plot(sample.time, sample.lag_cyclic_slp, label="Lag+cyclic+SLP")
    ax.set(ylabel="kW", title=f"Test sample, meter {sample.meter_id.iloc[0]}")
    ax.legend()
    save_fig(f, fig / "actual_vs_predicted_sample.png")
    f, ax = plt.subplots(figsize=(6, 4))
    ax.hist(tmp.y - tmp.lag_cyclic_slp, bins=60)
    ax.set(xlabel="Actual − predicted (kW)", title="H=1 SLP model error")
    save_fig(f, fig / "error_distribution_slp.png")
    for src, dest in (
        ("model_mae_h1.png", "forecast_mae.png"),
        ("actual_vs_predicted_sample.png", "forecast_actual_vs_predicted.png"),
    ):
        (ppt / dest).write_bytes((fig / src).read_bytes())
    print(metrics_df[metrics_df.horizon == 1].to_string(index=False))
    print(tests.to_string(index=False))


if __name__ == "__main__":
    main()

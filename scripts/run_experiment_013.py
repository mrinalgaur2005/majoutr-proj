#!/usr/bin/env python3
"""Experiment 013: per-meter conventional forecasts. No SLP features.

Does not overwrite Experiment 012 outputs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "forecasting"
FIG = ROOT / "results" / "figures" / "forecasting"
PPT = ROOT / "results" / "figures" / "ppt_ready"
PRED = OUT / "predictions" / "experiment_013"

TRAIN_END = np.datetime64("2020-07-01")
VAL_END = np.datetime64("2021-01-01")
COMMON_END = np.datetime64("2021-02-21")
MIN_TRAIN = 96 * 14
MIN_VAL = 96 * 3
MIN_TEST = 96 * 3
SVR_CAP = 1500
RIDGE_ALPHAS = (0.1, 1.0, 10.0, 100.0)
SVR_C = (1.0, 10.0, 100.0)
SVR_EPS = (0.05, 0.2)
LAGS = (1, 2, 4, 8, 12, 24, 48, 96)  # lag_k = y(t-k+1); lag_1 is y(t)
MAPE_MIN = 0.05
DPI = 300
plt.rcParams.update({"font.size": 11, "figure.dpi": DPI})


def save_fig(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    fig.savefig(path.with_suffix(".pdf"))
    fig.savefig(path.with_suffix(".svg"))
    plt.close(fig)


def metric_pack(y, p) -> dict:
    y = np.asarray(y, dtype=np.float64)
    p = np.asarray(p, dtype=np.float64)
    err = p - y
    sse = float(np.square(err).sum())
    sst = float(np.square(y - y.mean()).sum()) if len(y) else np.nan
    mask = np.abs(y) >= MAPE_MIN
    return {
        "n_test": int(len(y)),
        "MAE": float(np.mean(np.abs(err))) if len(y) else np.nan,
        "RMSE": float(np.sqrt(np.mean(np.square(err)))) if len(y) else np.nan,
        "WAPE": float(np.abs(err).sum() / np.abs(y).sum()) if np.abs(y).sum() else np.nan,
        "R2": float(1 - sse / sst) if sst else np.nan,
        "MAPE_pct": float(np.mean(np.abs(err[mask] / y[mask])) * 100) if mask.any() else np.nan,
    }


def design(y: np.ndarray, times: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rows at origin t predict y[t+1]. lag_k = y[t-k+1]."""
    n = len(y)
    slot = ((times.astype("datetime64[m]").astype(np.int64) // 15) % 96).astype(np.float64)
    # target time is t+1
    target_times = times + np.timedelta64(15, "m")
    tslot = ((target_times.astype("datetime64[m]").astype(np.int64) // 15) % 96).astype(np.float64)
    dow = (target_times.astype("datetime64[D]").astype(np.int64) + 3) % 7  # 1970-01-01 was Thursday
    # numpy datetime64[D] epoch Thursday=3 if Monday=0? 1970-01-01 was Thursday.
    # pandas dayofweek Monday=0. Thursday=3. (epoch_days + 3) % 7 = Thursday=3. Yes Monday=0.
    origin = np.arange(96, n - 1)
    cols = [y[origin - (k - 1)] for k in LAGS]
    X = np.column_stack(cols)
    cyc = np.column_stack([
        np.sin(2 * np.pi * tslot[origin] / 96),
        np.cos(2 * np.pi * tslot[origin] / 96),
        np.sin(2 * np.pi * dow[origin] / 7),
        np.cos(2 * np.pi * dow[origin] / 7),
        (dow[origin] >= 5).astype(np.float64),
    ])
    target = y[origin + 1]
    ok = np.isfinite(X).all(axis=1) & np.isfinite(target) & np.isfinite(y[origin - 96])
    seasonal = y[origin - 96]
    persistence = y[origin]
    return X[ok], cyc[ok], target[ok], times[origin][ok], persistence[ok], seasonal[ok], tslot[origin][ok], dow[origin][ok]


def split_mask(times: np.ndarray, start, end) -> np.ndarray:
    return (times >= start) & (times < end)


def fit_ridge(Xtr, ytr, Xva, yva, Xte):
    best_a, best_mae = None, np.inf
    scaler = StandardScaler().fit(Xtr)
    Ztr, Zva = scaler.transform(Xtr), scaler.transform(Xva)
    for alpha in RIDGE_ALPHAS:
        model = Ridge(alpha=alpha)
        model.fit(Ztr, ytr)
        pred = model.predict(Zva)
        mae = float(np.mean(np.abs(pred - yva)))
        if mae < best_mae:
            best_mae, best_a = mae, alpha
    Xall = np.vstack([Xtr, Xva])
    yall = np.concatenate([ytr, yva])
    scaler = StandardScaler().fit(Xall)
    model = Ridge(alpha=best_a)
    model.fit(scaler.transform(Xall), yall)
    return model.predict(scaler.transform(Xte)), best_a, best_mae


def fit_svr(Xtr, ytr, Xva, yva, Xte):
    cap = min(SVR_CAP, len(Xtr))
    Xtr_s, ytr_s = Xtr[-cap:], ytr[-cap:]
    best, best_mae = None, np.inf
    scaler = StandardScaler().fit(Xtr_s)
    Ztr, Zva = scaler.transform(Xtr_s), scaler.transform(Xva)
    for C in SVR_C:
        for eps in SVR_EPS:
            model = SVR(kernel="rbf", C=C, epsilon=eps, gamma="scale")
            model.fit(Ztr, ytr_s)
            mae = float(np.mean(np.abs(model.predict(Zva) - yva)))
            if mae < best_mae:
                best_mae = mae
                best = {"C": C, "epsilon": eps}
    Xall = np.vstack([Xtr, Xva])
    yall = np.concatenate([ytr, yva])
    cap2 = min(SVR_CAP, len(Xall))
    scaler = StandardScaler().fit(Xall[-cap2:])
    model = SVR(kernel="rbf", C=best["C"], epsilon=best["epsilon"], gamma="scale")
    model.fit(scaler.transform(Xall[-cap2:]), yall[-cap2:])
    return model.predict(scaler.transform(Xte)), best, best_mae, cap


def autocorr(y: np.ndarray, times: np.ndarray) -> dict:
    out = {}
    for k in (1, 2, 4, 8, 96):
        a = y[:-k]
        b = y[k:]
        train_pair = (times[:-k] < TRAIN_END) & (times[k:] < TRAIN_END)
        ok = train_pair & np.isfinite(a) & np.isfinite(b)
        if ok.sum() < 30:
            out[f"lag_{k}"] = np.nan
            continue
        aa, bb = a[ok], b[ok]
        aa = aa - aa.mean()
        bb = bb - bb.mean()
        denom = np.sqrt(np.square(aa).sum() * np.square(bb).sum())
        out[f"lag_{k}"] = float((aa * bb).sum() / denom) if denom else np.nan
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PRED.mkdir(parents=True, exist_ok=True)
    bins = pd.read_parquet(
        ROOT / "data/interim/ceew_15min_bins_dedup.parquet",
        columns=["meter_id", "city", "bin", "load_kw", "complete"],
    )
    bins = bins[bins.complete].copy()
    bins["load_kw"] = bins["load_kw"].astype(np.float32)
    rows_elig = []
    rows_metrics = []
    rows_sub = []
    rows_ac = []
    pred_chunks = []
    configs = []
    for (meter, city), g in bins.groupby(["meter_id", "city"], sort=True):
        g = g.sort_values("bin")
        times = g.bin.to_numpy(dtype="datetime64[ns]")
        yraw = g.load_kw.to_numpy(dtype=np.float64)
        full_t = np.arange(times[0], times[-1] + np.timedelta64(15, "m"), np.timedelta64(15, "m"))
        y = np.full(len(full_t), np.nan)
        pos = ((times - full_t[0]) / np.timedelta64(15, "m")).astype(np.int64)
        y[pos] = yraw
        X, cyc, target, t_origin, persistence, seasonal, tslot, dow = design(y, full_t)
        tr = split_mask(t_origin, np.datetime64("2019-01-01"), TRAIN_END)
        va = split_mask(t_origin, TRAIN_END, VAL_END)
        te = t_origin >= VAL_END
        usable_train = int(tr.sum())
        usable_val = int(va.sum())
        usable_test = int(te.sum())
        eligible = usable_train >= MIN_TRAIN and usable_val >= MIN_VAL and usable_test >= MIN_TEST
        reason = "eligible" if eligible else "below_minimum_usable_rows"
        rows_elig.append({
            "meter": meter,
            "city": city,
            "train_rows": int((times < TRAIN_END).sum()),
            "validation_rows": int(((times >= TRAIN_END) & (times < VAL_END)).sum()),
            "test_rows": int((times >= VAL_END).sum()),
            "usable_train_rows": usable_train,
            "usable_validation_rows": usable_val,
            "usable_test_rows": usable_test,
            "eligible": eligible,
            "reason": reason,
        })
        ac = autocorr(y, full_t)
        ac.update({"meter": meter, "city": city})
        rows_ac.append(ac)
        if not eligible:
            print(meter, "skip", usable_train, usable_val, usable_test, flush=True)
            continue
        print(meter, "fit", usable_train, usable_test, flush=True)
        Xtr, ytr = X[tr], target[tr]
        Xva, yva = X[va], target[va]
        Xte, yte = X[te], target[te]
        pred = {
            "persistence": persistence[te],
            "seasonal_naive": seasonal[te],
        }
        pred["ridge_lag"], a_lag, mae_lag = fit_ridge(Xtr, ytr, Xva, yva, Xte)
        pred["ridge_lag_cyclic"], a_cyc, mae_cyc = fit_ridge(
            np.hstack([Xtr, cyc[tr]]), ytr, np.hstack([Xva, cyc[va]]), yva, np.hstack([Xte, cyc[te]])
        )
        pred["svr_lag"], svr_best, mae_svr, cap = fit_svr(Xtr, ytr, Xva, yva, Xte)
        configs.append({"meter": meter, "ridge_lag_alpha": a_lag, "ridge_lag_cyclic_alpha": a_cyc, "svr": svr_best, "svr_cap": cap, "val_mae_ridge_lag": mae_lag, "val_mae_ridge_cyclic": mae_cyc, "val_mae_svr": mae_svr})
        train_level = float(np.nanmean(y[full_t < TRAIN_END]))
        for name, p in pred.items():
            pack = metric_pack(yte, p)
            rows_metrics.append({"meter": meter, "city": city, "model": name, "train_mean_kw": train_level, **pack})
        hour = (tslot[te] // 4).astype(int)
        weekend = dow[te] >= 5
        jump = np.abs(yte - persistence[te])
        jump_cut = np.nanpercentile(np.abs(target[tr] - persistence[tr]), 90)
        subgroups = {
            "peak_17_21": (hour >= 17) & (hour <= 21),
            "offpeak": ~((hour >= 17) & (hour <= 21)),
            "weekday": ~weekend,
            "weekend": weekend,
            "near_zero_lt_0.05": np.abs(yte) < MAPE_MIN,
            "sudden_transition": jump >= jump_cut,
        }
        for label, mask in subgroups.items():
            if mask.sum() < 20:
                continue
            for name in ("persistence", "ridge_lag", "ridge_lag_cyclic", "svr_lag"):
                rows_sub.append({"meter": meter, "city": city, "subgroup": label, "model": name, **metric_pack(yte[mask], pred[name][mask])})
        pred_chunks.append(pd.DataFrame({
            "meter": meter,
            "city": city,
            "time": pd.to_datetime(t_origin[te]),
            "y": yte,
            "persistence": pred["persistence"],
            "seasonal_naive": pred["seasonal_naive"],
            "ridge_lag": pred["ridge_lag"],
            "ridge_lag_cyclic": pred["ridge_lag_cyclic"],
            "svr_lag": pred["svr_lag"],
            "train_mean_kw": train_level,
        }))

    elig = pd.DataFrame(rows_elig)
    metrics = pd.DataFrame(rows_metrics)
    sub = pd.DataFrame(rows_sub)
    ac = pd.DataFrame(rows_ac)
    preds = pd.concat(pred_chunks, ignore_index=True)
    elig.to_csv(OUT / "per_meter_eligibility.csv", index=False)
    metrics.to_csv(OUT / "per_meter_metrics.csv", index=False)
    ac.to_csv(OUT / "autocorrelation_summary.csv", index=False)
    sub.to_csv(OUT / "subgroup_metrics_per_meter.csv", index=False)
    preds.to_parquet(PRED / "test_predictions.parquet", index=False)

    micro_rows = []
    for name in preds.columns.intersection(["persistence", "seasonal_naive", "ridge_lag", "ridge_lag_cyclic", "svr_lag"]):
        micro_rows.append({"model": name, "scope": "all", **metric_pack(preds.y, preds[name])})
        for city, g in preds.groupby("city"):
            micro_rows.append({"model": name, "scope": city, **metric_pack(g.y, g[name])})
        common = preds[preds.time < pd.Timestamp("2021-02-21")]
        micro_rows.append({"model": name, "scope": "common_through_2021_02_20", **metric_pack(common.y, common[name])})
    micro = pd.DataFrame(micro_rows)
    micro.to_csv(OUT / "micro_metrics.csv", index=False)

    macro_rows = []
    for model, g in metrics.groupby("model"):
        for col in ("MAE", "RMSE", "WAPE", "R2"):
            s = g[col]
            macro_rows.append({
                "model": model,
                "metric": col,
                "macro_mean": float(s.mean()),
                "median": float(s.median()),
                "p25": float(s.quantile(0.25)),
                "p75": float(s.quantile(0.75)),
                "min": float(s.min()),
                "max": float(s.max()),
                "n_meters": int(len(s)),
            })
    macro = pd.DataFrame(macro_rows)
    macro.to_csv(OUT / "macro_metrics.csv", index=False)

    # Pooled subgroup table for persistence vs learned models
    med_level = preds.groupby("meter").train_mean_kw.first().median()
    preds["load_group"] = np.where(preds.train_mean_kw >= med_level, "high_load_meter", "low_load_meter")
    preds["hour"] = preds.time.dt.hour
    preds["weekend"] = preds.time.dt.dayofweek >= 5
    scope_masks = {
        "peak_17_21": preds.hour.between(17, 21),
        "offpeak": ~preds.hour.between(17, 21),
        "weekday": ~preds.weekend,
        "weekend": preds.weekend,
        "high_load_meter": preds.load_group == "high_load_meter",
        "low_load_meter": preds.load_group == "low_load_meter",
        "near_zero_lt_0.05": preds.y.abs() < MAPE_MIN,
    }
    sub_micro = []
    for label, mask in scope_masks.items():
        part = preds.loc[mask]
        for name in ("persistence", "seasonal_naive", "ridge_lag", "ridge_lag_cyclic", "svr_lag"):
            sub_micro.append({"subgroup": label, "model": name, **metric_pack(part.y, part[name])})
    pd.DataFrame(sub_micro).to_csv(OUT / "subgroup_metrics.csv", index=False)

    pers = micro[(micro.model == "persistence") & (micro.scope == "all")].iloc[0]
    comp = []
    for _, r in micro.iterrows():
        base = micro[(micro.model == "persistence") & (micro.scope == r.scope)].iloc[0]
        comp.append({
            "model": r.model,
            "scope": r.scope,
            "MAE": r.MAE,
            "persistence_MAE": base.MAE,
            "mae_improvement_pct": 100 * (base.MAE - r.MAE) / base.MAE if base.MAE else np.nan,
        })
    pd.DataFrame(comp).to_csv(OUT / "persistence_comparison.csv", index=False)

    config = {
        "experiment": "013",
        "horizon": "H=1, next 15-minute average kW",
        "split": {"train_before": "2020-07-01", "validation_before": "2021-01-01", "test_from": "2021-01-01"},
        "lag_definition": "lag_k = load(t-k+1); lag_1 = load(t); target = load(t+1)",
        "seasonal_naive": "load(t-96)",
        "cyclic": "sin/cos of target 15-min slot/96, sin/cos of target day-of-week/7, weekend indicator",
        "eligibility": {"min_usable_train": MIN_TRAIN, "min_usable_validation": MIN_VAL, "min_usable_test": MIN_TEST},
        "ridge_alphas": list(RIDGE_ALPHAS),
        "svr": {"C": list(SVR_C), "epsilon": list(SVR_EPS), "gamma": "scale", "chronological_cap": SVR_CAP},
        "scaler": "StandardScaler fit on train for tuning; refit on train+validation for the test model",
        "competency_rule": "Micro MAE <= 1.02 * persistence micro MAE, macro median MAE <= 1.05 * persistence median MAE, and neither city worse than persistence by more than 10% MAE.",
        "eligible_meters": int(elig.eligible.sum()),
        "meters_total": int(len(elig)),
        "per_meter_selected": configs,
    }
    (OUT / "model_config_013.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    # Figures
    pers_m = metrics[metrics.model == "persistence"]
    f, ax = plt.subplots(figsize=(7, 4))
    ax.hist(pers_m.MAE, bins=20)
    ax.set(xlabel="Per-meter MAE (kW)", ylabel="Meters", title="Persistence MAE across meters")
    save_fig(f, FIG / "exp013_persistence_mae_distribution.png")
    learned = metrics[metrics.model == "ridge_lag_cyclic"]
    f, ax = plt.subplots(figsize=(7, 4))
    ax.hist(learned.MAE, bins=20)
    ax.set(xlabel="Per-meter MAE (kW)", ylabel="Meters", title="Ridge lag+cyclic MAE across meters")
    save_fig(f, FIG / "exp013_learned_mae_distribution.png")
    order = ["persistence", "seasonal_naive", "ridge_lag", "ridge_lag_cyclic", "svr_lag"]
    micro_all = micro[micro.scope == "all"].set_index("model").reindex(order)
    f, ax = plt.subplots(figsize=(8, 4))
    ax.bar(np.arange(len(micro_all)), micro_all.MAE)
    ax.set_xticks(np.arange(len(micro_all)))
    ax.set_xticklabels(order, rotation=20, ha="right")
    ax.set(ylabel="Micro MAE (kW)", title="Experiment 013 micro-averaged test MAE")
    save_fig(f, FIG / "exp013_micro_mae.png")
    med = macro[macro.metric == "MAE"].set_index("model").reindex(order)
    f, ax = plt.subplots(figsize=(8, 4))
    ax.bar(np.arange(len(med)), med.macro_mean)
    ax.set_xticks(np.arange(len(med)))
    ax.set_xticklabels(order, rotation=20, ha="right")
    ax.set(ylabel="Macro mean MAE (kW)", title="Experiment 013 macro-averaged test MAE")
    save_fig(f, FIG / "exp013_macro_mae.png")
    both = pers_m[["meter", "MAE"]].merge(learned[["meter", "MAE"]], on="meter", suffixes=("_persistence", "_learned"))
    f, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(both.MAE_persistence, both.MAE_learned, s=18)
    lim = max(both.MAE_persistence.max(), both.MAE_learned.max())
    ax.plot([0, lim], [0, lim], color="black", lw=1)
    ax.set(xlabel="Persistence MAE (kW)", ylabel="Ridge lag+cyclic MAE (kW)", title="Per meter")
    save_fig(f, FIG / "exp013_persistence_vs_learned.png")
    city = micro[micro.scope.isin(["Mathura", "Bareilly"])]
    f, ax = plt.subplots(figsize=(8, 4))
    width = 0.35
    for i, scope in enumerate(["Mathura", "Bareilly"]):
        part = city[city.scope == scope].set_index("model").reindex(order)
        ax.bar(np.arange(len(order)) + i * width, part.MAE, width=width, label=scope)
    ax.set_xticks(np.arange(len(order)) + width / 2)
    ax.set_xticklabels(order, rotation=20, ha="right")
    ax.set(ylabel="Micro MAE (kW)", title="Experiment 013 by city")
    ax.legend()
    save_fig(f, FIG / "exp013_by_city.png")
    load = pd.read_csv(OUT / "subgroup_metrics.csv")
    load = load[load.subgroup.isin(["high_load_meter", "low_load_meter"])]
    f, ax = plt.subplots(figsize=(8, 4))
    for i, scope in enumerate(["low_load_meter", "high_load_meter"]):
        part = load[load.subgroup == scope].set_index("model").reindex(order)
        ax.bar(np.arange(len(order)) + i * width, part.MAE, width=width, label=scope)
    ax.set_xticks(np.arange(len(order)) + width / 2)
    ax.set_xticklabels(order, rotation=20, ha="right")
    ax.set(ylabel="Micro MAE (kW)", title="Experiment 013 by training load level")
    ax.legend()
    save_fig(f, FIG / "exp013_by_load.png")
    ac_med = ac[["lag_1", "lag_2", "lag_4", "lag_8", "lag_96"]].median()
    f, ax = plt.subplots(figsize=(6, 4))
    ax.bar(np.arange(len(ac_med)), ac_med.to_numpy())
    ax.set_xticks(np.arange(len(ac_med)))
    ax.set_xticklabels(["1", "2", "4", "8", "96"])
    ax.set(xlabel="Lag (15-min steps)", ylabel="Median meter autocorrelation", title="Training-period autocorrelation")
    save_fig(f, FIG / "exp013_autocorrelation.png")
    sample_meter = preds.meter.iloc[0]
    sample = preds[preds.meter == sample_meter].sort_values("time").head(96 * 3)
    f, ax = plt.subplots(figsize=(9, 4))
    ax.plot(sample.y.to_numpy(), color="black", label="Actual")
    ax.plot(sample.persistence.to_numpy(), label="Persistence")
    ax.plot(sample.ridge_lag_cyclic.to_numpy(), label="Ridge lag+cyclic")
    ax.set(ylabel="kW", xlabel="Test step", title=f"Meter {sample_meter}")
    ax.legend()
    save_fig(f, FIG / "exp013_actual_vs_predicted.png")
    f, ax = plt.subplots(figsize=(7, 4))
    ax.hist(preds.y - preds.persistence, bins=60, alpha=0.6, label="Persistence")
    ax.hist(preds.y - preds.ridge_lag_cyclic, bins=60, alpha=0.6, label="Ridge lag+cyclic")
    ax.set(xlabel="Actual − predicted (kW)", title="Test error distribution")
    ax.legend()
    save_fig(f, FIG / "exp013_error_distribution.png")
    for src, dest in (
        ("exp013_micro_mae.png", "exp013_micro_mae.png"),
        ("exp013_persistence_vs_learned.png", "exp013_persistence_vs_learned.png"),
    ):
        (PPT / dest).write_bytes((FIG / src).read_bytes())
    print(micro[micro.scope == "all"].to_string(index=False))
    print("eligible", int(elig.eligible.sum()), "of", len(elig))


if __name__ == "__main__":
    main()

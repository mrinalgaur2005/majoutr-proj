#!/usr/bin/env python3
"""Experiment 015: leakage-free change-aware forecasts. No SLP, ToD, or BESS.

Does not write Experiment 013 or 014 artifacts.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "forecasting" / "experiment_015"
FIG = ROOT / "results" / "figures" / "forecasting"
PPT = ROOT / "results" / "figures" / "ppt_ready"
PRED = ROOT / "results" / "forecasting" / "predictions" / "experiment_015"
REF014 = ROOT / "results" / "forecasting" / "experiment_014" / "micro_load_metrics.csv"

TRAIN_END = np.datetime64("2020-07-01")
VAL_END = np.datetime64("2021-01-01")
MIN_TRAIN = 96 * 14
MIN_VAL = 96 * 3
MIN_TEST = 96 * 3
RIDGE_ALPHAS = (0.1, 1.0, 10.0, 100.0)
LAMBDAS = (0.0, 0.25, 0.5, 0.75, 1.0)
GATE_PCTS = (50, 75, 90)
HUBER_EPS = (1.35, 1.75)
HUBER_ALPHAS = (1e-4, 1e-2, 1.0)
LAGS = (1, 2, 4, 8, 12, 24, 48, 96)
MAPE_MIN = 0.05
SEED = 15
DPI = 300
MODELS = (
    "zero_change",
    "ridge_delta",
    "shrink_meter",
    "shrink_global",
    "gate_recent",
    "huber_delta",
)
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
        "n": int(len(y)),
        "MAE": float(np.mean(np.abs(err))) if len(y) else np.nan,
        "RMSE": float(np.sqrt(np.mean(np.square(err)))) if len(y) else np.nan,
        "WAPE": float(np.abs(err).sum() / np.abs(y).sum()) if np.abs(y).sum() else np.nan,
        "R2": float(1 - sse / sst) if sst else np.nan,
        "MAPE_pct": float(np.mean(np.abs(err[mask] / y[mask])) * 100) if mask.any() else np.nan,
    }


def split_mask(times: np.ndarray, start, end) -> np.ndarray:
    return (times >= start) & (times < end)


def design(y: np.ndarray, times: np.ndarray) -> dict:
    """Origin t predicts ΔP(t+1)=P(t+1)-P(t). Features use data through t only."""
    n = len(y)
    d = np.full(n, np.nan, dtype=np.float64)
    d[1:] = y[1:] - y[:-1]
    origin = np.arange(96, n - 1)
    target_delta = y[origin + 1] - y[origin]
    load_t = y[origin]
    actual_load = y[origin + 1]
    target_times = times[origin] + np.timedelta64(15, "m")
    tslot = ((target_times.astype("datetime64[m]").astype(np.int64) // 15) % 96).astype(np.float64)
    dow = (target_times.astype("datetime64[D]").astype(np.int64) + 3) % 7
    delta_X = np.column_stack([d[origin - (k - 1)] for k in LAGS])
    ok = np.isfinite(target_delta) & np.isfinite(load_t) & np.isfinite(delta_X).all(axis=1)
    if not np.allclose(target_delta[ok], actual_load[ok] - load_t[ok], equal_nan=True):
        raise AssertionError("target delta is not aligned with reconstructed load")
    return {
        "origin_times": times[origin][ok],
        "target_times": target_times[ok],
        "target_delta": target_delta[ok],
        "load_t": load_t[ok],
        "actual_load": actual_load[ok],
        "delta_X": delta_X[ok],
        "recent_abs_delta": np.abs(delta_X[ok, 0]),
        "tslot": tslot[ok],
        "dow": dow[ok],
        "n_dropped": int((~ok).sum()),
    }


def refit_ridge(Xtr, ytr, Xva, yva, Xte, alpha):
    Xall = np.vstack([Xtr, Xva])
    yall = np.concatenate([ytr, yva])
    scaler = StandardScaler().fit(Xall)
    model = Ridge(alpha=float(alpha))
    model.fit(scaler.transform(Xall), yall)
    return model.predict(scaler.transform(Xte))


def tune_huber(Xtr, ytr, Xva, yva):
    scaler = StandardScaler().fit(Xtr)
    Ztr, Zva = scaler.transform(Xtr), scaler.transform(Xva)
    best, best_mae, best_pred = None, np.inf, None
    for eps in HUBER_EPS:
        for alpha in HUBER_ALPHAS:
            model = HuberRegressor(epsilon=eps, alpha=alpha, max_iter=300)
            model.fit(Ztr, ytr)
            pred = model.predict(Zva)
            mae = float(np.mean(np.abs(pred - yva)))
            if mae < best_mae:
                best_mae = mae
                best = {"epsilon": eps, "alpha": alpha}
                best_pred = pred
    return best, best_pred, best_mae


def refit_huber(Xtr, ytr, Xva, yva, Xte, params):
    Xall = np.vstack([Xtr, Xva])
    yall = np.concatenate([ytr, yva])
    scaler = StandardScaler().fit(Xall)
    model = HuberRegressor(epsilon=params["epsilon"], alpha=params["alpha"], max_iter=300)
    model.fit(scaler.transform(Xall), yall)
    return model.predict(scaler.transform(Xte))


def meter_series(g: pd.DataFrame):
    g = g.sort_values("bin")
    times = g.bin.to_numpy(dtype="datetime64[ns]")
    if len(times) != len(np.unique(times)):
        raise AssertionError("duplicate timestamps inside a meter after dedup filter")
    yraw = g.load_kw.to_numpy(dtype=np.float64)
    full_t = np.arange(times[0], times[-1] + np.timedelta64(15, "m"), np.timedelta64(15, "m"))
    y = np.full(len(full_t), np.nan)
    pos = ((times - full_t[0]) / np.timedelta64(15, "m")).astype(np.int64)
    if np.unique(pos).size != pos.size:
        raise AssertionError("duplicate bin positions")
    y[pos] = yraw
    return y, full_t


def main() -> None:
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    PRED.mkdir(parents=True, exist_ok=True)
    bins = pd.read_parquet(
        ROOT / "data/interim/ceew_15min_bins_dedup.parquet",
        columns=["meter_id", "city", "bin", "load_kw", "complete"],
    )
    n_raw = len(bins)
    bins = bins[bins.complete].copy()
    bins["load_kw"] = bins["load_kw"].astype(np.float32)
    if bins.duplicated(["meter_id", "bin"]).any():
        raise AssertionError("duplicate meter-bin rows in complete dedup bins")

    rows_elig, rows_test, rows_val, configs = [], [], [], []
    pred_chunks = []
    zero_max = 0.0
    align_max = 0.0
    global_abs = {lam: 0.0 for lam in LAMBDAS}
    global_n = 0
    failures = []

    for (meter, city), g in bins.groupby(["meter_id", "city"], sort=True):
        y, full_t = meter_series(g)
        D = design(y, full_t)
        t_origin = D["origin_times"]
        if len(t_origin) != len(np.unique(t_origin)):
            raise AssertionError(f"duplicate origins {meter}")
        tr = split_mask(t_origin, np.datetime64("2019-01-01"), TRAIN_END)
        va = split_mask(t_origin, TRAIN_END, VAL_END)
        te = t_origin >= VAL_END
        ntr, nva, nte = int(tr.sum()), int(va.sum()), int(te.sum())
        eligible = ntr >= MIN_TRAIN and nva >= MIN_VAL and nte >= MIN_TEST
        rows_elig.append({
            "meter": meter,
            "city": city,
            "usable_train_rows": ntr,
            "usable_validation_rows": nva,
            "usable_test_rows": nte,
            "rows_dropped_incomplete_lags": D["n_dropped"],
            "eligible": eligible,
            "reason": "eligible" if eligible else "below_minimum_usable_rows",
        })
        if not eligible:
            print(meter, "skip", flush=True)
            continue
        print(meter, "fit", flush=True)
        X, yd = D["delta_X"], D["target_delta"]
        Xtr, ytr = X[tr], yd[tr]
        Xva, yva = X[va], yd[va]
        Xte, yte = X[te], yd[te]
        load_te, actual_te = D["load_t"][te], D["actual_load"][te]
        recent_te, recent_tr, recent_va = D["recent_abs_delta"][te], D["recent_abs_delta"][tr], D["recent_abs_delta"][va]
        align_max = max(align_max, float(np.max(np.abs((actual_te - load_te) - yte))))

        alpha, val_hat, val_mae = None, None, np.inf
        scaler = StandardScaler().fit(Xtr)
        Ztr, Zva = scaler.transform(Xtr), scaler.transform(Xva)
        for a in RIDGE_ALPHAS:
            pred = Ridge(alpha=a).fit(Ztr, ytr).predict(Zva)
            mae = float(np.mean(np.abs(pred - yva)))
            if mae < val_mae:
                alpha, val_hat, val_mae = a, pred, mae
        ridge_te = refit_ridge(Xtr, ytr, Xva, yva, Xte, alpha)

        best_lam, best_lam_mae = 1.0, np.inf
        for lam in LAMBDAS:
            mae = float(np.mean(np.abs(lam * val_hat - yva)))
            global_abs[lam] += float(np.abs(lam * val_hat - yva).sum())
            if mae < best_lam_mae:
                best_lam, best_lam_mae = lam, mae
        global_n += len(yva)
        shrink_te = best_lam * ridge_te

        best_pct, best_tau, best_gate_mae = None, None, np.inf
        for pct in GATE_PCTS:
            tau = float(np.percentile(recent_tr, pct))
            gated = np.where(recent_va >= tau, val_hat, 0.0)
            mae = float(np.mean(np.abs(gated - yva)))
            if mae < best_gate_mae:
                best_pct, best_tau, best_gate_mae = pct, tau, mae
        gate_te = np.where(recent_te >= best_tau, ridge_te, 0.0)

        try:
            hparams, hval, hmae = tune_huber(Xtr, ytr, Xva, yva)
            huber_te = refit_huber(Xtr, ytr, Xva, yva, Xte, hparams)
        except Exception as exc:  # recorded, not dropped silently
            failures.append({"meter": meter, "model": "huber_delta", "error": str(exc)})
            hparams, hval, hmae = None, np.zeros_like(yva), np.nan
            huber_te = np.full_like(yte, np.nan)
            print(meter, "huber failed", exc, flush=True)

        pred_delta = {
            "zero_change": np.zeros_like(yte),
            "ridge_delta": ridge_te,
            "shrink_meter": shrink_te,
            "gate_recent": gate_te,
            "huber_delta": huber_te,
        }
        zero_max = max(zero_max, float(np.max(np.abs(load_te + pred_delta["zero_change"] - load_te))))
        train_level = float(np.nanmean(y[full_t < TRAIN_END]))
        train_mean_abs = float(np.mean(np.abs(ytr)))
        tert = np.percentile(np.abs(ytr), [100 / 3, 200 / 3])
        cfg = {
            "meter": meter,
            "city": city,
            "ridge_alpha": alpha,
            "ridge_val_mae": val_mae,
            "shrink_lambda": best_lam,
            "shrink_val_mae": best_lam_mae,
            "gate_percentile": best_pct,
            "gate_tau_kw": best_tau,
            "gate_val_mae": best_gate_mae,
            "huber": hparams,
            "huber_val_mae": hmae,
            "train_mean_kw": train_level,
            "movement_tert_low": float(tert[0]),
            "movement_tert_high": float(tert[1]),
        }
        configs.append(cfg)
        val_preds = {
            "zero_change": np.zeros_like(yva),
            "ridge_delta": val_hat,
            "shrink_meter": best_lam * val_hat,
            "gate_recent": np.where(recent_va >= best_tau, val_hat, 0.0),
            "huber_delta": hval,
        }
        for name, p in val_preds.items():
            if p is None or not np.isfinite(p).all():
                continue
            rows_val.append({"meter": meter, "city": city, "model": name, "split": "validation", **metric_pack(yva, p)})
        for name, p in pred_delta.items():
            if not np.isfinite(p).all():
                continue
            rows_test.append({
                "meter": meter,
                "city": city,
                "model": name,
                "train_mean_kw": train_level,
                **metric_pack(actual_te, load_te + p),
            })
        move = np.where(np.abs(yte) <= tert[0], "movement_low", np.where(np.abs(yte) <= tert[1], "movement_mid", "movement_high"))
        chunk = pd.DataFrame({
            "meter": meter,
            "city": city,
            "time": pd.to_datetime(t_origin[te]),
            "target_time": pd.to_datetime(D["target_times"][te]),
            "actual_load": actual_te,
            "actual_delta": yte,
            "load_t": load_te,
            "recent_abs_delta": recent_te,
            "train_mean_kw": train_level,
            "train_mean_abs_delta": train_mean_abs,
            "movement_group": move,
            "pred_delta_ridge": ridge_te,
            "pred_delta_huber": huber_te,
        })
        for name, p in pred_delta.items():
            chunk[f"pred_load_{name}"] = load_te + p
        pred_chunks.append(chunk)

    if zero_max > 1e-9:
        raise AssertionError(f"zero-change mismatch {zero_max}")
    if align_max > 1e-8:
        raise AssertionError(f"alignment mismatch {align_max}")

    best_global_lam = min(LAMBDAS, key=lambda lam: global_abs[lam])
    global_val_mae = global_abs[best_global_lam] / global_n
    preds = pd.concat(pred_chunks, ignore_index=True)
    preds["pred_load_shrink_global"] = preds.load_t + best_global_lam * preds.pred_delta_ridge
    # validation score for shrink_global is pooled; per-meter test metrics added below
    for meter, g in preds.groupby("meter", sort=False):
        city = g.city.iloc[0]
        rows_test.append({
            "meter": meter,
            "city": city,
            "model": "shrink_global",
            "train_mean_kw": float(g.train_mean_kw.iloc[0]),
            **metric_pack(g.actual_load, g.pred_load_shrink_global),
        })
    rows_val.append({
        "meter": "ALL",
        "city": "ALL",
        "model": "shrink_global",
        "split": "validation",
        "n": int(global_n),
        "MAE": float(global_val_mae),
        "RMSE": np.nan,
        "WAPE": np.nan,
        "R2": np.nan,
        "MAPE_pct": np.nan,
    })

    elig = pd.DataFrame(rows_elig)
    test_m = pd.DataFrame(rows_test)
    val_m = pd.DataFrame(rows_val)
    elig.to_csv(OUT / "per_meter_eligibility.csv", index=False)
    test_m.to_csv(OUT / "per_meter_load_metrics.csv", index=False)
    val_m.to_csv(OUT / "validation_metrics.csv", index=False)
    preds.to_parquet(PRED / "test_predictions.parquet", index=False)
    pd.DataFrame(failures).to_csv(OUT / "model_failures.csv", index=False)

    # pooled validation MAE (selection evidence; shrink_global already pooled)
    val_select = []
    for name in ("zero_change", "ridge_delta", "shrink_meter", "gate_recent", "huber_delta"):
        part = val_m[val_m.model == name]
        # micro from per-meter n and MAE
        mae = float(np.average(part.MAE, weights=part.n))
        val_select.append({"model": name, "validation_micro_MAE": mae, "n": int(part.n.sum())})
    val_select.append({"model": "shrink_global", "validation_micro_MAE": float(global_val_mae), "n": int(global_n)})
    val_sel = pd.DataFrame(val_select).sort_values("validation_micro_MAE")
    val_sel.to_csv(OUT / "validation_selection.csv", index=False)
    learned = val_sel[val_sel.model != "zero_change"]
    selected = str(learned.iloc[0].model)
    selected_beats_val = float(learned.iloc[0].validation_micro_MAE) < float(val_sel[val_sel.model == "zero_change"].validation_micro_MAE.iloc[0])

    micro_rows = []
    for name in MODELS:
        col = f"pred_load_{name}"
        micro_rows.append({"model": name, "scope": "all", **metric_pack(preds.actual_load, preds[col])})
        for city, g in preds.groupby("city"):
            micro_rows.append({"model": name, "scope": city, **metric_pack(g.actual_load, g[col])})
        common = preds[preds.time < pd.Timestamp("2021-02-21")]
        micro_rows.append({"model": name, "scope": "common_through_2021_02_20", **metric_pack(common.actual_load, common[col])})
    micro = pd.DataFrame(micro_rows)
    micro.to_csv(OUT / "micro_load_metrics.csv", index=False)

    macro_rows = []
    for model, g in test_m.groupby("model"):
        for col in ("MAE", "RMSE"):
            s = g[col]
            macro_rows.append({
                "model": model,
                "metric": col,
                "macro_mean": float(s.mean()),
                "median": float(s.median()),
                "p25": float(s.quantile(0.25)),
                "p75": float(s.quantile(0.75)),
                "n_meters": int(len(s)),
            })
    macro = pd.DataFrame(macro_rows)
    macro.to_csv(OUT / "macro_load_metrics.csv", index=False)

    pers_mae = test_m[test_m.model == "zero_change"][["meter", "MAE", "RMSE"]].rename(columns={"MAE": "MAE_persistence", "RMSE": "RMSE_persistence"})
    paired_rows = []
    win_rows = []
    rng = np.random.default_rng(SEED)
    for name in MODELS:
        if name == "zero_change":
            continue
        m = test_m[test_m.model == name][["meter", "MAE", "RMSE"]].merge(pers_mae, on="meter")
        if len(m) != int(elig.eligible.sum()):
            raise AssertionError(f"{name} meter count {len(m)} != eligible")
        d = m.MAE.to_numpy() - m.MAE_persistence.to_numpy()
        # positive d means worse than persistence
        stat, p = stats.wilcoxon(d, alternative="two-sided", zero_method="wilcox")
        boots = []
        for _ in range(2000):
            boots.append(float(np.median(d[rng.integers(0, len(d), len(d))])))
        lo, hi = np.percentile(boots, [2.5, 97.5])
        paired_rows.append({
            "model": name,
            "n_meters": int(len(m)),
            "meters_mae_better": int((d < 0).sum()),
            "meters_mae_worse": int((d > 0).sum()),
            "meters_tie": int((d == 0).sum()),
            "median_meter_mae_diff": float(np.median(d)),
            "mean_meter_mae_diff": float(np.mean(d)),
            "boot_median_diff_ci95_low": float(lo),
            "boot_median_diff_ci95_high": float(hi),
            "wilcoxon_stat": float(stat),
            "wilcoxon_p_two_sided": float(p),
            "inference_unit": "meter",
        })
        for _, r in m.iterrows():
            win_rows.append({
                "meter": r.meter,
                "model": name,
                "MAE": r.MAE,
                "MAE_persistence": r.MAE_persistence,
                "mae_diff": r.MAE - r.MAE_persistence,
            })
    paired = pd.DataFrame(paired_rows)
    paired.to_csv(OUT / "meter_level_comparison.csv", index=False)
    pd.DataFrame(win_rows).to_csv(OUT / "per_meter_mae_diff.csv", index=False)

    base = micro[(micro.model == "zero_change")]
    comp = []
    for _, r in micro.iterrows():
        b = base[base.scope == r.scope].iloc[0]
        comp.append({
            "model": r.model,
            "scope": r.scope,
            "MAE": r.MAE,
            "RMSE": r.RMSE,
            "persistence_MAE": b.MAE,
            "mae_diff_kw": r.MAE - b.MAE,
            "mae_change_pct": 100 * (r.MAE - b.MAE) / b.MAE if b.MAE else np.nan,
        })
    pd.DataFrame(comp).to_csv(OUT / "persistence_comparison.csv", index=False)

    med_level = preds.groupby("meter").train_mean_kw.first().median()
    preds["load_group"] = np.where(preds.train_mean_kw >= med_level, "high_load_meter", "low_load_meter")
    preds["hour"] = preds.target_time.dt.hour
    preds["weekend"] = preds.target_time.dt.dayofweek >= 5
    scopes = {
        "peak_17_21": preds.hour.between(17, 21),
        "offpeak": ~preds.hour.between(17, 21),
        "weekday": ~preds.weekend,
        "weekend": preds.weekend,
        "high_load_meter": preds.load_group == "high_load_meter",
        "low_load_meter": preds.load_group == "low_load_meter",
        "near_zero_load_lt_0.05": preds.actual_load.abs() < MAPE_MIN,
        "retrospective_movement_low": preds.movement_group == "movement_low",
        "retrospective_movement_mid": preds.movement_group == "movement_mid",
        "retrospective_movement_high": preds.movement_group == "movement_high",
    }
    sub_rows = []
    for label, mask in scopes.items():
        part = preds.loc[mask]
        for name in MODELS:
            sub_rows.append({
                "subgroup": label,
                "model": name,
                "retrospective": label.startswith("retrospective") or label.startswith("near_zero"),
                **metric_pack(part.actual_load, part[f"pred_load_{name}"]),
            })
    pd.DataFrame(sub_rows).to_csv(OUT / "subgroup_load_metrics.csv", index=False)

    ref_note = {"compared": False}
    if REF014.exists():
        ref = pd.read_csv(REF014)
        ref_mae = float(ref[(ref.model == "ridge_delta") & (ref.scope == "all")].MAE.iloc[0])
        new_mae = float(micro[(micro.model == "ridge_delta") & (micro.scope == "all")].MAE.iloc[0])
        ref_note = {
            "compared": True,
            "experiment_014_ridge_delta_MAE": ref_mae,
            "experiment_015_ridge_delta_MAE": new_mae,
            "abs_diff": abs(new_mae - ref_mae),
            "match_tol_1e-6": abs(new_mae - ref_mae) < 1e-6,
        }
        if abs(new_mae - ref_mae) >= 1e-4:
            print("DISCREPANCY vs experiment 014 ridge_delta MAE", ref_mae, new_mae)

    pers_all = micro[(micro.model == "zero_change") & (micro.scope == "all")].iloc[0]
    sel_all = micro[(micro.model == selected) & (micro.scope == "all")].iloc[0]
    sel_med = float(test_m[test_m.model == selected].MAE.median())
    pers_med = float(test_m[test_m.model == "zero_change"].MAE.median())
    city_ok = True
    for city in ("Mathura", "Bareilly"):
        pm = float(micro[(micro.model == "zero_change") & (micro.scope == city)].MAE.iloc[0])
        sm = float(micro[(micro.model == selected) & (micro.scope == city)].MAE.iloc[0])
        city_ok = city_ok and sm <= 1.10 * pm
    competent = bool(
        sel_all.MAE <= 1.02 * pers_all.MAE
        and sel_med <= 1.05 * pers_med
        and city_ok
        and sel_all.MAE < pers_all.MAE
    )
    elapsed = time.perf_counter() - t0
    lam_counts = {}
    for c in configs:
        lam_counts[str(c["shrink_lambda"])] = lam_counts.get(str(c["shrink_lambda"]), 0) + 1
    shrink_paired = paired[paired.model == "shrink_meter"].iloc[0]
    summary = {
        "experiment": "015",
        "elapsed_sec": elapsed,
        "eligible_meters": int(elig.eligible.sum()),
        "meters_total": int(len(elig)),
        "test_rows": int(len(preds)),
        "zero_change_max_abs_diff": zero_max,
        "alignment_max_abs_diff": align_max,
        "shrink_global_lambda": best_global_lam,
        "validation_selected_model": selected,
        "selected_beats_persistence_on_validation": bool(selected_beats_val),
        "selected_test_MAE": float(sel_all.MAE),
        "persistence_test_MAE": float(pers_all.MAE),
        "competent_under_013_rule": competent,
        "reproduction_014": ref_note,
        "huber_failures": failures,
        "inference": "Wilcoxon and bootstrap use one MAE per meter, not individual 15-minute rows.",
        "not_tested": ["SLP", "ToD", "BESS", "calendar-cycle ridge", "load-lag ridge", "horizons other than H=1"],
        "macro_median_MAE_persistence": pers_med,
        "macro_median_MAE_selected": sel_med,
        "shrink_meter_lambda_counts": lam_counts,
        "shrink_meter_meters_better": int(shrink_paired.meters_mae_better),
        "shrink_meter_meters_worse": int(shrink_paired.meters_mae_worse),
        "shrink_meter_meters_tie": int(shrink_paired.meters_tie),
        "interpretation": (
            "Pooled test MAE can fall slightly while the median meter does not improve. "
            "The Experiment 013 band allows a median MAE up to 5% worse than persistence; "
            "meeting that band is not a meter-wide win."
        ),
    }
    (OUT / "experiment_015_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "model_config_015.json").write_text(json.dumps({
        "split": {"train_before": "2020-07-01", "validation_before": "2021-01-01", "test_from": "2021-01-01"},
        "eligibility": {"min_train": MIN_TRAIN, "min_val": MIN_VAL, "min_test": MIN_TEST},
        "lags": list(LAGS),
        "lag_definition": "column k uses ΔP(t-k+1); column 0 is ΔP(t)=P(t)-P(t-1), known at forecast time",
        "target": "ΔP(t+1)=P(t+1)-P(t); load forecast P(t)+delta_hat",
        "ridge_alphas": list(RIDGE_ALPHAS),
        "lambdas": list(LAMBDAS),
        "gate_percentiles": list(GATE_PCTS),
        "huber_epsilon": list(HUBER_EPS),
        "huber_alpha": list(HUBER_ALPHAS),
        "seed_bootstrap": SEED,
        "scaler": "StandardScaler fit on train for tuning; refit on train+validation before test predictions",
        "selection": "lowest validation micro MAE among learned models; test not used",
        "per_meter": configs,
        "shrink_global_lambda": best_global_lam,
        "summary": summary,
    }, indent=2), encoding="utf-8")
    (OUT / "feature_definitions.json").write_text(json.dumps({
        "delta_lags": [f"delta_lag_{k}" for k in LAGS],
        "gate_feature": "|ΔP(t)| = |P(t)-P(t-1)|",
        "forbidden_at_inference": ["actual ΔP(t+1)", "actual P(t+1)", "test error", "test movement tertile"],
        "retrospective_only": "movement_group tertiles of |ΔP(t+1)| from each meter's training distribution",
        "subgroups": {
            "peak_17_21": "target timestamp hour 17 through 21 inclusive",
            "weekend": "target timestamp dayofweek >= 5",
            "high_load_meter": "meter training-mean load >= median of eligible meters",
            "near_zero_load_lt_0.05": "retrospective |actual load| < 0.05 kW",
        },
    }, indent=2), encoding="utf-8")

    # Figures
    order = list(MODELS)
    mall = micro[micro.scope == "all"].set_index("model").reindex(order)
    f, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(order))
    ax.bar(x - 0.15, mall.MAE, width=0.3, label="MAE")
    ax.bar(x + 0.15, mall.RMSE, width=0.3, label="RMSE")
    ax.set_xticks(x)
    ax.set_xticklabels(order, rotation=25, ha="right")
    ax.set(ylabel="kW", title="Experiment 015 test error vs persistence (zero_change)")
    ax.legend()
    save_fig(f, FIG / "exp015_mae_rmse_vs_persistence.png")

    diff = pd.read_csv(OUT / "per_meter_mae_diff.csv")
    f, ax = plt.subplots(figsize=(9, 4))
    show = ["ridge_delta", "shrink_global", "gate_recent", "huber_delta"]
    for i, name in enumerate(show):
        ax.hist(diff[diff.model == name].mae_diff, bins=20, alpha=0.45, label=name)
    ax.axvline(0, color="black", lw=1)
    ax.set(xlabel="Meter MAE − persistence MAE (kW)", ylabel="Meters", title="Per-meter MAE difference")
    ax.legend(fontsize=8)
    save_fig(f, FIG / "exp015_per_meter_mae_diff.png")

    pick = preds.groupby("meter").train_mean_abs_delta.first()
    meter_id = (pick - pick.median()).abs().idxmin()
    sample = preds[preds.meter == meter_id].sort_values("time").head(288)
    f, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(sample.actual_delta, sample.pred_delta_ridge, s=8, alpha=0.7, label="Ridge")
    ax.scatter(sample.actual_delta, sample.pred_delta_huber, s=8, alpha=0.7, label="Huber")
    lim = float(np.nanmax(np.abs(sample[["actual_delta", "pred_delta_ridge", "pred_delta_huber"]].to_numpy())))
    ax.plot([-lim, lim], [-lim, lim], color="black", lw=1)
    ax.set(xlabel="Actual ΔP (kW)", ylabel="Predicted ΔP (kW)", title=f"Meter {meter_id}, first 288 test steps")
    ax.legend()
    save_fig(f, FIG / "exp015_delta_actual_vs_predicted.png")

    f, ax = plt.subplots(figsize=(7, 4))
    ax.hist(preds.actual_load - preds.pred_load_zero_change, bins=60, alpha=0.55, label="Persistence")
    ax.hist(preds.actual_load - preds[f"pred_load_{selected}"], bins=60, alpha=0.55, label=selected)
    ax.set(xlabel="Actual − predicted load (kW)", title="Test error distribution")
    ax.legend()
    save_fig(f, FIG / "exp015_error_distribution.png")

    sub = pd.read_csv(OUT / "subgroup_load_metrics.csv")
    labels = ["peak_17_21", "offpeak", "weekday", "weekend", "low_load_meter", "high_load_meter"]
    f, ax = plt.subplots(figsize=(9, 4))
    width = 0.15
    for i, name in enumerate(("zero_change", "ridge_delta", "shrink_global", "gate_recent")):
        part = sub[sub.model == name].set_index("subgroup").reindex(labels)
        ax.bar(np.arange(len(labels)) + i * width, part.MAE, width=width, label=name)
    ax.set_xticks(np.arange(len(labels)) + 1.5 * width)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set(ylabel="Micro MAE (kW)", title="Subgroup MAE (rules in feature_definitions.json)")
    ax.legend(fontsize=8)
    save_fig(f, FIG / "exp015_subgroup_mae.png")

    labs = ["retrospective_movement_low", "retrospective_movement_mid", "retrospective_movement_high"]
    f, ax = plt.subplots(figsize=(8, 4))
    for i, name in enumerate(("zero_change", "ridge_delta", "shrink_global", "gate_recent", "huber_delta")):
        part = sub[sub.model == name].set_index("subgroup").reindex(labs)
        ax.bar(np.arange(len(labs)) + i * width, part.MAE, width=width, label=name)
    ax.set_xticks(np.arange(len(labs)) + 2 * width)
    ax.set_xticklabels(["low |ΔP|", "mid |ΔP|", "high |ΔP|"])
    ax.set(ylabel="Micro MAE (kW)", title="Retrospective only: realized |ΔP(t+1)| tertiles")
    ax.legend(fontsize=8)
    save_fig(f, FIG / "exp015_retrospective_movement.png")

    f, ax = plt.subplots(figsize=(7, 4))
    ax.bar(np.arange(len(val_sel)), val_sel.validation_micro_MAE)
    ax.set_xticks(np.arange(len(val_sel)))
    ax.set_xticklabels(val_sel.model, rotation=25, ha="right")
    ax.set(ylabel="Validation micro MAE (kW)", title="Selection scores (test not used)")
    save_fig(f, FIG / "exp015_validation_selection.png")

    for src in ("exp015_mae_rmse_vs_persistence.png", "exp015_retrospective_movement.png"):
        PPT.mkdir(parents=True, exist_ok=True)
        (PPT / src).write_bytes((FIG / src).read_bytes())

    print(micro[micro.scope == "all"][["model", "MAE", "RMSE", "R2"]].to_string(index=False))
    print("selected", selected, "competent", competent, "global_lambda", best_global_lam)
    print("014 reproduction", ref_note)
    print(f"elapsed_sec {elapsed:.1f}")
    print("eligible", int(elig.eligible.sum()), "of", len(elig), "rows", len(preds))


if __name__ == "__main__":
    main()

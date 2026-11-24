#!/usr/bin/env python3
"""Experiment 014: per-meter load-change (residual) forecasting. No SLP."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "forecasting" / "experiment_014"
FIG = ROOT / "results" / "figures" / "forecasting"
PPT = ROOT / "results" / "figures" / "ppt_ready"
PRED = ROOT / "results" / "forecasting" / "predictions" / "experiment_014"

TRAIN_END = np.datetime64("2020-07-01")
VAL_END = np.datetime64("2021-01-01")
COMMON_END = np.datetime64("2021-02-21")
MIN_TRAIN = 96 * 14
MIN_VAL = 96 * 3
MIN_TEST = 96 * 3
RIDGE_ALPHAS = (0.1, 1.0, 10.0, 100.0)
LAGS = (1, 2, 4, 8, 12, 24, 48, 96)
MAPE_MIN = 0.05
H_PRIMARY = 1
H_EXTRA = (2, 4, 8)
WILCOX_STRIDE = 8
DPI = 300
plt.rcParams.update({"font.size": 11, "figure.dpi": DPI})

MODELS_H1 = (
    "zero_change",
    "ridge_delta",
    "ridge_load",
    "ridge_both",
    "ridge_delta_cyclic",
)


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


def fit_ridge_delta_mae(Xtr, ytr, Xva, yva, Xte):
    best_a, best_mae = None, np.inf
    scaler = StandardScaler().fit(Xtr)
    Ztr, Zva = scaler.transform(Xtr), scaler.transform(Xva)
    for alpha in RIDGE_ALPHAS:
        model = Ridge(alpha=alpha)
        model.fit(Ztr, ytr)
        mae = float(np.mean(np.abs(model.predict(Zva) - yva)))
        if mae < best_mae:
            best_mae, best_a = mae, alpha
    Xall = np.vstack([Xtr, Xva])
    yall = np.concatenate([ytr, yva])
    scaler = StandardScaler().fit(Xall)
    model = Ridge(alpha=best_a)
    model.fit(scaler.transform(Xall), yall)
    return model.predict(scaler.transform(Xte)), best_a, best_mae, scaler


def design(
    y: np.ndarray,
    times: np.ndarray,
    horizon: int = 1,
) -> dict:
    """Origin t: predict delta P(t+H)-P(t); load forecast P(t)+delta_hat."""
    n = len(y)
    d = np.full(n, np.nan, dtype=np.float64)
    d[1:] = y[1:] - y[:-1]
    origin = np.arange(96, n - horizon)
    target_delta = y[origin + horizon] - y[origin]
    load_t = y[origin]
    actual_load = y[origin + horizon]
    target_times = times[origin] + np.timedelta64(15 * horizon, "m")
    tslot = ((target_times.astype("datetime64[m]").astype(np.int64) // 15) % 96).astype(np.float64)
    dow = (target_times.astype("datetime64[D]").astype(np.int64) + 3) % 7
    delta_X = np.column_stack([d[origin - (k - 1)] for k in LAGS])
    load_X = np.column_stack([y[origin - (k - 1)] for k in LAGS])
    cyc = np.column_stack([
        np.sin(2 * np.pi * tslot / 96),
        np.cos(2 * np.pi * tslot / 96),
        np.sin(2 * np.pi * dow / 7),
        np.cos(2 * np.pi * dow / 7),
        (dow >= 5).astype(np.float64),
    ])
    ok = (
        np.isfinite(target_delta)
        & np.isfinite(load_t)
        & np.isfinite(delta_X).all(axis=1)
        & np.isfinite(load_X).all(axis=1)
    )
    return {
        "origin_times": times[origin][ok],
        "target_delta": target_delta[ok],
        "load_t": load_t[ok],
        "actual_load": actual_load[ok],
        "delta_X": delta_X[ok],
        "load_X": load_X[ok],
        "cyc": cyc[ok],
        "tslot": tslot[ok],
        "dow": dow[ok],
    }


def competency(micro_pers_mae: float, micro_model_mae: float, macro_pers_med: float, macro_model_med: float, city_rows: list[dict]) -> dict:
    ok_micro = micro_model_mae <= 1.02 * micro_pers_mae
    ok_macro = macro_model_med <= 1.05 * macro_pers_med
    ok_city = all(r["model_MAE"] <= 1.10 * r["pers_MAE"] for r in city_rows)
    return {
        "micro_ok": bool(ok_micro),
        "macro_ok": bool(ok_macro),
        "city_ok": bool(ok_city),
        "competent": bool(ok_micro and ok_macro and ok_city),
    }


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
    rows_delta_metrics = []
    rows_load_metrics = []
    rows_sub = []
    rows_move = []
    rows_horizon = []
    pred_chunks = []
    configs = []
    train_abs_delta = []
    zero_check_max = 0.0

    for (meter, city), g in bins.groupby(["meter_id", "city"], sort=True):
        g = g.sort_values("bin")
        times = g.bin.to_numpy(dtype="datetime64[ns]")
        yraw = g.load_kw.to_numpy(dtype=np.float64)
        full_t = np.arange(times[0], times[-1] + np.timedelta64(15, "m"), np.timedelta64(15, "m"))
        y = np.full(len(full_t), np.nan)
        pos = ((times - full_t[0]) / np.timedelta64(15, "m")).astype(np.int64)
        y[pos] = yraw

        D = design(y, full_t, horizon=H_PRIMARY)
        t_origin = D["origin_times"]
        tr = split_mask(t_origin, np.datetime64("2019-01-01"), TRAIN_END)
        va = split_mask(t_origin, TRAIN_END, VAL_END)
        te = t_origin >= VAL_END
        usable_train = int(tr.sum())
        usable_val = int(va.sum())
        usable_test = int(te.sum())
        eligible = usable_train >= MIN_TRAIN and usable_val >= MIN_VAL and usable_test >= MIN_TEST
        rows_elig.append({
            "meter": meter,
            "city": city,
            "usable_train_rows": usable_train,
            "usable_validation_rows": usable_val,
            "usable_test_rows": usable_test,
            "eligible": eligible,
            "reason": "eligible" if eligible else "below_minimum_usable_rows",
        })
        if not eligible:
            print(meter, "skip", flush=True)
            continue

        print(meter, "fit", flush=True)
        yd_tr, yd_va, yd_te = D["target_delta"][tr], D["target_delta"][va], D["target_delta"][te]
        load_tr, load_te = D["load_t"][tr], D["load_t"][te]
        actual_te = D["actual_load"][te]
        train_mean_abs_delta = float(np.mean(np.abs(yd_tr)))
        train_abs_delta.append({"meter": meter, "city": city, "train_mean_abs_delta": train_mean_abs_delta})

        pred_delta = {"zero_change": np.zeros_like(yd_te)}
        pred_load = {
            "zero_change": load_te,
            "persistence": load_te,
        }
        cfg = {"meter": meter}

        pred_d, a_d, vm_d, _ = fit_ridge_delta_mae(
            D["delta_X"][tr], yd_tr, D["delta_X"][va], yd_va, D["delta_X"][te]
        )
        pred_delta["ridge_delta"] = pred_d
        pred_load["ridge_delta"] = load_te + pred_d
        cfg.update({"ridge_delta_alpha": a_d, "val_mae_delta_ridge_delta": vm_d})

        pred_d, a_l, vm_l, _ = fit_ridge_delta_mae(
            D["load_X"][tr], yd_tr, D["load_X"][va], yd_va, D["load_X"][te]
        )
        pred_delta["ridge_load"] = pred_d
        pred_load["ridge_load"] = load_te + pred_d
        cfg.update({"ridge_load_alpha": a_l, "val_mae_delta_ridge_load": vm_l})

        Xb_tr = np.hstack([D["delta_X"][tr], D["load_X"][tr]])
        Xb_va = np.hstack([D["delta_X"][va], D["load_X"][va]])
        Xb_te = np.hstack([D["delta_X"][te], D["load_X"][te]])
        pred_d, a_b, vm_b, _ = fit_ridge_delta_mae(Xb_tr, yd_tr, Xb_va, yd_va, Xb_te)
        pred_delta["ridge_both"] = pred_d
        pred_load["ridge_both"] = load_te + pred_d
        cfg.update({"ridge_both_alpha": a_b, "val_mae_delta_ridge_both": vm_b})

        Xc_tr = np.hstack([D["delta_X"][tr], D["cyc"][tr]])
        Xc_va = np.hstack([D["delta_X"][va], D["cyc"][va]])
        Xc_te = np.hstack([D["delta_X"][te], D["cyc"][te]])
        pred_d, a_c, vm_c, _ = fit_ridge_delta_mae(Xc_tr, yd_tr, Xc_va, yd_va, Xc_te)
        pred_delta["ridge_delta_cyclic"] = pred_d
        pred_load["ridge_delta_cyclic"] = load_te + pred_d
        cfg.update({"ridge_delta_cyclic_alpha": a_c, "val_mae_delta_ridge_delta_cyclic": vm_c})
        configs.append(cfg)

        zc = pred_load["zero_change"]
        pers = pred_load["persistence"]
        zero_check_max = max(zero_check_max, float(np.max(np.abs(zc - pers))))

        train_level = float(np.nanmean(y[full_t < TRAIN_END]))
        for name in MODELS_H1:
            rows_delta_metrics.append({
                "meter": meter,
                "city": city,
                "model": name,
                **metric_pack(yd_te, pred_delta[name]),
            })
            rows_load_metrics.append({
                "meter": meter,
                "city": city,
                "model": name,
                "train_mean_kw": train_level,
                "train_mean_abs_delta": train_mean_abs_delta,
                **metric_pack(actual_te, pred_load[name]),
            })

        tert = np.nanpercentile(np.abs(yd_tr), [33.33, 66.67])
        move_labels = {
            "movement_low": np.abs(yd_te) <= tert[0],
            "movement_mid": (np.abs(yd_te) > tert[0]) & (np.abs(yd_te) <= tert[1]),
            "movement_high": np.abs(yd_te) > tert[1],
        }
        for label, mask in move_labels.items():
            if mask.sum() < 20:
                continue
            for name in ("zero_change", "ridge_delta", "ridge_both"):
                rows_move.append({
                    "meter": meter,
                    "city": city,
                    "movement_group": label,
                    "model": name,
                    **metric_pack(actual_te[mask], pred_load[name][mask]),
                })

        hour = (D["tslot"][te] // 4).astype(int)
        weekend = D["dow"][te] >= 5
        subgroups = {
            "peak_17_21": (hour >= 17) & (hour <= 21),
            "offpeak": ~((hour >= 17) & (hour <= 21)),
            "weekday": ~weekend,
            "weekend": weekend,
            "near_zero_lt_0.05": np.abs(actual_te) < MAPE_MIN,
        }
        for label, mask in subgroups.items():
            if mask.sum() < 20:
                continue
            for name in ("zero_change", "ridge_delta", "ridge_both"):
                rows_sub.append({
                    "meter": meter,
                    "city": city,
                    "subgroup": label,
                    "model": name,
                    **metric_pack(actual_te[mask], pred_load[name][mask]),
                })

        chunk = pd.DataFrame({
            "meter": meter,
            "city": city,
            "time": pd.to_datetime(t_origin[te]),
            "actual_load": actual_te,
            "actual_delta": yd_te,
            "load_t": load_te,
            "train_mean_kw": train_level,
            "train_mean_abs_delta": train_mean_abs_delta,
        })
        for name in MODELS_H1:
            chunk[f"pred_delta_{name}"] = pred_delta[name]
            chunk[f"pred_load_{name}"] = pred_load[name]
        pred_chunks.append(chunk)

        for H in H_EXTRA:
            Dh = design(y, full_t, horizon=H)
            te_h = Dh["origin_times"] >= VAL_END
            if te_h.sum() < MIN_TEST:
                continue
            yd_h = Dh["target_delta"][te_h]
            load_h = Dh["load_t"][te_h]
            actual_h = Dh["actual_load"][te_h]
            tr_h = split_mask(Dh["origin_times"], np.datetime64("2019-01-01"), TRAIN_END)
            va_h = split_mask(Dh["origin_times"], TRAIN_END, VAL_END)
            pred_h = {"zero_change": load_h}
            if tr_h.sum() >= MIN_TRAIN and va_h.sum() >= MIN_VAL:
                pd_h, _, _, _ = fit_ridge_delta_mae(
                    Dh["delta_X"][tr_h],
                    Dh["target_delta"][tr_h],
                    Dh["delta_X"][va_h],
                    Dh["target_delta"][va_h],
                    Dh["delta_X"][te_h],
                )
                pred_h["ridge_delta"] = load_h + pd_h
            for name, ph in pred_h.items():
                rows_horizon.append({
                    "horizon": H,
                    "meter": meter,
                    "city": city,
                    "model": name,
                    **metric_pack(actual_h, ph),
                })

    if zero_check_max > 1e-9:
        print(f"FATAL: zero_change != persistence, max diff {zero_check_max}", file=sys.stderr)
        sys.exit(1)
    print(f"zero_change check OK, max |diff| = {zero_check_max}")

    elig = pd.DataFrame(rows_elig)
    delta_m = pd.DataFrame(rows_delta_metrics)
    load_m = pd.DataFrame(rows_load_metrics)
    preds = pd.concat(pred_chunks, ignore_index=True)
    elig.to_csv(OUT / "per_meter_eligibility.csv", index=False)
    delta_m.to_csv(OUT / "per_meter_delta_metrics.csv", index=False)
    load_m.to_csv(OUT / "per_meter_load_metrics.csv", index=False)
    pd.DataFrame(rows_sub).to_csv(OUT / "subgroup_metrics_per_meter.csv", index=False)
    pd.DataFrame(rows_move).to_csv(OUT / "movement_subgroup_metrics.csv", index=False)
    pd.DataFrame(rows_horizon).to_csv(OUT / "horizon_load_metrics.csv", index=False)
    preds.to_parquet(PRED / "test_predictions.parquet", index=False)

    micro_load = []
    micro_delta = []
    for name in MODELS_H1:
        col = f"pred_load_{name}"
        dcol = f"pred_delta_{name}"
        micro_load.append({"model": name, "scope": "all", **metric_pack(preds.actual_load, preds[col])})
        micro_delta.append({"model": name, "scope": "all", **metric_pack(preds.actual_delta, preds[dcol])})
        for city, g in preds.groupby("city"):
            micro_load.append({"model": name, "scope": city, **metric_pack(g.actual_load, g[col])})
            micro_delta.append({"model": name, "scope": city, **metric_pack(g.actual_delta, g[dcol])})
        common = preds[preds.time < pd.Timestamp("2021-02-21")]
        micro_load.append({
            "model": name,
            "scope": "common_through_2021_02_20",
            **metric_pack(common.actual_load, common[col]),
        })
    micro_l = pd.DataFrame(micro_load)
    micro_d = pd.DataFrame(micro_delta)
    micro_l.to_csv(OUT / "micro_load_metrics.csv", index=False)
    micro_d.to_csv(OUT / "micro_delta_metrics.csv", index=False)

    macro_rows = []
    for model, g in load_m.groupby("model"):
        for col in ("MAE", "RMSE", "WAPE", "R2"):
            s = g[col]
            macro_rows.append({
                "model": model,
                "metric": col,
                "macro_mean": float(s.mean()),
                "median": float(s.median()),
                "n_meters": int(len(s)),
            })
    macro = pd.DataFrame(macro_rows)
    macro.to_csv(OUT / "macro_load_metrics.csv", index=False)

    pers_all = micro_l[(micro_l.model == "zero_change") & (micro_l.scope == "all")].iloc[0]
    comp = []
    for _, r in micro_l.iterrows():
        base = micro_l[(micro_l.model == "zero_change") & (micro_l.scope == r.scope)].iloc[0]
        comp.append({
            "model": r.model,
            "scope": r.scope,
            "MAE": r.MAE,
            "persistence_MAE": base.MAE,
            "mae_improvement_pct": 100 * (base.MAE - r.MAE) / base.MAE if base.MAE else np.nan,
        })
    pd.DataFrame(comp).to_csv(OUT / "persistence_comparison.csv", index=False)

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
        "near_zero_lt_0.05": preds.actual_load.abs() < MAPE_MIN,
    }
    sub_micro = []
    for label, mask in scope_masks.items():
        part = preds.loc[mask]
        for name in ("zero_change", "ridge_delta", "ridge_both", "ridge_delta_cyclic"):
            sub_micro.append({
                "subgroup": label,
                "model": name,
                **metric_pack(part.actual_load, part[f"pred_load_{name}"]),
            })
    pd.DataFrame(sub_micro).to_csv(OUT / "subgroup_load_metrics.csv", index=False)

    # Wilcoxon: best ridge vs persistence on reconstructed load
    best_name = "ridge_both"
    ae_p = np.abs(preds.actual_load - preds.pred_load_zero_change)
    ae_m = np.abs(preds.actual_load - preds[f"pred_load_{best_name}"])
    diff = ae_p - ae_m
    stride_idx = np.arange(0, len(diff), WILCOX_STRIDE)
    wstat, wp = stats.wilcoxon(diff[stride_idx], alternative="greater", zero_method="wilcox")
    wilcox_rows = [{
        "comparison": f"{best_name}_vs_zero_change",
        "n_pairs_total": int(len(diff)),
        "n_pairs_tested": int(len(stride_idx)),
        "mean_ae_reduction_kw": float(diff.mean()),
        "median_ae_reduction_kw": float(np.median(diff)),
        "wilcoxon_stat": float(wstat),
        "p_value": float(wp),
    }]
    for name in ("ridge_delta", "ridge_load", "ridge_delta_cyclic"):
        ae_m2 = np.abs(preds.actual_load - preds[f"pred_load_{name}"])
        d2 = ae_p - ae_m2
        idx2 = np.arange(0, len(d2), WILCOX_STRIDE)
        ws2, wp2 = stats.wilcoxon(d2[idx2], alternative="greater", zero_method="wilcox")
        wilcox_rows.append({
            "comparison": f"{name}_vs_zero_change",
            "n_pairs_total": int(len(d2)),
            "n_pairs_tested": int(len(idx2)),
            "mean_ae_reduction_kw": float(d2.mean()),
            "median_ae_reduction_kw": float(np.median(d2)),
            "wilcoxon_stat": float(ws2),
            "p_value": float(wp2),
        })
    pd.DataFrame(wilcox_rows).to_csv(OUT / "statistical_tests.csv", index=False)

    pers_med = load_m[load_m.model == "zero_change"].MAE.median()
    best_med = load_m[load_m.model == best_name].MAE.median()
    city_comp = []
    for city in ("Mathura", "Bareilly"):
        pr = micro_l[(micro_l.model == "zero_change") & (micro_l.scope == city)].iloc[0].MAE
        br = micro_l[(micro_l.model == best_name) & (micro_l.scope == city)].iloc[0].MAE
        city_comp.append({"city": city, "pers_MAE": pr, "model_MAE": br})
    comp_rule = competency(pers_all.MAE, micro_l[(micro_l.model == best_name) & (micro_l.scope == "all")].iloc[0].MAE, pers_med, best_med, city_comp)

    move_pool = pd.read_csv(OUT / "movement_subgroup_metrics.csv")
    move_agg = move_pool.groupby(["movement_group", "model"]).agg(MAE=("MAE", "mean")).reset_index()

    wins = {}
    for name in MODELS_H1:
        if name == "zero_change":
            continue
        merged = load_m[load_m.model == "zero_change"][["meter", "MAE"]].merge(
            load_m[load_m.model == name][["meter", "MAE"]],
            on="meter",
            suffixes=("_pers", "_model"),
        )
        wins[name] = int((merged.MAE_model < merged.MAE_pers).sum())

    summary = {
        "experiment": "014",
        "zero_change_equals_persistence_max_abs_diff": zero_check_max,
        "eligible_meters": int(elig.eligible.sum()),
        "test_rows": int(len(preds)),
        "micro_load_MAE": micro_l[micro_l.scope == "all"].set_index("model")["MAE"].to_dict(),
        "micro_delta_MAE": micro_d[micro_d.scope == "all"].set_index("model")["MAE"].to_dict(),
        "best_model_by_micro_load_MAE": str(micro_l[micro_l.scope == "all"].sort_values("MAE").iloc[0]["model"]),
        "competency_ridge_both": comp_rule,
        "meters_MAE_won_vs_persistence": wins,
        "decision_case": None,
    }
    if comp_rule["competent"]:
        summary["decision_case"] = "A"
        summary["next_step"] = "May proceed to leakage-safe SLP ablation (not run here)."
    elif move_agg[(move_agg.movement_group == "movement_high") & (move_agg.model == "ridge_delta")].MAE.iloc[0] < move_agg[
        (move_agg.movement_group == "movement_high") & (move_agg.model == "zero_change")
    ].MAE.iloc[0]:
        summary["decision_case"] = "B"
        summary["next_step"] = "Do not add SLP; residual skill may be localized to large movements only."
    else:
        summary["decision_case"] = "C"
        summary["next_step"] = "Do not add SLP; re-evaluate target or features."

    config = {
        "experiment": "014",
        "horizon_primary": H_PRIMARY,
        "horizons_extra": list(H_EXTRA),
        "target": "delta_P(t+H) = P(t+H) - P(t); reconstructed load = P(t) + delta_hat",
        "zero_change": "delta_hat=0 => load forecast P(t) (H=1 persistence)",
        "split": {"train_before": "2020-07-01", "validation_before": "2021-01-01", "test_from": "2021-01-01"},
        "ridge_alphas": list(RIDGE_ALPHAS),
        "ridge_tuning": "validation MAE on delta target",
        "models": list(MODELS_H1),
        "competency_rule": "same as Experiment 013 on reconstructed load MAE",
        "eligible_meters": int(elig.eligible.sum()),
        "per_meter_selected": configs,
    }
    (OUT / "model_config_014.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (OUT / "experiment_014_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Figures
    f, ax = plt.subplots(figsize=(7, 4))
    ax.hist(preds.actual_delta, bins=80, color="steelblue", alpha=0.85)
    ax.set(xlabel="Actual ΔP (kW)", ylabel="Count", title="Test-set load changes (H=1)")
    save_fig(f, FIG / "exp014_delta_distribution.png")

    sample_n = min(50000, len(preds))
    samp = preds.sample(sample_n, random_state=0)
    f, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(samp.actual_delta, samp.pred_delta_ridge_delta, s=3, alpha=0.2)
    lim = max(np.abs(samp.actual_delta).max(), np.abs(samp.pred_delta_ridge_delta).max())
    ax.plot([-lim, lim], [-lim, lim], "k", lw=1)
    ax.set(xlabel="Actual ΔP", ylabel="Predicted ΔP (ridge_delta)", title="Delta actual vs predicted")
    save_fig(f, FIG / "exp014_delta_actual_vs_predicted.png")

    order = list(MODELS_H1)
    micro_all = micro_l[micro_l.scope == "all"].set_index("model").reindex(order)
    f, ax = plt.subplots(figsize=(9, 4))
    ax.bar(np.arange(len(order)), micro_all.MAE)
    ax.set_xticks(np.arange(len(order)))
    ax.set_xticklabels(order, rotation=25, ha="right")
    ax.set(ylabel="Micro MAE on reconstructed load (kW)", title="Experiment 014 — reconstructed load MAE")
    save_fig(f, FIG / "exp014_reconstructed_mae.png")

    pers_m = load_m[load_m.model == "zero_change"]
    ridge_m = load_m[load_m.model == best_name]
    both = pers_m[["meter", "MAE"]].merge(ridge_m[["meter", "MAE"]], on="meter", suffixes=("_pers", "_ridge"))
    f, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(both.MAE_pers, both.MAE_ridge, s=18)
    lim = max(both.MAE_pers.max(), both.MAE_ridge.max())
    ax.plot([0, lim], [0, lim], "k", lw=1)
    ax.set(xlabel="Persistence MAE", ylabel=f"{best_name} MAE", title="Per meter")
    save_fig(f, FIG / "exp014_persistence_vs_residual_ridge.png")

    move_plot = move_pool.groupby(["movement_group", "model"]).MAE.mean().unstack("model")
    f, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(move_plot))
    width = 0.25
    for i, m in enumerate(("zero_change", "ridge_delta", "ridge_both")):
        if m in move_plot.columns:
            ax.bar(x + i * width, move_plot[m], width, label=m)
    ax.set_xticks(x + width)
    ax.set_xticklabels(move_plot.index, rotation=15)
    ax.set(ylabel="Mean MAE (kW)", title="Reconstructed load MAE by |ΔP| tertile")
    ax.legend()
    save_fig(f, FIG / "exp014_mae_by_movement.png")

    city = micro_l[micro_l.scope.isin(["Mathura", "Bareilly"])]
    f, ax = plt.subplots(figsize=(9, 4))
    width = 0.35
    for i, scope in enumerate(["Mathura", "Bareilly"]):
        part = city[city.scope == scope].set_index("model").reindex(order)
        ax.bar(np.arange(len(order)) + i * width, part.MAE, width=width, label=scope)
    ax.set_xticks(np.arange(len(order)) + width / 2)
    ax.set_xticklabels(order, rotation=25, ha="right")
    ax.set(ylabel="Micro MAE (kW)", title="By city")
    ax.legend()
    save_fig(f, FIG / "exp014_mae_by_city.png")

    load = pd.read_csv(OUT / "subgroup_load_metrics.csv")
    load = load[load.subgroup.isin(["high_load_meter", "low_load_meter"])]
    f, ax = plt.subplots(figsize=(9, 4))
    for i, scope in enumerate(["low_load_meter", "high_load_meter"]):
        part = load[load.subgroup == scope].set_index("model").reindex(order)
        ax.bar(np.arange(len(order)) + i * width, part.MAE, width=width, label=scope)
    ax.set_xticks(np.arange(len(order)) + width / 2)
    ax.set_xticklabels(order, rotation=25, ha="right")
    ax.set(ylabel="Micro MAE (kW)", title="By training load level")
    ax.legend()
    save_fig(f, FIG / "exp014_mae_by_load.png")

    f, ax = plt.subplots(figsize=(10, 4))
    for name, color in zip(order[1:], plt.cm.tab10.colors):
        ax.hist(load_m[load_m.model == name].MAE, bins=18, alpha=0.5, label=name)
    ax.set(xlabel="Per-meter MAE (kW)", title="Per-meter reconstructed-load MAE")
    ax.legend(fontsize=8)
    save_fig(f, FIG / "exp014_per_meter_comparison.png")

    tab = pd.DataFrame(train_abs_delta)
    med_target = tab.train_mean_abs_delta.median()
    pick = tab.iloc[(tab.train_mean_abs_delta - med_target).abs().argsort().iloc[0]].meter
    sample = preds[preds.meter == pick].sort_values("time").head(288)
    f, ax = plt.subplots(figsize=(9, 4))
    ax.plot(sample.actual_load.to_numpy(), color="black", label="Actual")
    ax.plot(sample.pred_load_zero_change.to_numpy(), label="Persistence")
    ax.plot(sample.pred_load_ridge_delta.to_numpy(), label="ridge_delta")
    ax.set(ylabel="kW", xlabel="Test step", title=f"Meter {pick} (median |ΔP| train)")
    ax.legend()
    save_fig(f, FIG / "exp014_example_trace.png")

    f, ax = plt.subplots(figsize=(7, 4))
    ax.hist(preds.actual_load - preds.pred_load_zero_change, bins=60, alpha=0.6, label="Persistence")
    ax.hist(preds.actual_load - preds.pred_load_ridge_both, bins=60, alpha=0.6, label="ridge_both")
    ax.set(xlabel="Actual − predicted load (kW)", title="Reconstructed load errors")
    ax.legend()
    save_fig(f, FIG / "exp014_error_distribution.png")

    for src in ("exp014_reconstructed_mae.png", "exp014_persistence_vs_residual_ridge.png"):
        PPT.mkdir(parents=True, exist_ok=True)
        (PPT / src).write_bytes((FIG / src).read_bytes())

    print(micro_l[micro_l.scope == "all"].to_string(index=False))
    print("summary", json.dumps(summary, indent=2))
    print("eligible", int(elig.eligible.sum()), "of", len(elig))


if __name__ == "__main__":
    main()

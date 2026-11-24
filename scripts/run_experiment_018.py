#!/usr/bin/env python3
"""Experiment 018: leakage-safe SLP forecasting. Does not overwrite Experiments 013–017."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "forecasting" / "experiment_018"
PRE = OUT / "preimplementation"
FIG = ROOT / "results" / "figures" / "forecasting"
PPT = ROOT / "results" / "figures" / "ppt_ready"
PRED = ROOT / "results" / "forecasting" / "predictions" / "experiment_018"
BINS = ROOT / "data/interim/ceew_15min_bins_dedup.parquet"
PROFILES = ROOT / "data/processed/daily_profiles.parquet"
PRED13 = ROOT / "results/forecasting/predictions/experiment_013/test_predictions.parquet"
PRED15 = ROOT / "results/forecasting/predictions/experiment_015/test_predictions.parquet"
SHA15_BEFORE = None

TRAIN_END = np.datetime64("2020-07-01")
VAL_END = np.datetime64("2021-01-01")
ORIGIN_TRAIN_START = np.datetime64("2019-01-01")
MIN_TRAIN = 96 * 14
MIN_VAL = 96 * 3
MIN_TEST = 96 * 3
LAGS = (1, 2, 4, 8, 12, 24, 48, 96)
RIDGE_ALPHAS = (0.1, 1.0, 10.0, 100.0)
K_PRIMARY = 2
SEED = 18
N_BOOT = 2000
TOL = 1e-6
DPI = 300
plt.rcParams.update({"font.size": 11, "figure.dpi": DPI})

MODELS_ORDER = (
    "persistence",
    "frozen_shrink_015",
    "frozen_ridge_lag_cyclic_013",
    "ridge_delta_cyclic",
    "ridge_delta_cyclic_slp",
    "ridge_delta_cyclic_slp_corr",
    "ridge_delta_cyclic_slp_noise",
)


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


def split_mask(times: np.ndarray, start, end) -> np.ndarray:
    return (times >= start) & (times < end)


def peak_norm_vec(v: np.ndarray) -> np.ndarray | None:
    v = np.asarray(v, dtype=np.float64)
    if v.size != 96 or not np.isfinite(v).all():
        return None
    p = float(v.max())
    if p <= 0:
        return None
    return v / p


class CausalSLP:
    """Peak-normalized K=2 centroids fit only from profiles dated < cutoff day."""

    def __init__(self, daily: pd.DataFrame):
        rows_p, rows_d, rows_m = [], [], []
        for _, r in daily.iterrows():
            p = peak_norm_vec(np.asarray(r.profile_kw))
            if p is None:
                continue
            rows_p.append(p)
            rows_d.append(np.datetime64(pd.Timestamp(r.date).normalize()))
            rows_m.append(str(r.meter_id))
        self.P = np.vstack(rows_p) if rows_p else np.zeros((0, 96))
        self.dates = np.asarray(rows_d, dtype="datetime64[D]")
        self.meters = np.asarray(rows_m)
        self.by_meter_p: dict[str, np.ndarray] = {}
        self.by_meter_d: dict[str, np.ndarray] = {}
        for m in np.unique(self.meters):
            sel = self.meters == m
            self.by_meter_p[m] = self.P[sel]
            self.by_meter_d[m] = self.dates[sel]
        self._centroid_cache: dict[np.datetime64, tuple[np.ndarray, int]] = {}
        self._meter_cache: dict[tuple[str, np.datetime64], dict] = {}

    def centroids_at(self, cutoff: np.datetime64) -> tuple[np.ndarray, int]:
        if cutoff in self._centroid_cache:
            return self._centroid_cache[cutoff]
        sel = self.dates < cutoff
        Pm = self.P[sel]
        if len(Pm) < K_PRIMARY * 10:
            cent = np.full((K_PRIMARY, 96), np.nan)
            self._centroid_cache[cutoff] = (cent, len(Pm))
            return cent, len(Pm)
        km = KMeans(n_clusters=K_PRIMARY, random_state=SEED, n_init=10)
        cent = km.fit(Pm).cluster_centers_
        self._centroid_cache[cutoff] = (cent, len(Pm))
        return cent, len(Pm)

    def features(self, meter: str, cutoff: np.datetime64) -> dict:
        key = (meter, cutoff)
        if key in self._meter_cache:
            return dict(self._meter_cache[key])
        centroids, n_hist = self.centroids_at(cutoff)
        out = {
            "centroid_cutoff_date": str(cutoff),
            "n_profiles_in_centroid_fit": n_hist,
            "latest_profile_date": None,
            "slp_nearest_dist": np.nan,
            "slp_nearest_centroid": -1,
            "slp_trailing_corr": np.nan,
        }
        if meter not in self.by_meter_p:
            self._meter_cache[key] = out
            return out
        dates, profs = self.by_meter_d[meter], self.by_meter_p[meter]
        before = dates < cutoff
        if not before.any():
            self._meter_cache[key] = out
            return out
        idx = np.where(before)[0][-1]
        latest = profs[idx]
        latest_date = dates[idx]
        if not np.isfinite(centroids).all():
            out["latest_profile_date"] = str(latest_date)
            self._meter_cache[key] = out
            return out
        dists = np.sqrt(np.square(latest - centroids).sum(axis=1))
        k = int(np.argmin(dists))
        out.update({
            "latest_profile_date": str(latest_date),
            "slp_nearest_dist": float(dists[k]),
            "slp_nearest_centroid": k,
        })
        last7 = np.where(before)[0][-7:]
        if len(last7) >= 3:
            stack = profs[last7]
            med = np.median(stack, axis=0)
            if np.std(latest) > 1e-12 and np.std(med) > 1e-12:
                out["slp_trailing_corr"] = float(np.corrcoef(latest, med)[0, 1])
        self._meter_cache[key] = out
        return out


def attach_slp_columns(times: np.ndarray, origin_idx: np.ndarray, meter: str, slp: CausalSLP) -> pd.DataFrame:
    cutoffs = times[origin_idx].astype("datetime64[D]")
    uniq = np.unique(cutoffs)
    lut = {c: slp.features(meter, c) for c in uniq}
    rows = [lut[c] for c in cutoffs]
    return pd.DataFrame(rows)


def design_row(y: np.ndarray, times: np.ndarray, slp: CausalSLP, meter: str) -> pd.DataFrame:
    n = len(y)
    d = np.full(n, np.nan)
    d[1:] = y[1:] - y[:-1]
    origin = np.arange(96, n - 1)
    target_delta = y[origin + 1] - y[origin]
    load_t = y[origin]
    target_times = times[origin] + np.timedelta64(15, "m")
    tslot = ((target_times.astype("datetime64[m]").astype(np.int64) // 15) % 96).astype(np.float64)
    dow = (target_times.astype("datetime64[D]").astype(np.int64) + 3) % 7
    delta_X = np.column_stack([d[origin - (k - 1)] for k in LAGS])
    cyc = np.column_stack([
        np.sin(2 * np.pi * tslot / 96),
        np.cos(2 * np.pi * tslot / 96),
        np.sin(2 * np.pi * dow / 7),
        np.cos(2 * np.pi * dow / 7),
        (dow >= 5).astype(np.float64),
    ])
    ok = np.isfinite(target_delta) & np.isfinite(load_t) & np.isfinite(delta_X).all(axis=1)
    o = origin[ok]
    sdf = attach_slp_columns(times, o, meter, slp)
    return pd.DataFrame({
        "origin_time": times[o],
        "target_time": target_times[ok],
        "target_delta": target_delta[ok],
        "load_t": load_t[ok],
        "actual_load": y[o + 1],
        "delta_X": list(delta_X[ok]),
        "cyc": list(cyc[ok]),
        **{c: sdf[c].to_numpy() for c in sdf.columns},
    })


def fit_ridge_delta(Xtr, ytr, Xva, yva, Xte):
    best_a, best_mae = 1.0, np.inf
    scaler = StandardScaler().fit(Xtr)
    for alpha in RIDGE_ALPHAS:
        mae = float(np.mean(np.abs(Ridge(alpha=alpha).fit(scaler.transform(Xtr), ytr).predict(scaler.transform(Xva)) - yva)))
        if mae < best_mae:
            best_mae, best_a = mae, alpha
    Xall = np.vstack([Xtr, Xva])
    yall = np.concatenate([ytr, yva])
    scaler = StandardScaler().fit(Xall)
    pred = Ridge(alpha=best_a).fit(scaler.transform(Xall), yall).predict(scaler.transform(Xte))
    return pred, best_a, best_mae, scaler


def leakage_self_test(slp: CausalSLP, daily: pd.DataFrame) -> dict:
    """Inject a fake future profile; historical origin features must not change."""
    meter = str(daily.meter_id.iloc[0])
    origin = np.datetime64("2020-08-15T12:00:00")
    before = slp.features(meter, origin.astype("datetime64[D]"))
    fake = daily.iloc[0].copy()
    fake["meter_id"] = meter
    fake["date"] = np.datetime64("2025-01-01")
    fake["profile_kw"] = daily.profile_kw.iloc[0]
    daily2 = pd.concat([daily, pd.DataFrame([fake])], ignore_index=True)
    slp2 = CausalSLP(daily2)
    after = slp2.features(meter, origin.astype("datetime64[D]"))
    keys = ("slp_nearest_dist", "slp_nearest_centroid", "n_profiles_in_centroid_fit")
    ok = all(before[k] == after[k] or (np.isnan(before[k]) and np.isnan(after[k])) for k in keys)
    return {"passed": bool(ok), "before": before, "after": after}


def main() -> None:
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    PRED.mkdir(parents=True, exist_ok=True)
    checks: list[tuple[str, bool, str]] = []

    global SHA15_BEFORE
    SHA15_BEFORE = sha256(PRED15)
    micro15 = pd.read_csv(ROOT / "results/forecasting/experiment_015/micro_load_metrics.csv")
    ref_pers = float(micro15[(micro15.model == "zero_change") & (micro15.scope == "all")].MAE.iloc[0])
    ref_shr = float(micro15[(micro15.model == "shrink_meter") & (micro15.scope == "all")].MAE.iloc[0])

    daily = pd.read_parquet(PROFILES, columns=["meter_id", "city", "date", "profile_kw", "completeness"])
    daily = daily[daily.completeness >= 0.999].copy()
    daily["date"] = pd.to_datetime(daily.date).dt.normalize()
    slp = CausalSLP(daily)
    leak_test = leakage_self_test(slp, daily)
    checks.append(("future_profile_injection_unchanged", leak_test["passed"], json.dumps(leak_test, default=str)))

    bins = pd.read_parquet(BINS, columns=["meter_id", "city", "bin", "load_kw", "complete"])
    bins = bins[bins.complete].copy()
    chunks = []
    configs = []
    centroid_hist = []

    for (meter, city), g in bins.groupby(["meter_id", "city"], sort=True):
        g = g.sort_values("bin")
        times = g.bin.to_numpy(dtype="datetime64[ns]")
        yraw = g.load_kw.to_numpy(dtype=np.float64)
        full_t = np.arange(times[0], times[-1] + np.timedelta64(15, "m"), np.timedelta64(15, "m"))
        y = np.full(len(full_t), np.nan)
        pos = ((times - full_t[0]) / np.timedelta64(15, "m")).astype(np.int64)
        y[pos] = yraw
        D = design_row(y, full_t, slp, meter)
        o = D.origin_time.to_numpy(dtype="datetime64[ns]")
        tr = split_mask(o, ORIGIN_TRAIN_START, TRAIN_END)
        va = split_mask(o, TRAIN_END, VAL_END)
        te = o >= VAL_END
        if int(tr.sum()) < MIN_TRAIN or int(va.sum()) < MIN_VAL or int(te.sum()) < MIN_TEST:
            continue
        print(meter, flush=True)
        delta_X = np.vstack(D.delta_X.to_numpy())
        cyc = np.vstack(D.cyc.to_numpy())
        slp_d = D.slp_nearest_dist.to_numpy(dtype=np.float64)
        slp_c = D.slp_trailing_corr.to_numpy(dtype=np.float64)
        slp_k = D.slp_nearest_centroid.to_numpy(dtype=np.int64)
        yd = D.target_delta.to_numpy()
        load_t = D.load_t.to_numpy()
        actual = D.actual_load.to_numpy()
        X_base = np.hstack([delta_X, cyc])
        ok_slp = np.isfinite(slp_d)
        X_slp = np.hstack([delta_X, cyc, slp_d.reshape(-1, 1)])
        ok_corr = ok_slp & np.isfinite(slp_c)
        X_corr = np.hstack([delta_X, cyc, slp_d.reshape(-1, 1), slp_c.reshape(-1, 1)])

        centroid_hist.append(
            D.loc[te, ["origin_time", "target_time", "slp_nearest_dist", "slp_nearest_centroid",
                       "slp_trailing_corr", "latest_profile_date", "centroid_cutoff_date",
                       "n_profiles_in_centroid_fit"]].assign(meter=meter, city=city)
        )

        # noise scale from train slp dist
        tr_ok = tr & ok_slp
        noise_scale = float(np.std(slp_d[tr_ok])) if tr_ok.sum() > 30 else 1.0
        rng = np.random.default_rng(SEED + hash(meter) % 10000)
        slp_noise = rng.normal(0, noise_scale, size=len(slp_d))
        X_noise = np.hstack([delta_X, cyc, slp_noise.reshape(-1, 1)])

        model_specs = {
            "ridge_delta_cyclic": (X_base, tr, va, te),
            "ridge_delta_cyclic_slp": (X_slp, tr & ok_slp, va & ok_slp, te & ok_slp),
            "ridge_delta_cyclic_slp_corr": (X_corr, tr & ok_corr, va & ok_corr, te & ok_corr),
            "ridge_delta_cyclic_slp_noise": (X_noise, tr, va, te),
        }
        cfg = {"meter": meter, "city": city, "noise_scale": noise_scale}
        preds_te = {}
        val_mae_load = {}
        te_idx = np.where(te)[0]
        for name, (X, mtr, mva, mte) in model_specs.items():
            fin = np.isfinite(X).all(axis=1)
            mtr2, mva2, mte2 = mtr & fin, mva & fin, mte & fin
            full = np.full(int(te.sum()), np.nan)
            if mtr2.sum() < MIN_TRAIN or mva2.sum() < MIN_VAL or mte2.sum() < MIN_TEST:
                preds_te[name] = full
                continue
            pred_va, alpha, vmae, _ = fit_ridge_delta(X[mtr2], yd[mtr2], X[mva2], yd[mva2], X[mva2])
            val_mae_load[name] = float(np.mean(np.abs(load_t[mva2] + pred_va - actual[mva2])))
            pred_te, alpha, vmae_d, _ = fit_ridge_delta(X[mtr2], yd[mtr2], X[mva2], yd[mva2], X[mte2])
            where_te = np.where(mte2)[0]
            pos = np.searchsorted(te_idx, where_te)
            full[pos] = load_t[mte2] + pred_te
            preds_te[name] = full
            cfg[f"{name}_alpha"] = alpha
            cfg[f"{name}_val_mae_delta"] = vmae_d
            cfg[f"{name}_val_mae_load"] = val_mae_load[name]
        configs.append(cfg)

        chunk = pd.DataFrame({
            "meter": meter,
            "city": city,
            "time": pd.to_datetime(D.origin_time[te]),
            "target_time": pd.to_datetime(D.target_time[te]),
            "actual_load": actual[te],
            "load_t": load_t[te],
            "slp_nearest_dist": slp_d[te],
            "slp_nearest_centroid": slp_k[te],
            "slp_trailing_corr": slp_c[te],
        })
        for name, arr in preds_te.items():
            chunk[f"pred_{name}"] = arr
        chunks.append(chunk)

    preds = pd.concat(chunks, ignore_index=True)
    # merge frozen baselines
    f15 = pd.read_parquet(PRED15, columns=["meter", "time", "pred_load_zero_change", "pred_load_shrink_meter"])
    f13 = pd.read_parquet(PRED13, columns=["meter", "time", "ridge_lag_cyclic", "persistence"])
    f15 = f15.rename(columns={"pred_load_zero_change": "pred_persistence", "pred_load_shrink_meter": "pred_frozen_shrink_015"})
    f13 = f13.rename(columns={"ridge_lag_cyclic": "pred_frozen_ridge_lag_cyclic_013"})
    preds = preds.merge(f15, on=["meter", "time"], how="left")
    preds = preds.merge(f13[["meter", "time", "pred_frozen_ridge_lag_cyclic_013"]], on=["meter", "time"], how="left")
    if len(preds) != 835410:
        checks.append(("test_row_count", False, str(len(preds))))
    else:
        checks.append(("test_row_count", True, "835410"))
    if preds.duplicated(["meter", "time"]).any():
        checks.append(("unique_keys", False, "dup"))
    else:
        checks.append(("unique_keys", True, "ok"))
    sha15_after = sha256(PRED15)
    if sha15_after != SHA15_BEFORE:
        checks.append(("pred15_unchanged", False, sha15_after))
    else:
        checks.append(("pred15_unchanged", True, "sha256 match"))

    rebuild_pers = float(np.mean(np.abs(preds.pred_persistence - preds.actual_load)))
    rebuild_shr = float(np.mean(np.abs(preds.pred_frozen_shrink_015 - preds.actual_load)))
    checks.append(("baseline_pers_repro", abs(rebuild_pers - ref_pers) < TOL, f"{rebuild_pers} vs {ref_pers}"))
    checks.append(("baseline_shr_repro", abs(rebuild_shr - ref_shr) < TOL, f"{rebuild_shr} vs {ref_shr}"))

    # metrics
    micro_rows = []
    per_meter = []
    for col, model in (
        ("pred_persistence", "persistence"),
        ("pred_frozen_shrink_015", "frozen_shrink_015"),
        ("pred_frozen_ridge_lag_cyclic_013", "frozen_ridge_lag_cyclic_013"),
        ("pred_ridge_delta_cyclic", "ridge_delta_cyclic"),
        ("pred_ridge_delta_cyclic_slp", "ridge_delta_cyclic_slp"),
        ("pred_ridge_delta_cyclic_slp_corr", "ridge_delta_cyclic_slp_corr"),
        ("pred_ridge_delta_cyclic_slp_noise", "ridge_delta_cyclic_slp_noise"),
    ):
        ok = np.isfinite(preds[col].to_numpy())
        pack = metric_pack(preds.actual_load[ok], preds[col][ok])
        micro_rows.append({"model": model, "scope": "all", **pack})
        for city, g in preds.groupby("city"):
            micro_rows.append({"model": model, "scope": city, **metric_pack(g.actual_load, g[col])})
        for meter, g in preds.groupby("meter"):
            pm = metric_pack(g.actual_load, g[col])
            per_meter.append({"meter": meter, "city": g.city.iloc[0], "model": model, **pm})

    micro = pd.DataFrame(micro_rows)
    pm = pd.DataFrame(per_meter)
    micro.to_csv(OUT / "experiment_018_micro_metrics.csv", index=False)
    pm.to_csv(OUT / "experiment_018_per_meter_metrics.csv", index=False)

    pers = micro[(micro.model == "persistence") & (micro.scope == "all")].iloc[0]
    best_slp = "ridge_delta_cyclic_slp_corr"
    for c in ("ridge_delta_cyclic_slp_corr", "ridge_delta_cyclic_slp"):
        if c in micro.model.values:
            best_slp = c
    # pick validation-best between slp and slp_corr using val preds - simplified: use micro min MAE on val file skipped; use slp_corr if exists
    val_pick = "ridge_delta_cyclic_slp"
    # select by validation pooled from per-meter val_mae in configs
    # fallback primary report model
    # validation-pooled MAE on load for SLP ablations (018 fits only)
    val_scores = {}
    for c in configs:
        for key in ("ridge_delta_cyclic_slp", "ridge_delta_cyclic_slp_corr", "ridge_delta_cyclic"):
            vk = f"{key}_val_mae_load"
            if vk in c and c[vk] is not None:
                val_scores.setdefault(key, []).append(c[vk])
    val_pooled = {k: float(np.mean(v)) for k, v in val_scores.items()}
    primary = min(val_pooled, key=lambda k: val_pooled[k]) if val_pooled else "ridge_delta_cyclic_slp"

    pers_pm = pm[pm.model == "persistence"].set_index("meter")["MAE"]
    slp_pm = pm[pm.model == primary].set_index("meter")["MAE"]
    diff = slp_pm - pers_pm
    rng = np.random.default_rng(SEED)
    boots = [float(np.median(diff.to_numpy()[rng.integers(0, len(diff), len(diff))])) for _ in range(N_BOOT)]
    wil = stats.wilcoxon(diff.to_numpy(), zero_method="pratt", alternative="two-sided")
    stat_rows = [{
        "comparison": f"{primary}_vs_persistence",
        "n_meters": int(len(diff)),
        "n_improved": int((diff < -1e-12).sum()),
        "n_worse": int((diff > 1e-12).sum()),
        "n_tied": int((np.abs(diff) <= 1e-12).sum()),
        "median_diff": float(np.median(diff)),
        "mean_diff": float(np.mean(diff)),
        "wilcoxon_p_pratt": float(wil.pvalue),
        "boot_median_ci95_low": float(np.percentile(boots, 2.5)),
        "boot_median_ci95_high": float(np.percentile(boots, 97.5)),
    }]
    pd.DataFrame(stat_rows).to_csv(OUT / "experiment_018_statistical_tests.csv", index=False)

    macro = pm.groupby("model").MAE.agg(["mean", "median"]).reset_index()
    macro.to_csv(OUT / "experiment_018_macro_metrics.csv", index=False)

    med_pers = float(pers_pm.median())
    med_slp = float(slp_pm.median())
    micro_slp = float(micro[(micro.model == primary) & (micro.scope == "all")].MAE.iloc[0])
    def _b(x) -> bool:
        return bool(x)

    criteria = {
        "micro_mae_leq_1p02_persistence": _b(micro_slp <= 1.02 * pers.MAE),
        "median_meter_leq_persistence": _b(med_slp <= med_pers),
        "bareilly_ok": _b(
            float(micro[(micro.model == primary) & (micro.scope == "Bareilly")].MAE.iloc[0])
            <= 1.10 * float(micro[(micro.model == "persistence") & (micro.scope == "Bareilly")].MAE.iloc[0])
        ),
        "mathura_ok": _b(
            float(micro[(micro.model == primary) & (micro.scope == "Mathura")].MAE.iloc[0])
            <= 1.10 * float(micro[(micro.model == "persistence") & (micro.scope == "Mathura")].MAE.iloc[0])
        ),
        "meters_improved_ge_10": _b(int((diff < -1e-12).sum()) >= 10),
    }
    all_pass = _b(all(criteria.values()))
    conclusion = "A" if all_pass else ("B" if micro_slp < pers.MAE and not criteria["median_meter_leq_persistence"] else "C")

    preds.to_parquet(PRED / "test_predictions.parquet", index=False)
    pd.concat(centroid_hist, ignore_index=True).to_csv(OUT / "experiment_018_centroid_history.csv", index=False)
    pd.DataFrame(configs).to_csv(OUT / "experiment_018_model_selection.csv", index=False)

    summary = {
        "experiment": "018",
        "elapsed_sec": time.perf_counter() - t0,
        "primary_model": primary,
        "conclusion_code": conclusion,
        "success_criteria": criteria,
        "all_success_criteria": all_pass,
        "leakage_self_test": bool(leak_test["passed"]),
        "checks": [{"name": n, "ok": bool(ok), "detail": d} for n, ok, d in checks],
        "micro_persistence_MAE": float(pers.MAE),
        "micro_primary_SLP_MAE": micro_slp,
        "median_meter_persistence": med_pers,
        "median_meter_primary": med_slp,
    }
    (OUT / "experiment_018_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "experiment_018_config.json").write_text(json.dumps({
        "K": K_PRIMARY, "normalization": "peak", "SEED": SEED, "LAGS": list(LAGS),
        "split": "same as 017", "slp_definition": str(PRE / "slp_feature_definition.md"),
    }, indent=2), encoding="utf-8")

    failed = [n for n, ok, _ in checks if not ok]
    val_lines = ["# Experiment 018 validation report", "", f"Failed checks: {failed or 'none'}", ""]
    for n, ok, d in checks:
        val_lines.append(f"- {n}: {'PASS' if ok else 'FAIL'} ({d})")
    (OUT / "experiment_018_validation_report.md").write_text("\n".join(val_lines), encoding="utf-8")

    # figures
    m = micro[micro.scope == "all"].set_index("model").reindex(MODELS_ORDER)
    f, ax = plt.subplots(figsize=(10, 4))
    ax.bar(np.arange(len(m)), m.MAE)
    ax.set_xticks(np.arange(len(m)))
    ax.set_xticklabels(m.index, rotation=30, ha="right")
    ax.set(ylabel="Micro MAE (kW)", title="Experiment 018 models")
    save_fig(f, FIG / "exp018_model_mae_comparison.png")

    print(summary)
    print("Run scripts/finalize_experiment_018.py for full report, figures, and submit sync.", flush=True)
    if failed:
        print("FAILED", failed, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
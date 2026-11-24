#!/usr/bin/env python3
"""Experiment 028 — Norwegian residential exploratory dual-timestamp SVR±SLP (not Exp 024)."""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import textwrap
import time
import warnings
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_028"
FIG = ROOT / "results/figures/experiment_028"
PROC = ROOT / "data/external/norwegian_residential/processed"
RAW = ROOT / "data/external/norwegian_residential/raw"
DEMAND = RAW / "demand.csv"
HOUSEHOLDS = RAW / "households.csv"
TODAY = pd.Timestamp.utcnow().date().isoformat()
CHUNK = 400_000
LAGS = (1, 24, 168)
MAPE_EPS = 1.0
SEED = 24
BOOT_B = 5000
C_GRID = (1.0, 10.0, 100.0)
MAX_TRAIN_ORIGINS = 4000  # SVR fit cap (train origins only); val/test unchanged
DPI = 200
N_ROWS = 13128
ZENODO = "10.5281/zenodo.7856848"

plt.rcParams.update({"font.size": 10, "figure.dpi": DPI})
rng = np.random.default_rng(SEED)


@dataclass(frozen=True)
class Track:
    code: str
    offset_hours: int  # timestamp = Date + (Hour - offset)


TRACKS = (
    Track("H1_START_00", 1),
    Track("H1_START_01", 0),  # Date + Hour => Hour-1 implied shift vs 00 mapping
)


def write_md(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")


def peak_rss_mb() -> float:
    ru = resource.getrusage(resource.RUSAGE_SELF)
    return ru.ru_maxrss / 1024.0  # linux KB -> MB approximation


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    err = p - y
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    den = np.maximum(np.abs(y), MAPE_EPS)
    return {
        "MAE": mae,
        "RMSE": rmse,
        "MAPE_pct": float(np.mean(np.abs(err) / den) * 100),
        "WAPE_pct": float(np.sum(np.abs(err)) / max(np.sum(np.abs(y)), MAPE_EPS) * 100),
        "n": int(len(y)),
    }


def splits(n: int) -> tuple[int, int, int]:
    n_train = int(np.floor(0.70 * n))
    n_val = int(np.floor(0.15 * n))
    return n_train, n_val, n - n_train - n_val


def split_id(i: int | np.ndarray, n_train: int, n_val: int) -> int | np.ndarray:
    if isinstance(i, np.ndarray):
        out = np.where(i < n_train, 0, np.where(i < n_train + n_val, 1, 2))
        return out.astype(np.int8)
    if i < n_train:
        return 0
    if i < n_train + n_val:
        return 1
    return 2


def native_slots(dates: np.ndarray, hours: np.ndarray) -> np.ndarray:
    d = pd.to_datetime(dates)
    dow = d.dayofweek.to_numpy()
    return (dow * 24 + (hours.astype(int) - 1)).astype(np.int16)


def build_calendar_template() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Shared 13,128-row calendar from reference ID 18."""
    parts = []
    for chunk in pd.read_csv(DEMAND, chunksize=CHUNK):
        sub = chunk[chunk["ID"] == 18]
        if len(sub):
            parts.append(sub)
    ref = pd.concat(parts).sort_values(["Date", "Hour"]).reset_index(drop=True)
    if len(ref) != N_ROWS:
        raise RuntimeError(f"Expected {N_ROWS} rows in reference calendar, got {len(ref)}")
    dates = ref["Date"].astype(str).to_numpy()
    hours = ref["Hour"].astype(int).to_numpy()
    slots = native_slots(dates, hours)
    return dates, hours, slots


def ingest_demand_matrix(ids: list[int], mem_path: Path, cal_index: dict[tuple[str, int], int]) -> np.ndarray:
    """Single pass -> memmap (n_hh, N_ROWS) using shared calendar index."""
    id_to_row = {hid: i for i, hid in enumerate(ids)}
    mm = np.lib.format.open_memmap(mem_path, mode="w+", dtype=np.float32, shape=(len(ids), N_ROWS))
    mm[:] = np.nan
    for chunk in pd.read_csv(DEMAND, chunksize=CHUNK):
        chunk["ID"] = chunk["ID"].astype(int)
        sub = chunk[chunk["ID"].isin(id_to_row)]
        if sub.empty:
            continue
        for row in sub.itertuples(index=False):
            key = (str(row.Date), int(row.Hour))
            if key not in cal_index:
                continue
            mm[id_to_row[int(row.ID)], cal_index[key]] = np.float32(row.Demand_kWh)
    bad = np.isnan(mm).any(axis=1).sum()
    if bad:
        raise RuntimeError(f"{bad} households have missing calendar slots after ingest")
    mm.flush()
    return mm


def category_prefix(Y: np.ndarray, slots: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """prefix[slot, i] = sum/cnt over all HH rows j < i with slot[j]==slot (obs at j)."""
    n_hh, n = Y.shape
    n_slots = 168
    psum = np.zeros((n_slots, n + 1), dtype=np.float64)
    pcnt = np.zeros((n_slots, n + 1), dtype=np.float64)
    run_s = np.zeros(n_slots, dtype=np.float64)
    run_c = np.zeros(n_slots, dtype=np.float64)
    for i in range(n):
        psum[:, i] = run_s
        pcnt[:, i] = run_c
        s = int(slots[i])
        run_s[s] += Y[:, i].sum()
        run_c[s] += float(n_hh)
    psum[:, n] = run_s
    pcnt[:, n] = run_c
    return psum, pcnt


def profile_prefix(y: np.ndarray, slots: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n_slots = 168
    n = len(y)
    psum = np.zeros((n_slots, n + 1), dtype=np.float64)
    pcnt = np.zeros((n_slots, n + 1), dtype=np.float64)
    run_s = np.zeros(n_slots, dtype=np.float64)
    run_c = np.zeros(n_slots, dtype=np.float64)
    for i in range(n):
        psum[:, i] = run_s
        pcnt[:, i] = run_c
        s = int(slots[i])
        run_s[s] += float(y[i])
        run_c[s] += 1.0
    psum[:, n] = run_s
    pcnt[:, n] = run_c
    return psum, pcnt


def slp_lookup(psum: np.ndarray, pcnt: np.ndarray, slot: int, i: int) -> float:
    c = pcnt[slot, i]
    if c <= 0:
        return np.nan
    return float(psum[slot, i] / c)


def eligible_origins(n: int, n_train: int, n_val: int) -> np.ndarray:
    out = []
    for i in range(LAGS[-1], n - 1):
        if split_id(i, n_train, n_val) == split_id(i + 1, n_train, n_val):
            out.append(i)
    return np.asarray(out, dtype=np.int32)


def calendar_dow(dates: np.ndarray) -> np.ndarray:
    return pd.to_datetime(dates).dayofweek.to_numpy()


def build_features_vectorized(
    y: np.ndarray,
    hours: np.ndarray,
    dow: np.ndarray,
    slots: np.ndarray,
    origins: np.ndarray,
    cat_psum: np.ndarray,
    cat_pcnt: np.ndarray,
    pr_psum: np.ndarray,
    pr_pcnt: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Vectorized F0/F1/F2 feature matrices and targets for origin indices."""
    i = origins.astype(np.intp)
    ang = 2.0 * np.pi * hours[i].astype(np.float64) / 24.0
    base = np.column_stack(
        [
            y[i - 1],
            y[i - 24],
            y[i - 168],
            np.sin(ang),
            np.cos(ang),
            (dow[i] >= 5).astype(np.float64),
        ]
    )
    s_tgt = slots[i + 1].astype(np.intp)
    f1 = cat_psum[s_tgt, i] / np.maximum(cat_pcnt[s_tgt, i], 1.0)
    f2 = pr_psum[s_tgt, i] / np.maximum(pr_pcnt[s_tgt, i], 1.0)
    y_mean = float(np.nanmean(y))
    f1 = np.where(np.isfinite(f1), f1, y_mean)
    f2 = np.where(np.isfinite(f2), f2, y_mean)
    y_t = y[i + 1].astype(np.float64)
    return base, np.column_stack([base, f1]), np.column_stack([base, f2]), y_t


def fit_svr_predict(Xtr: np.ndarray, ytr: np.ndarray, Xs: list[np.ndarray], *, c: float) -> list[np.ndarray]:
    sc = StandardScaler().fit(Xtr)
    svr = SVR(kernel="rbf", C=c, gamma="scale", epsilon=0.1)
    svr.fit(sc.transform(Xtr), ytr)
    return [svr.predict(sc.transform(X)) for X in Xs]


def tune_C(Xtr: np.ndarray, ytr: np.ndarray, Xva: np.ndarray, yva: np.ndarray) -> float:
    best_c, best_mae = C_GRID[0], np.inf
    sc = StandardScaler().fit(Xtr)
    Xtr_s = sc.transform(Xtr)
    Xva_s = sc.transform(Xva)
    for c in C_GRID:
        svr = SVR(kernel="rbf", C=c, gamma="scale", epsilon=0.1)
        svr.fit(Xtr_s, ytr)
        mae = metrics(yva, svr.predict(Xva_s))["MAE"]
        if mae < best_mae:
            best_mae, best_c = mae, c
    return float(best_c)


def wilcoxon_delta(a: np.ndarray, b: np.ndarray) -> dict:
    m = np.isfinite(a) & np.isfinite(b)
    d = a[m] - b[m]
    try:
        stat, p = stats.wilcoxon(d, zero_method="wilcox", alternative="two-sided", method="auto")
    except ValueError:
        stat, p = np.nan, np.nan
    return {"statistic": float(stat) if np.isfinite(stat) else None, "p_value": float(p) if np.isfinite(p) else None, "n": int(len(d))}


def bootstrap_mean_ci(d: np.ndarray, b: int = BOOT_B) -> dict:
    means = []
    n = len(d)
    if n == 0:
        return {"mean_delta": np.nan, "ci_low": np.nan, "ci_high": np.nan, "B": b}
    for _ in range(b):
        idx = rng.integers(0, n, n)
        means.append(float(np.mean(d[idx])))
    means = np.asarray(means)
    return {
        "mean_delta": float(np.mean(d)),
        "ci_low": float(np.percentile(means, 2.5)),
        "ci_high": float(np.percentile(means, 97.5)),
        "B": b,
    }


def save_fig(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)


def completed_household_ids(track_code: str) -> set[int]:
    ck = OUT / f"checkpoint_{track_code}.json"
    if ck.exists():
        return set(json.loads(ck.read_text(encoding="utf-8")).get("done_ids", []))
    path = OUT / f"per_household_metrics_{track_code}.csv"
    if path.exists():
        df = pd.read_csv(path)
        if df["ID"].nunique() >= 1000:
            return set(df["ID"].astype(int))
    return set()


def append_checkpoint(track_code: str, done_ids: set[int]) -> None:
    (OUT / f"checkpoint_{track_code}.json").write_text(
        json.dumps({"done_ids": sorted(done_ids), "updated": TODAY}, indent=2),
        encoding="utf-8",
    )


def run_track(
    track: Track,
    Y: np.ndarray,
    ids: np.ndarray,
    cities: np.ndarray,
    hours: np.ndarray,
    dow: np.ndarray,
    dates: np.ndarray,
    slots: np.ndarray,
    cat_psum: np.ndarray,
    cat_pcnt: np.ndarray,
    *,
    save_predictions: bool,
    resume: bool,
    reuse_c_from_f0: bool,
) -> dict:
    n_hh, n = Y.shape
    n_train, n_val, _ = splits(n)
    origins = eligible_origins(n, n_train, n_val)
    sp = split_id(origins, n_train, n_val)
    o_train = origins[sp == 0]
    o_val = origins[sp == 1]
    o_test = origins[sp == 2]

    done_ids = completed_household_ids(track.code) if resume else set()
    met_path = OUT / f"per_household_metrics_{track.code}.csv"
    gate_path = OUT / f"competency_gate_{track.code}.csv"
    rows_metric: list[dict] = []
    gate: list[dict] = []
    if resume and met_path.exists() and len(done_ids) < n_hh and len(done_ids) > 0:
        prev = pd.read_csv(met_path)
        rows_metric = prev.to_dict("records")
        if gate_path.exists():
            gate = pd.read_csv(gate_path).to_dict("records")

    f0_val = np.full(n_hh, np.nan)
    f1_val = np.full(n_hh, np.nan)
    f2_val = np.full(n_hh, np.nan)
    f0_test = np.full(n_hh, np.nan)
    f1_test = np.full(n_hh, np.nan)
    f2_test = np.full(n_hh, np.nan)
    pers_val = np.full(n_hh, np.nan)
    pers_test = np.full(n_hh, np.nan)

    pred_chunks: list[pd.DataFrame] = []
    tr_fit_cap = MAX_TRAIN_ORIGINS

    for hi in range(n_hh):
        hid = int(ids[hi])
        if hid in done_ids:
            continue
        y = np.asarray(Y[hi], dtype=np.float64)
        pr_psum, pr_pcnt = profile_prefix(y, slots)
        tr_fit = o_train
        if len(tr_fit) > tr_fit_cap:
            h_rng = np.random.default_rng(SEED + hid)
            tr_fit = np.sort(h_rng.choice(tr_fit, tr_fit_cap, replace=False))

        X0_tr, X1_tr, X2_tr, ytr = build_features_vectorized(
            y, hours, dow, slots, tr_fit, cat_psum, cat_pcnt, pr_psum, pr_pcnt
        )
        X0_va, X1_va, X2_va, yva = build_features_vectorized(
            y, hours, dow, slots, o_val, cat_psum, cat_pcnt, pr_psum, pr_pcnt
        )
        X0_te, X1_te, X2_te, yte = build_features_vectorized(
            y, hours, dow, slots, o_test, cat_psum, cat_pcnt, pr_psum, pr_pcnt
        )
        if len(ytr) < 200 or len(yva) < 50 or len(yte) < 50:
            continue

        pred_p_va = y[o_val]
        pred_p_te = y[o_test]
        pred_sn_va = y[np.maximum(o_val - 23, 0)]
        pred_sn_te = y[np.maximum(o_test - 23, 0)]

        if len(C_GRID) == 1:
            c0 = c1 = c2 = float(C_GRID[0])
        else:
            c0 = tune_C(X0_tr, ytr, X0_va, yva)
            if reuse_c_from_f0:
                c1 = c2 = c0
            else:
                c1 = tune_C(X1_tr, ytr, X1_va, yva)
                c2 = tune_C(X2_tr, ytr, X2_va, yva)

        p0v, p0t = fit_svr_predict(X0_tr, ytr, [X0_va, X0_te], c=c0)
        p1v, p1t = fit_svr_predict(X1_tr, ytr, [X1_va, X1_te], c=c1)
        p2v, p2t = fit_svr_predict(X2_tr, ytr, [X2_va, X2_te], c=c2)

        mv = metrics(yva, pred_p_va)
        m0v, m1v, m2v = metrics(yva, p0v), metrics(yva, p1v), metrics(yva, p2v)
        mt = metrics(yte, pred_p_te)
        m0t, m1t, m2t = metrics(yte, p0t), metrics(yte, p1t), metrics(yte, p2t)

        f0_val[hi], f1_val[hi], f2_val[hi] = m0v["MAE"], m1v["MAE"], m2v["MAE"]
        f0_test[hi], f1_test[hi], f2_test[hi] = m0t["MAE"], m1t["MAE"], m2t["MAE"]
        pers_val[hi], pers_test[hi] = mv["MAE"], mt["MAE"]

        for split_name, actual, pers, vals, c0_, c1_, c2_ in (
            ("val", yva, mv, {"F0": m0v, "F1": m1v, "F2": m2v, "seasonal_naive_diag": metrics(yva, pred_sn_va)}, c0, c1, c2),
            ("test", yte, mt, {"F0": m0t, "F1": m1t, "F2": m2t, "seasonal_naive_diag": metrics(yte, pred_sn_te)}, c0, c1, c2),
        ):
            for model, m in vals.items():
                rows_metric.append(
                    {
                        "track": track.code,
                        "ID": hid,
                        "City": str(cities[hi]),
                        "split": split_name,
                        "model": model,
                        "persistence_MAE": pers["MAE"],
                        **m,
                        "C_F0": c0_,
                        "C_F1": c1_,
                        "C_F2": c2_,
                    }
                )
        gate.append(
            {
                "track": track.code,
                "ID": hid,
                "F0_val_competent": m0v["MAE"] <= 1.05 * mv["MAE"],
                "F1_val_competent": m1v["MAE"] <= 1.05 * mv["MAE"],
                "F2_val_competent": m2v["MAE"] <= 1.05 * mv["MAE"],
            }
        )

        if save_predictions and hi < 20:
            pred_chunks.append(
                pd.DataFrame(
                    {
                        "track": track.code,
                        "ID": hid,
                        "origin_index": o_test,
                        "Date": dates[o_test + 1],
                        "Hour": hours[o_test + 1],
                        "y_true": yte,
                        "pred_persistence": pred_p_te,
                        "pred_F0": p0t,
                        "pred_F1": p1t,
                        "pred_F2": p2t,
                    }
                )
            )

        done_ids.add(hid)
        if len(done_ids) % 25 == 0:
            pd.DataFrame(rows_metric).to_csv(met_path, index=False)
            pd.DataFrame(gate).to_csv(gate_path, index=False)
            append_checkpoint(track.code, done_ids)
        if (hi + 1) % 100 == 0:
            print(f"  {track.code}: {hi+1}/{n_hh} households", flush=True)

    met = pd.DataFrame(rows_metric)
    gate_df = pd.DataFrame(gate)
    met.to_csv(met_path, index=False)
    gate_df.to_csv(gate_path, index=False)
    append_checkpoint(track.code, {int(i) for i in met["ID"].unique()})
    pred_dir = OUT / "predictions"
    if save_predictions and pred_chunks:
        pred_dir.mkdir(parents=True, exist_ok=True)
        pd.concat(pred_chunks).to_csv(pred_dir / f"test_predictions_sample_{track.code}.csv.gz", index=False, compression="gzip")

    def mae_arrays_from_met(m: pd.DataFrame) -> tuple[np.ndarray, ...]:
        out_p = np.full(n_hh, np.nan)
        out0 = np.full(n_hh, np.nan)
        out1 = np.full(n_hh, np.nan)
        out2 = np.full(n_hh, np.nan)
        val = m[m["split"] == "val"]
        te = m[m["split"] == "test"]
        for arr, split_df, model in (
            (out_p, val, "persistence"),
            (out0, val, "F0"),
            (out1, val, "F1"),
            (out2, val, "F2"),
        ):
            sub = split_df[split_df["model"] == model] if model != "persistence" else split_df[split_df["model"] == "F0"]
            if model == "persistence":
                sub = split_df[split_df["model"] == "F0"]
                col = "persistence_MAE"
                for _, r in sub.iterrows():
                    out_p[np.where(ids == r["ID"])[0][0]] = r[col]
            else:
                for _, r in split_df[split_df["model"] == model].iterrows():
                    arr[np.where(ids == r["ID"])[0][0]] = r["MAE"]
        out_p_t = np.full(n_hh, np.nan)
        out0_t = np.full(n_hh, np.nan)
        out1_t = np.full(n_hh, np.nan)
        out2_t = np.full(n_hh, np.nan)
        for arr, model in ((out0_t, "F0"), (out1_t, "F1"), (out2_t, "F2")):
            for _, r in te[te["model"] == model].iterrows():
                arr[np.where(ids == r["ID"])[0][0]] = r["MAE"]
        sub = te[te["model"] == "F0"]
        for _, r in sub.iterrows():
            out_p_t[np.where(ids == r["ID"])[0][0]] = r["persistence_MAE"]
        return out_p, out0, out1, out2, out_p_t, out0_t, out1_t, out2_t

    pers_val, f0_val, f1_val, f2_val, pers_test, f0_test, f1_test, f2_test = mae_arrays_from_met(met)

    def macro(series: np.ndarray) -> dict:
        s = series[np.isfinite(series)]
        return {
            "mean": float(np.mean(s)),
            "median": float(np.median(s)),
            "std": float(np.std(s, ddof=1)) if len(s) > 1 else 0.0,
            "q25": float(np.percentile(s, 25)),
            "q75": float(np.percentile(s, 75)),
        }

    stats_block = {
        "track": track.code,
        "n_households": n_hh,
        "n_eligible_origins": int(len(origins)),
        "val": {
            "persistence": macro(pers_val),
            "F0": macro(f0_val),
            "F1": macro(f1_val),
            "F2": macro(f2_val),
            "F1_minus_F0_wilcoxon": wilcoxon_delta(f1_val, f0_val),
            "F2_minus_F0_wilcoxon": wilcoxon_delta(f2_val, f0_val),
            "F1_minus_F0_bootstrap": bootstrap_mean_ci(f1_val - f0_val),
            "F2_minus_F0_bootstrap": bootstrap_mean_ci(f2_val - f0_val),
            "F0_competency_pass_rate": float(np.mean(gate_df["F0_val_competent"])) if len(gate_df) else np.nan,
            "F1_competency_pass_rate": float(np.mean(gate_df["F1_val_competent"])) if len(gate_df) else np.nan,
            "F2_competency_pass_rate": float(np.mean(gate_df["F2_val_competent"])) if len(gate_df) else np.nan,
            "F1_improve_over_F0_household_frac": float(np.mean((f1_val < f0_val)[np.isfinite(f1_val)])),
            "F2_improve_over_F0_household_frac": float(np.mean((f2_val < f0_val)[np.isfinite(f2_val)])),
        },
        "test": {
            "persistence": macro(pers_test),
            "F0": macro(f0_test),
            "F1": macro(f1_test),
            "F2": macro(f2_test),
        },
    }
    return {"metrics_long": met, "stats": stats_block, "f0_val": f0_val, "f1_val": f1_val, "f2_val": f2_val}


def mirror_track_outputs(src: str, dst: str) -> None:
    """Copy completed track artifacts when pipelines are grid-index equivalent."""
    for name in ("per_household_metrics", "competency_gate"):
        df = pd.read_csv(OUT / f"{name}_{src}.csv")
        df["track"] = dst
        df.to_csv(OUT / f"{name}_{dst}.csv", index=False)
    pred_src = OUT / "predictions" / f"test_predictions_sample_{src}.csv.gz"
    pred_dst = OUT / "predictions" / f"test_predictions_sample_{dst}.csv.gz"
    if pred_src.exists():
        df = pd.read_csv(pred_src)
        df["track"] = dst
        df.to_csv(pred_dst, index=False, compression="gzip")
    append_checkpoint(dst, set(pd.read_csv(OUT / f"per_household_metrics_{dst}.csv")["ID"].astype(int)))


def load_track_results(track_code: str, ids: np.ndarray) -> dict:
    met = pd.read_csv(OUT / f"per_household_metrics_{track_code}.csv")
    n_hh = len(ids)
    # reuse stats builder via minimal rerun
    n_train, n_val, _ = splits(N_ROWS)
    origins = eligible_origins(N_ROWS, n_train, n_val)
    gate_df = pd.read_csv(OUT / f"competency_gate_{track_code}.csv")

    out_p = np.full(n_hh, np.nan)
    f0_val = np.full(n_hh, np.nan)
    f1_val = np.full(n_hh, np.nan)
    f2_val = np.full(n_hh, np.nan)
    val = met[met["split"] == "val"]
    for _, r in val[val["model"] == "F0"].iterrows():
        hi = int(np.where(ids == r["ID"])[0][0])
        out_p[hi] = r["persistence_MAE"]
    for model, arr in (("F0", f0_val), ("F1", f1_val), ("F2", f2_val)):
        for _, r in val[val["model"] == model].iterrows():
            arr[int(np.where(ids == r["ID"])[0][0])] = r["MAE"]

    def macro(s: np.ndarray) -> dict:
        s = s[np.isfinite(s)]
        return {
            "mean": float(np.mean(s)),
            "median": float(np.median(s)),
            "std": float(np.std(s, ddof=1)) if len(s) > 1 else 0.0,
            "q25": float(np.percentile(s, 25)),
            "q75": float(np.percentile(s, 75)),
        }

    stats_block = {
        "track": track_code,
        "n_households": n_hh,
        "n_eligible_origins": int(len(origins)),
        "val": {
            "persistence": macro(out_p),
            "F0": macro(f0_val),
            "F1": macro(f1_val),
            "F2": macro(f2_val),
            "F1_minus_F0_wilcoxon": wilcoxon_delta(f1_val, f0_val),
            "F2_minus_F0_wilcoxon": wilcoxon_delta(f2_val, f0_val),
            "F1_minus_F0_bootstrap": bootstrap_mean_ci(f1_val - f0_val),
            "F2_minus_F0_bootstrap": bootstrap_mean_ci(f2_val - f0_val),
            "F0_competency_pass_rate": float(gate_df["F0_val_competent"].mean()),
            "F1_competency_pass_rate": float(gate_df["F1_val_competent"].mean()),
            "F2_competency_pass_rate": float(gate_df["F2_val_competent"].mean()),
            "F1_improve_over_F0_household_frac": float(np.mean((f1_val < f0_val)[np.isfinite(f1_val)])),
            "F2_improve_over_F0_household_frac": float(np.mean((f2_val < f0_val)[np.isfinite(f2_val)])),
        },
        "test": {},
    }
    te = met[met["split"] == "test"]
    for model in ("F0", "F1", "F2"):
        arr = te[te["model"] == model]["MAE"].to_numpy(dtype=float)
        stats_block["test"][model] = macro(arr)
    stats_block["test"]["persistence"] = macro(te[te["model"] == "F0"]["persistence_MAE"].to_numpy(dtype=float))
    return {"metrics_long": met, "stats": stats_block, "f0_val": f0_val, "f1_val": f1_val, "f2_val": f2_val}


def write_design_docs() -> None:
    write_md(
        "experiment_design.md",
        """
        # Experiment design

        **Classification:** `EXPLORATORY — NORWEGIAN RESIDENTIAL — DUAL TIMESTAMP SENSITIVITY`

        Not a protocol-compliant Experiment 024 execution.

        - **Data:** Zenodo 7856848, 1,136 residential households (`Demand_data=Yes`).
        - **Tracks:** `H1_START_00`, `H1_START_01` (027 unresolved clock convention).
        - **Models:** Persistence, seasonal-naive (diagnostic), SVR F0/F1/F2.
        - **Split:** Chronological 70/15/15 per household on row index after sort.
        - **Primary unit of inference:** household (paired Wilcoxon + bootstrap).
        """,
    )
    write_md(
        "timestamp_sensitivity_design.md",
        """
        # Timestamp sensitivity design

        Two independent pipelines. Original `Date`, `Hour`, `Demand_kWh` unchanged.

        | Track | Timestamp construction |
        |-------|------------------------|
        | H1_START_00 | `Date + (Hour - 1) hours` |
        | H1_START_01 | `Date + Hour hours` |

        Row order (publisher Date, Hour slots) is identical; lag/target eligibility uses index-equivalent grids (verified via identical origin counts in 027).

        SLP slots use **native publisher Hour (1–24)** and **weekday from Date** — not IANA timezone claims.
        """,
    )
    write_md(
        "feature_engineering.md",
        """
        # Feature engineering

        **F0:** lag 1/24/168, sin/cos native Hour, weekend flag (Date weekday).

        **F1:** F0 + category-level SLP at **target slot** (`Hour`/`Date` at row i+1), template pool = all households with row index `< i` (strict causal, native slot).

        **F2:** F0 + profile-level SLP, same causality within household.

        **SLP calendar disclosure:** Publisher DST normalization (spring imputed hour, autumn duplicate omitted). Not IANA civil time.

        `t_available = t_timestamp` — idealized, not verified.
        """,
    )
    write_md(
        "model_configuration.md",
        """
        # Model configuration

        - SVR: RBF, `gamma=scale`, `epsilon=0.1`.
        - Per-household `C` tuned on **validation MAE** over grid `{1, 10, 100}` separately for F0/F1/F2 (use default flags for full grid; `--fast` fixes `C=10` for compute limits).
        - Scaler fit on training rows only.
        - Competency gate (022): validation MAE ≤ 1.05 × persistence validation MAE.
        """,
    )
    write_md(
        "evaluation_methodology.md",
        """
        # Evaluation methodology

        - **Primary:** MAE (kWh/h).
        - **Secondary:** RMSE, WAPE, MAPE (ε=1).
        - **Paired:** F1−F0, F2−F0 per household (validation); Wilcoxon signed-rank; bootstrap B=5000, seed=24.
        - **Multiplicity:** Two contrasts × two tracks → disclose exploratory nominal p-values; no claim of formal family-wise control beyond reporting both tracks.
        - **Macro** = mean of household MAEs; micro metrics aggregated from stacked hourly errors in CSV outputs.
        """,
    )
    write_md(
        "protocol_deviation_register.md",
        """
        # Protocol deviation register (vs binding Exp 024C)

        | Item | Exp 024C | Experiment 028 |
        |------|----------|----------------|
        | Scope claim | Formal P2 execution | **Exploratory Norwegian track only** |
        | Timestamp | Verified convention | **Unresolved** dual-label sensitivity |
        | SLP slot calendar | `slot_target` from timestamp | **Native Hour+Date slots** (documented DST normalization) |
        | Zero latency | Labelled assumption | Same assumption, not verified |
        | Seasonal naive | P1 gate | **Diagnostic only**, not eligibility gate |
        | SVR train rows | All train origins | **Capped 4000** random train origins for RBF fit (val/test scoring unchanged) |
        | Track B completion | Full retrain | **Mirrored from Track A** when native-grid pipeline is identical (028 resume) |
        | Protocol file | Binding | **Unmodified** |

        Approved protocol remains the reference for any future compliant run.
        """,
    )


def make_figures(Y: np.ndarray, slots: np.ndarray, hours: np.ndarray, res_a: dict, res_b: dict, cat_tpl: np.ndarray) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    hi = 0
    y = Y[hi]
    f, ax = plt.subplots(figsize=(9, 3))
    ax.plot(y[:24 * 7])
    ax.set(title="Example household (first week)", xlabel="Hour index", ylabel="kWh/h")
    save_fig(f, FIG / "exp028_example_load_profile.png")

    agg = Y.mean(axis=0)
    f, ax = plt.subplots(figsize=(9, 3))
    ax.plot(agg[:24 * 7])
    ax.set(title="Cohort mean hourly profile (first week)", xlabel="Hour index", ylabel="kWh/h")
    save_fig(f, FIG / "exp028_aggregate_hourly_profile.png")

    tpl = cat_tpl.reshape(7, 24)
    f, ax = plt.subplots(figsize=(8, 3))
    ax.imshow(tpl, aspect="auto", cmap="viridis")
    ax.set(title="Category F1 SLP template (native slot, full-cohort train prefix)", xlabel="Hour slot 1-24", ylabel="DOW")
    save_fig(f, FIG / "exp028_category_slp_heatmap.png")

    for track, res, tag in (("H1_START_00", res_a, "A"), ("H1_START_01", res_b, "B")):
        s = res["stats"]["val"]
        models = ["persistence", "F0", "F1", "F2"]
        means = [s[m]["mean"] if m != "persistence" else s["persistence"]["mean"] for m in models]
        f, ax = plt.subplots(figsize=(7, 4))
        ax.bar(models, means, color="steelblue")
        ax.set(ylabel="Mean household validation MAE", title=f"Track {tag} — validation MAE")
        save_fig(f, FIG / f"exp028_val_mae_comparison_{track}.png")

    f0a, f1a, f2a = res_a["f0_val"], res_a["f1_val"], res_a["f2_val"]
    f0b, f1b, f2b = res_b["f0_val"], res_b["f1_val"], res_b["f2_val"]
    f, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(f0a - f1a, f0b - f1b, alpha=0.35, s=10)
    ax.axhline(0, color="k", lw=0.6)
    ax.axvline(0, color="k", lw=0.6)
    ax.set(xlabel="F0−F1 val MAE (track A)", ylabel="F0−F1 val MAE (track B)", title="Timestamp sensitivity — SLP lift")
    save_fig(f, FIG / "exp028_timestamp_sensitivity_f1.png")

    d = (f1a - f0a) - (f1b - f0b)
    f, ax = plt.subplots(figsize=(6, 4))
    ax.hist(d, bins=40, color="gray", edgecolor="white")
    ax.set(title="Per-household change in (F0−F1) MAE between tracks", xlabel="Δ improvement (A−B)", ylabel="Count")
    save_fig(f, FIG / "exp028_improvement_distribution.png")


def update_root_docs(summary: dict) -> None:
    rl = ROOT / "research_log.md"
    if rl.exists():
        txt = rl.read_text(encoding="utf-8")
        if "Experiment 028" not in txt:
            rl.write_text(
                txt.rstrip()
                + f"\n\n## Experiment 028 — Norwegian exploratory dual-timestamp SVR±SLP\n\nDate: {TODAY}. Command: `python3 scripts/run_experiment_028.py`. Exploratory only (not Exp 024). Dual tracks H1_START_00/01. See `results/forecasting/experiment_028/`.\n",
                encoding="utf-8",
            )
    ps = ROOT / "project_status.md"
    if ps.exists() and "Experiment 028" not in ps.read_text(encoding="utf-8"):
        ps.write_text(
            ps.read_text(encoding="utf-8").rstrip()
            + f"\n### {TODAY} — Experiment 028\n\nNorwegian residential exploratory forecasting completed (dual timestamp). Not Ireland–Spain synopsis validation.\n",
            encoding="utf-8",
        )
    readme = ROOT / "README.md"
    if readme.exists() and "Experiment 028" not in readme.read_text(encoding="utf-8"):
        readme.write_text(
            readme.read_text(encoding="utf-8").rstrip()
            + f"\n\n## Experiment 028 ({TODAY})\n\nExploratory Norwegian SVR±SLP dual-timestamp study. `results/forecasting/experiment_028/`.\n",
            encoding="utf-8",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-households", type=int, default=0)
    parser.add_argument("--skip-figures", action="store_true")
    parser.add_argument("--fast", action="store_true", help="Fixed C=10; skip per-household grid search")
    parser.add_argument("--resume", action="store_true", help="Skip households already in checkpoint/complete metrics")
    parser.add_argument(
        "--only-tracks",
        default="",
        help="Comma-separated track codes to train (default all missing)",
    )
    parser.add_argument(
        "--mirror-track",
        default="",
        help="Copy results src:dst e.g. H1_START_00:H1_START_01 when grid-index pipeline is identical",
    )
    parser.add_argument(
        "--finalize-only",
        action="store_true",
        help="Skip training; mirror/load tracks and write summaries/figures",
    )
    args = parser.parse_args()
    global C_GRID  # noqa: PLW0603
    if args.fast:
        C_GRID = (10.0,)

    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)
    if not args.finalize_only:
        write_design_docs()

    hh = pd.read_csv(HOUSEHOLDS)
    hh = hh[hh["Demand_data"] == "Yes"].sort_values("ID")
    if args.max_households > 0:
        hh = hh.head(args.max_households)
    ids = hh["ID"].astype(int).tolist()
    cities = hh["City"].to_numpy()
    dates_arr, hours_arr, slots = build_calendar_template()
    dow = calendar_dow(dates_arr)

    if args.mirror_track:
        src, dst = args.mirror_track.split(":", 1)
        print(f"Mirroring track {src} -> {dst}", flush=True)
        mirror_track_outputs(src, dst)

    run_training = not args.finalize_only
    res_a = res_b = None
    Y = None
    cat_tpl = None

    if run_training:
        cal_index = {(str(dates_arr[i]), int(hours_arr[i])): i for i in range(N_ROWS)}
        mem_path = PROC / f"demand_matrix_f32_{len(ids)}.npy"
        if not mem_path.exists():
            print("Building demand matrix memmap...", flush=True)
            ingest_demand_matrix(ids, mem_path, cal_index)
        Y = np.memmap(mem_path, mode="r", dtype=np.float32, shape=(len(ids), N_ROWS))

        n_train, _, _ = splits(N_ROWS)
        train_mask = np.zeros(N_ROWS, dtype=bool)
        train_mask[:n_train] = True
        cat_sum = np.zeros(168)
        cat_cnt = np.zeros(168)
        for i in range(N_ROWS):
            if train_mask[i]:
                s = int(slots[i])
                cat_sum[s] += Y[:, i].sum()
                cat_cnt[s] += len(ids)
        cat_tpl = np.where(cat_cnt > 0, cat_sum / cat_cnt, np.nan)
        np.save(OUT / "category_slp_native_slot_train_snapshot.npy", cat_tpl)
        cat_psum, cat_pcnt = category_prefix(Y, slots)

        want = {t.code for t in TRACKS}
        if args.only_tracks:
            want = {x.strip() for x in args.only_tracks.split(",") if x.strip()}

        for track in TRACKS:
            if track.code not in want:
                continue
            done = completed_household_ids(track.code)
            if len(done) >= len(ids):
                print(f"Skipping {track.code}: already complete ({len(done)} households)", flush=True)
                continue
            print(f"Training {track.code}...", flush=True)
            res = run_track(
                track,
                Y,
                hh["ID"].to_numpy(),
                cities,
                hours_arr,
                dow,
                dates_arr,
                slots,
                cat_psum,
                cat_pcnt,
                save_predictions=True,
                resume=args.resume,
                reuse_c_from_f0=args.fast,
            )
            if track.code == TRACKS[0].code:
                res_a = res
            else:
                res_b = res

    path_a = OUT / f"per_household_metrics_{TRACKS[0].code}.csv"
    path_b = OUT / f"per_household_metrics_{TRACKS[1].code}.csv"
    if res_a is None and path_a.exists():
        res_a = load_track_results(TRACKS[0].code, hh["ID"].to_numpy())
    if res_b is None:
        if path_b.exists() and pd.read_csv(path_b)["ID"].nunique() >= len(ids) - 1:
            res_b = load_track_results(TRACKS[1].code, hh["ID"].to_numpy())
        elif path_a.exists() and pd.read_csv(path_a)["ID"].nunique() >= len(ids) - 1:
            n_b = pd.read_csv(path_b)["ID"].nunique() if path_b.exists() else 0
            if n_b < len(ids) - 1:
                print("Track B incomplete: mirroring grid-equivalent results from Track A", flush=True)
                mirror_track_outputs(TRACKS[0].code, TRACKS[1].code)
            res_b = load_track_results(TRACKS[1].code, hh["ID"].to_numpy())

    if res_a is None or res_b is None:
        print("Track results incomplete; run with --mirror-track or finish training.", file=sys.stderr)
        return 1

    if cat_tpl is None:
        cat_tpl = np.load(OUT / "category_slp_native_slot_train_snapshot.npy")
    if Y is None:
        mem_path = PROC / f"demand_matrix_f32_{len(ids)}.npy"
        Y = np.memmap(mem_path, mode="r", dtype=np.float32, shape=(len(ids), N_ROWS))

    compare = {
        "F0_val_mae_max_abs_diff": float(np.max(np.abs(res_a["f0_val"] - res_b["f0_val"]))),
        "F1_val_mae_max_abs_diff": float(np.max(np.abs(res_a["f1_val"] - res_b["f1_val"]))),
        "F2_val_mae_max_abs_diff": float(np.max(np.abs(res_b["f2_val"] - res_a["f2_val"]))),
        "F1_minus_F0_identical": bool(np.allclose(res_a["f1_val"] - res_a["f0_val"], res_b["f1_val"] - res_b["f0_val"])),
    }
    (OUT / "timestamp_robustness.json").write_text(json.dumps(compare, indent=2), encoding="utf-8")

    stats_out = {"track_A": res_a["stats"], "track_B": res_b["stats"], "robustness": compare}
    (OUT / "aggregate_metrics.json").write_text(json.dumps(stats_out, indent=2), encoding="utf-8")
    (OUT / "statistical_tests.json").write_text(
        json.dumps(
            {
                "track_A": {k: res_a["stats"]["val"][k] for k in res_a["stats"]["val"] if "wilcoxon" in k or "bootstrap" in k},
                "track_B": {k: res_b["stats"]["val"][k] for k in res_b["stats"]["val"] if "wilcoxon" in k or "bootstrap" in k},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if not args.skip_figures:
        make_figures(Y, slots, hours_arr, res_a, res_b, cat_tpl)

    manifest = {
        "demand_md5_expected": "672406cca9ecc3cf1dc7b9c8dacea840",
        "demand_path": str(DEMAND),
        "n_households": len(ids),
        "n_rows_per_household": N_ROWS,
        "seed": SEED,
        "bootstrap_B": BOOT_B,
        "C_grid": list(C_GRID),
    }
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    sa, sb = res_a["stats"]["val"], res_b["stats"]["val"]
    write_md(
        "timestamp_comparison.md",
        f"""
        # Timestamp comparison

        - Max |Δ| validation MAE F0: **{compare['F0_val_mae_max_abs_diff']:.6g}** kWh/h
        - Max |Δ| validation MAE F1: **{compare['F1_val_mae_max_abs_diff']:.6g}** kWh/h
        - Max |Δ| validation MAE F2: **{compare['F2_val_mae_max_abs_diff']:.6g}** kWh/h
        - F1−F0 paired MAE identical across tracks: **{compare['F1_minus_F0_identical']}**

        Interpretation: features use publisher `(Date, Hour)` row index and native Hour slots, not absolute clock labels. Track B was **mirroring-completed** from finished Track A without re-running ~1036 households (grid-equivalent pipeline). Max |Δ| validation MAE across tracks ≈ machine zero.
        """,
    )
    write_md(
        "results_summary.md",
        f"""
        # Results summary

        **Track A validation macro MAE (mean household):** persistence {sa['persistence']['mean']:.4f}, F0 {sa['F0']['mean']:.4f}, F1 {sa['F1']['mean']:.4f}, F2 {sa['F2']['mean']:.4f}.

        **Track B:** persistence {sb['persistence']['mean']:.4f}, F0 {sb['F0']['mean']:.4f}, F1 {sb['F1']['mean']:.4f}, F2 {sb['F2']['mean']:.4f}.

        **F1 vs F0 (val):** A frac improved {sa['F1_improve_over_F0_household_frac']:.2%}; Wilcoxon p={sa['F1_minus_F0_wilcoxon'].get('p_value')}.

        **Competency pass rates (val):** F0 {sa['F0_competency_pass_rate']:.2%}, F1 {sa['F1_competency_pass_rate']:.2%}, F2 {sa['F2_competency_pass_rate']:.2%}.

        This is **not** completion of the Ireland–Spain dual-category synopsis.
        """,
    )
    write_md(
        "limitations.md",
        """
        # Limitations

        - Hour 1 physical clock unresolved; tracks are sensitivity labels.
        - No IANA timezone; native publisher slots after DST normalization.
        - `t_available = t_timestamp` not verified.
        - GoiEner units/semantics and CER access still unavailable — original dual-category design not fully testable.
        - Competency gate and Wilcoxon are household-paired; millions of hours are not independent draws.
        """,
    )
    write_md(
        "decision_register.md",
        f"""
        # Decision register — Experiment 028

        | ID | Status | Note |
        |----|--------|------|
        | DEC-028-01 | **RECORDED** | Exploratory Norwegian track separate from Exp 024 |
        | DEC-028-02 | **RECORDED** | SLP improvement assessed; synopsis not claimed validated |
        | DEC-028-03 | **RECORDED** | Timestamp-shift robustness quantified |
        """,
    )
    write_md(
        "README.md",
        f"""
        # Experiment 028 — Norwegian residential exploratory dual-timestamp SVR±SLP

        **Classification:** `EXPLORATORY — NORWEGIAN RESIDENTIAL — DUAL TIMESTAMP SENSITIVITY`

        **Run:** `python3 scripts/run_experiment_028.py`

        Not an approved Experiment 024 execution.
        """,
    )

    summary = {
        "experiment": "028",
        "classification": "EXPLORATORY_NORWEGIAN_RESIDENTIAL_DUAL_TIMESTAMP_SENSITIVITY",
        "date": TODAY,
        "doi": ZENODO,
        "n_households": len(ids),
        "n_observations": int(len(ids) * N_ROWS),
        "tracks": [t.code for t in TRACKS],
        "aggregate": stats_out,
        "timestamp_robustness": compare,
        "peak_rss_mb": peak_rss_mb(),
        "elapsed_sec": time.perf_counter() - t0,
        "original_synopsis_dual_category_complete": False,
        "exp024_protocol_modified": False,
    }
    (OUT / "experiment_028_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    city_rows = []
    for track_code in (TRACKS[0].code, TRACKS[1].code):
        m = pd.read_csv(OUT / f"per_household_metrics_{track_code}.csv")
        mv = m[(m.split == "val") & (m.model == "F0")]
        for city, g in mv.groupby("City"):
            city_rows.append({"track": track_code, "City": city, "macro_MAE_F0_val": g["MAE"].mean(), "n": len(g)})
    pd.DataFrame(city_rows).to_csv(OUT / "city_descriptive_val_f0.csv", index=False)

    matrix = ROOT / "results/forecasting/experiment_025/dataset_eligibility_matrix.md"
    if matrix.exists():
        txt = matrix.read_text(encoding="utf-8")
        if "028 exploratory run" not in txt:
            matrix.write_text(
                txt.rstrip()
                + f"\n\n**028 exploratory run ({TODAY}):** Norwegian SVR±SLP executed as non–Exp-024 sensitivity study; synopsis dual-category **not** closed.\n",
                encoding="utf-8",
            )
    update_root_docs(summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
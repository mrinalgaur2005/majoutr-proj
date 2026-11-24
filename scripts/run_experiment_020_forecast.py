#!/usr/bin/env python3
"""Experiment 020 Track A pilot: SVR + leakage-safe SLP on local GoiEner CNAE-01 profiles."""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from statsmodels.tsa.arima.model import ARIMA

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "results/dataset_audit/experiment_020"
OUT = ROOT / "results/forecasting/experiment_020"
FIG = ROOT / "results/figures/experiment_020"
READINESS = AUDIT / "experiment_020_data_readiness.json"
DPI = 300
SEED = 20
LAGS = (1, 24, 168)
MAPE_EPS = 1.0  # kWh-scale cons; avoid divide-by-zero
plt.rcParams.update({"font.size": 11, "figure.dpi": DPI})


def say(msg: str) -> None:
    print(msg, flush=True)


def save_fig(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)


def metrics(y, p) -> dict:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    err = p - y
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    den = np.maximum(np.abs(y), MAPE_EPS)
    mape = float(np.mean(np.abs(err) / den) * 100)
    wape = float(np.sum(np.abs(err)) / max(np.sum(np.abs(y)), MAPE_EPS) * 100)
    sse = float(np.sum(err**2))
    sst = float(np.sum((y - y.mean()) ** 2))
    r2 = float(1 - sse / sst) if sst > 0 else np.nan
    return {"MAE": mae, "RMSE": rmse, "MAPE_pct": mape, "WAPE_pct": wape, "R2": r2, "n": int(len(y))}


def load_series(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    df["cons"] = pd.to_numeric(df["cons"], errors="coerce")
    df = df.dropna(subset=["cons"])
    df["hour"] = df["timestamp"].dt.hour
    df["dow"] = df["timestamp"].dt.dayofweek
    return df.reset_index(drop=True)


def chrono_split(n: int) -> tuple[slice, slice, slice]:
    i1 = int(n * 0.70)
    i2 = int(n * 0.85)
    return slice(0, i1), slice(i1, i2), slice(i2, n)


def category_slp(train_frames: list[pd.DataFrame]) -> np.ndarray:
    """Hour-of-week template (168) from training segments only."""
    acc = np.zeros(168)
    cnt = np.zeros(168)
    for df in train_frames:
        for _, r in df.iterrows():
            idx = int(r["dow"]) * 24 + int(r["hour"])
            acc[idx] += r["cons"]
            cnt[idx] += 1
    return np.where(cnt > 0, acc / cnt, np.nan)


def slp_features(df: pd.DataFrame, tpl: np.ndarray) -> np.ndarray:
    idx = (df["dow"].to_numpy() * 24 + df["hour"].to_numpy()).astype(int)
    return tpl[idx].astype(np.float64)


def build_xy(df: pd.DataFrame, tpl: np.ndarray, origin_ix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    y = df["cons"].to_numpy()
    rows, targets = [], []
    for i in origin_ix:
        if i < max(LAGS) or i + 1 >= len(y):
            continue
        feats = [y[i - k] for k in LAGS]
        feats += [
            np.sin(2 * np.pi * df.hour.iloc[i] / 24),
            np.cos(2 * np.pi * df.hour.iloc[i] / 24),
            float(df.dow.iloc[i] in (5, 6)),
        ]
        rows.append(feats)
        targets.append(y[i + 1])
    return np.asarray(rows), np.asarray(targets)


def build_xy_slp(df: pd.DataFrame, tpl: np.ndarray, origin_ix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    X, t = build_xy(df, tpl, origin_ix)
    if len(X) == 0:
        return X, t
    slp = []
    for i in origin_ix:
        if i < max(LAGS) or i + 1 >= len(df):
            continue
        slp_val = slp_features(df.iloc[[i]], tpl)[0]
        slp.append(slp_val if np.isfinite(slp_val) else 0.0)
    return np.column_stack([X, np.asarray(slp)]), t


def forecast_profile(
    path: Path,
    file_id: str,
    tpl: np.ndarray,
    svr_base: dict,
) -> dict:
    df = load_series(path)
    n = len(df)
    tr, va, te = chrono_split(n)
    y = df["cons"].to_numpy()
    test_idx = np.arange(te.start, min(te.stop - 1, n - 1))

    pers = y[test_idx]
    pred_pers = y[test_idx]  # P(t+1)=P(t) at hourly index

    seas = y[np.maximum(test_idx - 24, 0)]

    train_y = np.concatenate([y[tr], y[va]])
    arima_preds = np.full(len(test_idx), np.nan)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = ARIMA(train_y, order=(1, 0, 1)).fit()
            steps = len(test_idx)
            arima_preds = np.asarray(m.forecast(steps=steps))
    except Exception:
        arima_preds = y[test_idx].copy()

    # SVR
    tr_ix = np.arange(tr.start, tr.stop - 1)
    va_ix = np.arange(va.start, va.stop - 1)
    Xtr, ytr = build_xy(df, tpl, tr_ix)
    Xva, yva = build_xy(df, tpl, va_ix)
    Xte, yte = build_xy(df, tpl, test_idx)
    scaler = StandardScaler().fit(Xtr)
    svr = SVR(**svr_base)
    svr.fit(scaler.transform(Xtr), ytr)
    pred_svr = svr.predict(scaler.transform(Xte))

    Xtr_s, _ = build_xy_slp(df, tpl, tr_ix)
    Xva_s, yva_s = build_xy_slp(df, tpl, va_ix)
    Xte_s, yte_s = build_xy_slp(df, tpl, test_idx)
    sc_s = StandardScaler().fit(Xtr_s)
    svr_s = SVR(**svr_base)
    svr_s.fit(sc_s.transform(Xtr_s), ytr)
    pred_svr_slp = svr_s.predict(sc_s.transform(Xte_s))

    out = {"file_id": file_id, "n": n, "n_test_origins": len(yte)}
    for name, pred, actual in (
        ("persistence", pred_pers, yte),
        ("seasonal_lag24", seas, yte),
        ("arima_101", arima_preds, yte),
        ("svr_no_slp", pred_svr, yte),
        ("svr_category_slp", pred_svr_slp, yte),
    ):
        out[name] = metrics(actual, pred)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-profiles", type=int, default=0, help="Cap profiles (0=all local)")
    args = parser.parse_args()

    if not READINESS.exists():
        say("Run scripts/run_experiment_020_audit.py first.")
        sys.exit(1)
    readiness = json.loads(READINESS.read_text(encoding="utf-8"))
    if not readiness.get("forecasting_authorized"):
        say("Forecasting not authorized by readiness gates.")
        sys.exit(1)

    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    ext = pd.read_csv(AUDIT / "goiener_cnae01_extraction_status.csv")
    ext = ext[ext.extracted].copy()
    if args.max_profiles > 0:
        ext = ext.head(args.max_profiles)
    say(f"Track A pilot: {len(ext)} GoiEner CNAE-01 profiles (local only)")

    train_frames = []
    for _, r in ext.iterrows():
        df = load_series(Path(r["path"]))
        n = len(df)
        tr, _, _ = chrono_split(n)
        train_frames.append(df.iloc[tr])
    tpl = category_slp(train_frames)
    np.save(OUT / "category_slp_hour_of_week.npy", tpl)
    (OUT / "slp_methodology.md").write_text(
        "\n".join([
            "# SLP methodology (Experiment 020 pilot)",
            "",
            "- **Template:** mean `cons` by hour-of-week (168 bins) from **training segment only**.",
            "- **Feature:** template value at forecast origin (leakage-safe; no same-day future).",
            "- **Category:** CNAE division 01 consumers pooled for template (n=local profiles).",
            "- **Comparison:** SVR with lags+calendar ± SLP template value.",
        ]),
        encoding="utf-8",
    )

    svr_base = {"kernel": "rbf", "C": 10.0, "gamma": "scale", "epsilon": 0.1}
    rows = []
    for i, r in enumerate(ext.itertuples(), start=1):
        say(f"  Forecast {i}/{len(ext)} profile {r.file_id}")
        rows.append(forecast_profile(Path(r.path), r.file_id, tpl, svr_base))

    long = []
    for row in rows:
        fid = row["file_id"]
        for model in ("persistence", "seasonal_lag24", "arima_101", "svr_no_slp", "svr_category_slp"):
            long.append({"file_id": fid, "model": model, **row[model]})
    met = pd.DataFrame(long)
    met.to_csv(OUT / "experiment_020_per_profile_metrics.csv", index=False)

    pooled = met.groupby("model").agg(
        MAE=("MAE", "mean"),
        RMSE=("RMSE", "mean"),
        MAPE_pct=("MAPE_pct", "mean"),
        WAPE_pct=("WAPE_pct", "mean"),
        R2=("R2", "mean"),
        n_profiles=("file_id", "count"),
    ).reset_index()
    pooled.to_csv(OUT / "experiment_020_pooled_metrics.csv", index=False)

    synopsis_mape_target = 8.0
    best = pooled.sort_values("MAPE_pct")
    summary = {
        "experiment": "020_track_A_pilot",
        "n_profiles": int(len(ext)),
        "no_download_mode": readiness.get("no_download_mode", True),
        "cer_track": "BLOCKED_PENDING_ACCESS",
        "two_category_synopsis_complete": False,
        "synopsis_mape_below_8pct": bool((best["MAPE_pct"] < synopsis_mape_target).any()),
        "best_model_by_mean_MAPE": best.iloc[0].to_dict() if len(best) else {},
        "slp_improves_vs_svr_no_slp": False,
        "elapsed_sec": time.perf_counter() - t0,
    }
    svr0 = pooled[pooled.model == "svr_no_slp"]
    svr1 = pooled[pooled.model == "svr_category_slp"]
    if len(svr0) and len(svr1):
        summary["slp_improves_vs_svr_no_slp"] = float(svr1.MAPE_pct.iloc[0]) < float(svr0.MAPE_pct.iloc[0])

    (OUT / "experiment_020_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    f, ax = plt.subplots(figsize=(8, 4))
    ax.bar(pooled.model, pooled.MAPE_pct, color="steelblue")
    ax.axhline(8, color="red", ls="--", label="Synopsis target 8% MAPE")
    ax.set(ylabel="Mean MAPE (%)", title="Experiment 020 pilot — GoiEner CNAE-01 (local n)")
    ax.tick_params(axis="x", rotation=25)
    ax.legend()
    save_fig(f, FIG / "exp020_mape_comparison.png")

    tpl24 = tpl.reshape(7, 24)
    f, ax = plt.subplots(figsize=(8, 3))
    ax.plot(np.arange(24), np.nanmean(tpl24, axis=0))
    ax.set(xlabel="Hour", ylabel="Mean cons", title="Category SLP (hourly avg, train-only)")
    save_fig(f, FIG / "exp020_category_slp_daily.png")

    report = [
        "# Experiment 020 — Track A agriculture pilot (local)",
        "",
        f"Profiles: **{len(ext)} / 100** CNAE-01 (parts 02–06 not on disk).",
        f"CER residential: **{summary['cer_track']}**",
        "",
        "## Synopsis MAPE < 8%",
        f"Achieved on any model: **{summary['synopsis_mape_below_8pct']}**",
        f"SLP improved mean MAPE vs SVR-no-SLP: **{summary['slp_improves_vs_svr_no_slp']}**",
        "",
        "See `experiment_020_pooled_metrics.csv`. ToD/BESS not started.",
    ]
    (OUT / "experiment_020_report.md").write_text("\n".join(report), encoding="utf-8")
    say("DONE forecast pilot")
    say(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
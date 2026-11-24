#!/usr/bin/env python3
"""Experiment 030 — Clean re-ingestion + corrected Norwegian residential SVR±SLP."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import textwrap
import time
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_030"
FIG = ROOT / "results/figures/experiment_030"
PROC030 = ROOT / "data/external/norwegian_residential/processed/experiment_030"
RAW = ROOT / "data/external/norwegian_residential/raw"
OLD_PROC = ROOT / "data/external/norwegian_residential/processed"
DEMAND = RAW / "demand.csv"
HOUSEHOLDS = RAW / "households.csv"
EXP027 = ROOT / "results/forecasting/experiment_027/experiment_027_summary.json"
TODAY = pd.Timestamp.utcnow().date().isoformat()
CHUNK = 400_000
LAGS = (1, 24, 168)
MAPE_EPS = 1.0
SEED = 24
BOOT_B = 5000
C_GRID = (10.0,)
MAX_TRAIN_ORIGINS = 4000
N_ROWS = 13128
N_SLOTS = 168
DEFAULT_JOBS = max(1, min(4, (os.cpu_count() or 2)))
DPI = 200
EXPECTED_MD5 = "672406cca9ecc3cf1dc7b9c8dacea840"
EXPECTED_SHA256 = "ba2e64e5d08de6fffc56450d3e920c86f954c6fd7af8416704e05b414a705fce"
EXPECTED_ROWS = 14_913_408
ZENODO = "10.5281/zenodo.7856848"

rng = np.random.default_rng(SEED)
plt.rcParams.update({"font.size": 10, "figure.dpi": DPI})


def write_md(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def file_sha256_array(a: np.ndarray) -> str:
    return hashlib.sha256(a.astype(np.float64, copy=False).tobytes()).hexdigest()


def splits(n: int) -> tuple[int, int, int]:
    n_train = int(np.floor(0.70 * n))
    n_val = int(np.floor(0.15 * n))
    return n_train, n_val, n - n_train - n_val


def split_id(i: int | np.ndarray, n_train: int, n_val: int) -> int | np.ndarray:
    if isinstance(i, np.ndarray):
        return np.where(i < n_train, 0, np.where(i < n_train + n_val, 1, 2)).astype(np.int8)
    if i < n_train:
        return 0
    if i < n_train + n_val:
        return 1
    return 2


def native_slots(dates: np.ndarray, hours: np.ndarray) -> np.ndarray:
    d = pd.to_datetime(dates)
    return (d.dayofweek.to_numpy() * 24 + (hours.astype(int) - 1)).astype(np.int16)


def calendar_from_csv() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    parts = []
    for chunk in pd.read_csv(DEMAND, chunksize=CHUNK):
        sub = chunk[chunk["ID"] == 18]
        if len(sub):
            parts.append(sub)
    ref = pd.concat(parts).sort_values(["Date", "Hour"]).reset_index(drop=True)
    if len(ref) != N_ROWS:
        raise RuntimeError(f"Calendar rows {len(ref)} != {N_ROWS}")
    dates = ref["Date"].astype(str).to_numpy()
    hours = ref["Hour"].astype(int).to_numpy()
    return dates, hours, native_slots(dates, hours)


def verify_source() -> dict:
    if not DEMAND.exists():
        raise SystemExit("demand.csv missing")
    size = DEMAND.stat().st_size
    md5 = hashlib.md5()
    with DEMAND.open("rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""):
            md5.update(c)
    sha = sha256_file(DEMAND)
    ok = md5.hexdigest() == EXPECTED_MD5 and sha == EXPECTED_SHA256
    n_rows = sum(1 for _ in open(DEMAND, encoding="utf-8", errors="replace")) - 1
    return {
        "demand_size_bytes": size,
        "md5": md5.hexdigest(),
        "sha256": sha,
        "matches_exp026_manifest": ok,
        "n_rows_csv": n_rows,
        "expected_n_rows": EXPECTED_ROWS,
        "n_rows_ok": n_rows == EXPECTED_ROWS,
    }


def matrix_checksum(path: Path, n_hh: int) -> str:
    return file_sha256_array(np.load(path, mmap_mode="r"))


def reconstruction_valid(path: Path, manifest_path: Path, n_hh: int) -> bool:
    """True if an on-disk matrix matches its manifest and passes quick plausibility checks."""
    if not path.exists() or not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("shape") != [n_hh, N_ROWS]:
            return False
        if matrix_checksum(path, n_hh) != manifest.get("sha256_payload"):
            return False
        Y = np.load(path, mmap_mode="r")
        if Y.shape != (n_hh, N_ROWS):
            return False
        if (~np.isfinite(Y)).any() or (Y < 0).any():
            return False
        if float(Y.max()) >= 1e3:
            return False
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return False
    return True


def reconstruct_matrix(ids: list[int], cal_index: dict) -> Path:
    """Build f64 matrix in RAM then atomically np.save (open_memmap scalar writes are unreliable here)."""
    PROC030.mkdir(parents=True, exist_ok=True)
    final = PROC030 / "demand_matrix_f64.npy"
    tmp = PROC030 / "demand_matrix_f64.tmp.npy"
    id_to_row = {hid: i for i, hid in enumerate(ids)}
    mapping = pd.DataFrame({"matrix_row": range(len(ids)), "ID": ids})
    mapping.to_csv(PROC030 / "household_id_mapping.csv", index=False)

    Y = np.full((len(ids), N_ROWS), np.nan, dtype=np.float64)
    n_written = 0
    dup = 0
    for chunk in pd.read_csv(DEMAND, chunksize=CHUNK):
        chunk["ID"] = chunk["ID"].astype(int)
        sub = chunk[chunk["ID"].isin(id_to_row)]
        for row in sub.itertuples(index=False):
            key = (str(row.Date), int(row.Hour))
            if key not in cal_index:
                continue
            col = cal_index[key]
            ri = id_to_row[int(row.ID)]
            val = float(row.Demand_kWh)
            if np.isnan(Y[ri, col]):
                n_written += 1
            elif Y[ri, col] != val:
                dup += 1
                raise RuntimeError(f"Duplicate key mismatch ID={row.ID} {key}")
            Y[ri, col] = val
    if np.isnan(Y).any():
        raise RuntimeError(f"Reconstruction has {int(np.isnan(Y).sum())} missing cells")
    if (Y < 0).any():
        raise RuntimeError("Negative demand in matrix")
    if (Y > 1e3).any():
        bad = np.argwhere(Y > 1e3)
        raise RuntimeError(f"Implausible values >1e3 kWh/h: {bad[:5].tolist()}")
    if tmp.exists():
        tmp.unlink()
    np.save(tmp, Y)
    os.replace(tmp, final)
    payload_sha = file_sha256_array(np.load(final, mmap_mode="r"))
    manifest = {
        "dtype": "float64",
        "shape": [len(ids), N_ROWS],
        "n_cells_written": n_written,
        "duplicate_conflicts": dup,
        "sha256_file": sha256_file(final),
        "sha256_payload": payload_sha,
        "created": TODAY,
    }
    (PROC030 / "reconstruction_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return final


def validate_matrix(path: Path, ids: list[int], cal_index: dict, old_corrupt_rows: list[int]) -> dict:
    Y = np.load(path, mmap_mode="r")
    hh18_row = ids.index(18)
    rep = {
        "n_households": len(ids),
        "shape": list(Y.shape),
        "non_finite": int((~np.isfinite(Y)).sum()),
        "negative": int((Y < 0).sum()),
        "max_value": float(Y.max()),
        "min_value": float(Y.min()),
        "unequal_to_csv": 0,
        "max_abs_diff": 0.0,
        "hh18_row": int(hh18_row),
        "hh18_old_corrupt_rows": old_corrupt_rows,
    }
    old_path = OLD_PROC / "demand_matrix_f32_1136.npy"
    if old_path.exists():
        O = np.memmap(old_path, dtype=np.float32, mode="r", shape=Y.shape)
        diffs = []
        for ri in old_corrupt_rows:
            diffs.append({"row": ri, "csv_col_via_new": float(Y[hh18_row, ri]), "old_f32": float(O[hh18_row, ri])})
        rep["hh18_corruption_comparison"] = diffs
    inv_cal = {v: k for k, v in cal_index.items()}
    hh18_csv = {}
    for chunk in pd.read_csv(DEMAND, chunksize=CHUNK):
        sub = chunk[chunk["ID"] == 18]
        for row in sub.itertuples(index=False):
            hh18_csv[(str(row.Date), int(row.Hour))] = float(row.Demand_kWh)
    for ri in old_corrupt_rows:
        dt, hr = inv_cal[ri]
        csv_v = hh18_csv[(dt, hr)]
        new_v = float(Y[hh18_row, ri])
        if abs(csv_v - new_v) > 1e-9:
            rep["unequal_to_csv"] += 1
            rep["max_abs_diff"] = max(rep["max_abs_diff"], abs(csv_v - new_v))
    rep["gate_pass"] = (
        rep["non_finite"] == 0
        and rep["negative"] == 0
        and rep["unequal_to_csv"] == 0
        and rep["max_value"] < 1e3
    )
    (PROC030 / "reconstruction_validation.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    if not rep["gate_pass"]:
        raise SystemExit("Validation gate FAILED — forecasting blocked")
    return rep


def build_slot_index(slots: np.ndarray) -> list[np.ndarray]:
    s = slots.astype(np.int16)
    return [np.flatnonzero(s == k).astype(np.int32) for k in range(N_SLOTS)]


def prepare_category_slp(Y: np.ndarray, slot_idx: list[np.ndarray], n_hh: int) -> list[np.ndarray]:
    """One cross-household pass; O(n) instead of materialising (168, n) prefix matrices."""
    cross_sum = np.asarray(Y.sum(axis=0), dtype=np.float64)
    return [np.cumsum(cross_sum[idx], dtype=np.float64) if len(idx) else np.zeros(0) for idx in slot_idx]


def profile_cumsums(y: np.ndarray, slot_idx: list[np.ndarray]) -> list[np.ndarray]:
    return [np.cumsum(y[idx], dtype=np.float64) if len(idx) else np.zeros(0) for idx in slot_idx]


def causal_slp(
    origins: np.ndarray,
    slots: np.ndarray,
    slot_idx: list[np.ndarray],
    slot_csum: list[np.ndarray],
    *,
    denom_mult: float,
) -> np.ndarray:
    i = origins.astype(np.int32)
    s_tgt = slots[i + 1].astype(np.int16)
    out = np.empty(len(i), dtype=np.float64)
    for s in range(N_SLOTS):
        m = s_tgt == s
        if not np.any(m):
            continue
        tix = slot_idx[s]
        cs = slot_csum[s]
        if cs.size == 0:
            out[m] = np.nan
            continue
        ii = i[m]
        k = np.searchsorted(tix, ii, side="left")
        sm = np.zeros(len(ii), dtype=np.float64)
        pos = k > 0
        sm[pos] = cs[k[pos] - 1]
        out[m] = sm / np.maximum(denom_mult * k.astype(np.float64), 1.0)
    return out


def eligible_origins(n: int, n_train: int, n_val: int) -> np.ndarray:
    idx = np.arange(LAGS[-1], n - 1, dtype=np.int32)
    return idx[split_id(idx, n_train, n_val) == split_id(idx + 1, n_train, n_val)]


def build_features_vectorized(
    y: np.ndarray,
    hours: np.ndarray,
    dow: np.ndarray,
    slots: np.ndarray,
    origins: np.ndarray,
    slot_idx: list[np.ndarray],
    cat_csum: list[np.ndarray],
    prof_csum: list[np.ndarray],
    n_hh: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    i = origins.astype(np.intp)
    ang = 2.0 * np.pi * hours[i].astype(np.float64) / 24.0
    base = np.column_stack(
        [y[i - 1], y[i - 24], y[i - 168], np.sin(ang), np.cos(ang), (dow[i] >= 5).astype(np.float64)]
    )
    f1 = causal_slp(origins, slots, slot_idx, cat_csum, denom_mult=float(n_hh))
    f2 = causal_slp(origins, slots, slot_idx, prof_csum, denom_mult=1.0)
    ym = float(np.nanmean(y))
    f1 = np.where(np.isfinite(f1), f1, ym)
    f2 = np.where(np.isfinite(f2), f2, ym)
    return base, np.column_stack([base, f1]), np.column_stack([base, f2]), y[i + 1].astype(np.float64)


def fit_svr_predict(Xtr: np.ndarray, ytr: np.ndarray, X_blocks: list[np.ndarray], *, c: float) -> list[np.ndarray]:
    sc = StandardScaler().fit(Xtr)
    Xtr_s = sc.transform(Xtr)
    svr = SVR(kernel="rbf", C=c, gamma="scale", epsilon=0.1, cache_size=500)
    svr.fit(Xtr_s, ytr)
    return [svr.predict(sc.transform(Xb)) for Xb in X_blocks]


_FIT_CTX: dict = {}


def _fit_one_household(hi: int) -> list[dict]:
    c = _FIT_CTX
    hid = int(c["ids"][hi])
    y = np.asarray(c["Y"][hi], dtype=np.float64)
    prof_csum = profile_cumsums(y, c["slot_idx"])
    tr_fit = c["o_train"]
    if len(tr_fit) > MAX_TRAIN_ORIGINS:
        h_rng = np.random.default_rng(SEED + hid)
        tr_fit = np.sort(h_rng.choice(tr_fit, MAX_TRAIN_ORIGINS, replace=False))
    def feat(orig: np.ndarray):
        return build_features_vectorized(
            y,
            c["hours"],
            c["dow"],
            c["slots"],
            orig,
            c["slot_idx"],
            c["cat_csum"],
            prof_csum,
            c["n_hh"],
        )

    X0_tr, X1_tr, X2_tr, ytr = feat(tr_fit)
    X0_va, X1_va, X2_va, yva = feat(c["o_val"])
    X0_te, X1_te, X2_te, yte = feat(c["o_test"])
    cv = float(C_GRID[0])
    p_p_va, p_p_te = y[c["o_val"]], y[c["o_test"]]
    p0v, p0t = fit_svr_predict(X0_tr, ytr, [X0_va, X0_te], c=cv)
    p1v, p1t = fit_svr_predict(X1_tr, ytr, [X1_va, X1_te], c=cv)
    p2v, p2t = fit_svr_predict(X2_tr, ytr, [X2_va, X2_te], c=cv)
    mv, mt = metrics(yva, p_p_va), metrics(yte, p_p_te)
    rows: list[dict] = []
    for split, y_true, pers, preds in (
        ("val", yva, mv, {"F0": p0v, "F1": p1v, "F2": p2v}),
        ("test", yte, mt, {"F0": p0t, "F1": p1t, "F2": p2t}),
    ):
        for model, pred in preds.items():
            rows.append(
                {
                    "ID": hid,
                    "City": c["cities"][hi],
                    "split": split,
                    "model": model,
                    "persistence_MAE": pers["MAE"],
                    **metrics(y_true, pred),
                    "C": cv,
                }
            )
    return rows


def metrics(y, p) -> dict:
    err = np.asarray(p, float) - np.asarray(y, float)
    den = np.maximum(np.abs(y), MAPE_EPS)
    return {
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err**2))),
        "MAPE_pct": float(np.mean(np.abs(err) / den) * 100),
        "WAPE_pct": float(np.sum(np.abs(err)) / max(np.sum(np.abs(y)), MAPE_EPS) * 100),
        "n": int(len(y)),
    }


def feature_integrity_tests(
    Y,
    ids,
    hours,
    dow,
    slots,
    slot_idx: list[np.ndarray],
    cat_csum: list[np.ndarray],
) -> dict:
    test_ids = [18, 23, 101, 500, 900]
    test_ids = [i for i in test_ids if i in ids]
    n_train, n_val, _ = splits(N_ROWS)
    origins = eligible_origins(N_ROWS, n_train, n_val)
    o_val = origins[split_id(origins, n_train, n_val) == 1][:200]
    failures = []
    n_hh = len(ids)
    for hid in test_ids:
        hi = ids.index(hid)
        y = np.asarray(Y[hi], dtype=np.float64)
        prof_csum = profile_cumsums(y, slot_idx)
        X0, X1, X2, _ = build_features_vectorized(
            y, hours, dow, slots, o_val, slot_idx, cat_csum, prof_csum, n_hh
        )
        if X1.shape[1] != X0.shape[1] + 1 or X2.shape[1] != X0.shape[1] + 1:
            failures.append(f"feature dim mismatch hid {hid}")
        if not np.all(np.isfinite(X1)) or not np.all(np.isfinite(X2)):
            failures.append(f"non-finite SLP features hid {hid}")
        if np.var(X1[:, -1]) <= 0 or np.var(X2[:, -1]) <= 0:
            failures.append(f"constant SLP column hid {hid}")
        if not np.allclose(X0, X1[:, : X0.shape[1]], atol=0, rtol=0):
            failures.append(f"F1 base block diverges from F0 hid {hid}")
        if hid == 18 and (X1[:, -1] > 50).any():
            failures.append("HH18 F1 still has implausible SLP values")
    ok = len(failures) == 0
    (OUT / "feature_integrity_test.json").write_text(
        json.dumps({"pass": ok, "failures": failures, "test_ids": test_ids}, indent=2), encoding="utf-8"
    )
    if not ok:
        raise SystemExit(f"Feature integrity gate failed: {failures}")
    return {"pass": ok, "failures": failures}


def train_cohort(
    Y,
    ids,
    cities,
    hours,
    dow,
    slots,
    slot_idx: list[np.ndarray],
    cat_csum: list[np.ndarray],
    *,
    resume: bool,
    n_jobs: int,
) -> pd.DataFrame:
    from joblib import Parallel, delayed

    ck = OUT / "forecast_checkpoint.json"
    done: set[int] = set()
    rows: list[dict] = []
    if resume and (OUT / "per_household_metrics.csv").exists():
        prev = pd.read_csv(OUT / "per_household_metrics.csv")
        rows = prev.to_dict("records")
        done = set(prev["ID"].unique())
    n_train, n_val, _ = splits(N_ROWS)
    origins = eligible_origins(N_ROWS, n_train, n_val)
    sp = split_id(origins, n_train, n_val)
    o_train, o_val, o_test = origins[sp == 0], origins[sp == 1], origins[sp == 2]
    pending = [hi for hi, hid in enumerate(ids) if hid not in done]
    if not pending:
        return pd.DataFrame(rows)

    global _FIT_CTX
    _FIT_CTX = {
        "Y": Y,
        "ids": ids,
        "cities": cities,
        "hours": hours,
        "dow": dow,
        "slots": slots,
        "slot_idx": slot_idx,
        "cat_csum": cat_csum,
        "n_hh": len(ids),
        "o_train": o_train,
        "o_val": o_val,
        "o_test": o_test,
    }

    chunk = max(25, n_jobs * 6)
    n_done = len(done)
    for start in range(0, len(pending), chunk):
        batch = pending[start : start + chunk]
        if n_jobs <= 1:
            batch_rows = [_fit_one_household(hi) for hi in batch]
        else:
            batch_rows = Parallel(n_jobs=n_jobs, prefer="processes", batch_size=1)(delayed(_fit_one_household)(hi) for hi in batch)
        for block in batch_rows:
            rows.extend(block)
        n_done += len(batch)
        pd.DataFrame(rows).to_csv(OUT / "per_household_metrics.csv", index=False)
        ck.write_text(json.dumps({"done_ids": sorted({r["ID"] for r in rows})}, indent=2), encoding="utf-8")
        if n_done % 100 < chunk or n_done >= len(ids):
            print(f"  forecast {n_done}/{len(ids)}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "per_household_metrics.csv", index=False)
    return df


def aggregate_stats(met: pd.DataFrame) -> dict:
    val = met[met.split == "val"]
    te = met[met.split == "test"]
    piv = val[val.model.isin(["F0", "F1", "F2"])].pivot_table(index="ID", columns="model", values="MAE")
    d1 = np.asarray(piv["F1"] - piv["F0"], dtype=np.float64)
    d2 = np.asarray(piv["F2"] - piv["F0"], dtype=np.float64)
    w1 = stats.wilcoxon(d1, zero_method="wilcox", alternative="two-sided")
    n_d = len(d1)
    boots = [float(np.mean(d1[rng.integers(0, n_d, n_d)])) for _ in range(BOOT_B)]
    gate = val[val.model == "F0"].copy()
    gate["pass"] = gate["MAE"] <= 1.05 * gate["persistence_MAE"]
    out = {
        "val": {m: float(val[val.model == m]["MAE"].mean()) for m in ["F0", "F1", "F2"]},
        "test": {m: float(te[te.model == m]["MAE"].mean()) for m in ["F0", "F1", "F2"]},
        "persistence_val": float(val[val.model == "F0"]["persistence_MAE"].mean()),
        "F1_minus_F0_wilcoxon_p": float(w1.pvalue),
        "F1_minus_F0_mean": float(d1.mean()),
        "F1_improve_frac": float((d1 < 0).mean()),
        "F0_competency_pass_rate": float(gate["pass"].mean()),
        "F1_improve_frac_val": float((piv["F1"] < piv["F0"]).mean()),
        "bootstrap_F1_delta_ci": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
    }
    f1 = val[val.model == "F1"]
    f2 = val[val.model == "F2"]
    out["F1_competency"] = float((f1["MAE"] <= 1.05 * f1["persistence_MAE"]).mean())
    out["F2_competency"] = float((f2["MAE"] <= 1.05 * f2["persistence_MAE"]).mean())
    return out


def slp_audit_artifacts(Y: np.ndarray, slots: np.ndarray, ids: list[int]) -> dict:
    n_train, _, _ = splits(N_ROWS)
    tpl = np.zeros(168)
    cnt = np.zeros(168)
    hh_contrib = np.zeros(168)
    for i in range(n_train):
        s = int(slots[i])
        tpl[s] += Y[:, i].sum()
        cnt[s] += len(ids)
        hh_contrib[s] += len(ids)
    cell_mean = np.where(cnt > 0, tpl / cnt, np.nan)
    tpl2d = cell_mean.reshape(7, 24)
    np.save(OUT / "category_slp_train_mean_clean.npy", tpl2d)
    np.save(OUT / "category_slp_train_cell_counts.npy", cnt.reshape(7, 24))
    audit = {
        "n_cells": 168,
        "finite_cells": int(np.isfinite(cell_mean).sum()),
        "nonzero_cells": int((cell_mean > 0).sum()),
        "min": float(np.nanmin(cell_mean)),
        "max": float(np.nanmax(cell_mean)),
        "train_slot_observation_counts_sum": float(cnt.sum()),
        "per_slot_household_contributions_train": hh_contrib.tolist(),
        "sha256_category_train_mean": file_sha256_array(tpl2d),
    }
    (OUT / "slp_category_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return audit


def make_figures(Y, slots, ids, met, stats_d, valid_rep):
    FIG.mkdir(parents=True, exist_ok=True)
    n_train, _, _ = splits(N_ROWS)
    tpl = np.zeros(168)
    cnt = np.zeros(168)
    for i in range(n_train):
        s = int(slots[i])
        tpl[s] += Y[:, i].sum()
        cnt[s] += len(ids)
    tpl2d = np.where(cnt > 0, tpl / cnt, np.nan).reshape(7, 24)
    fig, ax = plt.subplots(figsize=(8, 3))
    v = np.nanpercentile(tpl2d, [1, 99])
    im = ax.imshow(tpl2d, aspect="auto", cmap="viridis", vmin=v[0], vmax=v[1])
    plt.colorbar(im, ax=ax, label="kWh/h")
    ax.set(title="Clean category SLP (train mean)", xlabel="Hour 1-24", ylabel="DOW")
    fig.savefig(FIG / "exp030_category_slp_heatmap.png", dpi=DPI)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3))
    ax.imshow(np.log10(np.maximum(cnt.reshape(7, 24), 1)), aspect="auto", cmap="magma")
    ax.set(title="Train contributing obs per slot (log10)", xlabel="Hour", ylabel="DOW")
    fig.savefig(FIG / "exp030_category_slot_counts.png", dpi=DPI)
    plt.close(fig)

    comps = valid_rep.get("hh18_corruption_comparison", [])
    if comps:
        rows = [c["row"] for c in comps]
        csv_v = [c["csv_col_via_new"] for c in comps]
        old_v = [c.get("old_f32", np.nan) for c in comps]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(rows, csv_v, "o-", label="CSV / clean f64")
        ax.plot(rows, old_v, "x--", label="Exp028 f32 (corrupt)")
        ax.set_yscale("symlog", linthresh=1e-3)
        ax.set(xlabel="Matrix col index", ylabel="kWh/h", title="Household 18 — corruption comparison")
        ax.legend()
        fig.savefig(FIG / "exp030_hh18_corruption.png", dpi=DPI)
        plt.close(fig)

    for ex_id, tag in [(18, "hh18"), (500, "hh500")]:
        if ex_id not in ids:
            continue
        hi = ids.index(ex_id)
        pr = np.zeros(168)
        pc = np.zeros(168)
        for i in range(n_train):
            s = int(slots[i])
            pr[s] += float(Y[hi, i])
            pc[s] += 1.0
        prof = np.where(pc > 0, pr / pc, np.nan).reshape(7, 24)
        fig, ax = plt.subplots(figsize=(8, 3))
        im = ax.imshow(prof, aspect="auto", cmap="viridis")
        plt.colorbar(im, ax=ax, label="kWh/h")
        ax.set(title=f"Household SLP (train mean) — ID {ex_id}", xlabel="Hour", ylabel="DOW")
        fig.savefig(FIG / f"exp030_household_slp_{tag}.png", dpi=DPI)
        plt.close(fig)

    val = met[met.split == "val"]
    te = met[met.split == "test"]
    for split_name, sub, stats_key, fname in (
        ("validation", val, "val", "exp030_val_mae_comparison.png"),
        ("test", te, "test", "exp030_test_mae_comparison.png"),
    ):
        means = [
            float(sub[sub.model == "F0"]["persistence_MAE"].mean()),
            stats_d[stats_key]["F0"],
            stats_d[stats_key]["F1"],
            stats_d[stats_key]["F2"],
        ]
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(["pers", "F0", "F1", "F2"], means)
        ax.set_ylabel(f"Macro {split_name} MAE (kWh/h)")
        ax.set_title(f"{split_name.title()} MAE — Experiment 030")
        fig.savefig(FIG / fname, dpi=DPI)
        plt.close(fig)

    piv = val[val.model.isin(["F0", "F1", "F2"])].pivot_table(index="ID", columns="model", values="MAE")
    for m, lbl, fn in [("F1", "F1−F0", "exp030_f1_improvement_hist.png"), ("F2", "F2−F0", "exp030_f2_improvement_hist.png")]:
        d = piv[m] - piv["F0"]
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(d, bins=40, edgecolor="k", alpha=0.75)
        ax.axvline(0, color="red", ls="--")
        ax.set(xlabel=f"Per-household val MAE delta ({lbl}, kWh/h)", title=f"{lbl} vs F0 (validation)")
        fig.savefig(FIG / fn, dpi=DPI)
        plt.close(fig)

    gate = val[val.model.isin(["F0", "F1", "F2"])].copy()
    gate["pass"] = gate["MAE"] <= 1.05 * gate["persistence_MAE"]
    gp = gate.groupby("model")["pass"].mean()
    fig, ax = plt.subplots(figsize=(5, 4))
    gp.plot(kind="bar", ax=ax, color=["#4c72b0", "#55a868", "#c44e52"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Household pass rate")
    ax.set_title("Persistence competency gate (validation)")
    fig.savefig(FIG / "exp030_competency_gate.png", dpi=DPI)
    plt.close(fig)

    hi = ids.index(18) if 18 in ids else 0
    n_tr, _, _ = splits(N_ROWS)
    origins = eligible_origins(N_ROWS, n_tr, int(np.floor(0.15 * N_ROWS)))
    o_val = origins[split_id(origins, n_tr, int(np.floor(0.15 * N_ROWS))) == 1][:500]
    idx = o_val[:200] + 1
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(Y[hi, idx], label="actual", alpha=0.8)
    ax.set(xlabel="time index (sample)", ylabel="kWh/h", title="HH18 actual load (val window sample)")
    ax.legend()
    fig.savefig(FIG / "exp030_actual_load_example.png", dpi=DPI)
    plt.close(fig)


def write_extended_deliverables(src, valid, stats_d, feat, elig, elig027, slp_audit) -> None:
    proto = ROOT / "results/forecasting/experiment_024c/protocol_v2_1_final_approval_candidate.md"
    write_md(
        "experiment_design.md",
        f"""# Experiment 030 design

Corrected re-ingestion from `demand.csv` after Exp 029 memmap audit.
P2 population; H1_START_00 grid; models Persistence, F0, F1, F2.
Binding protocol reference (read-only): `{proto}`.
""",
    )
    write_md(
        "protocol_compliance.md",
        "Uses Exp 024 candidate protocol sections as binding reference without modification. Operational timestamp: H1_START_00. Native publisher 24-slot SLP grid.",
    )
    write_md("slp_integrity_report.md", f"Category SLP audit: ```json\n{json.dumps(slp_audit, indent=2)}\n```")
    write_md("feature_integrity_report.md", f"```json\n{json.dumps(feat, indent=2)}\n```")
    write_md(
        "evaluation_methodology.md",
        "Primary MAE (kWh/h); Wilcoxon on per-household paired MAE; bootstrap B=5000 seed=24; DEC-022 competency 1.05× persistence.",
    )
    write_md(
        "model_configuration.md",
        "SVR RBF C=10 epsilon=0.1 gamma=scale; StandardScaler; lags 1,24,168; train origins capped at 4000.",
    )
    write_md(
        "robustness_analysis.md",
        f"Exclude HH18 cohort stats in summary JSON. Eligibility per HH: {elig} (Exp027 median ref {elig027}).",
    )
    write_md(
        "decision_register.md",
        "- DEC-030-A: Rebuild matrix via RAM+np.save (open_memmap scalar write unsafe on this host).\n"
        "- DEC-030-B: Exp028 F1 claims superseded by 030 when gates pass.\n",
    )


def update_docs(summary: dict) -> None:
    for path, marker, block in [
        (ROOT / "research_log.md", "Experiment 030", f"\n\n## Experiment 030 — Clean Norwegian forecasting\n\nDate: {TODAY}. `scripts/run_experiment_030.py`. Corrected f64 matrix; P2 exploratory track. See `results/forecasting/experiment_030/`.\n"),
        (ROOT / "README.md", "Experiment 030", f"\n\n## Experiment 030 ({TODAY})\n\nCorrected Norwegian SVR±SLP after Exp 029 audit.\n"),
    ]:
        if path.exists() and marker not in path.read_text(encoding="utf-8"):
            path.write_text(path.read_text(encoding="utf-8").rstrip() + block, encoding="utf-8")
    ps = ROOT / "project_status.md"
    if ps.exists() and "Experiment 030" not in ps.read_text():
        ps.write_text(ps.read_text().rstrip() + f"\n### {TODAY} — Experiment 030\n\nCorrected residential forecasting complete.\n", encoding="utf-8")


def sync_new_submit() -> None:
    import shutil

    ns = ROOT / "new_submit"
    ns.mkdir(exist_ok=True)
    pairs = [
        (OUT / "experiment_030_summary.json", "86_exp030_summary.json"),
        (OUT / "results_summary.md", "87_exp030_report.md"),
        (OUT / "reconstruction_validation.md", "88_exp030_reconstruction.md"),
        (OUT / "corruption_comparison.md", "88b_exp030_corruption.md"),
        (PROC030 / "reconstruction_manifest.json", "89_exp030_manifest.json"),
        (OUT / "decision_register.md", "89b_exp030_decisions.md"),
        (FIG / "exp030_category_slp_heatmap.png", "90_exp030_slp_heatmap.png"),
        (FIG / "exp030_val_mae_comparison.png", "91_exp030_val_mae.png"),
        (FIG / "exp030_test_mae_comparison.png", "92_exp030_test_mae.png"),
        (FIG / "exp030_hh18_corruption.png", "93_exp030_hh18_corruption.png"),
        (FIG / "exp030_f1_improvement_hist.png", "94_exp030_f1_improve_hist.png"),
        (FIG / "exp030_competency_gate.png", "95_exp030_competency.png"),
        (OUT / "category_slp_train_mean_clean.npy", "96_exp030_clean_category_slp.npy"),
    ]
    for src, name in pairs:
        if src.exists():
            shutil.copy2(src, ns / name)
    idx = ns / "00_NEW_SUBMIT_INDEX.md"
    block = (
        "\n\n## Experiment 030 (corrected forecasting)\n\n"
        "See `86_*` … `96_*` files. Replaces no prior experiment; Exp028/029 preserved.\n"
    )
    if idx.exists() and "Experiment 030" not in idx.read_text(encoding="utf-8"):
        idx.write_text(idx.read_text(encoding="utf-8").rstrip() + block, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconstruct-only", action="store_true")
    parser.add_argument("--force-reconstruct", action="store_true")
    parser.add_argument("--skip-forecast", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--jobs", type=int, default=DEFAULT_JOBS, help=f"Parallel households (default {DEFAULT_JOBS})")
    args = parser.parse_args()
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    PROC030.mkdir(parents=True, exist_ok=True)

    src = verify_source()
    if not src["matches_exp026_manifest"]:
        raise SystemExit("Source hash mismatch — stop")

    hh = pd.read_csv(HOUSEHOLDS)
    ids = sorted(hh.loc[hh["Demand_data"] == "Yes", "ID"].astype(int).tolist())
    cities = hh.set_index("ID").loc[ids, "City"].to_numpy()
    dates, hours, slots = calendar_from_csv()
    dow = pd.to_datetime(dates).dayofweek.to_numpy()
    cal_index = {(str(dates[i]), int(hours[i])): i for i in range(N_ROWS)}

    manifest_path = PROC030 / "reconstruction_manifest.json"
    path = PROC030 / "demand_matrix_f64.npy"
    if args.force_reconstruct or not reconstruction_valid(path, manifest_path, len(ids)):
        print("Reconstructing f64 matrix...", flush=True)
        path = reconstruct_matrix(ids, cal_index)
    Y = np.load(path, mmap_mode="r")

    corrupt_rows = [0, 3, 7, 8, 9, 11, 13, 18]
    valid = validate_matrix(path, ids, cal_index, corrupt_rows)
    if args.reconstruct_only:
        print(json.dumps(valid, indent=2))
        return 0

    print("Preparing SLP indices...", flush=True)
    slot_idx = build_slot_index(slots)
    cat_csum = prepare_category_slp(Y, slot_idx, len(ids))
    feat = feature_integrity_tests(Y, ids, hours, dow, slots, slot_idx, cat_csum)

    n_train_elig, n_val_elig, _ = splits(N_ROWS)
    elig = len(eligible_origins(N_ROWS, n_train_elig, n_val_elig))
    elig027 = json.loads(EXP027.read_text())["p2_population"]["median_p2_per_household"] if EXP027.exists() else None

    if args.skip_forecast and (OUT / "per_household_metrics.csv").exists():
        met = pd.read_csv(OUT / "per_household_metrics.csv")
    elif not args.skip_forecast:
        print("Forecasting...", flush=True)
        met = train_cohort(
            Y, ids, cities, hours, dow, slots, slot_idx, cat_csum, resume=args.resume, n_jobs=max(1, args.jobs)
        )
    else:
        raise SystemExit("No metrics and --skip-forecast")

    stats_d = aggregate_stats(met)
    slp_audit = slp_audit_artifacts(Y, slots, ids)
    make_figures(Y, slots, ids, met, stats_d, valid)

    write_md("source_verification.md", f"Source MD5/SHA256 verified: {src}")
    write_md("reconstruction_report.md", f"Clean matrix at `{path}`.")
    write_md("reconstruction_validation.md", f"```\n{json.dumps(valid, indent=2)}\n```")
    write_md(
        "corruption_comparison.md",
        f"HH18 old f32 vs new f64: {json.dumps(valid.get('hh18_corruption_comparison', []), indent=2)}",
    )
    pv, v0, v1, v2 = (
        stats_d["persistence_val"],
        stats_d["val"]["F0"],
        stats_d["val"]["F1"],
        stats_d["val"]["F2"],
    )
    d_f1 = stats_d["F1_minus_F0_mean"]
    p_f1 = stats_d["F1_minus_F0_wilcoxon_p"]
    pass_f0 = 100 * stats_d["F0_competency_pass_rate"]
    write_md(
        "results_summary.md",
        (
            "# Results summary (corrected)\n\n"
            f"- Val macro MAE: persistence {pv:.4f}, F0 {v0:.4f}, F1 {v1:.4f}, F2 {v2:.4f}\n"
            f"- F1−F0 mean Δ {d_f1:.4f}; Wilcoxon p {p_f1:.4g}\n"
            f"- F0 competency pass {pass_f0:.1f}%\n"
            "- Not Ireland–Spain dual-category completion.\n"
        ),
    )
    write_md(
        "limitations.md",
        "Hour 1 clock unresolved; native slots; t_available idealized; train cap 4000 origins; C=10 fixed. "
        f"SLP via searchsorted; parallel jobs={DEFAULT_JOBS}.",
    )
    write_md("README.md", "# Experiment 030 — corrected Norwegian forecasting\n\n`python3 scripts/run_experiment_030.py`")
    write_extended_deliverables(src, valid, stats_d, feat, elig, elig027, slp_audit)

    excl = met[~met.ID.isin([18])]
    stats_excl = aggregate_stats(excl)

    summary = {
        "experiment": "030",
        "classification": "CORRECTED_NORWEGIAN_RESIDENTIAL",
        "date": TODAY,
        "source_verified": src["matches_exp026_manifest"],
        "reconstruction_gate": valid["gate_pass"],
        "feature_integrity": feat["pass"],
        "n_households": len(ids),
        "p2_eligible_origins_per_hh": elig,
        "p2_reference_027_median": elig027,
        "forecasting": stats_d,
        "robustness_exclude_hh18": stats_excl,
        "exp028_interpretation": "028 F1 superiority claim invalid; 030 is authoritative for corrected SLP",
        "elapsed_sec": time.perf_counter() - t0,
    }
    (OUT / "experiment_030_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "aggregate_metrics.json").write_text(json.dumps(stats_d, indent=2), encoding="utf-8")
    update_docs(summary)
    sync_new_submit()
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
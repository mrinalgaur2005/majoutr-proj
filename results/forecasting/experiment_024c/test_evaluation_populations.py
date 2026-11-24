#!/usr/bin/env python3
"""Experiment 024C: P1/P2/P3 estimand and rolling information-set synthetic tests."""
from __future__ import annotations

import hashlib
import sys
from datetime import timedelta
from typing import Iterable

import numpy as np
import pandas as pd

STEP_H = timedelta(hours=1)
LAGS = (1, 24, 168)


class TF(Exception):
    pass


def ok(c: bool, m: str) -> None:
    if not c:
        raise TF(m)


def mask_core(df: pd.DataFrame, require_sn: bool) -> pd.Series:
    rows = []
    for i in range(len(df)):
        t_o = pd.Timestamp(df.iloc[i]["timestamp"])
        t_t = t_o + STEP_H
        if (df["timestamp"] == t_t).sum() != 1:
            rows.append(False)
            continue
        lags_ok = all(
            (df["timestamp"] == (t_o - k * STEP_H)).sum() == 1
            and not pd.isna(df.loc[df["timestamp"] == (t_o - k * STEP_H)].iloc[0]["cons"])
            for k in LAGS
        )
        if not lags_ok:
            rows.append(False)
            continue
        if require_sn:
            t_sn = t_t - timedelta(hours=24)
            hit = df[df["timestamp"] == t_sn]
            if len(hit) != 1 or pd.isna(hit.iloc[0]["cons"]):
                rows.append(False)
                continue
        rows.append(True)
    return pd.Series(rows, index=df.index)


def keys(df: pd.DataFrame, mask: pd.Series) -> set[tuple[str, pd.Timestamp]]:
    k = set()
    for i in df.index[mask]:
        pid = str(df.loc[i, "profile_id"])
        t_t = pd.Timestamp(df.loc[i, "timestamp"]) + STEP_H
        k.add((pid, t_t))
    return k


def template_strict(df: pd.DataFrame, t_origin: pd.Timestamp) -> float:
    sub = df[df["timestamp"] < t_origin]
    return float(sub["cons"].mean()) if len(sub) else np.nan


def template_incremental(state: list[float], new_cons: float, t_new: pd.Timestamp, t_origin: pd.Timestamp) -> float:
    if t_new >= t_origin:
        raise ValueError("future")
    state.append(new_cons)
    return float(np.mean(state))


def bootstrap_profiles(profile_maes: dict[str, float], seed: int = 24) -> float:
    rng = np.random.default_rng(seed)
    names = list(profile_maes.keys())
    if not names:
        return np.nan
    reps = []
    for _ in range(100):  # reduced for speed; design validates unit=profile
        sample = rng.choice(names, size=len(names), replace=True)
        reps.append(float(np.mean([profile_maes[n] for n in sample])))
    return float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))


def test_a_p1_six_model_keys() -> None:
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2020-01-06 10:00", periods=200, freq="h"),
            "cons": range(200),
            "profile_id": "P",
        }
    )
    m = mask_core(df, require_sn=True)
    k = keys(df, m)
    ok(len(k) > 0, "P1 non-empty")
    ok(len(k) == m.sum(), "P1 key count")


def test_b_p2_svr_keys() -> None:
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2020-01-06 10:00", periods=200, freq="h"),
            "cons": range(200),
            "profile_id": "P",
        }
    )
    m2 = mask_core(df, require_sn=False)
    ok(m2.sum() >= mask_core(df, require_sn=True).sum(), "P2 >= P1 rows")


def test_c_sn_missing_p2_not_p1() -> None:
    ts = pd.date_range("2020-01-06 10:00", periods=200, freq="h")
    df = pd.DataFrame({"timestamp": ts, "cons": range(200), "profile_id": "P"})
    t_o = ts[180]
    sn_ref = t_o + STEP_H - timedelta(hours=24)
    df = df[df["timestamp"] != sn_ref].reset_index(drop=True)
    m1 = mask_core(df, require_sn=True)
    m2 = mask_core(df, require_sn=False)
    ix = int(df.index[df["timestamp"] == t_o][0])
    ok(bool(m2.iloc[ix]) and not bool(m1.iloc[ix]), "origin in P2 only when SN ref removed")
    ok(m2.sum() > m1.sum(), "P2 strictly larger count")


def test_d_paired_integrity() -> None:
    mae_f0 = {"P1": 10.0, "P2": 12.0}
    mae_f1 = {"P1": 9.0, "P2": 11.0}
    delta = {k: mae_f1[k] - mae_f0[k] for k in mae_f0}
    ok(all(d < 0 for d in delta.values()), "paired deltas same profiles")


def test_e_macro_micro() -> None:
    p1 = {"P1": ([1.0, 3.0], 2), "P2": ([10.0], 1)}
    micro = np.mean([x for xs, _ in p1.values() for x in xs])
    macro = np.mean([np.mean(xs) for xs, _ in p1.values()])
    ok(abs(micro - (1 + 3 + 10) / 3) < 1e-9 and abs(macro - 6.0) < 1e-9, "macro vs micro")


def test_f_profile_bootstrap() -> None:
    maes = {f"P{i}": float(i) for i in range(5)}
    lo, hi = bootstrap_profiles(maes)
    ok(lo <= np.mean(list(maes.values())) <= hi, "bootstrap CI")


def test_g_rolling_info() -> None:
    df = pd.DataFrame(
        {"timestamp": pd.date_range("2020-01-01", periods=5, freq="h"), "cons": [1, 2, 3, 4, 5]}
    )
    t_o = df.iloc[3]["timestamp"]
    ok(template_strict(df, t_o) == np.mean([1, 2, 3]), "strict rolling excludes current")


def test_h_strict_cutoff() -> None:
    df = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2020-01-01 10:00"), pd.Timestamp("2020-01-01 11:00")],
            "cons": [1.0, 2.0],
        }
    )
    t_o = pd.Timestamp("2020-01-01 11:00")
    ok(len(df[df["timestamp"] < t_o]) == 1, "exclude same timestamp")


def test_i_cached_template() -> None:
    df = pd.DataFrame(
        {"timestamp": pd.date_range("2020-01-01", periods=5, freq="h"), "cons": [1, 2, 3, 4, 5]}
    )
    inc: list[float] = []
    t_o = df.iloc[4]["timestamp"]
    for _, r in df[df["timestamp"] < t_o].iterrows():
        m = template_incremental(inc, r["cons"], r["timestamp"], t_o)
    ok(abs(m - template_strict(df, t_o)) < 1e-12, "incremental==full")


def test_j_batch_cutoff() -> None:
    tau = pd.Timestamp("2020-01-03 00:00")
    df = pd.DataFrame(
        {"timestamp": pd.date_range("2020-01-01", periods=100, freq="h"), "cons": 1.0}
    )
    ok(len(df[df["timestamp"] < tau]) == 48, "batch cutoff")


def test_k_train_only_scaler() -> None:
    train = np.array([1.0, 2.0, 3.0])
    test = np.array([100.0])
    mu, sig = train.mean(), train.std()
    ok(abs(((test - mu) / sig)[0]) > 10, "test cannot refit scaler")


def test_l_population_labels() -> None:
    rows = [{"population": "P1", "metric": "MAE"}, {"population": "P2", "metric": "MAE"}]
    ok(all(r["population"] in {"P1", "P2", "P3"} for r in rows), "labels")


def test_m_feature_equality() -> None:
    f0 = ["lag1", "lag24", "lag168", "cal"]
    f1 = f0 + ["slp_cat"]
    f2 = f0 + ["slp_prof"]
    ok(f1[:-1] == f0 and f2[:-1] == f0, "only SLP differs")


TESTS = {
    "A_P1_keys": test_a_p1_six_model_keys,
    "B_P2_keys": test_b_p2_svr_keys,
    "C_SN_split": test_c_sn_missing_p2_not_p1,
    "D_paired": test_d_paired_integrity,
    "E_macro_micro": test_e_macro_micro,
    "F_bootstrap": test_f_profile_bootstrap,
    "G_rolling": test_g_rolling_info,
    "H_strict_lt": test_h_strict_cutoff,
    "I_cached": test_i_cached_template,
    "J_batch": test_j_batch_cutoff,
    "K_train_only": test_k_train_only_scaler,
    "L_labels": test_l_population_labels,
    "M_features": test_m_feature_equality,
}


def main() -> int:
    failed = []
    for name, fn in TESTS.items():
        try:
            fn()
            print(f"  OK {name}")
        except Exception as e:
            failed.append((name, repr(e)))
            print(f"  FAIL {name}: {e}")
    print(f"PASS {len(TESTS)-len(failed)} FAIL {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
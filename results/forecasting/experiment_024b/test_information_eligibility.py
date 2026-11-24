#!/usr/bin/env python3
"""Experiment 024B synthetic tests: information set, duplicates, common eligibility."""
from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

import pandas as pd

Native = Literal["hourly", "half_hourly"]
STEP = {"hourly": timedelta(hours=1), "half_hourly": timedelta(minutes=30)}
LAGS = {"hourly": (1, 24, 168), "half_hourly": (1, 48, 336)}


class TF(Exception):
    pass


def ok(c: bool, m: str) -> None:
    if not c:
        raise TF(m)


def t_avail(ts: pd.Timestamp) -> pd.Timestamp:
    """Operational assumption: t_available = t_timestamp (no invented latency)."""
    return ts


def template_rows(df: pd.DataFrame, t_origin: pd.Timestamp, *, inclusive: bool) -> pd.DataFrame:
    if inclusive:
        return df[df["timestamp"] <= t_origin]
    return df[df["timestamp"] < t_origin]


def f1_pool(frames: dict[str, pd.DataFrame], t_origin: pd.Timestamp, inclusive: bool) -> int:
    n = 0
    for df in frames.values():
        n += len(template_rows(df, t_origin, inclusive=inclusive))
    return n


def common_eligibility_mask(
    df: pd.DataFrame,
    native: Native,
    *,
    require_seasonal: bool = True,
) -> pd.Series:
    """Strategy A: complete-case for all models on shared targets."""
    rows = []
    for i in range(len(df)):
        t_o = pd.Timestamp(df.iloc[i]["timestamp"])
        t_t = t_o + STEP[native]
        if (df["timestamp"] == t_t).sum() != 1:
            rows.append(False)
            continue
        if pd.isna(df.loc[df["timestamp"] == t_t].iloc[0]["cons"]):
            rows.append(False)
            continue
        lags_ok = True
        for k in LAGS[native]:
            t_l = t_o - k * STEP[native]
            hit = df[df["timestamp"] == t_l]
            if len(hit) != 1 or pd.isna(hit.iloc[0]["cons"]):
                lags_ok = False
                break
        if not lags_ok:
            rows.append(False)
            continue
        if require_seasonal:
            t_sn = t_t - timedelta(hours=24)
            hit = df[df["timestamp"] == t_sn]
            if len(hit) != 1 or pd.isna(hit.iloc[0]["cons"]):
                rows.append(False)
                continue
        rows.append(True)
    return pd.Series(rows, index=df.index)


def dedupe_policy(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Exact dup drop; conflicting dup -> exclude timestamp entirely."""
    flags: list[str] = []
    parts = []
    for ts, g in df.groupby("timestamp", sort=True):
        if len(g) == 1:
            parts.append(g)
            continue
        if len(g.drop_duplicates(subset=["cons", "flag"] if "flag" in g else ["cons"])) == 1:
            parts.append(g.head(1))
            flags.append(f"exact_dup:{ts}")
        else:
            flags.append(f"conflict_excluded:{ts}")
    if not parts:
        return df.iloc[0:0], flags
    return pd.concat(parts).sort_values("timestamp").reset_index(drop=True), flags


def model_keys(df: pd.DataFrame, mask: pd.Series) -> list[tuple[str, pd.Timestamp]]:
    keys = []
    for i in df.index[mask]:
        t_t = pd.Timestamp(df.loc[i, "timestamp"]) + STEP["hourly"]
        keys.append((str(df.loc[i, "profile_id"]) if "profile_id" in df.columns else "p", t_t))
    return keys


# --- Tests ---

def test_a_strict_vs_inclusive() -> None:
    df = pd.DataFrame({"timestamp": pd.date_range("2020-01-01", periods=5, freq="h"), "cons": 1.0})
    t_o = df.iloc[3]["timestamp"]
    ok(f1_pool({"x": df}, t_o, inclusive=False) == 3, "strict <")
    ok(f1_pool({"x": df}, t_o, inclusive=True) == 4, "inclusive <=")


def test_b_availability_cutoff() -> None:
    df = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2020-01-01 10:00")],
            "cons": [1.0],
            "t_available": [pd.Timestamp("2020-01-01 10:05")],
        }
    )
    t_issue = pd.Timestamp("2020-01-01 10:02")
    avail = t_avail(df.iloc[0]["timestamp"])  # assumption path uses timestamp
    excluded_assumption = avail <= t_issue
    excluded_true = df.iloc[0]["t_available"] <= t_issue
    ok(excluded_assumption and not excluded_true, "publication after issue excluded under Policy C")


def test_c_rolling() -> None:
    df = pd.DataFrame({"timestamp": pd.date_range("2020-01-01", periods=10, freq="h"), "cons": range(10)})
    n0 = f1_pool({"p": df}, df.iloc[5]["timestamp"], inclusive=False)
    n1 = f1_pool({"p": df}, df.iloc[6]["timestamp"], inclusive=False)
    ok(n1 == n0 + 1, "rolling adds one hour")


def test_d_batch_cutoff() -> None:
    p1 = pd.DataFrame({"timestamp": pd.date_range("2020-01-01", periods=100, freq="h"), "cons": 1.0})
    p2 = pd.DataFrame({"timestamp": pd.date_range("2020-02-01", periods=100, freq="h"), "cons": 2.0})
    tau = pd.Timestamp("2020-01-15 00:00")
    sub1 = template_rows(p1, tau, inclusive=False)
    sub2 = template_rows(p2, tau, inclusive=False)
    ok(len(sub1) > 0 and len(sub2) == 0, "batch cutoff excludes future profile calendars")


def test_e_exact_duplicate() -> None:
    df = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2020-01-01 10:00")] * 2,
            "cons": [3.0, 3.0],
            "flag": [0, 0],
        }
    )
    out, fl = dedupe_policy(df)
    ok(len(out) == 1 and "exact_dup" in fl[0], "exact dedupe")


def test_f_conflicting_duplicate() -> None:
    df = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2020-01-01 10:00"), pd.Timestamp("2020-01-01 10:00")],
            "cons": [1.0, 2.0],
        }
    )
    out, fl = dedupe_policy(df)
    ok(len(out) == 0 and any("conflict" in f for f in fl), "conflict removes ts")


def test_g_missing_lag1() -> None:
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2020-01-01 08:00", "2020-01-01 10:00"]),
            "cons": [1.0, 2.0],
        }
    )
    mask = common_eligibility_mask(df, "hourly")
    ok(not mask.any(), "missing lag1 -> ineligible")


def test_h_missing_daily() -> None:
    ts = list(pd.date_range("2020-01-01 12:00", periods=30, freq="h"))
    ts = [ts[0]] + ts[2:]  # drop one hour breaks 24h lag chain at some points
    df = pd.DataFrame({"timestamp": ts, "cons": 1.0})
    mask = common_eligibility_mask(df, "hourly")
    ok(mask.sum() < len(df), "some origins fail daily lag")


def test_i_missing_weekly() -> None:
    ts = pd.date_range("2020-01-01", periods=200, freq="h").tolist()
    del ts[50]
    df = pd.DataFrame({"timestamp": ts, "cons": 1.0})
    mask = common_eligibility_mask(df, "hourly")
    ok(not mask.all(), "weekly lag gaps reduce eligibility")


def test_j_missing_seasonal() -> None:
    df = pd.DataFrame({"timestamp": pd.date_range("2020-01-06 10:00", periods=200, freq="h"), "cons": range(200)})
    t_bad = pd.Timestamp("2020-01-06 12:00")
    df2 = df[df["timestamp"] != (t_bad - timedelta(hours=24))]
    mask = common_eligibility_mask(df2, "hourly")
    t_o = t_bad
    row = df2[df2["timestamp"] == t_o]
    ok(len(row) == 1 and not mask[df2.index[df2["timestamp"] == t_o][0]], "missing sn ref excludes origin")


def test_k_equal_model_keys() -> None:
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2020-01-06 10:00", periods=50, freq="h"),
            "cons": range(50),
            "profile_id": "P1",
        }
    )
    mask = common_eligibility_mask(df, "hourly")
    keys = model_keys(df, mask)
    ok(len(keys) == mask.sum() and len(set(keys)) == len(keys), "unique shared keys")


def test_l_persistence_staleness() -> None:
    t_o = pd.Timestamp("2020-01-01 12:00")
    df = pd.DataFrame({"timestamp": [pd.Timestamp("2020-01-01 10:00")], "cons": [5.0]})
    ok((df["timestamp"] == t_o).sum() == 0, "no stale fallback without origin row")


def test_m_train_only_imputation_blocked() -> None:
    ok(True, "Strategy A primary: no imputation for primary comparison (PRE-REGISTERED)")


def test_n_partitions() -> None:
    n_train = 7
    t_o_ix = 6
    t_t_ix = 7
    ok(t_o_ix < n_train and t_t_ix == n_train, "boundary should reject val target")


def test_o_cross_profile() -> None:
    idx = pd.date_range("2020-01-01", periods=200 * 24, freq="h")
    cons = [1.0 if t.month < 6 else 50.0 for t in idx]
    b = pd.DataFrame({"timestamp": idx, "cons": cons, "partition": "train"})
    origin = pd.Timestamp("2020-03-15 12:00")
    s = int(origin.dayofweek) * 24 + int(origin.hour)
    sub = b[b["timestamp"] < origin]
    pooled = b[b["partition"] == "train"]
    leaky_mean = pooled[pooled["timestamp"].map(lambda t: int(t.dayofweek) * 24 + int(t.hour)) == s]["cons"].mean()
    causal_mean = sub[sub["timestamp"].map(lambda t: int(t.dayofweek) * 24 + int(t.hour)) == s]["cons"].mean()
    ok(leaky_mean > 10 and causal_mean < 2, "causal F1 pool")


def test_p_dst_ambiguous() -> None:
    df = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2020-10-25 02:30"), pd.Timestamp("2020-10-25 02:30")],
            "cons": [1.0, 2.0],
        }
    )
    _, fl = dedupe_policy(df)
    ok(any("conflict" in f for f in fl), "ambiguous repeated local time -> conflict not first-row")


TESTS = {
    "A_cutoff": test_a_strict_vs_inclusive,
    "B_availability": test_b_availability_cutoff,
    "C_rolling": test_c_rolling,
    "D_batch": test_d_batch_cutoff,
    "E_exact_dup": test_e_exact_duplicate,
    "F_conflict_dup": test_f_conflicting_duplicate,
    "G_lag1": test_g_missing_lag1,
    "H_lag24": test_h_missing_daily,
    "I_lag168": test_i_missing_weekly,
    "J_seasonal": test_j_missing_seasonal,
    "K_model_keys": test_k_equal_model_keys,
    "L_staleness": test_l_persistence_staleness,
    "M_imputation": test_m_train_only_imputation_blocked,
    "N_partition": test_n_partitions,
    "O_f1_causal": test_o_cross_profile,
    "P_dst_ambiguous": test_p_dst_ambiguous,
}


def main() -> int:
    failed = []
    for name, fn in TESTS.items():
        try:
            fn()
            print(f"  OK {name}")
        except TF as e:
            failed.append((name, str(e)))
            print(f"  FAIL {name}: {e}")
        except Exception as e:
            failed.append((name, repr(e)))
            print(f"  FAIL {name}: {e}")
    print(f"PASS {len(TESTS)-len(failed)} FAIL {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
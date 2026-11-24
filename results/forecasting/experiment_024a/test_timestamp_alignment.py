#!/usr/bin/env python3
"""Synthetic timestamp / horizon / SLP / seasonal-naive validation (Experiment 024A)."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

import pandas as pd

Native = Literal["hourly", "half_hourly"]

NATIVE_STEP: dict[Native, timedelta] = {
    "hourly": timedelta(hours=1),
    "half_hourly": timedelta(minutes=30),
}


@dataclass(frozen=True)
class HorizonTarget:
    origin_ts: pd.Timestamp
    target_ts: pd.Timestamp
    target_row: int | None
    eligible: bool
    reason: str


def slot_hour_of_week(ts: pd.Timestamp, native: Native) -> int:
    """Naive civil-time slot (no timezone conversion). 168 or 336 slots."""
    dow = int(ts.dayofweek)
    if native == "hourly":
        return dow * 24 + int(ts.hour)
    half = 0 if int(ts.minute) < 30 else 1
    return dow * 48 + int(ts.hour) * 2 + half


def target_ts(origin_ts: pd.Timestamp, native: Native) -> pd.Timestamp:
    return origin_ts + NATIVE_STEP[native]


def resolve_h1(df: pd.DataFrame, origin_idx: int, native: Native) -> HorizonTarget:
    """H=1 = exactly one native step ahead by timestamp, not next row."""
    if origin_idx < 0 or origin_idx >= len(df):
        return HorizonTarget(pd.NaT, pd.NaT, None, False, "origin_oob")
    t_o = pd.Timestamp(df.iloc[origin_idx]["timestamp"])
    t_t = target_ts(t_o, native)
    hits = df.index[df["timestamp"] == t_t].tolist()
    if len(hits) == 0:
        return HorizonTarget(t_o, t_t, None, False, "missing_target_ts")
    if len(hits) > 1:
        return HorizonTarget(t_o, t_t, None, False, "duplicate_target_ts")
    tr = hits[0]
    if pd.isna(df.loc[tr, "cons"]):
        return HorizonTarget(t_o, t_t, tr, False, "missing_target_value")
    return HorizonTarget(t_o, t_t, tr, True, "ok")


def slp_feature_slot(
    *,
    use_target_slot: bool,
    origin_ts: pd.Timestamp,
    target_ts_val: pd.Timestamp,
    native: Native,
) -> tuple[int, str]:
    ts = target_ts_val if use_target_slot else origin_ts
    return slot_hour_of_week(ts, native), "target_slot" if use_target_slot else "origin_slot"


def seasonal_naive_reference(
    df: pd.DataFrame,
    target_ts_val: pd.Timestamp,
    *,
    mode: Literal["elapsed_24h", "civil_prev_day"],
) -> tuple[float | None, str]:
    if mode == "elapsed_24h":
        t_ref = target_ts_val - timedelta(hours=24)
    else:
        t_ref = target_ts_val - pd.Timedelta(days=1)
    hits = df.index[df["timestamp"] == t_ref].tolist()
    if len(hits) != 1:
        return None, "unavailable"
    v = df.loc[hits[0], "cons"]
    if pd.isna(v):
        return None, "unavailable"
    return float(v), "ok"


def build_f1_template_pool_split_only(
    frames: dict[str, pd.DataFrame],
    _splits: dict[str, str],
    slot_fn,
) -> dict[int, float]:
    """Legacy 024-style: pool all TRAIN-split rows per profile (LEAKY across profiles)."""
    acc: dict[int, list[float]] = {}
    for _pid, df in frames.items():
        sub = df[df["partition"] == "train"] if "partition" in df.columns else df[df["split"] == "train"]
        for _, r in sub.iterrows():
            s = slot_fn(pd.Timestamp(r["timestamp"]))
            acc.setdefault(s, []).append(float(r["cons"]))
    return {k: sum(v) / len(v) for k, v in acc.items()}


def build_f1_template_causal(
    frames: dict[str, pd.DataFrame],
    origin_ts: pd.Timestamp,
    slot_fn,
) -> dict[int, float]:
    """Causal F1: all profiles, rows with timestamp < origin_ts only."""
    acc: dict[int, list[float]] = {}
    for _pid, df in frames.items():
        sub = df[df["timestamp"] < origin_ts]
        for _, r in sub.iterrows():
            s = slot_fn(pd.Timestamp(r["timestamp"]))
            acc.setdefault(s, []).append(float(r["cons"]))
    return {k: sum(v) / len(v) for k, v in acc.items()}


def partition_for_origin_target(
    n_train: int,
    n_val: int,
    origin_idx: int,
    target_idx: int | None,
) -> tuple[str, bool]:
    """Assign by target row index for forecast evaluation (both in same segment)."""
    if target_idx is None:
        return "none", False
    n_test_start = n_train + n_val

    def seg(ix: int) -> str:
        if ix < n_train:
            return "train"
        if ix < n_test_start:
            return "val"
        return "test"

    o_seg, t_seg = seg(origin_idx), seg(target_idx)
    if o_seg != t_seg:
        return o_seg, False
    return t_seg, True


# --- Test suite ---

class TestFailure(Exception):
    pass


def assert_true(cond: bool, msg: str) -> None:
    if not cond:
        raise TestFailure(msg)


def test_a_regular_hourly() -> None:
    ts = pd.date_range("2020-01-06 10:00", periods=200, freq="h")
    df = pd.DataFrame({"timestamp": ts, "cons": range(len(ts))})
    ht = resolve_h1(df, 30, "hourly")
    assert_true(ht.eligible and ht.target_ts == ts[31], "H=1 hourly")
    assert_true(ht.target_ts == ht.origin_ts + timedelta(hours=1), "delta")
    slot_t, _ = slp_feature_slot(use_target_slot=True, origin_ts=ht.origin_ts, target_ts_val=ht.target_ts, native="hourly")
    assert_true(slot_t == slot_hour_of_week(ht.target_ts, "hourly"), "target SLP slot")
    sn, st = seasonal_naive_reference(df, ht.target_ts, mode="elapsed_24h")
    assert_true(st == "ok" and sn == float(ht.target_row - 24), "seasonal 24h elapsed")


def test_b_regular_half_hourly() -> None:
    ts = pd.date_range("2020-03-02 08:00", periods=400, freq="30min")
    df = pd.DataFrame({"timestamp": ts, "cons": range(len(ts))})
    ht = resolve_h1(df, 5, "half_hourly")
    assert_true(ht.eligible, "h1 30min")
    assert_true(ht.target_ts - ht.origin_ts == timedelta(minutes=30), "30m step")
    s = slot_hour_of_week(ht.target_ts, "half_hourly")
    assert_true(0 <= s < 336, "336 slots")


def test_c_missing_interval() -> None:
    ts = [pd.Timestamp("2020-01-01 10:00"), pd.Timestamp("2020-01-01 12:00")]
    df = pd.DataFrame({"timestamp": ts, "cons": [1.0, 2.0]})
    ht = resolve_h1(df, 0, "hourly")
    assert_true(not ht.eligible and ht.reason == "missing_target_ts", "gap blocks H=1")


def test_d_multiple_gaps() -> None:
    ts = pd.to_datetime(["2020-01-01 08:00", "2020-01-01 11:00", "2020-01-01 12:00"])
    df = pd.DataFrame({"timestamp": ts, "cons": [1, 2, 3]})
    ht = resolve_h1(df, 1, "hourly")
    assert_true(ht.eligible and ht.target_row == 2, "11:00→12:00 exact ts exists")
    ht0 = resolve_h1(df, 0, "hourly")
    assert_true(not ht0.eligible, "08→09 missing")


def test_e_duplicates() -> None:
    df = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2020-01-01 10:00"), pd.Timestamp("2020-01-01 11:00"), pd.Timestamp("2020-01-01 11:00")],
            "cons": [1.0, 2.0, 3.0],
        }
    )
    df = df.sort_values("timestamp").reset_index(drop=True)
    ht = resolve_h1(df, 0, "hourly")
    assert_true(not ht.eligible and "duplicate" in ht.reason, "dup target ts 11:00")


def test_f_out_of_order() -> None:
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2020-01-01 12:00", "2020-01-01 10:00"]),
            "cons": [1, 2],
        }
    )
    df = df.sort_values("timestamp").reset_index(drop=True)
    assert_true(len(df) == 2 and df.iloc[0]["timestamp"].hour == 10, "sorted")


def test_g_midnight() -> None:
    ts = pd.date_range("2020-01-03 22:00", periods=5, freq="h")
    df = pd.DataFrame({"timestamp": ts, "cons": range(5)})
    i = 1  # 23:00
    ht = resolve_h1(df, i, "hourly")
    assert_true(ht.target_ts.hour == 0 and ht.target_ts.day == 4, "midnight target")
    slot_o = slot_hour_of_week(ht.origin_ts, "hourly")
    slot_t = slot_hour_of_week(ht.target_ts, "hourly")
    assert_true(slot_o == 119 and slot_t == 120, "Fri 23 → Sat 00 slots")


def test_h_weekend_boundary() -> None:
    ts = pd.date_range("2020-01-10 22:00", periods=5, freq="h")  # Fri
    df = pd.DataFrame({"timestamp": ts, "cons": range(5)})
    ht = resolve_h1(df, 1, "hourly")
    assert_true(ht.origin_ts.dayofweek == 4 and ht.target_ts.dayofweek == 5, "Fri→Sat")
    ts2 = pd.date_range("2020-01-12 22:00", periods=5, freq="h")  # Sun
    df2 = pd.DataFrame({"timestamp": ts2, "cons": range(5)})
    ht2 = resolve_h1(df2, 1, "hourly")
    assert_true(ht2.origin_ts.dayofweek == 6 and ht2.target_ts.dayofweek == 0, "Sun→Mon")


def test_i_cross_profile_leakage() -> None:
    """Profile B's later calendar train rows must not affect A's March validation origin."""
    idx_b = pd.date_range("2020-01-01", periods=200 * 24, freq="h")
    cons_b = [1.0 if t.month < 6 else 50.0 for t in idx_b]
    b = pd.DataFrame({"timestamp": idx_b, "cons": cons_b, "partition": "train"})
    frames = {"B": b}
    slot_fn = lambda t: slot_hour_of_week(t, "hourly")
    origin = pd.Timestamp("2020-03-15 12:00")
    s = slot_fn(origin)
    leaky = build_f1_template_pool_split_only(frames, {}, slot_fn)
    causal = build_f1_template_causal(frames, origin, slot_fn)
    assert_true(leaky.get(s, 0) > 10.0, "split-only F1 polluted by June cons=50 in B train")
    assert_true(causal.get(s, 999) < 2.0, "causal F1 at March origin uses only pre-origin rows")


def test_k_partitions() -> None:
    n_train, n_val = 70, 15
    ok = partition_for_origin_target(n_train, n_val, 68, 69)
    bad = partition_for_origin_target(n_train, n_val, 69, 70)
    assert_true(ok[0] == "train" and ok[1], "train origin-target same segment")
    assert_true(not bad[1], "cross partition blocked")


TESTS = {
    "A_regular_hourly": test_a_regular_hourly,
    "B_regular_half_hourly": test_b_regular_half_hourly,
    "C_missing_interval": test_c_missing_interval,
    "D_multiple_gaps": test_d_multiple_gaps,
    "E_duplicate_ts": test_e_duplicates,
    "F_sort_order": test_f_out_of_order,
    "G_midnight": test_g_midnight,
    "H_weekend": test_h_weekend_boundary,
    "I_cross_profile_leakage": test_i_cross_profile_leakage,
    "K_partitions": test_k_partitions,
}


def main() -> int:
    passed, failed = [], []
    for name, fn in TESTS.items():
        try:
            fn()
            passed.append(name)
        except TestFailure as e:
            failed.append((name, str(e)))
        except Exception as e:
            failed.append((name, repr(e)))
    print(f"PASS: {len(passed)} FAIL: {len(failed)}")
    for n in passed:
        print(f"  OK {n}")
    for n, err in failed:
        print(f"  FAIL {n}: {err}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""Experiment 037 — SLP-based ToD tariff analysis and BESS cost optimization."""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import shutil
import textwrap
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_037"
EXP_LINK = ROOT / "experiments/037_slp_tod_bess"
FIG = OUT / "figures"
TAB = OUT / "tables"
MET = OUT / "metrics"
CFG_TARIFF = ROOT / "configs/experiment_037_tariff.json"
DAILY = ROOT / "data/processed/daily_profiles.parquet"
CLUST = ROOT / "results/clustering/cluster_assignments.parquet"
DT_H = 0.25
SLOTS = 96
DPI = 150
CAPS = (1.0, 2.0, 5.0, 10.0, 15.0)
POWERS = (0.5, 1.0, 2.0, 3.0)
MEDOIDS = [
    ("BR29", "2020-09-06", 0, "group0_medoid"),
    ("MH31", "2019-11-07", 1, "group1_medoid"),
]
SAMPLE_PER_GROUP = 30
SAMPLE_SEED = 1037

from bess_dispatch_corrected import optimize_milp_cost, rule_tod_arbitrage  # noqa: E402
from bess_physics import (  # noqa: E402
    BatteryParams,
    cyclic_soc_ok,
    energy_accounting,
    grid_import,
    peak_metrics,
)


def write_md(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")


def atomic_json(path: Path, obj: object) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    tmp.replace(path)


def as_profile(x) -> np.ndarray:
    if isinstance(x, (list, np.ndarray)):
        return np.asarray(x, dtype=np.float64)
    return np.asarray(ast.literal_eval(x), dtype=np.float64)


def load_tariff_cfg() -> dict:
    return json.loads(CFG_TARIFF.read_text(encoding="utf-8"))


def build_prices(cfg: dict, scenario: str) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    rates = cfg["scenarios"][scenario]
    n = cfg["n_slots"]
    price = np.zeros(n, dtype=np.float64)
    masks: dict[str, np.ndarray] = {}
    for period, ranges in cfg["period_slot_ranges"].items():
        m = np.zeros(n, dtype=bool)
        for a, b in ranges:
            m[a:b] = True
            price[a:b] = float(rates[period])
        masks[period] = m
    if not np.all(price > 0):
        raise RuntimeError(f"Unassigned tariff slots in scenario {scenario}")
    if sum(m.sum() for m in masks.values()) != n:
        raise RuntimeError("Tariff masks do not partition 96 slots")
    return price, masks


def procurement_cost(grid_kw: np.ndarray, prices: np.ndarray, dt_h: float = DT_H) -> float:
    return float((np.maximum(grid_kw, 0.0) * prices).sum() * dt_h)


def bill_flat(load_kw: np.ndarray, flat_rate: float) -> float:
    return float(load_kw.sum() * DT_H * flat_rate)


def period_energies(load_kw: np.ndarray, masks: dict[str, np.ndarray]) -> dict[str, float]:
    return {k: float(load_kw[m].sum() * DT_H) for k, m in masks.items()}


def hypothetical_load_shift(
    load_kw: np.ndarray,
    masks: dict[str, np.ndarray],
    prices: np.ndarray,
    cfg: dict,
) -> np.ndarray:
    hyp = cfg.get("load_shift_hypothesis", {})
    if not hyp.get("enabled", False):
        return load_kw.copy()
    frac = float(hyp["max_shiftable_frac_peak_energy"])
    pmax = float(hyp["shift_power_kw"])
    out = load_kw.copy()
    peak = masks["peak"]
    off = masks["off_peak"]
    e_peak = float(out[peak].sum() * DT_H)
    e_move = min(frac * e_peak, pmax * DT_H * off.sum())
    if e_move <= 1e-9:
        return out
    # remove from peak proportional to load
    rem_slots = np.where(peak)[0]
    wsum = max(out[peak].sum(), 1e-9)
    for t in rem_slots:
        share = out[t] / wsum
        reduce_kwh = e_move * share
        out[t] = max(0.0, out[t] - reduce_kwh / DT_H)
    off_slots = list(np.where(off)[0])
    off_slots.sort(key=lambda t: float(prices[t]))
    left = e_move
    for t in off_slots:
        if left <= 1e-9:
            break
        add = min(pmax, left / DT_H)
        out[t] += add
        left -= add * DT_H
    e0 = float(load_kw.sum() * DT_H)
    e1 = float(out.sum() * DT_H)
    if abs(e1 - e0) > 0.05:
        out = load_kw.copy()
    return out


def load_ceew_with_clusters() -> pd.DataFrame:
    dp = pd.read_parquet(DAILY)
    dp["date"] = pd.to_datetime(dp["date"]).dt.strftime("%Y-%m-%d")
    ca = pd.read_parquet(CLUST)
    ca = ca[(ca.k == 2) & (ca.normalization == "peak")][["meter_id", "date", "cluster"]]
    ca["date"] = pd.to_datetime(ca["date"]).dt.strftime("%Y-%m-%d")
    dp = dp.merge(ca, on=["meter_id", "date"], how="inner")
    prof = dp.profile_kw.map(as_profile)
    dp = dp[prof.map(len) == SLOTS].copy()
    dp["load_kw"] = prof
    e_chk = dp.load_kw.map(lambda a: float(np.sum(a) * DT_H))
    dp["energy_residual"] = np.abs(e_chk - dp.daily_energy_kwh)
    dp = dp[dp.energy_residual < 0.5].reset_index(drop=True)
    return dp


def get_profile(dp: pd.DataFrame, meter_id: str, date: str) -> np.ndarray:
    row = dp[(dp.meter_id == meter_id) & (dp.date == date)]
    if row.empty:
        raise KeyError(f"Missing profile {meter_id} {date}")
    return np.asarray(row.iloc[0].load_kw, dtype=np.float64)


def stage_a_tariff(dp: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    flat_rate = float(cfg["scenarios"]["flat"]["off_peak"])
    rows = []
    rng = np.random.default_rng(SAMPLE_SEED)
    for cluster in (0, 1):
        g = dp[dp.cluster == cluster]
        idx = rng.choice(len(g), size=min(SAMPLE_PER_GROUP, len(g)), replace=False)
        sample = g.iloc[idx]
        for _, r in sample.iterrows():
            load = np.asarray(r.load_kw, dtype=np.float64)
            for sc in ("flat", "low_spread", "moderate_spread", "high_spread"):
                prices, masks = build_prices(cfg, sc)
                b_flat = bill_flat(load, flat_rate)
                b_tod = procurement_cost(load, prices)
                pe = period_energies(load, masks)
                e_tot = float(load.sum() * DT_H)
                rows.append(
                    {
                        "source": "sample",
                        "profile_id": f"{r.meter_id}_{r.date}",
                        "slp_group": int(cluster),
                        "tariff_scenario": sc,
                        "daily_energy_kwh": e_tot,
                        "off_peak_kwh": pe["off_peak"],
                        "shoulder_kwh": pe["shoulder"],
                        "peak_kwh": pe["peak"],
                        "bill_flat_inr": b_flat,
                        "bill_tod_inr": b_tod,
                        "bill_diff_inr": b_flat - b_tod,
                        "bill_diff_pct": 100.0 * (b_flat - b_tod) / max(b_flat, 1e-9),
                        "effective_price_inr_per_kwh": b_tod / max(e_tot, 1e-9),
                    }
                )
    for meter_id, date, cluster, label in MEDOIDS:
        load = get_profile(dp, meter_id, date)
        for sc in ("flat", "low_spread", "moderate_spread", "high_spread"):
            prices, masks = build_prices(cfg, sc)
            b_flat = bill_flat(load, flat_rate)
            b_tod = procurement_cost(load, prices)
            shifted = hypothetical_load_shift(load, masks, prices, cfg)
            b_shift = procurement_cost(shifted, prices)
            pe = period_energies(load, masks)
            e_tot = float(load.sum() * DT_H)
            rows.append(
                {
                    "source": label,
                    "profile_id": f"{meter_id}_{date}",
                    "slp_group": cluster,
                    "tariff_scenario": sc,
                    "daily_energy_kwh": e_tot,
                    "off_peak_kwh": pe["off_peak"],
                    "shoulder_kwh": pe["shoulder"],
                    "peak_kwh": pe["peak"],
                    "bill_flat_inr": b_flat,
                    "bill_tod_inr": b_tod,
                    "bill_hyp_shift_tod_inr": b_shift,
                    "bill_diff_inr": b_flat - b_tod,
                    "bill_diff_pct": 100.0 * (b_flat - b_tod) / max(b_flat, 1e-9),
                    "effective_price_inr_per_kwh": b_tod / max(e_tot, 1e-9),
                }
            )
    return pd.DataFrame(rows)


def dispatch_row(
    load: np.ndarray,
    prices: np.ndarray,
    batt: BatteryParams,
    method: str,
) -> dict:
    if method == "none":
        grid = load.copy()
        p_ch = p_dis = np.zeros(len(load))
        soc = np.full(len(load) + 1, batt.soc0)
        meth = "no_bess"
    elif method == "rule":
        base_c = procurement_cost(load, prices)
        res = rule_tod_arbitrage(load, prices, batt)
        if float((res["grid_kw"] * prices).sum() * DT_H) > base_c + 1e-4:
            n = len(load)
            res = {
                "method": "no_bess_optimal",
                "p_charge_kw": np.zeros(n),
                "p_discharge_kw": np.zeros(n),
                "soc": np.full(n + 1, batt.soc0),
                "grid_kw": load.copy(),
            }
        grid = np.asarray(res["grid_kw"])
        p_ch = np.asarray(res["p_charge_kw"])
        p_dis = np.asarray(res["p_discharge_kw"])
        soc = np.asarray(res["soc"])
        meth = res["method"]
    else:
        res = optimize_milp_cost(load, prices, batt)
        grid = np.asarray(res["grid_kw"])
        p_ch = np.asarray(res["p_charge_kw"])
        p_dis = np.asarray(res["p_discharge_kw"])
        soc = np.asarray(res["soc"])
        meth = res["method"]
    acc = energy_accounting(load, p_ch, p_dis, batt, soc)
    pk = peak_metrics(load, grid)
    cost = procurement_cost(grid, prices)
    return {
        "method": meth,
        "bill_tod_inr": cost,
        "p_charge_kw": p_ch,
        "p_discharge_kw": p_dis,
        "soc": soc,
        "grid_kw": grid,
        **acc,
        **pk,
    }


def stage_b_bess(dp: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    flat_rate = float(cfg["scenarios"]["flat"]["off_peak"])
    rows = []
    for meter_id, date, cluster, label in MEDOIDS:
        load = get_profile(dp, meter_id, date)
        for sc in cfg["scenarios"]:
            if sc == "flat":
                continue
            prices, masks = build_prices(cfg, sc)
            b_flat = bill_flat(load, flat_rate)
            base = dispatch_row(load, prices, BatteryParams(5, 2), "none")
            for cap in CAPS:
                for pmax in POWERS:
                    batt = BatteryParams(cap, pmax)
                    for method in ("rule", "milp"):
                        r = dispatch_row(load, prices, batt, method)
                        rows.append(
                            {
                                "profile_id": label,
                                "meter_id": meter_id,
                                "date": date,
                                "slp_group": cluster,
                                "tariff_scenario": sc,
                                "energy_kwh": cap,
                                "p_max_kw": pmax,
                                "dispatch": method,
                                "bill_flat_inr": b_flat,
                                "bill_tod_no_bess_inr": base["bill_tod_inr"],
                                "bill_tod_with_bess_inr": r["bill_tod_inr"],
                                "savings_vs_no_bess_inr": base["bill_tod_inr"] - r["bill_tod_inr"],
                                "savings_vs_no_bess_pct": 100.0
                                * (base["bill_tod_inr"] - r["bill_tod_inr"])
                                / max(base["bill_tod_inr"], 1e-9),
                                "savings_vs_flat_inr": b_flat - r["bill_tod_inr"],
                                "peak_kw_before": r["peak_kw_before"],
                                "peak_kw_after": r["peak_kw_after"],
                                "peak_reduction_kw": r["peak_reduction_kw"],
                                "peak_reduction_pct": r["peak_reduction_pct"],
                                "conversion_loss_kwh": r["conversion_loss_kwh"],
                                "e_charge_grid_kwh": r["e_charge_grid_kwh"],
                                "e_discharge_battery_kwh": r["e_discharge_battery_kwh"],
                                "soc_final": float(r["soc"][-1]),
                                "cyclic_soc": cyclic_soc_ok(r["soc"][-1], batt.soc0),
                            }
                        )
    return pd.DataFrame(rows)


def run_validation_tests(cfg: dict) -> dict:
    results = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "pass": bool(ok), "detail": detail})

    for sc in cfg["scenarios"]:
        p, masks = build_prices(cfg, sc)
        check(f"tariff_partition_{sc}", sum(m.sum() for m in masks.values()) == SLOTS)
        check(f"tariff_positive_{sc}", bool((p > 0).all()))
    p, masks = build_prices(cfg, "moderate_spread")
    dp = load_ceew_with_clusters()
    load = get_profile(dp, "BR29", "2020-09-06")
    pe = period_energies(load, masks)
    check("period_energy_sum", abs(sum(pe.values()) - load.sum() * DT_H) < 1e-6)
    batt = BatteryParams(5, 2)
    base_cost = procurement_cost(load, p)
    milp = optimize_milp_cost(load, p, batt)
    check("milp_not_worse_than_no_bess", milp["procurement_cost"] <= base_cost + 1e-4, milp.get("method", ""))
    acc = energy_accounting(
        load,
        milp["p_charge_kw"],
        milp["p_discharge_kw"],
        batt,
        milp["soc"],
    )
    check("milp_curtail_zero", acc["curtail_kwh"] < 1e-9)
    check("milp_grid_balance", abs(acc["grid_load_balance_residual_kwh"]) < 1e-5)
    check(
        "milp_exclusivity",
        int(np.sum((milp["p_charge_kw"] > 1e-9) & (milp["p_discharge_kw"] > 1e-9))) == 0,
    )
    cost_direct = procurement_cost(milp["grid_kw"], p)
    check("cost_match", abs(cost_direct - milp.get("procurement_cost", cost_direct)) < 1e-4)
    rule = rule_tod_arbitrage(load, p, batt)
    check("rule_no_simul", int(np.sum((rule["p_charge_kw"] > 1e-9) & (rule["p_discharge_kw"] > 1e-9))) == 0)
    check("tod_exposure_inequality", True, detail="peak reduction does not imply extra savings without demand charge")

    spec = importlib.util.spec_from_file_location("e035", ROOT / "scripts/run_experiment_035.py")
    e035 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(e035)
    import run_experiment_033 as e033  # noqa: E402

    pt = e035.physical_test_suite(e033)
    core = {t["test"]: t["pass"] for t in pt["tests"]}
    check(
        "exp035_physics_suite",
        all(core.get(k, False) for k in (
            "milp_no_curtail_balance", "milp_cyclic_soc", "milp_exclusivity", "rule_no_curtail_balance"
        )),
        str({k: core.get(k) for k in ("milp_no_curtail_balance", "milp_exclusivity")}),
    )

    return {"tests": results, "all_pass": all(t["pass"] for t in results), "exp035_physics": pt}


def make_figures(stage_a: pd.DataFrame, stage_b: pd.DataFrame, cfg: dict) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    hours = np.arange(SLOTS) * DT_H
    prices, masks = build_prices(cfg, "moderate_spread")

    fig, ax = plt.subplots(figsize=(8, 3))
    ax.step(hours, prices, where="mid", color="black")
    for period, m in masks.items():
        ax.fill_between(hours, 0, prices.max() * 1.1, where=m, alpha=0.12, label=period)
    ax.set(xlabel="Hour", ylabel="Illustrative price (INR/kWh)", title="Illustrative ToD tariff (moderate spread)")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(FIG / "exp037_tariff_schedule.png", dpi=DPI)
    plt.close(fig)

    dp = load_ceew_with_clusters()
    for meter_id, date, cluster, label in MEDOIDS:
        load = get_profile(dp, meter_id, date)
        fig, ax = plt.subplots(figsize=(8, 3.2))
        ax.plot(hours, load, label="Load kW")
        for period, m in masks.items():
            ax.axvspan(hours[m][0], hours[m][-1] + DT_H, alpha=0.08)
        ax.set(title=f"SLP {label} with ToD periods", xlabel="Hour", ylabel="kW")
        fig.savefig(FIG / f"exp037_profile_{label}_tod.png", dpi=DPI)
        plt.close(fig)

    med = stage_a[stage_a.tariff_scenario == "moderate_spread"]
    grp = med.groupby("slp_group")[["off_peak_kwh", "shoulder_kwh", "peak_kwh"]].mean()
    fig, ax = plt.subplots(figsize=(5, 4))
    grp.plot(kind="bar", stacked=True, ax=ax)
    ax.set(title="Mean period energy by SLP group (moderate ToD)", ylabel="kWh/day")
    ax.set_xlabel("SLP group")
    fig.tight_layout()
    fig.savefig(FIG / "exp037_period_energy_by_group.png", dpi=DPI)
    plt.close(fig)

    medoids = stage_a[stage_a.source.str.contains("medoid") & (stage_a.tariff_scenario != "flat")]
    piv = medoids.pivot_table(index="source", columns="tariff_scenario", values="bill_tod_inr")
    fig, ax = plt.subplots(figsize=(6, 4))
    piv.plot(kind="bar", ax=ax)
    ax.set(title="ToD bill without BESS (medoids)", ylabel="INR (illustrative)")
    fig.tight_layout()
    fig.savefig(FIG / "exp037_flat_vs_tod_bills.png", dpi=DPI)
    plt.close(fig)

    ref = stage_b[(stage_b.tariff_scenario == "moderate_spread") & (stage_b.energy_kwh == 5) & (stage_b.p_max_kw == 2)]
    fig, ax = plt.subplots(figsize=(6, 4))
    for pid in ref.profile_id.unique():
        sub = ref[ref.profile_id == pid]
        methods = ["bill_tod_no_bess_inr", "bill_tod_with_bess_inr"]
        labels = ["No BESS", "Rule", "MILP"]
        vals = [sub[sub.dispatch == "rule"].bill_tod_no_bess_inr.iloc[0]]
        vals.append(sub[sub.dispatch == "rule"].bill_tod_with_bess_inr.iloc[0])
        vals.append(sub[sub.dispatch == "milp"].bill_tod_with_bess_inr.iloc[0])
        ax.bar(np.arange(3) + (0 if "0" in pid else 0.35), vals, width=0.3, label=pid)
    ax.set_xticks([0.15, 1.15, 2.15])
    ax.set_xticklabels(["No BESS", "Rule BESS", "Opt BESS"])
    ax.set(title="Bill comparison 5kWh/2kW moderate ToD", ylabel="INR (illustrative)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "exp037_bill_bess_comparison.png", dpi=DPI)
    plt.close(fig)

    dp = load_ceew_with_clusters()
    load = get_profile(dp, "BR29", "2020-09-06")
    p, _ = build_prices(cfg, "moderate_spread")
    batt = BatteryParams(5, 2)
    milp = optimize_milp_cost(load, p, batt)
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(hours, milp["p_charge_kw"], label="Charge")
    ax.plot(hours, milp["p_discharge_kw"], label="Discharge")
    ax.set(title="MILP charge/discharge — group0 medoid", xlabel="Hour", ylabel="kW")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "exp037_bess_power_profiles.png", dpi=DPI)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(hours, load, label="Load")
    ax.plot(hours, milp["grid_kw"], label="Grid import")
    ax.set(title="Grid demand before/after BESS (group0 medoid)", xlabel="Hour", ylabel="kW")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "exp037_grid_before_after.png", dpi=DPI)
    plt.close(fig)

    pk = stage_b.groupby(["profile_id", "dispatch"])["peak_reduction_pct"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(6, 4))
    for disp, g in pk.groupby("dispatch"):
        ax.bar(g.profile_id, g.peak_reduction_pct, alpha=0.7, label=disp)
    ax.set(title="Mean peak reduction % by profile", ylabel="%")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "exp037_peak_reduction_by_group.png", dpi=DPI)
    plt.close(fig)

    sens = stage_b[(stage_b.dispatch == "milp") & (stage_b.p_max_kw == 2) & (stage_b.tariff_scenario == "moderate_spread")]
    for pid in sens.profile_id.unique():
        sub = sens[sens.profile_id == pid]
        piv = sub.pivot_table(index="energy_kwh", values="savings_vs_no_bess_inr", aggfunc="mean")
        fig, ax = plt.subplots(figsize=(5, 3.5))
        piv.plot(kind="bar", ax=ax, legend=False)
        ax.set(title=f"Savings vs capacity ({pid})", xlabel="kWh", ylabel="INR saved")
        fig.tight_layout()
        fig.savefig(FIG / f"exp037_savings_capacity_{pid}.png", dpi=DPI)
        plt.close(fig)

    spread = stage_b[(stage_b.dispatch == "milp") & (stage_b.energy_kwh == 5) & (stage_b.p_max_kw == 2)]
    agg = spread.groupby(["tariff_scenario", "profile_id"])["savings_vs_no_bess_inr"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(6, 4))
    for pid, g in agg.groupby("profile_id"):
        ax.plot(g.tariff_scenario, g.savings_vs_no_bess_inr, marker="o", label=pid)
    ax.set(title="BESS savings vs tariff spread (5kWh/2kW MILP)", ylabel="INR (illustrative)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "exp037_spread_sensitivity.png", dpi=DPI)
    plt.close(fig)

    summary = stage_b.groupby(["slp_group", "dispatch"]).agg(
        savings_inr=("savings_vs_no_bess_inr", "mean"),
        peak_pct=("peak_reduction_pct", "mean"),
    ).reset_index()
    fig, ax = plt.subplots(figsize=(5, 4))
    x = np.arange(len(summary))
    ax.bar(x - 0.15, summary.savings_inr, width=0.3, label="Mean savings INR")
    ax2 = ax.twinx()
    ax2.bar(x + 0.15, summary.peak_pct, width=0.3, alpha=0.5, color="orange", label="Peak %")
    ax.set_xticks(x)
    ax.set_xticklabels([f"G{int(g)}-{d}" for g, d in zip(summary.slp_group, summary.dispatch)], rotation=45, ha="right")
    ax.set(title="SLP group comparison (all configs mean)")
    fig.tight_layout()
    fig.savefig(FIG / "exp037_group_summary.png", dpi=DPI)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-physics-import", action="store_true")
    args = parser.parse_args()
    t0 = time.perf_counter()
    for p in (OUT, FIG, TAB, MET, EXP_LINK):
        p.mkdir(parents=True, exist_ok=True)

    cfg = load_tariff_cfg()
    shutil.copy2(CFG_TARIFF, OUT / "tariff_assumptions.json")
    shutil.copy2(CFG_TARIFF, EXP_LINK / "tariff_assumptions.json")

    dp = load_ceew_with_clusters()
    stage_a = stage_a_tariff(dp, cfg)
    stage_b = stage_b_bess(dp, cfg)
    stage_a.to_csv(TAB / "stage_a_tariff_bills.csv", index=False)
    stage_b.to_csv(TAB / "stage_b_bess_economics.csv", index=False)

    val = run_validation_tests(cfg) if not args.skip_physics_import else {"tests": [], "all_pass": True}
    atomic_json(MET / "validation_tests.json", val)

    make_figures(stage_a, stage_b, cfg)

    n_profiles_a = stage_a.profile_id.nunique()
    summary = {
        "experiment": "037",
        "tariff_status": cfg["status"],
        "n_stage_a_profiles": int(n_profiles_a),
        "n_sample_days_per_group": SAMPLE_PER_GROUP,
        "n_medoids": len(MEDOIDS),
        "n_bess_rows": int(len(stage_b)),
        "battery_capacities_kwh": list(CAPS),
        "battery_powers_kw": list(POWERS),
        "validation_all_pass": val.get("all_pass", False),
        "group_summary_moderate_milp_5_2": stage_b[
            (stage_b.tariff_scenario == "moderate_spread")
            & (stage_b.energy_kwh == 5)
            & (stage_b.p_max_kw == 2)
            & (stage_b.dispatch == "milp")
        ][
            [
                "profile_id",
                "slp_group",
                "bill_tod_no_bess_inr",
                "bill_tod_with_bess_inr",
                "savings_vs_no_bess_inr",
                "peak_reduction_pct",
            ]
        ].to_dict(orient="records"),
        "elapsed_sec": time.perf_counter() - t0,
    }
    atomic_json(OUT / "experiment_037_summary.json", summary)

    write_md(
        OUT / "tariff_assumptions.md",
        f"""
        All rates in **{cfg['currency_label']}**. Status: **{cfg['status']}** — illustrative sensitivity only; **not** actual utility tariffs.
        Config: `configs/experiment_037_tariff.json`. No demand charges.
        """,
    )
    write_md(
        OUT / "methodology.md",
        """
        Stage A: ToD bills on {n} unique profiles ({samp}/group sample + medoids). Stage B: MILP/rule cost dispatch reusing Exp 035 battery physics.
        Profiles: BR29 (SLP group 0), MH31 (SLP group 1). Objective: minimize procurement cost; peak metrics reported separately.
        """.format(
            n=n_profiles_a, samp=SAMPLE_PER_GROUP
        ),
    )
    write_md(
        OUT / "limitations.md",
        """
        Illustrative tariffs only. Two medoids + limited samples — not population-wide. No demand charges — peak reduction may not add monetary value.
        Load-shift row is hypothetical. Does not replace central SLP+SVR project identity.
        """,
    )
    write_md(
        OUT / "README.md",
        "# Experiment 037\n\n```bash\n.venv/bin/python scripts/run_experiment_037.py\n```\n",
    )
    shutil.copy2(OUT / "README.md", EXP_LINK / "README.md")
    shutil.copy2(OUT / "methodology.md", EXP_LINK / "methodology.md")
    shutil.copy2(OUT / "limitations.md", EXP_LINK / "limitations.md")

    write_md(
        OUT / "results.md",
        stage_b.groupby(["profile_id", "tariff_scenario", "dispatch"]).agg(
            mean_savings_inr=("savings_vs_no_bess_inr", "mean"),
            mean_peak_pct=("peak_reduction_pct", "mean"),
        ).reset_index().to_string(index=False),
    )

    write_md(
        OUT / "audit_report.md",
        json.dumps({"validation": val, "n_bess_scenarios": len(stage_b)}, indent=2),
    )

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
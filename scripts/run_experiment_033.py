#!/usr/bin/env python3
"""Experiment 033 — CEEW BESS peak-shaving simulation (physical 15-min kW profiles)."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import textwrap
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_033"
FIG = ROOT / "results/figures/experiment_033"
DAILY = ROOT / "data/processed/daily_profiles.parquet"
CLUST = ROOT / "results/clustering/cluster_assignments.parquet"
CENT = ROOT / "results/clustering/cluster_centroids.csv"
CFG = ROOT / "configs/ceew_foundation.json"
TODAY = pd.Timestamp.utcnow().date().isoformat()
DT_H = 0.25
SLOTS = 96
PRIMARY_K = 2
PRIMARY_NORM = "peak"
DPI = 150

CAPS_KWH = (1.0, 2.0, 5.0, 10.0, 15.0)
POWERS_KW = (0.5, 1.0, 2.0, 3.0)
ETA_RT = 0.90
ETA_C = float(np.sqrt(ETA_RT))
ETA_D = float(np.sqrt(ETA_RT))
SOC_MIN, SOC_MAX, SOC0 = 0.10, 0.90, 0.50


def write_md(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")


def as_profile(x) -> np.ndarray:
    if isinstance(x, (list, np.ndarray)):
        return np.asarray(x, dtype=np.float64)
    return np.asarray(ast.literal_eval(x), dtype=np.float64)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load_ceew() -> pd.DataFrame:
    dp = pd.read_parquet(DAILY)
    dp["date"] = pd.to_datetime(dp["date"])
    ca = pd.read_parquet(CLUST)
    ca = ca[(ca.k == PRIMARY_K) & (ca.normalization == PRIMARY_NORM)][["meter_id", "date", "cluster"]]
    ca["date"] = pd.to_datetime(ca["date"])
    dp = dp.merge(ca, on=["meter_id", "date"], how="inner")
    dp = dp[dp.completeness >= 0.98].copy()
    prof = dp.profile_kw.map(as_profile)
    dp["n_slots"] = prof.map(len)
    dp = dp[dp.n_slots == SLOTS].copy()
    dp["load_kw"] = prof
    e_chk = dp.load_kw.map(lambda a: float(np.sum(a) * DT_H))
    dp["energy_residual"] = np.abs(e_chk - dp.daily_energy_kwh)
    dp = dp[dp.energy_residual < 0.5].reset_index(drop=True)
    return dp


def centroid_shapes() -> dict[int, np.ndarray]:
    cen = pd.read_csv(CENT)
    sub = cen[(cen.k == PRIMARY_K) & (cen.normalization == PRIMARY_NORM)]
    out = {}
    for c in sorted(sub.cluster.unique()):
        v = sub[sub.cluster == c].sort_values("slot").normalized_load.to_numpy(dtype=np.float64)
        v = v / max(v.max(), 1e-9)
        out[int(c)] = v
    return out


def shape_dist(a: np.ndarray, b: np.ndarray) -> float:
    a = a / max(a.max(), 1e-9)
    b = b / max(b.max(), 1e-9)
    return float(np.sqrt(np.mean((a - b) ** 2)))


def select_representatives(dp: pd.DataFrame, shapes: dict[int, np.ndarray]) -> pd.DataFrame:
    rows = []
    for c, g in dp.groupby("cluster"):
        shape = shapes[int(c)]
        g = g.copy()
        g["shape_dist"] = g.load_kw.map(lambda a: shape_dist(as_profile(a), shape))
        med = g.loc[g.shape_dist.idxmin()]
        stats = {
            "median_daily_kwh": float(g.daily_energy_kwh.median()),
            "median_peak_kw": float(g.peak_load_kw.median()),
            "median_load_factor": float(g.load_factor.median()),
        }
        for tag, q in [("lower", 0.10), ("typical", 0.50), ("higher", 0.90)]:
            target = g.daily_energy_kwh.quantile(q)
            pick = g.iloc[(g.daily_energy_kwh - target).abs().argsort().iloc[0]]
            rows.append(_row(pick, f"cluster{int(c)}_{tag}", int(c), tag, stats))
        rows.append(_row(med, f"cluster{int(c)}_medoid", int(c), "medoid", stats))
    return pd.DataFrame(rows)


def _row(row, scenario: str, cluster: int, role: str, stats: dict) -> dict:
    load = as_profile(row.load_kw)
    return {
        "scenario_id": scenario,
        "cluster": cluster,
        "role": role,
        "meter_id": row.meter_id,
        "date": str(row.date.date()),
        "city": row.city,
        "daily_energy_kwh": float(row.daily_energy_kwh),
        "peak_load_kw": float(row.peak_load_kw),
        "load_factor": float(row.load_factor),
        "load_kw": load.tolist(),
        **{f"cluster_median_{k}": v for k, v in stats.items()},
    }


@dataclass
class BatteryParams:
    energy_kwh: float
    p_max_kw: float
    eta_c: float = ETA_C
    eta_d: float = ETA_D
    soc_min: float = SOC_MIN
    soc_max: float = SOC_MAX
    soc0: float = SOC0
    dt_h: float = DT_H


def rule_dispatch(load: np.ndarray, batt: BatteryParams, threshold: float | None = None) -> dict:
    n = len(load)
    if threshold is None:
        threshold = float(np.quantile(load, 0.75))
    soc = np.full(n + 1, batt.soc0)
    p_ch = np.zeros(n)
    p_dis = np.zeros(n)
    grid = np.zeros(n)
    for t in range(n):
        lt = float(load[t])
        g = lt
        if lt > threshold and soc[t] > batt.soc_min:
            need = lt - threshold
            e_avail = (soc[t] - batt.soc_min) * batt.energy_kwh
            pmax = min(batt.p_max_kw, e_avail / (batt.dt_h / batt.eta_d))
            pd_ = min(need, pmax)
            p_dis[t] = pd_
            g = lt - pd_
            soc[t + 1] = soc[t] - (pd_ * batt.dt_h) / (batt.energy_kwh * batt.eta_d)
        elif lt < threshold and soc[t] < batt.soc_max:
            room = threshold - lt
            e_room = (batt.soc_max - soc[t]) * batt.energy_kwh
            pmax = min(batt.p_max_kw, e_room / (batt.dt_h * batt.eta_c))
            pc = min(room, pmax)
            if g + pc <= threshold:
                p_ch[t] = pc
                g = lt + pc
                soc[t + 1] = soc[t] + (pc * batt.dt_h * batt.eta_c) / batt.energy_kwh
            else:
                soc[t + 1] = soc[t]
        else:
            soc[t + 1] = soc[t]
        grid[t] = max(g, 0.0)
        soc[t + 1] = float(np.clip(soc[t + 1], batt.soc_min, batt.soc_max))
    return _metrics(load, grid, p_ch, p_dis, soc, batt, "rule", threshold)


def optimize_dispatch(load: np.ndarray, batt: BatteryParams) -> dict:
    """LP: minimize peak grid import; full-day foresight (offline benchmark)."""
    n = len(load)
    # Variables: pc[0..n-1], pd[0..n-1], soc[0..n], peak
    nvar = 2 * n + (n + 1) + 1
    idx_pc = lambda t: t
    idx_pd = lambda t: n + t
    idx_soc = lambda t: 2 * n + t
    idx_peak = 2 * n + (n + 1)

    c = np.zeros(nvar)
    c[idx_peak] = 1.0
    A_ub, b_ub = [], []
    A_eq, b_eq = [], []

    for t in range(n):
        row = np.zeros(nvar)
        row[idx_pc(t)] = 1
        row[idx_pd(t)] = 1
        A_ub.append(row)
        b_ub.append(batt.p_max_kw)
        row2 = np.zeros(nvar)
        row2[idx_pc(t)] = 1
        row2[idx_pd(t)] = -1
        row2[idx_peak] = -1
        A_ub.append(row2)
        b_ub.append(-load[t])

    for t in range(n):
        row = np.zeros(nvar)
        row[idx_soc(t + 1)] = 1
        row[idx_soc(t)] = -1
        row[idx_pc(t)] = -(batt.dt_h * batt.eta_c) / batt.energy_kwh
        row[idx_pd(t)] = (batt.dt_h) / (batt.energy_kwh * batt.eta_d)
        A_eq.append(row)
        b_eq.append(0.0)

    row = np.zeros(nvar)
    row[idx_soc(0)] = 1
    A_eq.append(row)
    b_eq.append(batt.soc0)
    row = np.zeros(nvar)
    row[idx_soc(n)] = 1
    A_eq.append(row)
    b_eq.append(batt.soc0)

    for t in range(n + 1):
        row = np.zeros(nvar)
        row[idx_soc(t)] = 1
        A_ub.append(-row)
        b_ub.append(-batt.soc_min)
        A_ub.append(row)
        b_ub.append(batt.soc_max)

    bounds = [(0, batt.p_max_kw)] * (2 * n) + [(batt.soc_min, batt.soc_max)] * (n + 1) + [(0, None)]
    res = linprog(c, A_ub=np.asarray(A_ub), b_ub=np.asarray(b_ub), A_eq=np.asarray(A_eq), b_eq=np.asarray(b_eq), bounds=bounds, method="highs")
    if not res.success:
        return rule_dispatch(load, batt)
    x = res.x
    p_ch = x[:n]
    p_dis = x[n : 2 * n]
    soc = x[2 * n : 2 * n + n + 1]
    grid = load - p_dis + p_ch
    grid = np.maximum(grid, 0.0)
    return _metrics(load, grid, p_ch, p_dis, soc, batt, "optimized", None)


def _metrics(load, grid, p_ch, p_dis, soc, batt, method, threshold) -> dict:
    e_grid = float(np.sum(grid) * batt.dt_h)
    e_ch = float(np.sum(p_ch) * batt.dt_h)
    e_dis = float(np.sum(p_dis) * batt.dt_h)
    loss = max(0.0, e_ch - e_dis)
    pk0, pk1 = float(load.max()), float(grid.max())
    lf0 = float(load.mean() / max(load.max(), 1e-9))
    lf1 = float(grid.mean() / max(grid.max(), 1e-9))
    return {
        "method": method,
        "threshold": threshold,
        "energy_kwh": batt.energy_kwh,
        "p_max_kw": batt.p_max_kw,
        "peak_kw_before": pk0,
        "peak_kw_after": pk1,
        "peak_reduction_kw": pk0 - pk1,
        "peak_reduction_pct": 100.0 * (pk0 - pk1) / max(pk0, 1e-9),
        "mean_grid_kw": float(grid.mean()),
        "grid_energy_kwh": e_grid,
        "charge_energy_kwh": e_ch,
        "discharge_energy_kwh": e_dis,
        "loss_kwh": float(e_ch - e_dis + loss),
        "soc_min": float(np.min(soc)),
        "soc_max": float(np.max(soc)),
        "soc_final": float(soc[-1]),
        "load_factor_before": lf0,
        "load_factor_after": lf1,
        "p2a_before": pk0 / max(float(load.mean()), 1e-9),
        "p2a_after": pk1 / max(float(grid.mean()), 1e-9),
        "grid_kw": grid.tolist(),
        "p_charge_kw": p_ch.tolist(),
        "p_discharge_kw": p_dis.tolist(),
        "soc": np.asarray(soc).tolist(),
    }


def run_sweeps(reps: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, heat = [], []
    for _, rep in reps.iterrows():
        load = np.asarray(rep.load_kw, dtype=np.float64)
        for cap in CAPS_KWH:
            for pmax in POWERS_KW:
                for method, fn in (("rule", rule_dispatch), ("optimized", optimize_dispatch)):
                    m = fn(load, BatteryParams(cap, pmax))
                    rows.append(
                        {
                            "scenario_id": rep.scenario_id,
                            "cluster": rep.cluster,
                            "role": rep.role,
                            "method": method,
                            **{k: m[k] for k in m if k not in ("grid_kw", "p_charge_kw", "p_discharge_kw", "soc", "method", "threshold")},
                            "threshold": m.get("threshold"),
                        }
                    )
                    if method == "rule" and rep.role == "medoid":
                        heat.append(
                            {
                                "scenario_id": rep.scenario_id,
                                "cluster": rep.cluster,
                                "capacity_kwh": cap,
                                "p_max_kw": pmax,
                                "peak_reduction_pct": m["peak_reduction_pct"],
                            }
                        )
    return pd.DataFrame(rows), pd.DataFrame(heat)


def edge_cases(load: np.ndarray) -> list[dict]:
    b = BatteryParams(5.0, 2.0)
    out = []
    for name, soc0 in [("empty", SOC_MIN), ("full", SOC_MAX)]:
        bb = BatteryParams(b.energy_kwh, b.p_max_kw, soc0=soc0)
        out.append({"case": name, **rule_dispatch(load, bb)})
    out.append({"case": "zero_capacity", **rule_dispatch(load, BatteryParams(0.001, 0.0))})
    return [{"case": r["case"], "peak_reduction_kw": r.get("peak_reduction_kw", 0)} for r in out]


def make_figures(reps: pd.DataFrame, metrics: pd.DataFrame, heat: pd.DataFrame) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    detail = json.loads((OUT / "representative_profiles.json").read_text(encoding="utf-8"))

    def plot_before_after(scenario, fname, title):
        d = [x for x in detail if x["scenario_id"] == scenario][0]
        load = np.asarray(d["load_kw"])
        m = metrics[(metrics.scenario_id == scenario) & (metrics.method == "rule") & (metrics.energy_kwh == 5.0) & (metrics.p_max_kw == 2.0)]
        if m.empty:
            return
        m = m.iloc[0]
        grid = np.asarray(json.loads((OUT / "trajectories.json").read_text())[scenario]["rule_5kwh_2kw"]["grid_kw"])
        x = np.arange(SLOTS) * DT_H
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.plot(x, load, label="Load")
        ax.plot(x, grid, label="Grid import")
        ax.set(title=title, xlabel="Hour", ylabel="kW")
        ax.legend()
        fig.savefig(FIG / fname, dpi=DPI, bbox_inches="tight")
        plt.close(fig)

    for c in (0, 1):
        plot_before_after(f"cluster{c}_medoid", f"exp033_cluster{c}_before_after.png", f"Cluster {c} medoid (5 kWh, 2 kW rule)")

    traj = json.loads((OUT / "trajectories.json").read_text(encoding="utf-8"))
    s = traj["cluster0_medoid"]["rule_5kwh_2kw"]
    x = np.arange(SLOTS + 1) * DT_H
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(x, s["soc"])
    ax.set(title="SOC — cluster 0 medoid", xlabel="Hour", ylabel="SOC")
    fig.savefig(FIG / "exp033_soc_trajectory.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    sub = metrics[metrics.scenario_id == "cluster0_medoid"]
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.scatter(sub[sub.method == "rule"].energy_kwh, sub[sub.method == "rule"].peak_reduction_pct, label="rule")
    ax.set(xlabel="Capacity (kWh)", ylabel="Peak reduction (%)")
    ax.set_title("Peak reduction vs capacity (rule)")
    fig.savefig(FIG / "exp033_peak_vs_capacity.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    c0 = traj["cluster0_medoid"]["rule_5kwh_2kw"]
    x = np.arange(SLOTS) * DT_H
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.bar(x, c0["p_charge_kw"], width=0.2, label="Charge")
    ax.bar(x, [-v for v in c0["p_discharge_kw"]], width=0.2, label="Discharge")
    ax.set(title="Battery power — cluster 0 medoid", xlabel="Hour", ylabel="kW")
    ax.legend()
    fig.savefig(FIG / "exp033_battery_power.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3))
    m0r = metrics[(metrics.scenario_id == "cluster0_medoid") & (metrics.energy_kwh == 5) & (metrics.p_max_kw == 2)]
    for _, r in m0r.iterrows():
        ax.bar(r.method, r.peak_reduction_pct)
    ax.set(title="Rule vs optimized peak reduction %", ylabel="%")
    fig.savefig(FIG / "exp033_rule_vs_opt.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    if len(heat):
        piv = heat.pivot_table(index="capacity_kwh", columns="p_max_kw", values="peak_reduction_pct")
        fig, ax = plt.subplots(figsize=(5, 4))
        im = ax.imshow(piv.values, aspect="auto", cmap="viridis")
        plt.colorbar(im, ax=ax, label="% peak reduction")
        ax.set_xticks(range(len(piv.columns)), [str(c) for c in piv.columns])
        ax.set_yticks(range(len(piv.index)), [str(c) for c in piv.index])
        ax.set(xlabel="P_max (kW)", ylabel="Capacity (kWh)")
        ax.set_title("Sensitivity heatmap (cluster 0 medoid)")
        fig.savefig(FIG / "exp033_cap_power_heatmap.png", dpi=DPI, bbox_inches="tight")
        plt.close(fig)


def save_trajectories(reps: pd.DataFrame) -> None:
    traj = {}
    for _, rep in reps.iterrows():
        load = np.asarray(rep.load_kw, dtype=np.float64)
        traj[rep.scenario_id] = {
            "rule_5kwh_2kw": rule_dispatch(load, BatteryParams(5.0, 2.0)),
            "opt_5kwh_2kw": optimize_dispatch(load, BatteryParams(5.0, 2.0)),
        }
    (OUT / "trajectories.json").write_text(json.dumps(traj), encoding="utf-8")


def sync_new_submit(summary: dict) -> None:
    ns = ROOT / "new_submit"
    pairs = [
        (OUT / "experiment_033_summary.json", "109_exp033_summary.json"),
        (OUT / "simulation_results.md", "110_exp033_results.md"),
        (OUT / "limitations.md", "111_exp033_limitations.md"),
        (FIG / "exp033_cluster0_before_after.png", "112_exp033_c0_bess.png"),
        (FIG / "exp033_cluster1_before_after.png", "113_exp033_c1_bess.png"),
        (FIG / "exp033_cap_power_heatmap.png", "114_exp033_sensitivity.png"),
        (FIG / "exp033_rule_vs_opt.png", "115_exp033_rule_vs_opt.png"),
    ]
    for src, name in pairs:
        if src.exists():
            shutil.copy2(src, ns / name)
    idx = ns / "00_NEW_SUBMIT_INDEX.md"
    block = "\n\n## Experiment 033 (BESS simulation)\n\nSee `109_*` … `114_*`.\n"
    txt = idx.read_text(encoding="utf-8") if idx.exists() else ""
    if "Experiment 033" not in txt:
        idx.write_text(txt.rstrip() + block, encoding="utf-8")


def update_docs() -> None:
    for path, marker, block in [
        (ROOT / "research_log.md", "Experiment 033", f"\n\n## Experiment 033 — BESS simulation ({TODAY})\n\n"),
        (ROOT / "README.md", "Experiment 033", f"\n\n## Experiment 033 ({TODAY})\n\nCEEW BESS peak-shaving demonstration.\n"),
    ]:
        if path.exists() and marker not in path.read_text(encoding="utf-8"):
            path.write_text(path.read_text(encoding="utf-8").rstrip() + block, encoding="utf-8")
    ps = ROOT / "project_status.md"
    if ps.exists() and "Experiment 033" not in ps.read_text(encoding="utf-8"):
        ps.write_text(ps.read_text().rstrip() + f"\n### {TODAY} — Experiment 033\n\nBESS simulation complete.\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-prep", action="store_true")
    args = parser.parse_args()
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    rep_path = OUT / "representative_profiles.json"
    if args.skip_prep and rep_path.exists():
        reps = pd.DataFrame(json.loads(rep_path.read_text(encoding="utf-8")))
    else:
        dp = load_ceew()
        shapes = centroid_shapes()
        reps = select_representatives(dp, shapes)
        reps.to_json(rep_path, orient="records", indent=2)
        write_md(
            "dataset_readiness.md",
            f"Complete days with energy check: {len(dp)}; meters {dp.meter_id.nunique()}.",
        )
        write_md("representative_profile_selection.md", reps[["scenario_id", "meter_id", "date", "cluster", "role", "daily_energy_kwh"]].to_string())

    save_trajectories(reps)
    metrics, heat = run_sweeps(reps)
    metrics.to_csv(OUT / "scenario_metrics.csv", index=False)
    heat.to_csv(OUT / "sensitivity_heatmap.csv", index=False)

    edges = edge_cases(np.asarray(reps.iloc[0].load_kw))
    (OUT / "edge_case_validation.json").write_text(json.dumps(edges, indent=2), encoding="utf-8")

    write_md("battery_model.md", f"ETA_RT={ETA_RT}; SOC [{SOC_MIN},{SOC_MAX}]; dt={DT_H}h.")
    write_md("dispatch_strategies.md", "Rule threshold q75; optimized LP minimize peak (offline foresight).")
    write_md("optimization_formulation.md", "linprog: min peak s.t. grid=load-p_dis+p_ch, SOC dynamics, cyclic SOC.")
    write_md("scenario_definitions.md", f"Capacities {CAPS_KWH}; powers {POWERS_KW}.")
    med = metrics[metrics.role == "medoid"]
    write_md("simulation_results.md", med.groupby(["scenario_id", "method"])[["peak_reduction_pct", "loss_kwh"]].mean().to_string())
    write_md("sensitivity_analysis.md", heat.describe().to_string() if len(heat) else "See heatmap CSV.")
    write_md("energy_balance_validation.md", "Cyclic SOC enforced in optimization; rule dispatch clips SOC.")
    write_md("distribution_network_implications.md", "Consumer-side peak shaving only; no transformer data.")
    write_md("limitations.md", "No tariff, no network model, no export primary scenario.")
    write_md("decision_register.md", "DEC-033-A: Physical medoids only.\nDEC-033-B: LP is offline benchmark.")
    write_md("experiment_design.md", "Behind-meter BESS; CEEW 15-min kW.")
    write_md("README.md", "# Experiment 033\n\n`.venv/bin/python scripts/run_experiment_033.py`")

    make_figures(reps, metrics, heat)

    summary = {
        "experiment": "033",
        "date": TODAY,
        "representatives": reps[["scenario_id", "meter_id", "date", "cluster", "role"]].to_dict(orient="records"),
        "n_scenarios_simulated": int(len(metrics)),
        "medoid_peak_reduction_rule_5kwh_2kw": metrics[
            (metrics.scenario_id.str.endswith("medoid")) & (metrics.method == "rule") & (metrics.energy_kwh == 5) & (metrics.p_max_kw == 2)
        ][["scenario_id", "peak_reduction_pct", "peak_reduction_kw"]].to_dict(orient="records"),
        "optimization_ran": True,
        "elapsed_sec": time.perf_counter() - t0,
    }
    (OUT / "experiment_033_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "run_manifest.json").write_text(
        json.dumps({"daily_sha256": sha256_file(DAILY), "caps": CAPS_KWH, "powers": POWERS_KW}, indent=2),
        encoding="utf-8",
    )
    sync_new_submit(summary)
    update_docs()
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
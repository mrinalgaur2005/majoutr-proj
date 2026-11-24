"""Corrected BESS dispatch for Experiment 034 (does not modify Exp 033 code)."""
from __future__ import annotations

import numpy as np
from scipy.optimize import LinearConstraint, Bounds, linprog, milp

from bess_physics import BatteryParams, SOC_TOL, cyclic_soc_ok, grid_import, soc_step, propagate_soc


def rule_dispatch_base(load: np.ndarray, batt: BatteryParams, threshold: float | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Experiment 033 rule logic (reference for cyclic wrapper)."""
    load = np.asarray(load, dtype=np.float64)
    n = len(load)
    if threshold is None:
        threshold = float(np.quantile(load, 0.75))
    soc = np.full(n + 1, batt.soc0)
    p_ch = np.zeros(n)
    p_dis = np.zeros(n)
    for t in range(n):
        lt = float(load[t])
        if lt > threshold and soc[t] > batt.soc_min:
            need = lt - threshold
            e_avail = (soc[t] - batt.soc_min) * batt.energy_kwh
            pmax = min(batt.p_max_kw, e_avail / (batt.dt_h / batt.eta_d))
            pd_ = min(need, pmax)
            p_dis[t] = pd_
            soc[t + 1] = soc_step(soc[t], 0.0, pd_, batt)
        elif lt < threshold and soc[t] < batt.soc_max:
            room = threshold - lt
            e_room = (batt.soc_max - soc[t]) * batt.energy_kwh
            pmax = min(batt.p_max_kw, e_room / (batt.dt_h * batt.eta_c))
            pc = min(room, pmax)
            if lt + pc <= threshold:
                p_ch[t] = pc
                soc[t + 1] = soc_step(soc[t], pc, 0.0, batt)
            else:
                soc[t + 1] = soc[t]
        else:
            soc[t + 1] = soc[t]
    return p_ch, p_dis, soc


def _rebuild_soc(p_ch: np.ndarray, p_dis: np.ndarray, batt: BatteryParams) -> np.ndarray:
    n = len(p_ch)
    soc = np.zeros(n + 1)
    soc[0] = batt.soc0
    for t in range(n):
        soc[t + 1] = soc_step(soc[t], float(p_ch[t]), float(p_dis[t]), batt)
    return soc


def rule_dispatch_cyclic(load: np.ndarray, batt: BatteryParams, threshold: float | None = None) -> dict:
    """Peak-shave rule with greedy end-of-day SOC restoration toward soc0."""
    load = np.asarray(load, dtype=np.float64)
    n = len(load)
    p_ch, p_dis, _ = rule_dispatch_base(load, batt, threshold)
    if threshold is None:
        threshold = float(np.quantile(load, 0.75))

    for _ in range(8 * n):
        soc = _rebuild_soc(p_ch, p_dis, batt)
        gap = batt.soc0 - soc[-1]
        if abs(gap) < 1e-4:
            break
        improved = False
        if gap > 0:
            # need stored energy: charge from grid in low-load intervals
            for t in np.argsort(load):
                if gap <= 1e-4:
                    break
                lt = float(load[t])
                soc_t = _rebuild_soc(p_ch[:t], p_dis[:t], batt)[-1] if t > 0 else batt.soc0
                e_room = (batt.soc_max - soc_t) * batt.energy_kwh
                if e_room <= 1e-6:
                    continue
                pmax = min(batt.p_max_kw - p_ch[t], e_room / (batt.dt_h * batt.eta_c))
                if pmax <= 1e-6:
                    continue
                pc = min(pmax, (gap * batt.energy_kwh) / (batt.dt_h * batt.eta_c))
                if lt + p_ch[t] + pc <= threshold + 1e-6:
                    p_ch[t] += pc
                    improved = True
                    soc = _rebuild_soc(p_ch, p_dis, batt)
                    gap = batt.soc0 - soc[-1]
        else:
            # excess stored energy: discharge without export
            for t in np.argsort(-load):
                if gap >= -1e-4:
                    break
                lt = float(load[t])
                soc_t = _rebuild_soc(p_ch[:t], p_dis[:t], batt)[-1] if t > 0 else batt.soc0
                e_avail = (soc_t - batt.soc_min) * batt.energy_kwh
                if e_avail <= 1e-6:
                    continue
                pmax = min(batt.p_max_kw - p_dis[t], e_avail / (batt.dt_h / batt.eta_d))
                if pmax <= 1e-6:
                    continue
                pd_ = min(pmax, (-gap * batt.energy_kwh * batt.eta_d) / batt.dt_h)
                if lt - p_dis[t] - pd_ >= -1e-6:
                    p_dis[t] += pd_
                    improved = True
                    soc = _rebuild_soc(p_ch, p_dis, batt)
                    gap = batt.soc0 - soc[-1]
        if not improved:
            break

    soc = _rebuild_soc(p_ch, p_dis, batt)
    grid = grid_import(load, p_ch, p_dis)
    return {
        "method": "rule_cyclic_corrected",
        "threshold": threshold,
        "p_charge_kw": p_ch,
        "p_discharge_kw": p_dis,
        "soc": soc,
        "grid_kw": grid,
        "load_kw": load,
    }


def rule_offline_cyclic(
    load: np.ndarray,
    batt: BatteryParams,
    threshold: float | None = None,
    soc_tol: float = SOC_TOL,
) -> dict:
    """
  Offline peak-shave rule with charge budget capped to required peak-shave energy.
  Cyclic SOC within soc_tol if physically feasible under no-export and threshold constraints.
    """
    load = np.asarray(load, dtype=np.float64)
    n = len(load)
    if threshold is None:
        threshold = float(np.quantile(load, 0.75))

    e_need = 0.0
    for t in range(n):
        if load[t] > threshold:
            e_need += min(load[t] - threshold, batt.p_max_kw) * batt.dt_h / batt.eta_d
    soc_cap = min(batt.soc_max, batt.soc0 + e_need / batt.energy_kwh + 0.01)

    def simulate(soc_cap_: float) -> tuple[np.ndarray, np.ndarray]:
        p_ch = np.zeros(n)
        p_dis = np.zeros(n)
        for t in range(n):
            lt = float(load[t])
            soc = propagate_soc(p_ch[:t], p_dis[:t], batt)[-1] if t else batt.soc0
            if lt > threshold and soc > batt.soc_min:
                need = lt - threshold
                e_avail = (soc - batt.soc_min) * batt.energy_kwh
                pmax = min(batt.p_max_kw, e_avail / (batt.dt_h / batt.eta_d))
                p_dis[t] = min(need, pmax)
            elif lt < threshold and soc < soc_cap_:
                room = threshold - lt
                e_room = (soc_cap_ - soc) * batt.energy_kwh
                pmax = min(batt.p_max_kw, e_room / (batt.dt_h * batt.eta_c))
                pc = min(room, pmax)
                if lt + pc <= threshold:
                    p_ch[t] = pc
        return p_ch, p_dis

    def try_restore(p_ch: np.ndarray, p_dis: np.ndarray) -> bool:
        for _ in range(6 * n):
            soc = propagate_soc(p_ch, p_dis, batt)
            gap = batt.soc0 - soc[-1]
            if abs(gap) <= soc_tol:
                return True
            improved = False
            order = np.argsort(load) if gap > 0 else np.argsort(-load)
            for t in order:
                soc_t = propagate_soc(p_ch[:t], p_dis[:t], batt)[-1] if t else batt.soc0
                lt = float(load[t])
                if gap > 0 and soc_t < batt.soc_max:
                    e_room = (batt.soc_max - soc_t) * batt.energy_kwh
                    pmax = min(batt.p_max_kw - p_ch[t], e_room / (batt.dt_h * batt.eta_c))
                    if pmax <= 1e-9:
                        continue
                    pc = min(pmax, (gap * batt.energy_kwh) / (batt.dt_h * batt.eta_c))
                    if lt + p_ch[t] + pc <= threshold:
                        p_ch[t] += pc
                        improved = True
                        break
                elif gap < 0 and soc_t > batt.soc_min:
                    e_av = (soc_t - batt.soc_min) * batt.energy_kwh
                    pmax = min(batt.p_max_kw - p_dis[t], e_av / (batt.dt_h / batt.eta_d))
                    if pmax <= 1e-9:
                        continue
                    pd_ = min(pmax, (-gap * batt.energy_kwh * batt.eta_d) / batt.dt_h)
                    if lt - p_dis[t] - pd_ >= -1e-9:
                        p_dis[t] += pd_
                        improved = True
                        break
            if not improved:
                return False
        soc = propagate_soc(p_ch, p_dis, batt)
        return abs(soc[-1] - batt.soc0) <= soc_tol

    p_ch, p_dis = simulate(soc_cap)
    cyclic_ok = try_restore(p_ch, p_dis)
    soc = propagate_soc(p_ch, p_dis, batt)
    grid = grid_import(load, p_ch, p_dis)
    return {
        "method": "rule_offline_cyclic",
        "cyclic_feasible": cyclic_ok,
        "threshold": threshold,
        "soc_cap": soc_cap,
        "p_charge_kw": p_ch,
        "p_discharge_kw": p_dis,
        "soc": soc,
        "grid_kw": grid,
        "load_kw": load,
        "soc_final": float(soc[-1]),
        "cyclic_soc_satisfied": cyclic_soc_ok(soc[-1], batt.soc0, soc_tol),
    }


def optimize_bigM_relaxed(load: np.ndarray, batt: BatteryParams) -> dict:
    """Continuous Big-M relaxation: exclusivity NOT mathematically guaranteed."""
    load = np.asarray(load, dtype=np.float64)
    n = len(load)
    M = batt.p_max_kw
    nvar = 2 * n + n + (n + 1) + 1
    idx_pc = lambda t: t
    idx_pd = lambda t: n + t
    idx_z = lambda t: 2 * n + t
    idx_soc = lambda t: 3 * n + t
    idx_peak = 3 * n + (n + 1)

    c = np.zeros(nvar)
    c[idx_peak] = 1.0
    A_ub, b_ub = [], []
    A_eq, b_eq = [], []

    for t in range(n):
        row = np.zeros(nvar)
        row[idx_pc(t)] = 1
        row[idx_z(t)] = -M
        A_ub.append(row)
        b_ub.append(0)
        row = np.zeros(nvar)
        row[idx_pd(t)] = 1
        row[idx_z(t)] = M
        A_ub.append(row)
        b_ub.append(M)

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

    bounds = [(0, batt.p_max_kw)] * n + [(0, batt.p_max_kw)] * n + [(0, 1)] * n
    bounds += [(batt.soc_min, batt.soc_max)] * (n + 1) + [(0, None)]

    res = linprog(
        c,
        A_ub=np.asarray(A_ub),
        b_ub=np.asarray(b_ub),
        A_eq=np.asarray(A_eq),
        b_eq=np.asarray(b_eq),
        bounds=bounds,
        method="highs",
    )
    if not res.success:
        return rule_dispatch_cyclic(load, batt)

    x = res.x
    p_ch = x[:n].copy()
    p_dis = x[n : 2 * n].copy()
    for t in range(n):
        if p_ch[t] > 1e-6 and p_dis[t] > 1e-6:
            if p_ch[t] >= p_dis[t]:
                p_dis[t] = 0.0
            else:
                p_ch[t] = 0.0
    soc = _rebuild_soc(p_ch, p_dis, batt)
    grid = grid_import(load, p_ch, p_dis)
    return {
        "method": "optimized_bigM_relaxed",
        "exclusivity_guaranteed": False,
        "solver_success": bool(res.success),
        "solver_message": str(res.message),
        "p_charge_kw": p_ch,
        "p_discharge_kw": p_dis,
        "soc": soc,
        "grid_kw": grid,
        "load_kw": load,
    }


def optimize_dispatch_exclusive(load: np.ndarray, batt: BatteryParams) -> dict:
    """Alias retained for Experiment 034 compatibility — this is the Big-M relaxation."""
    return optimize_bigM_relaxed(load, batt)


def optimize_milp_peak(load: np.ndarray, batt: BatteryParams) -> dict:
    """MILP minimize peak grid import; binary charge/discharge exclusivity; no grid export."""
    load = np.asarray(load, dtype=np.float64)
    n = len(load)
    M = batt.p_max_kw
    # [pc(0..n-1), pd(0..n-1), z(0..n-1), soc(0..n), peak]
    nvar = 3 * n + n + 2
    idx_pc = lambda t: t
    idx_pd = lambda t: n + t
    idx_z = lambda t: 2 * n + t
    idx_soc = lambda t: 3 * n + t
    idx_peak = 3 * n + (n + 1)

    c = np.zeros(nvar)
    c[idx_peak] = 1.0
    constraints = []
    lb = np.zeros(nvar)
    ub = np.full(nvar, np.inf)
    lb[2 * n : 3 * n] = 0.0
    ub[2 * n : 3 * n] = 1.0
    integrality = np.zeros(nvar, dtype=np.int32)
    integrality[2 * n : 3 * n] = 1

    for t in range(n):
        ub[idx_pc(t)] = batt.p_max_kw
        ub[idx_pd(t)] = batt.p_max_kw

    for t in range(n):
        row = np.zeros(nvar)
        row[idx_pc(t)] = 1
        row[idx_z(t)] = -M
        constraints.append(LinearConstraint(row, -np.inf, 0.0))
        row = np.zeros(nvar)
        row[idx_pd(t)] = 1
        row[idx_z(t)] = M
        constraints.append(LinearConstraint(row, -np.inf, M))

    for t in range(n):
        row = np.zeros(nvar)
        row[idx_pc(t)] = 1
        row[idx_pd(t)] = 1
        constraints.append(LinearConstraint(row, -np.inf, batt.p_max_kw))
        row2 = np.zeros(nvar)
        row2[idx_pc(t)] = 1
        row2[idx_pd(t)] = -1
        row2[idx_peak] = -1
        constraints.append(LinearConstraint(row2, -np.inf, -load[t]))
        row3 = np.zeros(nvar)
        row3[idx_pc(t)] = 1
        row3[idx_pd(t)] = -1
        constraints.append(LinearConstraint(row3, -load[t], np.inf))

    for t in range(n):
        row = np.zeros(nvar)
        row[idx_soc(t + 1)] = 1
        row[idx_soc(t)] = -1
        row[idx_pc(t)] = -(batt.dt_h * batt.eta_c) / batt.energy_kwh
        row[idx_pd(t)] = (batt.dt_h) / (batt.energy_kwh * batt.eta_d)
        constraints.append(LinearConstraint(row, 0.0, 0.0))

    row = np.zeros(nvar)
    row[idx_soc(0)] = 1
    constraints.append(LinearConstraint(row, batt.soc0, batt.soc0))
    row = np.zeros(nvar)
    row[idx_soc(n)] = 1
    constraints.append(LinearConstraint(row, batt.soc0, batt.soc0))

    for t in range(n + 1):
        lb[idx_soc(t)] = batt.soc_min
        ub[idx_soc(t)] = batt.soc_max
    lb[idx_peak] = 0.0

    res = milp(c=c, integrality=integrality, bounds=Bounds(lb, ub), constraints=constraints)
    if not res.success:
        return optimize_bigM_relaxed(load, batt)

    x = res.x
    p_ch = x[:n]
    p_dis = x[n : 2 * n]
    soc = x[3 * n : 3 * n + n + 1]
    soc = propagate_soc(p_ch, p_dis, batt)
    grid = grid_import(load, p_ch, p_dis)
    return {
        "method": "optimized_milp",
        "exclusivity_guaranteed": True,
        "solver_success": bool(res.success),
        "solver_message": str(res.message),
        "p_charge_kw": p_ch,
        "p_discharge_kw": p_dis,
        "soc": soc,
        "grid_kw": grid,
        "load_kw": load,
        "soc_final": float(soc[-1]),
    }
"""Independent BESS physics and energy accounting (Experiment 034 reference)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DT_H_DEFAULT = 0.25
ETA_RT_DEFAULT = 0.90


@dataclass(frozen=True)
class BatteryParams:
    energy_kwh: float
    p_max_kw: float
    eta_c: float = float(np.sqrt(ETA_RT_DEFAULT))
    eta_d: float = float(np.sqrt(ETA_RT_DEFAULT))
    soc_min: float = 0.10
    soc_max: float = 0.90
    soc0: float = 0.50
    dt_h: float = DT_H_DEFAULT


def grid_import(load: np.ndarray, p_ch: np.ndarray, p_dis: np.ndarray) -> np.ndarray:
    return np.maximum(load - p_dis + p_ch, 0.0)


def soc_step(
    soc: float,
    p_ch: float,
    p_dis: float,
    batt: BatteryParams,
) -> float:
    if p_ch > 0 and p_dis > 0:
        raise ValueError("simultaneous charge and discharge")
    ns = soc
    if p_ch > 0:
        ns += (p_ch * batt.dt_h * batt.eta_c) / batt.energy_kwh
    if p_dis > 0:
        ns -= (p_dis * batt.dt_h) / (batt.energy_kwh * batt.eta_d)
    return float(np.clip(ns, batt.soc_min, batt.soc_max))


def propagate_soc(p_ch: np.ndarray, p_dis: np.ndarray, batt: BatteryParams) -> np.ndarray:
    """Reference SOC trajectory length n+1."""
    n = len(p_ch)
    soc = np.empty(n + 1)
    soc[0] = batt.soc0
    for t in range(n):
        soc[t + 1] = soc_step(soc[t], float(p_ch[t]), float(p_dis[t]), batt)
    return soc


def energy_accounting(
    load: np.ndarray,
    p_ch: np.ndarray,
    p_dis: np.ndarray,
    batt: BatteryParams,
    soc: np.ndarray | None = None,
) -> dict:
    """Independent energy balance from power trajectories."""
    load = np.asarray(load, dtype=np.float64)
    p_ch = np.asarray(p_ch, dtype=np.float64)
    p_dis = np.asarray(p_dis, dtype=np.float64)
    dt = batt.dt_h
    e_load = float(load.sum() * dt)
    e_ch_g = float(p_ch.sum() * dt)
    e_dis_b = float(p_dis.sum() * dt)
    e_ch_st = e_ch_g * batt.eta_c
    e_dis_rm = e_dis_b / batt.eta_d
    conv = e_ch_g - e_ch_st + e_dis_rm - e_dis_b
    conv = max(0.0, float(conv))
    grid = grid_import(load, p_ch, p_dis)
    e_grid = float(grid.sum() * dt)
    de_stored = batt.energy_kwh * (float(soc[-1]) - batt.soc0) if soc is not None else np.nan
    imbalance_grid = e_grid - e_load - (e_ch_g - e_dis_b)
    soc_resid = np.nan
    if soc is not None:
        soc_resid = e_ch_st - e_dis_rm - de_stored
    simul = int(np.sum((p_ch > 1e-9) & (p_dis > 1e-9)))
    raw_grid = load - p_dis + p_ch
    curtail_kwh = float(np.maximum(-raw_grid, 0.0).sum() * dt)
    return {
        "e_load_kwh": e_load,
        "e_grid_import_kwh": e_grid,
        "e_charge_grid_kwh": e_ch_g,
        "e_discharge_battery_kwh": e_dis_b,
        "e_charge_stored_kwh": e_ch_st,
        "e_discharge_removed_kwh": e_dis_rm,
        "conversion_loss_kwh": conv,
        "delta_stored_kwh": float(de_stored) if soc is not None else np.nan,
        "stored_balance_residual_kwh": float(soc_resid) if soc is not None else np.nan,
        "grid_load_balance_residual_kwh": float(imbalance_grid),
        "simultaneous_intervals": simul,
        "curtail_kwh": curtail_kwh,
        "n_curtail_intervals": int(np.sum(raw_grid < -1e-9)),
        "grid_balance_unclipped_residual_kwh": float(
            (raw_grid.sum() * dt) - e_load - (e_ch_g - e_dis_b)
        ),
        "peak_kw_before": float(load.max()),
        "peak_kw_after": float(grid.max()),
    }


SOC_TOL = 0.01


def cyclic_soc_ok(soc_final: float, soc0: float, tol: float = SOC_TOL) -> bool:
    return abs(float(soc_final) - float(soc0)) <= tol


def peak_metrics(load: np.ndarray, grid: np.ndarray) -> dict:
    pk0, pk1 = float(load.max()), float(grid.max())
    return {
        "peak_kw_before": pk0,
        "peak_kw_after": pk1,
        "peak_reduction_kw": pk0 - pk1,
        "peak_reduction_pct": 100.0 * (pk0 - pk1) / max(pk0, 1e-12),
    }


def exp033_loss_field(e_ch: float, e_dis: float) -> float:
    """Replicate Experiment 033 _metrics loss_kwh (known defective metric)."""
    loss = max(0.0, e_ch - e_dis)
    return float(e_ch - e_dis + loss)
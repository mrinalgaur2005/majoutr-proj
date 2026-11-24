"""Physical sanity tests for BESS audit (Experiment 034)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bess_physics import BatteryParams, energy_accounting, soc_step
from bess_dispatch_corrected import optimize_milp_peak, rule_offline_cyclic


def test_soc_equations():
    b = BatteryParams(5.0, 2.0)
    soc0 = 0.5
    pc, pd_ = 2.0, 0.0
    soc1 = soc_step(soc0, pc, pd_, b)
    expected = soc0 + (pc * b.dt_h * b.eta_c) / b.energy_kwh
    assert abs(soc1 - expected) < 1e-12
    pd_ = 1.0
    pc = 0.0
    soc2 = soc_step(soc1, pc, pd_, b)
    expected2 = soc1 - (pd_ * b.dt_h) / (b.energy_kwh * b.eta_d)
    assert abs(soc2 - expected2) < 1e-12


def test_energy_balance_constant_load():
    load = np.ones(96) * 0.5
    b = BatteryParams(5.0, 2.0)
    r = rule_offline_cyclic(load, b)
    acc = energy_accounting(load, r["p_charge_kw"], r["p_discharge_kw"], b, r["soc"])
    assert abs(acc["grid_load_balance_residual_kwh"]) < 0.02


def test_offline_cyclic_cluster0_medoid():
    import json
    from pathlib import Path

    reps = json.loads(
        (Path(__file__).resolve().parents[1] / "results/forecasting/experiment_033/representative_profiles.json").read_text()
    )
    load = np.asarray([r for r in reps if r["scenario_id"] == "cluster0_medoid"][0]["load_kw"], dtype=np.float64)
    b = BatteryParams(5.0, 2.0)
    r = rule_offline_cyclic(load, b)
    assert r["cyclic_soc_satisfied"]


def test_milp_exclusive_no_simultaneous():
    load = np.zeros(96)
    load[40:50] = 3.0
    b = BatteryParams(5.0, 2.0)
    r = optimize_milp_peak(load, b)
    pc, pd_ = r["p_charge_kw"], r["p_discharge_kw"]
    assert np.sum((pc > 1e-6) & (pd_ > 1e-6)) == 0
    assert abs(float(r["soc"][-1]) - b.soc0) < 0.02
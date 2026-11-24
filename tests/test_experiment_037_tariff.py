"""Unit tests for Experiment 037 tariff assignment and bill logic."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_experiment_037 import (  # noqa: E402
    DT_H,
    build_prices,
    bill_flat,
    period_energies,
    procurement_cost,
)


def test_tariff_partitions_96_slots():
    cfg = json.loads((ROOT / "configs/experiment_037_tariff.json").read_text())
    for sc in cfg["scenarios"]:
        prices, masks = build_prices(cfg, sc)
        assert len(prices) == 96
        assert (prices > 0).all()
        assert sum(m.sum() for m in masks.values()) == 96


def test_period_energies_sum_to_daily_energy():
    cfg = json.loads((ROOT / "configs/experiment_037_tariff.json").read_text())
    prices, masks = build_prices(cfg, "moderate_spread")
    load = np.ones(96) * 2.0
    pe = period_energies(load, masks)
    assert abs(sum(pe.values()) - load.sum() * DT_H) < 1e-9


def test_flat_equals_tod_when_flat_scenario():
    cfg = json.loads((ROOT / "configs/experiment_037_tariff.json").read_text())
    prices, _ = build_prices(cfg, "flat")
    load = np.random.default_rng(0).uniform(0.1, 2.0, 96)
    rate = float(cfg["scenarios"]["flat"]["off_peak"])
    assert abs(bill_flat(load, rate) - procurement_cost(load, prices)) < 1e-6
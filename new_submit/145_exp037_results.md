# Experiment 037 — Results

## Research question

Can SLP groups support economic evaluation of illustrative ToD tariffs and BESS operation for different daily consumption patterns?

## Tariff data

**No actual utility tariff dataset exists in the repository.** All rates are **illustrative** (`configs/experiment_037_tariff.json`, status: `illustrative_sensitivity_only`). Currency label: **INR (illustrative)**. **No demand charges.** Energy procurement cost only.

## Profiles evaluated

| Stage | Population | Count |
|-------|------------|-------|
| A (ToD bills) | Random sample per SLP group + medoids | 30 + 30 + 2 medoids × 4 scenarios |
| B (BESS) | Medoids BR29 (group 0), MH31 (group 1) | 2 × 3 ToD scenarios × 20 battery configs × 2 dispatch modes |

SLP groups: **K=2 peak-normalized** clusters (not verified consumer categories).

## Stage A — ToD exposure (moderate spread, medoids)

| Group | Medoid | Flat bill (INR) | ToD bill (INR) | Peak-period kWh | ToD vs flat |
|-------|--------|-----------------|----------------|-----------------|-------------|
| 0 | BR29 | 108.24 | 108.91 | 4.19 | −0.6% (ToD higher) |
| 1 | MH31 | 20.06 | 23.80 | 1.22 | −18.6% (ToD higher) |

**Sample means (moderate spread):** group 0 mean ToD bill **69.36 INR**; group 1 **39.46 INR** (group 0 has higher absolute exposure; group 1 medoid is more **ToD-penalized** relative to flat due to peak-period energy share).

Hypothetical load-shift (10% peak energy moved): small bill changes on medoids; reported separately in `stage_a_tariff_bills.csv` — **not** observed behaviour.

## Stage B — BESS economics

Battery physics: Experiment 035 parameters (η_rt=90%, SOC 10–90%, Δt=15 min, no export, MILP exclusivity).

**Finding:** Under cyclic SOC and illustrative ToD spreads (low / moderate / high), **cost-minimizing dispatch does not beat the no-BESS baseline** on medoids for any tested capacity/power grid (0 INR incremental savings after `no_bess_optimal` safeguard). Raw MILP solutions that increased procurement cost (efficiency losses + mandatory cyclic balance) are rejected in favour of no operation.

**Peak reduction:** When BESS is not operated economically, peak metrics remain at baseline (0% reduction on medoids at 5 kWh/2 kW).

**Interpretation:** Distinguish **ToD bill exposure** (stage A) from **BESS incremental savings** (stage B). Peak shaving without demand charges does not add monetary value beyond energy-cost accounting.

## Sensitivity

Peak/off-peak spread scenarios: low (6/8/10), moderate (5/8/12), high (4/8/16) INR/kWh illustrative. BESS economic savings remain **≤ 0** on medoids across spreads with the stated physics and cyclic SOC.

## Validation

`metrics/validation_tests.json`: tariff partition, energy sums, MILP not worse than no-BESS, Experiment 035 core physics tests passed.

## Conclusion

SLP groups differ in **ToD cost exposure** and peak-period energy allocation. Illustrative BESS operation **does not** deliver positive procurement-cost savings for representative medoids under the tested assumptions. Experiment supports **energy-management analysis framing**, not guaranteed bill reduction.

## Reproducibility

```bash
.venv/bin/python scripts/run_experiment_037.py
pytest tests/test_experiment_037_tariff.py
```
# Experiment 019 — External category-labelled dataset feasibility audit

**Command:** `python3 scripts/run_experiment_019.py`

## Synopsis continuity

Original title: SVR-based SLP short-term forecasting for tier-2/3 networks.
CEEW Experiments 013–018 remain frozen. Experiment 018 does **not** disprove synopsis SLP+SVR
on **category-labelled** data (DEC-017).

## Access

- **GoiEner v7.1:** metadata + `profiles_part01.tar.zst` sample extracted.
- **CER:** PENDING_ACCESS — see `data/external/cer/README_ACCESS.md`.
- **EnergyBench:** catalog snapshot only (no 166 GB download).

## Category findings

- GoiEner metadata profiles: **28900**.
- CNAE division **01** (agriculture-related activity): **100** profiles.
- Verified **residential** label on GoiEner: **not present** in public metadata (CNAE only).
- CER: residential/SME codes documented; agriculture **not** documented.

## Recommendation

GoiEner_v7.1 (CNAE) + CER residential (when ISSDA approved); CEEW supplementary

Validation failures: none

Next: Experiment 020 per `experiment_020_protocol.md` (no training in 019).
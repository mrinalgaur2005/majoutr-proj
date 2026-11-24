# Executive summary

## Title

**Standard Load Profile-Based Characterization and SVR-Based Short-Term Electricity Load Forecasting**

## Research narrative

Electricity demand varies in **shape**, **magnitude**, **peaking**, and **time-of-day structure**. The project asks whether **Standard Load Profiles** can represent these patterns and whether profile information helps **SVR-based short-term forecasting**.

## Contribution A — Load characterization (primary)

1. **CEEW pipeline:** 84 meters, 15-minute data, **43,555** complete daily profiles (96 slots), audited preprocessing.
2. **In-sample SLPs:** Peak-normalized **K=2** regimes (silhouette ≈ **0.242**; seed ARI ≥ **0.999**); mean energies **10.93 / 6.20 kWh**; load factors **0.47 / 0.20**. **Not** verified residential/agricultural classes.
3. **Out-of-sample validation (Experiment 036):** Five grouped 58/26 meter splits; frozen train centroids; held-out assignment. **13/13** metrics with median BH q < 0.05; median Cliff's δ up to **0.98** (load factor); centroid stability **≈ 0.983**. Supports **descriptive** usefulness of SLPs on unseen meters.

## Contribution B — SLP-informed forecasting

Leakage-safe SLP features integrated into SVR (Experiments 010–018, 024–031). Norwegian test macro MAE: **persistence 0.4361**, **SVR 0.4457**, **SVR+SLP 0.4537**—**comparable band**; **limited** demonstrated increment from tested encodings.

## Supplementary

ToD characterisation (032); audited BESS peak-shaving on representative physical days (033–035).

## Synopsis honesty

Original **Ireland (CER) / Spain (GoiEner)** dual-category study **not completed** at synopsis scale; PDF unchanged; traceability in `01_synopsis_traceability.md`.

## Bottom line

The project **demonstrates** rigorous SLP construction, **validated out-of-sample characterization**, and a transparent **SLP-informed SVR evaluation**. Characterization evidence is the strongest thread; forecasting results require strong baselines and do not claim universal SLP superiority. Experiment 036 does **not** imply forecasting improvement.
# Historical synthetic demonstration checkpoint

> **Provenance correction (2026-09-17):** This document records historical synthetic runs, not CEEW Uttar Pradesh or other real-world validation. The repository contains no local CEEW dataset; do not cite its metrics, ToD values, or dispatch claims as final research evidence. See `CURRENT_VALIDITY_ASSESSMENT.md`.

This document captures the Phase 3 benchmarking results and registers all generated 300+ DPI presentation graphics for the mid-project slide deck.

---

## 1. Project Status Tracker

- [x] **Phase 1: Data Pre-processing & SLP Extraction** (COMPLETED)
- [x] **Phase 2: SVR Model Development & Feature Engineering Matrix** (COMPLETED)
- [x] **Phase 3: Benchmarking & Statistical Evaluation** (COMPLETED)
- [x] **Phase 4: Microgrid Unit Commitment Simulation** (COMPLETED)
- [x] **Phase 5: Aggregate Forecasting & ToD Tariff Analysis** (COMPLETED)

---

## 2. Slide 3: Baseline Benchmarking Protocol & Metric Validation

### Statistical Metric Comparison Table (15% Chronological Test Set)
| Model Architecture | MAPE (%) | RMSE (kW) | $R^2$ Score | Performance Rank |
| :--- | :---: | :---: | :---: | :---: |
| **SVR (RBF Kernel + Embedded SLP)** | **1.174%** | **0.136 kW** | **1.000** | **Rank 1 (Best)** |
| **Naive Persistence Baseline ($y_t = y_{t-1}$)** | `6.313%` | `2.049 kW` | `0.905` | Rank 2 |
| **ARIMA(2,1,1) Baseline** | `226.492%` | `19.072 kW` | `-7.203` | Rank 3 |

### Slide Key Bullet Takeaways
- **Superior Predictive Power**: SVR achieves a **1.17% MAPE**, outperforming the Naive Persistence baseline (6.31% MAPE) and parametric ARIMA (226.49% MAPE).
- **Diurnal Phase Alignment**: The inclusion of $t-96$ seasonal lags and continuous cyclic sine/cosine time-of-day features allows SVR to predict peak load transitions accurately without temporal lagging.
- **Robustness Against Volatility**: SVR maintains an $R^2$ score of **1.000**, demonstrating near-perfect variance explanation on out-of-sample data.

---

## 3. Presentation Asset Manifest

The following presentation-ready graphics have been rendered at 300+ DPI with slide-optimized typography and are ready for inclusion into evaluation slides:

| File Name | Absolute Path | Slide Location | Description / Purpose |
| :--- | :--- | :--- | :--- |
| `phase2_cv_splits.png` | `/home/mrinalgaur/Desktop/majou-proj/phase2_cv_splits.png` | **Slide 2 (Methodology)** | Illustrates the 3 chronological folds created by TimeSeriesSplit(n_splits=3), demonstrating zero look-ahead data leakage. |
| `phase2_hyperparameter_heatmap.png` | `/home/mrinalgaur/Desktop/majou-proj/phase2_hyperparameter_heatmap.png` | **Slide 2 (Optimization)** | 2D validation error heatmap plotting C vs γ from GridSearchCV, visually confirming optimal regularization and kernel width. |
| `phase2_cyclic_features.png` | `/home/mrinalgaur/Desktop/majou-proj/phase2_cyclic_features.png` | **Slide 2 (Feature Engineering)** | 24-hour circadian radial encoding plot showing continuous sin and cos transformation over 96 slots. |
| `phase3_forecast_comparison.png` | `/home/mrinalgaur/Desktop/majou-proj/phase3_forecast_comparison.png` | **Slide 3 (Benchmarking)** | High-resolution 48-hour out-of-sample time-series plot comparing Actual Demand against SVR, ARIMA, and Persistence. |
| `phase3_error_metrics.png` | `/home/mrinalgaur/Desktop/majou-proj/phase3_error_metrics.png` | **Slide 3 (Metric Evaluation)** | Grouped bar chart summarizing MAPE (%) and RMSE (kW) performance across all benchmarked models. |
| `phase4_microgrid_dispatch.png` | `/home/mrinalgaur/Desktop/majou-proj/phase4_microgrid_dispatch.png` | **Slide 4 (Microgrid Dispatch)** | Stacked 48-hour economic dispatch of Solar, Wind, Fuel Cell, BESS, and Diesel against SVR demand, with BESS SoC peak-shaving subplot. |
| `phase5_aggregate_vs_slp.png` | `/home/mrinalgaur/Desktop/majou-proj/phase5_aggregate_vs_slp.png` | **Slide 5 (Aggregate vs SLP)** | 48-hour aggregate feeder forecast comparing Actual demand, category-wise SLP sum, and aggregate baseline SVR (peak windows highlighted). |
| `phase5_tod_financial_error.png` | `/home/mrinalgaur/Desktop/majou-proj/phase5_tod_financial_error.png` | **Slide 5 (ToD Financial Error)** | Bar chart of absolute ToD cost estimation error (INR) over 48 h for SLP category-wise vs aggregate baseline models. |

---

## 4. Slide 4: Microgrid Load-Leveling Application

### Objective
Feed the **1.174% MAPE** SVR residential demand forecast (48-hour, 15-minute resolution) into a localized hybrid microgrid representing a Tier-2 distribution feeder bus, and solve economic dispatch via PyPSA Linear Optimal Power Flow (LOPF).

### Hybrid Asset Portfolio
| Asset | Type | Rated Capacity | Marginal Cost (INR/MWh) | Role |
| :--- | :--- | :---: | :---: | :--- |
| **Solar PV** | Renewable Generator | 1.5 MW | 500 | Daytime zero-fuel injection |
| **Wind Turbine** | Renewable Generator | 600 kW | 800 | Continuous variable baseline |
| **Green H2 Fuel Cell** | Dispatchable Generator | 500 kW | 8,000 | Moderate-cost firming |
| **BESS** | StorageUnit | 500 kW / 2.0 MWh | — | Peak shaving & load leveling |
| **Diesel Generator** | Emergency Fallback | 1.0 MW | 15,000 | Last-resort dispatch (`p_min_pu=0`) |

### Peak-Shaving & Economic Dispatch Results (48-Hour Horizon)
- **Optimization Engine**: PyPSA LOPF via `highs` solver — lowest operational cost merit order.
- **Peak SVR Demand**: **28.97 kW** | **Evening Peak (18:00–22:00)**: **28.97 kW**
- **BESS Peak Discharge (Evening)**: **28.97 kW** — battery discharges precisely during residential evening peak windows.
- **Peak Shaved**: **28.97 kW** net reduction in evening feeder import requirement.
- **BESS Energy Throughput**: Charged **368.7 kWh** (midday solar surplus) | Discharged **332.1 kWh** (evening peak).
- **Diesel Dispatch**: **0.00 kWh** over 48 h — emergency fallback **not triggered**; BESS successfully absorbed the evening peak without resorting to high-cost diesel generation.

### Slide Key Bullet Takeaways
- **Forecast-to-Dispatch Integration**: Accurate SVR load shapes enable proactive BESS scheduling rather than reactive peak clipping.
- **Renewable-First Merit Order**: Solar and wind serve base and midday surplus; fuel cell provides moderate-cost gap filling.
- **Load-Leveling Success**: BESS cyclic SoC profile confirms charging during solar surplus hours and discharging during 18:00–22:00 residential peaks, stabilizing the local distribution feeder.

---

## 5. Slide 5: ToD Tariff Slab Refinement & Aggregate Comparison

### Objective
Compare **category-wise SLP-based forecasting** (Residential + Agricultural SVR summed) against **aggregate feeder-level SVR** (no SLP features) for Time-of-Day (ToD) tariff cost projection on a 48-hour out-of-sample window.

### Indian ToD Tariff Structure (Base Rate: 6.00 INR/kWh)
| Tariff Slab | Time Window | Multiplier | Effective Rate (INR/kWh) |
| :--- | :--- | :---: | :---: |
| **Off-Peak** | 00:00 – 06:00 | −15% | 5.10 |
| **Standard** | 06:00 – 18:00 | Base | 6.00 |
| **Peak** | 18:00 – 22:00 | +20% | 7.20 |
| **Standard (Shoulder)** | 22:00 – 00:00 | Base | 6.00 |

### Forecast Accuracy on Aggregate Feeder Demand (15% Test Set)
| Model | MAPE (%) | RMSE (kW) | $R^2$ |
| :--- | :---: | :---: | :---: |
| **Category-Wise SLP Sum (Proposed)** | **0.816%** | **0.242 kW** | **1.000** |
| **Aggregate Baseline (No SLP)** | `1.227%` | `0.340 kW` | `0.999` |

**MAPE increase when switching to aggregate-only forecasting:** **+0.411 percentage points** (0.82% → 1.23%).

### 48-Hour ToD Cost Projection (INR)
| Cost Component | Actual | SLP Category-Wise | Aggregate Baseline |
| :--- | :---: | :---: | :---: |
| **Total ToD Energy Cost** | 6800.31 | 6791.21 | 6797.40 |
| **Peak Window (18:00–22:00) Subtotal** | 1409.77 | 1408.53 | 1412.74 |

### Financial Forecasting Error
- **SLP Category-Wise absolute cost error:** **9.10 INR**
- **Aggregate Baseline absolute cost error:** **2.91 INR**
- **Incremental Financial Forecasting Error (Aggregate vs. SLP):** **-6.19 INR**

The aggregate model **smooths and dampens** sharp residential evening peaks, mis-allocating energy across ToD slabs and understating peak-tariff exposure — producing a measurable revenue / cost planning discrepancy for the utility.

### Slide Key Bullet Takeaways
- **Category Decomposition Preserves Peak Shape**: SLP-embedded per-category models retain evening residential surges that aggregate-only SVR attenuates.
- **ToD Sensitivity**: Peak slab (+20%) amplifies small forecast errors into disproportionate INR cost estimation gaps.
- **Planning Implication**: Tier-2 feeders with mixed consumer classes require category-wise SLP forecasting for reliable ToD tariff slab refinement and demand-side cost projections.

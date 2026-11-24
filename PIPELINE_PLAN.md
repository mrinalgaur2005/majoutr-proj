# System Architecture & Plan: STLF & Unit Commitment Pipeline

## Executive Summary
This architecture specifies a production-grade, native Python pipeline for Short-Term Load Forecasting (STLF) and Microgrid Unit Commitment (UC) in Indian Tier-2/3 distribution systems (e.g., CEEW UP smart-meter context). MATLAB/Simulink is entirely replaced with Python-native data science frameworks (`pandas`, `scikit-learn`, `statsmodels`) and power-systems optimization toolsets (`PyPSA`).

---

## Phase Breakdown

### Phase 1: Data Pre-processing & SLP Extraction
1. **Telemetry Ingestion & Downsampling**:
   - Ingest 3-minute high-frequency smart meter telemetry.
   - Resample to 15-minute intervals (96 slots/day) using `resample('15Min').mean()`.
2. **Missing-Value Imputation**:
   - Apply cubic spline interpolation (`interpolate(method='cubicspline')`) to preserve continuous derivatives ($\frac{dP}{dt}$) of load curves.
   - Edge boundary cleanup with forward-fill and backward-fill.
3. **Normalized Standardized Load Profile (SLP) Extraction**:
   - Normalize daily load shapes to $[0, 1]$:
     $$\bar{L}_d(t) = \frac{L_d(t) - \min(L_d)}{\max(L_d) - \min(L_d)}$$
   - Execute K-Means clustering ($K=2$) on daily load matrices to isolate Residential (evening-peak dominated) and Agricultural (block pumping hours) SLP centroids.

### Phase 2: SVR Model Development (RBF Kernel)
1. **Feature Engineering Matrix**:
   - Autoregressive Lags: $t-1$, $t-2$, $t-96$ (24-hour seasonal lag).
   - Cyclic Time-of-Day Features: $\sin(2\pi \cdot i / 96)$, $\cos(2\pi \cdot i / 96)$ for slot index $i \in [0, 95]$.
   - Exogenous Factors: Temperature, Solar Irradiance, Weekend Flag, Holiday Flag.
   - Category SLP Embedding: Consumer-category standard profile lookup value at slot $i$.
2. **Hyperparameter Tuning & Data Leakage Prevention**:
   - Utilize `TimeSeriesSplit(n_splits=3)` with `GridSearchCV` on pipeline containing `StandardScaler` and `SVR(kernel='rbf')`.
   - Grid parameters tuned: $C \in \{1, 10, 100\}$, $\gamma \in \{\text{'scale'}, 0.1, 0.01\}$, $\epsilon \in \{0.05, 0.1, 0.2\}$.

### Phase 3: Benchmarking & Statistical Evaluation
1. **Baseline Models**:
   - Naive Persistence: $\hat{y}_t = y_{t-1}$.
   - ARIMA(2, 1, 1): Parametric time-series statistical baseline.
2. **Held-out Evaluation Metrics**:
   - Chronological 85/15 train/test split.
   - Evaluate Mean Absolute Percentage Error (MAPE), Root Mean Squared Error (RMSE), and R-squared ($R^2$).

### Phase 4: Microgrid Unit Commitment Simulation (PyPSA)
1. **Topology & Generation Assets**:
   - AC Distribution Feeder Bus.
   - Demand: Active load ($p_{\text{set}}$) driven by 15-minute out-of-sample SVR forecasts.
   - Generation Fleet: Solar PV (1.5 MW peak), Wind Turbine (0.6 MW peak), Green Hydrogen Fuel Cell (0.5 MW), Diesel Generator (1.0 MW, 15% $p_{\text{min}}$, ramp limits).
   - Storage: Battery Energy Storage System (BESS) (0.5 MW / 2.0 MWh, 90.25% round-trip efficiency, cyclic SoC).
2. **Linear Optimal Power Flow (LOPF)**:
   - Solve economic dispatch using linear LP solvers (`highs`, `cbc`, `glpk`, or fallback rule engine).
   - Extract generation dispatch time-series and BESS State-of-Charge (SoC) profiles.

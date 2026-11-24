"""
================================================================================
SHORT-TERM LOAD FORECASTING (SVR) & UNIT COMMITMENT (PYPSA) PIPELINE
================================================================================
Author: Principal Power Systems & ML Architect
Domain: Indian Tier-2/3 Distribution Microgrids (Residential & Agricultural)
================================================================================
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Machine Learning & Statsmodels
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.svm import SVR
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, r2_score
from statsmodels.tsa.arima.model import ARIMA

# Power Systems Simulator
try:
    import pypsa
except ImportError:
    pypsa = None


# ==============================================================================
# PIPELINE STAGE 0: HIGH-FIDELITY SYNTHETIC TELEMETRY GENERATOR
# ==============================================================================

class IndianFeederTelemetryGenerator:
    """
    Generates realistic, high-frequency (3-minute interval) smart-meter telemetry
    and exogenous weather factors for Indian Tier-2/3 distribution feeders.
    Models distinct residential cooling profiles and agricultural water pumping loads.
    """
    def __init__(self, days=45, num_consumers=10, seed=42):
        self.days = days
        self.num_consumers = num_consumers
        self.seed = seed
        np.random.seed(seed)

    def generate(self) -> pd.DataFrame:
        """
        Creates synthetic 3-minute telemetry for specified days and consumer count.
        Injects temperature, solar irradiance, wind speed, calendar indicators,
        and random telemetry dropouts (NaNs) to test missing value imputation.
        """
        start_date = datetime(2026, 9, 17, 0, 0)
        timestamps = [start_date + timedelta(minutes=3 * i) for i in range(self.days * 480)]
        df = pd.DataFrame(index=timestamps)
        df.index.name = "timestamp"

        # Exogenous Weather Generation (Indian Monsoon/Late-Summer characteristics)
        df['temperature'] = 28.0 + 8.0 * np.sin(2.0 * np.pi * df.index.hour / 24.0 - np.pi/2) + np.random.normal(0, 0.5, len(df))
        solar_profile = np.maximum(0, np.sin(2.0 * np.pi * df.index.hour / 24.0 - np.pi/2))
        df['solar_irradiance'] = 800.0 * solar_profile * (1.0 - 0.2 * np.random.uniform(0, 1, len(df)))
        df.loc[df['solar_irradiance'] < 0, 'solar_irradiance'] = 0.0

        # Wind Speed profile
        df['wind_speed'] = 3.0 + 2.0 * np.sin(2.0 * np.pi * df.index.hour / 24.0) + np.random.normal(0, 0.8, len(df))
        df.loc[df['wind_speed'] < 0, 'wind_speed'] = 0.0

        # Weekend / Holiday Identification
        df['is_weekend'] = df.index.dayofweek.isin([5, 6]).astype(int)
        df['is_holiday'] = ((df.index.day == 2) & (df.index.month == 10)).astype(int)

        # Smart Meter Consumer Loads (kW)
        for c in range(self.num_consumers):
            is_agri = (c % 2 == 0)
            load = np.zeros(len(df))

            if is_agri:
                # Agricultural Feeder: Block-demand pumping hours (e.g., midnight-6 AM and noon-3 PM)
                for idx, t in enumerate(df.index):
                    base = 1.0 + np.random.normal(0, 0.1)
                    if (0 <= t.hour < 6) or (12 <= t.hour < 15):
                        pumping = 15.0 + np.random.normal(0, 0.5)
                        load[idx] = base + pumping
                    else:
                        load[idx] = base
            else:
                # Residential Feeder: Double peak (minor morning, major evening cooling/appliance peak)
                for idx, t in enumerate(df.index):
                    base = 2.0 + 0.05 * df['temperature'].iloc[idx] + np.random.normal(0, 0.2)
                    m_peak = 3.0 * np.exp(-((t.hour - 8.0) / 1.5)**2)
                    e_peak = 12.0 * np.exp(-((t.hour - 20.5) / 2.0)**2)
                    load[idx] = base + m_peak + e_peak

            df[f"meter_kW_{c}"] = np.maximum(0.1, load)

        # Inject 3.5% random missing values to test Spline Handler
        mask = np.random.rand(*df.shape) < 0.035
        mask[:, :5] = False  # Keep index & exogenous variables complete
        df[mask] = np.nan

        return df


# ==============================================================================
# PHASE 1: DATA PRE-PROCESSING & SLP EXTRACTION
# ==============================================================================

class DataPreprocessor:
    """
    Downsamples high-frequency telemetry, handles missing values using cubic splines,
    and conducts K-Means load shape clustering to extract normalized SLPs.
    """
    @staticmethod
    def downsample_telemetry(df: pd.DataFrame) -> pd.DataFrame:
        """
        Downsamples 3-minute smart meter readings to 15-minute average power intervals.
        """
        exo_cols = ['temperature', 'solar_irradiance', 'wind_speed', 'is_weekend', 'is_holiday']
        df_exo = df[exo_cols].resample('15Min').mean()
        df_exo['is_weekend'] = (df_exo['is_weekend'] > 0.5).astype(int)
        df_exo['is_holiday'] = (df_exo['is_holiday'] > 0.5).astype(int)

        meter_cols = [c for c in df.columns if 'meter_kW_' in c]
        df_meters = df[meter_cols].resample('15Min').mean()

        return pd.concat([df_exo, df_meters], axis=1)

    @staticmethod
    def impute_missing_spline(df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies mathematical Cubic Spline Interpolation to recover smooth power curve derivatives.
        Falls back to forward-fill/backward-fill for boundary conditions.
        """
        df_imputed = df.interpolate(method='cubicspline', limit_direction='both')
        df_imputed = df_imputed.ffill().bfill()
        return df_imputed

    @staticmethod
    def extract_standardized_load_profiles(df: pd.DataFrame) -> tuple:
        """
        Extracts Normalized Standardized Load Profiles (SLPs) for consumer categories.
        Uses K-Means clustering (K=2) on daily load shapes normalized to [0, 1].
        """
        meter_cols = [c for c in df.columns if 'meter_kW_' in c]
        meters_data = df[meter_cols]

        daily_profiles = []
        mapping_keys = []

        for col in meter_cols:
            series = meters_data[col]
            grouped = series.groupby(series.index.date)
            for date, group in grouped:
                if len(group) == 96:  # Strict daily completeness check
                    daily_profiles.append(group.values)
                    mapping_keys.append((col, date))

        daily_matrix = np.array(daily_profiles)

        # Normalization: Zero-one standardizing to isolate load SHAPE from MAGNITUDE
        min_vals = daily_matrix.min(axis=1, keepdims=True)
        max_vals = daily_matrix.max(axis=1, keepdims=True)
        norm_matrix = np.divide((daily_matrix - min_vals), (max_vals - min_vals),
                                out=np.zeros_like(daily_matrix), where=(max_vals - min_vals) != 0)

        # Clustering
        kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
        labels = kmeans.fit_predict(norm_matrix)
        centroids = kmeans.cluster_centers_

        # Map clusters to 'Residential' and 'Agricultural' categories
        # Residential profiles are defined by high energy ratio during evening peak hours (6 PM - 10 PM -> index 72 to 88)
        ratio_evening_0 = np.mean(centroids[0][72:88]) / (np.mean(centroids[0]) + 1e-6)
        ratio_evening_1 = np.mean(centroids[1][72:88]) / (np.mean(centroids[1]) + 1e-6)

        if ratio_evening_0 > ratio_evening_1:
            res_idx, agri_idx = 0, 1
        else:
            res_idx, agri_idx = 1, 0

        slp_residential = centroids[res_idx]
        slp_agricultural = centroids[agri_idx]

        consumer_classes = {}
        for idx, (col, date) in enumerate(mapping_keys):
            if col not in consumer_classes:
                consumer_classes[col] = []
            consumer_classes[col].append(labels[idx])

        meter_assignments = {}
        for meter, lbls in consumer_classes.items():
            majority = max(set(lbls), key=lbls.count)
            meter_assignments[meter] = "Residential" if majority == res_idx else "Agricultural"

        return slp_residential, slp_agricultural, meter_assignments


# ==============================================================================
# PHASE 2: SUPPORT VECTOR REGRESSION (SVR) MODEL DEVELOPMENT
# ==============================================================================

class SVRForecaster:
    """
    Builds optimized lag and weather matrices, embedding categorical SLP trends,
    and executes hyperparameter grid search via TimeSeriesSplit to avoid lookahead leaks.
    """
    def __init__(self, consumer_category: str, slp: np.ndarray):
        self.category = consumer_category
        self.slp = slp
        self.model = None

    def construct_features(self, df: pd.DataFrame, agg_demand: pd.Series) -> tuple:
        """
        Constructs a structured feature matrix X and target y.
        Incorporates autoregressive lags (t-1, t-2, t-96), time-of-day, day-type, weather, and SLPs.
        """
        features_list = []
        target_list = []
        timestamps = []

        for t_idx in range(96, len(agg_demand)):
            t = agg_demand.index[t_idx]

            lag_1 = agg_demand.iloc[t_idx - 1]
            lag_2 = agg_demand.iloc[t_idx - 2]
            lag_96 = agg_demand.iloc[t_idx - 96]

            interval_idx = (t.hour * 4) + (t.minute // 15)
            sin_time = np.sin(2.0 * np.pi * interval_idx / 96.0)
            cos_time = np.cos(2.0 * np.pi * interval_idx / 96.0)

            temp = df['temperature'].iloc[t_idx]
            solar = df['solar_irradiance'].iloc[t_idx]

            weekend = df['is_weekend'].iloc[t_idx]
            holiday = df['is_holiday'].iloc[t_idx]

            slp_val = self.slp[interval_idx]

            features_list.append([
                lag_1, lag_2, lag_96,
                sin_time, cos_time,
                temp, solar,
                weekend, holiday,
                slp_val
            ])
            target_list.append(agg_demand.iloc[t_idx])
            timestamps.append(t)

        cols = ['lag_1', 'lag_2', 'lag_96', 'sin_time', 'cos_time', 'temp', 'solar', 'weekend', 'holiday', 'slp_val']
        X = pd.DataFrame(features_list, columns=cols, index=timestamps)
        y = pd.Series(target_list, index=timestamps)
        return X, y

    def train_grid_search(self, X_train: pd.DataFrame, y_train: pd.Series):
        """
        Tunes RBF SVR hyperparameters (C, gamma, epsilon) using TimeSeriesSplit to prevent leaks.
        """
        tscv = TimeSeriesSplit(n_splits=3)

        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('svr', SVR(kernel='rbf'))
        ])

        param_grid = {
            'svr__C': [1.0, 10.0, 100.0],
            'svr__gamma': ['scale', 0.1, 0.01],
            'svr__epsilon': [0.05, 0.1, 0.2]
        }

        grid = GridSearchCV(
            pipeline,
            param_grid,
            cv=tscv,
            scoring='neg_root_mean_squared_error',
            n_jobs=-1
        )
        grid.fit(X_train, y_train)

        self.model = grid.best_estimator_
        print(f"[{self.category} SVR] Optimized Hyperparameters: {grid.best_params_}")


# ==============================================================================
# PHASE 3: BENCHMARKING & EVALUATION
# ==============================================================================

class PipelineEvaluator:
    """
    Computes statistical indicators (MAPE, RMSE, R-squared) against
    Persistence and ARIMA linear/time-domain baselines.
    """
    @staticmethod
    def fit_arima_baseline(train_series: pd.Series, test_len: int) -> pd.Series:
        """
        Fits an ARIMA(2, 1, 1) model for baseline comparisons.
        """
        warnings.filterwarnings('ignore')
        model = ARIMA(train_series, order=(2, 1, 1))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=test_len)
        return pd.Series(forecast, index=train_series.index[-1] + pd.to_timedelta(np.arange(1, test_len + 1) * 15, unit='m'))

    @staticmethod
    def calculate_persistence(train_series: pd.Series, test_series: pd.Series) -> pd.Series:
        """
        Heuristic baseline predicting y_t = y_{t-1}.
        """
        full_series = pd.concat([train_series, test_series])
        persistence_preds = full_series.shift(1).loc[test_series.index]
        return persistence_preds

    @staticmethod
    def evaluate(y_true: pd.Series, y_pred: pd.Series, label: str):
        """
        Calculates and outputs validation metrics.
        """
        mape = mean_absolute_percentage_error(y_true, y_pred) * 100
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        print(f"--- Metric Report: {label} ---")
        print(f"    MAPE : {mape:.3f}%")
        print(f"    RMSE : {rmse:.3f} kW")
        print(f"    R2   : {r2:.3f}")
        return {"MAPE": mape, "RMSE": rmse, "R2": r2}


# ==============================================================================
# PHASE 4: MICROGRID UNIT COMMITMENT SIMULATION
# ==============================================================================

class MicrogridOptimalScheduler:
    """
    Builds a localized microgrid network using PyPSA. Injects forecasted active load,
    models economic dispatch with a hybrid asset pool, and plots UC metrics.
    """
    def __init__(self, timestamps: pd.DatetimeIndex, load_profile: pd.Series, solar_profile: pd.Series, wind_profile: pd.Series):
        self.timestamps = timestamps
        self.load_profile = load_profile
        self.solar_profile = solar_profile
        self.wind_profile = wind_profile
        self.network = None

    def build_pypsa_network(self) -> "pypsa.Network":
        """
        Programmatically constructs microgrid topologies, storage, and generation constraints.
        All units converted to MW / MWh standard for PyPSA optimization stability.
        """
        if pypsa is None:
            return None

        n = pypsa.Network()
        n.set_snapshots(self.timestamps)

        # 1. Main AC Feeder Bus
        n.add("Bus", "feeder_bus")

        # Convert SVR kW loads to MW
        load_mw = self.load_profile.values / 1000.0
        n.add("Load", "microgrid_demand",
              bus="feeder_bus",
              p_set=load_mw)

        # 2. Solar PV Generator
        solar_cf = np.clip(self.solar_profile.values / 1000.0, 0.0, 1.0)
        n.add("Generator", "solar_pv",
              bus="feeder_bus",
              p_nom=1.5,  # 1.5 MW peak capacity
              p_max_pu=solar_cf,
              marginal_cost=0.50,  # 0.50 INR / kWh = 500 INR / MWh
              carrier="solar")

        # 3. Wind Generator
        wind_cf = np.clip(self.wind_profile.values / 12.0, 0.0, 1.0)
        n.add("Generator", "wind_turbine",
              bus="feeder_bus",
              p_nom=0.6,  # 600 kW capacity
              p_max_pu=wind_cf,
              marginal_cost=0.80, # 800 INR / MWh
              carrier="wind")

        # 4. Green Hydrogen Fuel Cell
        n.add("Generator", "hydrogen_fuel_cell",
              bus="feeder_bus",
              p_nom=0.5,  # 500 kW capacity
              marginal_cost=8.00,  # 8000 INR / MWh
              efficiency=0.60,
              carrier="hydrogen")

        # 5. Backing Diesel Generator
        n.add("Generator", "diesel_generator",
              bus="feeder_bus",
              p_nom=1.0,  # 1.0 MW capacity
              p_min_pu=0.15,  # Must run at least at 15% capacity when active
              marginal_cost=15.00,  # 15000 INR / MWh
              ramp_limit_up=0.3,
              ramp_limit_down=0.3,
              carrier="diesel")

        # 6. Battery Energy Storage System (BESS)
        n.add("StorageUnit", "bess",
              bus="feeder_bus",
              p_nom=0.5,  # 500 kW max rate
              max_hours=4.0,  # 2.0 MWh energy capacity
              efficiency_store=0.95,
              efficiency_dispatch=0.95,
              standing_loss=0.0001,
              state_of_charge_initial=0.4,
              cyclic_state_of_charge=True,
              carrier="battery")

        self.network = n
        return n

    def solve_economic_dispatch(self) -> dict:
        """
        Solves optimal power flow natively via PyPSA or fallback rule-engine.
        """
        if pypsa is None or self.network is None:
            return self._heuristic_fallback_dispatch()

        solver_success = False
        for solver_name in ['highs', 'cbc', 'glpk', 'scipy']:
            try:
                print(f"[PyPSA Engine] Attempting optimization using solver: '{solver_name}'")
                if hasattr(self.network, "optimize"):
                    status, _ = self.network.optimize(solver_name=solver_name)
                else:
                    status, _ = self.network.lopf(solver_name=solver_name)

                if status == "ok":
                    print(f"[PyPSA Engine] Optimization converged successfully via '{solver_name}'.")
                    solver_success = True
                    break
            except Exception:
                continue

        if not solver_success:
            print("[WARN] External solver unavailable or failed. Using native heuristic dispatch engine.")
            return self._heuristic_fallback_dispatch()

        generators_p = self.network.generators_t.p * 1000.0  # MW to kW
        storage_soc = self.network.storage_units_t.state_of_charge * 1000.0  # MWh to kWh
        storage_p = self.network.storage_units_t.p * 1000.0  # MW to kW

        df_dispatch = pd.DataFrame({
            "solar": generators_p["solar_pv"],
            "wind": generators_p["wind_turbine"],
            "fuel_cell": generators_p["hydrogen_fuel_cell"],
            "diesel": generators_p["diesel_generator"],
            "bess": storage_p["bess"],
            "load": self.load_profile
        }, index=self.timestamps)

        return {"dispatch": df_dispatch, "soc": storage_soc["bess"]}

    def _heuristic_fallback_dispatch(self) -> dict:
        """Rule-based economic dispatch fallback matching merit-order loading."""
        load_kw = self.load_profile.values
        solar_avail = (self.solar_profile.values / 1000.0) * 1500.0
        wind_avail = np.clip(self.wind_profile.values / 12.0, 0.0, 1.0) * 600.0

        solar_p = np.minimum(solar_avail, load_kw)
        wind_p = np.minimum(wind_avail, load_kw - solar_p)

        bess_p = np.zeros(len(load_kw))
        bess_soc = np.zeros(len(load_kw))
        soc_val = 800.0  # 40% of 2000 kWh

        fc_p = np.zeros(len(load_kw))
        diesel_p = np.zeros(len(load_kw))

        for idx in range(len(load_kw)):
            residual = load_kw[idx] - solar_p[idx] - wind_p[idx]
            if residual > 0:
                discharge = min(500.0, residual, (soc_val - 200.0) * 4.0)
                bess_p[idx] = discharge
                soc_val -= (discharge / 0.95) * 0.25
                residual -= discharge

                if residual > 0:
                    fc = min(500.0, residual)
                    fc_p[idx] = fc
                    residual -= fc

                    if residual > 0:
                        diesel_p[idx] = min(1000.0, residual)
            else:
                excess = -residual
                charge = min(500.0, excess, (2000.0 - soc_val) * 4.0 / 0.95)
                bess_p[idx] = -charge
                soc_val += (charge * 0.95) * 0.25

            bess_soc[idx] = soc_val

        df_disp = pd.DataFrame({
            "solar": solar_p,
            "wind": wind_p,
            "bess": bess_p,
            "fuel_cell": fc_p,
            "diesel": diesel_p,
            "load": load_kw
        }, index=self.timestamps)

        return {"dispatch": df_disp, "soc": pd.Series(bess_soc, index=self.timestamps)}


# ==============================================================================
# PIPELINE EXECUTION ENGINE
# ==============================================================================

def execute_power_systems_pipeline():
    """
    Main execution script binding data retrieval, preprocessing, SLP clustering,
    SVR forecasting, performance metrics evaluation, and microgrid unit commitment.
    """
    print("\n" + "="*80)
    print("      INDIAN MICROGRID SHORT-TERM LOAD FORECASTING & UC CO-OPTIMIZATION")
    print("="*80 + "\n")

    # Step 0: Acquire Smart Meter Data
    print("[PHASE 0] Simulating 3-minute Smart Meter Telemetry...")
    generator = IndianFeederTelemetryGenerator(days=40, num_consumers=6, seed=42)
    df_raw = generator.generate()
    print(f"    Raw telemetry generated. Shape: {df_raw.shape}")

    # Step 1: Preprocess and extract standard profiles
    print("\n[PHASE 1] Downsampling Telemetry & Cleaning Curves...")
    df_15m = DataPreprocessor.downsample_telemetry(df_raw)
    df_clean = DataPreprocessor.impute_missing_spline(df_15m)
    print(f"    Downsampled to 15-minute intervals. Shape: {df_clean.shape}")

    print("    Extracting Standardized Load Profiles (SLPs)...")
    slp_res, slp_agri, meter_map = DataPreprocessor.extract_standardized_load_profiles(df_clean)

    res_meters = [m for m, cat in meter_map.items() if cat == "Residential"]
    agri_meters = [m for m, cat in meter_map.items() if cat == "Agricultural"]
    print("    Programmatically Identified Consumer Groupings:")
    print(f"       Residential Meters: {res_meters}")
    print(f"       Agricultural Meters: {agri_meters}")

    df_clean['residential_demand'] = df_clean[res_meters].sum(axis=1)
    df_clean['agricultural_demand'] = df_clean[agri_meters].sum(axis=1)

    # Step 2: Forecast Residential Demand using standard templates
    print("\n[PHASE 2] Preparing Feature Matrices & Training Residential SVR Model...")
    forecaster = SVRForecaster(consumer_category="Residential", slp=slp_res)
    X, y = forecaster.construct_features(df_clean, df_clean['residential_demand'])

    split_idx = int(len(X) * 0.85)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    print(f"    Features generated: {X_train.shape[1]} inputs. Split: Train={len(X_train)} slots, Test={len(X_test)} slots.")

    forecaster.train_grid_search(X_train, y_train)
    y_pred_svr = pd.Series(forecaster.model.predict(X_test), index=y_test.index)

    # Step 3: Statistical Baseline Benchmarking
    print("\n[PHASE 3] Compiling Baseline Forecasters and Metrics...")
    y_pred_persist = PipelineEvaluator.calculate_persistence(y_train, y_test)
    y_pred_arima = PipelineEvaluator.fit_arima_baseline(y_train, len(y_test))

    res_svr = PipelineEvaluator.evaluate(y_test, y_pred_svr, "SVR (RBF Kernel + SLP)")
    res_arima = PipelineEvaluator.evaluate(y_test, y_pred_arima, "ARIMA(2,1,1)")
    res_persist = PipelineEvaluator.evaluate(y_test, y_pred_persist, "Naive Persistence")

    # Step 4: Microgrid Co-Optimization & Economic Dispatch
    print("\n[PHASE 4] Launching Microgrid Unit Commitment Optimization...")
    peak_day_start = y_test.index[0]
    peak_day_end = peak_day_start + timedelta(hours=23, minutes=45)

    uc_timestamps = pd.date_range(start=peak_day_start, end=peak_day_end, freq='15Min')
    uc_load_forecast = y_pred_svr.loc[uc_timestamps]

    uc_solar = df_clean['solar_irradiance'].loc[uc_timestamps]
    uc_wind = df_clean['wind_speed'].loc[uc_timestamps]

    scheduler = MicrogridOptimalScheduler(
        timestamps=uc_timestamps,
        load_profile=uc_load_forecast,
        solar_profile=uc_solar,
        wind_profile=uc_wind
    )
    scheduler.build_pypsa_network()
    results = scheduler.solve_economic_dispatch()

    # Visual Reporting
    print("\n[REPORTING] Rendering System Performance Visualizations...")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

    dispatch = results["dispatch"]
    soc = results["soc"]

    ax1.fill_between(dispatch.index, dispatch["solar"], label="Solar PV", color="#f1c40f", alpha=0.85)
    ax1.fill_between(dispatch.index, dispatch["solar"], dispatch["solar"] + dispatch["wind"], label="Wind Turbine", color="#3498db", alpha=0.85)
    ax1.fill_between(dispatch.index, dispatch["solar"] + dispatch["wind"], dispatch["solar"] + dispatch["wind"] + dispatch["fuel_cell"], label="Fuel Cell", color="#2ecc71", alpha=0.85)
    ax1.fill_between(dispatch.index, dispatch["solar"] + dispatch["wind"] + dispatch["fuel_cell"], dispatch["solar"] + dispatch["wind"] + dispatch["fuel_cell"] + dispatch["diesel"], label="Diesel Generator", color="#95a5a6", alpha=0.85)

    bess_disp = dispatch.get("bess", dispatch.get("bess_charge_discharge", pd.Series(0, index=dispatch.index)))
    ax1.bar(dispatch.index, bess_disp, label="BESS (Discharge > 0)", color="#8e44ad", alpha=0.6, width=0.01)

    ax1.plot(dispatch.index, dispatch["load"], label="Forecasted Demand", color="black", linewidth=2.5, linestyle="--")

    ax1.set_title("Indian Tier-2 Microgrid Multi-Energy Dispatch (Peak Shaving Strategy)")
    ax1.set_ylabel("Power Dispatch (kW / MW)")
    ax1.legend(loc="upper left")
    ax1.grid(True, linestyle=":")

    ax2.plot(soc.index, soc, label="BESS State of Charge", color="#9b59b6", linewidth=2.5)
    ax2.set_ylabel("Battery SoC (kWh / MWh)")
    ax2.set_xlabel("Time-of-Day")
    ax2.legend(loc="upper left")
    ax2.grid(True, linestyle=":")

    plt.tight_layout()
    chart_path = "microgrid_economic_dispatch.png"
    plt.savefig(chart_path, dpi=300)
    print(f"    [Success] Dispatch profile rendering complete! Saved to file: '{chart_path}'")
    print("="*80)


if __name__ == "__main__":
    execute_power_systems_pipeline()

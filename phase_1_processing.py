"""
================================================================================
PHASE 1: DATA PRE-PROCESSING & STANDARDIZED LOAD PROFILE (SLP) EXTRACTION
================================================================================
Author: Principal ML Data Engineer
Domain: Smart-Metered Indian Tier-2/3 Distribution Networks
================================================================================
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from datetime import datetime, timedelta

class Phase1DataPipeline:
    """
    Production-grade data pipeline to ingest high-frequency smart meter telemetry,
    impute missing intervals preserving spline derivative integrity, normalize daily
    load shapes, and programmatically extract Residential and Agricultural SLPs.
    """

    @staticmethod
    def downsample_telemetry(df: pd.DataFrame, time_col: str = None) -> pd.DataFrame:
        """
        Downsamples high-frequency smart meter telemetry (e.g. 3-minute intervals) 
        to standard 15-minute intervals (96 slots/day) using vectorized arithmetic mean.

        Parameters:
        -----------
        df : pd.DataFrame
            Input DataFrame containing high-frequency smart meter telemetry.
        time_col : str, optional
            Name of the timestamp column. If None, index is assumed to be DatetimeIndex.

        Returns:
        --------
        pd.DataFrame
            Downsampled 15-minute interval telemetry.
        """
        if time_col is not None:
            df = df.set_index(time_col)
            
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
            
        # Vectorized aggregate resampling
        return df.resample('15min').mean()

    @staticmethod
    def impute_missing_spline(df: pd.DataFrame) -> pd.DataFrame:
        """
        Imputes missing values and sensor dropouts (NaNs) using cubic spline interpolation.
        Cubic splines maintain C2 continuity (smooth first and second load derivatives),
        minimizing artificial step transitions. Boundary edges are capped with FFILL/BFILL.

        Parameters:
        -----------
        df : pd.DataFrame
            Resampled DatetimeIndex DataFrame containing NaNs.

        Returns:
        --------
        pd.DataFrame
            Imputed complete DataFrame.
        """
        # Fit cubic spline across time index values to maintain electrical demand continuity
        df_imputed = df.interpolate(method='cubicspline', limit_direction='both')
        # Handle residual edge boundaries
        return df_imputed.ffill().bfill()

    @staticmethod
    def pivot_and_normalize_daily(df: pd.DataFrame, meter_column: str) -> tuple:
        """
        Pivots continuous 15-minute time series data of a selected meter into a daily
        load matrix (N days x 96 time-slots) and normalizes each daily row to [0, 1].

        Parameters:
        -----------
        df : pd.DataFrame
            DatetimeIndex DataFrame with complete 15-minute intervals.
        meter_column : str
            Target column containing active load telemetry.

        Returns:
        --------
        daily_matrix : np.ndarray
            Re-shaped (N days x 96 slots) array of raw active load.
        normalized_matrix : np.ndarray
            Min-Max normalized daily profiles scaling each day individually to [0, 1].
        valid_dates : list
            List of dates corresponding to each row in the matrix.
        """
        series = df[meter_column]
        
        # Fast vectorized group-by-date to construct daily records
        grouped = series.groupby(series.index.date)
        
        daily_list = []
        valid_dates = []
        
        for date, group in grouped:
            if len(group) == 96:  # Filter out incomplete days (e.g. start/end day anomalies)
                daily_list.append(group.values)
                valid_dates.append(date)
                
        daily_matrix = np.array(daily_list)
        
        if len(daily_matrix) == 0:
            raise ValueError(f"No complete days (96 slots) found in the telemetry for column: {meter_column}")
            
        # Vectorized row-wise Min-Max Normalization to isolate load shapes from absolute magnitude
        row_min = daily_matrix.min(axis=1, keepdims=True)
        row_max = daily_matrix.max(axis=1, keepdims=True)
        denom = row_max - row_min
        
        # Safe vectorized division preventing divide-by-zero on empty/constant flatlines
        normalized_matrix = np.divide((daily_matrix - row_min), denom, 
                                      out=np.zeros_like(daily_matrix), 
                                      where=denom != 0)
                                      
        return daily_matrix, normalized_matrix, valid_dates

    @staticmethod
    def extract_slps(normalized_matrix: np.ndarray) -> tuple:
        """
        Applies K-Means clustering (K=2) on the daily normalized matrix to extract
        representative centroids. Programmatically classifies and returns centroids as
        the definitive Residential and Agricultural Standardized Load Profiles (SLPs).

        Residential profile is characterized by distinct evening peaks (6 PM to 10 PM),
        while Agricultural profile features high continuous block pumping loads.

        Parameters:
        -----------
        normalized_matrix : np.ndarray
            Matrix of daily normalized load shape vectors of shape (N_samples, 96).

        Returns:
        --------
        slp_residential : np.ndarray
            Extracted Standardized Load Profile for Residential consumers (length 96).
        slp_agricultural : np.ndarray
            Extracted Standardized Load Profile for Agricultural consumers (length 96).
        """
        # Execute K-Means clustering with deterministic seed
        kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
        kmeans.fit(normalized_matrix)
        centroids = kmeans.cluster_centers_
        
        # Distinguish categories programmatically:
        # Residential consumers exhibit high energy usage in evening peaks (slots 72 to 88, representing 18:00 - 22:00)
        evening_ratio_0 = np.mean(centroids[0][72:88]) / (np.mean(centroids[0]) + 1e-9)
        evening_ratio_1 = np.mean(centroids[1][72:88]) / (np.mean(centroids[1]) + 1e-9)
        
        if evening_ratio_0 > evening_ratio_1:
            slp_residential = centroids[0]
            slp_agricultural = centroids[1]
        else:
            slp_residential = centroids[1]
            slp_agricultural = centroids[0]
            
        return slp_residential, slp_agricultural


# ==============================================================================
# VERIFICATION AND SELF-TEST PIPELINE
# ==============================================================================

def generate_telemetry_dataset(days=30, num_consumers=4) -> pd.DataFrame:
    """Generates synthetic high-frequency smart meter telemetry for verification."""
    np.random.seed(42)
    start_date = datetime(2026, 9, 17, 0, 0)
    timestamps = [start_date + timedelta(minutes=3 * i) for i in range(days * 480)]
    df = pd.DataFrame(index=timestamps)
    
    for c in range(num_consumers):
        is_agri = (c % 2 == 0)
        load = np.zeros(len(df))
        
        if is_agri:
            # Ag Load: Midnight pumping and afternoon pumping blocks
            for idx, t in enumerate(df.index):
                base = 1.0 + np.random.normal(0, 0.1)
                if (0 <= t.hour < 6) or (12 <= t.hour < 15):
                    load[idx] = base + 15.0 + np.random.normal(0, 0.4)
                else:
                    load[idx] = base
        else:
            # Res Load: Evening and minor morning peaks
            for idx, t in enumerate(df.index):
                base = 2.0 + np.random.normal(0, 0.1)
                m_peak = 3.0 * np.exp(-((t.hour - 8.0) / 1.5)**2)
                e_peak = 12.0 * np.exp(-((t.hour - 20.5) / 2.0)**2)
                load[idx] = base + m_peak + e_peak
                
        df[f"meter_kW_{c}"] = np.maximum(0.05, load)
        
    # Inject missing intervals to verify spline imputations
    mask = np.random.rand(*df.shape) < 0.04
    df[mask] = np.nan
    return df

if __name__ == "__main__":
    print("[RUNNING] Executing Phase 1 Pipeline Test...")
    
    # 1. Synthesize smart meter telemetry
    df_raw = generate_telemetry_dataset(days=30, num_consumers=4)
    print(f"    Raw telemetry synthesized. Shape: {df_raw.shape} (3-min interval)")
    print(f"    Missing entries count before imputation: {df_raw.isnull().sum().sum()}")
    
    # 2. Downsampling
    df_15m = Phase1DataPipeline.downsample_telemetry(df_raw)
    print(f"    Telemetry downsampled to 15-minute intervals. Shape: {df_15m.shape}")
    
    # 3. Spline Imputation
    df_clean = Phase1DataPipeline.impute_missing_spline(df_15m)
    print(f"    Missing entries count after spline imputation: {df_clean.isnull().sum().sum()}")
    
    # 4. Daily Normalization and Aggregation for K-Means Clustering
    all_normalized_profiles = []
    
    # Aggregate all daily normalized shapes across all meters to construct universal consumer templates
    meter_cols = [c for c in df_clean.columns if "meter_kW_" in c]
    for meter in meter_cols:
        _, norm_matrix, _ = Phase1DataPipeline.pivot_and_normalize_daily(df_clean, meter)
        all_normalized_profiles.append(norm_matrix)
        
    cluster_dataset = np.vstack(all_normalized_profiles)
    print(f"    Aggregated Daily profiles compiled. Shape: {cluster_dataset.shape} days")
    
    # 5. Extract Residential & Agricultural SLPs
    slp_res, slp_agri = Phase1DataPipeline.extract_slps(cluster_dataset)
    print(f"    SLP extraction complete.")
    print(f"    Residential SLP Mean Value: {np.mean(slp_res):.4f}")
    print(f"    Agricultural SLP Mean Value: {np.mean(slp_agri):.4f}")
    print("[SUCCESS] Phase 1 Pipeline executed flawlessly.")

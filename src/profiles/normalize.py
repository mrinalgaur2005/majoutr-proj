"""Peak and daily-energy profile normalizations."""
from __future__ import annotations

import numpy as np
import pandas as pd


def profiles_to_matrix(profile_df: pd.DataFrame) -> np.ndarray:
    return np.vstack(profile_df["profile_kw"].to_numpy())


def peak_normalize(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """P_t / P_max; rows with zero max are invalid."""
    peak = X.max(axis=1)
    valid = peak > 0
    out = np.zeros_like(X)
    out[valid] = X[valid] / peak[valid, None]
    return out, valid


def energy_normalize(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """P_t / sum(P_t); equivalent shape to sum-normalized daily curve."""
    energy = X.sum(axis=1)
    valid = energy > 0
    out = np.zeros_like(X)
    out[valid] = X[valid] / energy[valid, None]
    return out, valid


def filter_valid_days(
    profile_df: pd.DataFrame,
    norm_valid: np.ndarray,
) -> tuple[pd.DataFrame, np.ndarray]:
    mask = norm_valid
    return profile_df.loc[mask].reset_index(drop=True), mask

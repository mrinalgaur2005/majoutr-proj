"""K-means clustering with metrics and multi-seed stability."""
from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)


def _subsample_indices(n: int, size: int, seed: int) -> np.ndarray:
    if n <= size:
        return np.arange(n)
    rng = np.random.default_rng(seed)
    return rng.choice(n, size=size, replace=False)


def run_kmeans_grid(
    X: np.ndarray,
    profile_df: pd.DataFrame,
    k_values: list[int],
    seeds: list[int],
    n_init: int,
    silhouette_subsample: int,
    primary_seed: int,
    normalization: str,
) -> dict[str, Any]:
    n = len(X)
    sil_idx = _subsample_indices(n, silhouette_subsample, primary_seed)
    metrics_rows = []
    stability_rows = []
    assignments_rows = []
    centroids_rows = []

    for k in k_values:
        labels_by_seed = []
        for seed in seeds:
            km = KMeans(n_clusters=k, random_state=seed, n_init=n_init)
            labels = km.fit_predict(X)
            labels_by_seed.append(labels)
            if seed == seeds[0]:
                sil = silhouette_score(X[sil_idx], labels[sil_idx])
                metrics_rows.append(
                    {
                        "normalization": normalization,
                        "k": k,
                        "silhouette_subsample": sil,
                        "silhouette_subsample_n": len(sil_idx),
                        "davies_bouldin": davies_bouldin_score(X, labels),
                        "calinski_harabasz": calinski_harabasz_score(X, labels),
                        "inertia": km.inertia_,
                        "n_iter": int(km.n_iter_),
                        "random_seed_reported": seed,
                        "cluster_sizes": json.dumps(
                            np.bincount(labels, minlength=k).tolist()
                        ),
                    }
                )
                for i, row in enumerate(profile_df.itertuples(index=False)):
                    assignments_rows.append(
                        {
                            "profile_index": i,
                            "meter_id": row.meter_id,
                            "city": row.city,
                            "date": str(row.date),
                            "normalization": normalization,
                            "k": k,
                            "cluster": int(labels[i]),
                        }
                    )
                for c, center in enumerate(km.cluster_centers_):
                    for slot, val in enumerate(center):
                        centroids_rows.append(
                            {
                                "normalization": normalization,
                                "k": k,
                                "cluster": c,
                                "slot": slot,
                                "normalized_load": float(val),
                            }
                        )

        aris = [
            adjusted_rand_score(labels_by_seed[0], z) for z in labels_by_seed[1:]
        ]
        stability_rows.append(
            {
                "normalization": normalization,
                "k": k,
                "seed_ARI_mean": float(np.mean(aris)),
                "seed_ARI_std": float(np.std(aris)),
                "seed_ARI_min": float(np.min(aris)),
                "n_seeds": len(seeds),
            }
        )

    return {
        "metrics": pd.DataFrame(metrics_rows),
        "stability": pd.DataFrame(stability_rows),
        "assignments": pd.DataFrame(assignments_rows),
        "centroids": pd.DataFrame(centroids_rows),
        "primary_labels": assignments_rows,
    }


def describe_cluster_profiles(
    profile_df: pd.DataFrame,
    labels: np.ndarray,
    k: int,
) -> pd.DataFrame:
    """Quantitative cluster characterization from raw kW profiles."""
    X = np.vstack(profile_df["profile_kw"].to_numpy())
    rows = []
    for c in range(k):
        mask = labels == c
        sub = profile_df.loc[mask]
        arr = X[mask]
        n = len(sub)
        if n == 0:
            continue
        mean_profile = arr.mean(axis=0)
        morning = mean_profile[24:40].mean()  # 06:00-10:00 slots 24-39
        daytime = mean_profile[40:68].mean()  # 10:00-17:00
        evening = mean_profile[68:88].mean()  # 17:00-22:00
        overnight = np.concatenate([mean_profile[:24], mean_profile[88:]]).mean()
        rows.append(
            {
                "cluster": c,
                "n_profiles": n,
                "pct_profiles": 100.0 * n / len(profile_df),
                "mean_daily_energy_kwh": float(sub.daily_energy_kwh.mean()),
                "mean_peak_load_kw": float(sub.peak_load_kw.mean()),
                "mean_peak_slot": float(sub.peak_slot.mean()),
                "mean_load_factor": float(sub.load_factor.mean()),
                "morning_strength_kw": float(morning),
                "daytime_strength_kw": float(daytime),
                "evening_strength_kw": float(evening),
                "overnight_strength_kw": float(overnight),
                "profile_flatness": float(mean_profile.std() / (mean_profile.mean() + 1e-9)),
            }
        )
    return pd.DataFrame(rows)

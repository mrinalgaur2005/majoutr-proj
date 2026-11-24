"""Publication-oriented figures for audit, profiles, and clustering."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_profile_eda(profile_df: pd.DataFrame, out_dir: Path, rng_seed: int = 42) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(rng_seed)
    X = np.vstack(profile_df["profile_kw"].to_numpy())
    slots = np.arange(96)
    hours = slots / 4

    fig, ax = plt.subplots(figsize=(9, 4))
    mean_all = X.mean(axis=0)
    ax.plot(hours, mean_all, label="Mean (all)", color="black", lw=2)
    for city in profile_df.city.unique():
        m = profile_df.city == city
        ax.plot(hours, X[m].mean(axis=0), label=f"Mean ({city})")
    ax.set(xlabel="Hour of day", ylabel="Mean load (kW)", title="Mean daily load profiles")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "mean_profiles_by_location.png", dpi=200)
    plt.close(fig)

    idx = rng.choice(len(X), size=min(12, len(X)), replace=False)
    fig, ax = plt.subplots(figsize=(9, 4))
    for i in idx:
        ax.plot(hours, X[i], alpha=0.5, lw=0.8)
    ax.set(xlabel="Hour of day", ylabel="Load (kW)", title="Sample daily profiles")
    fig.tight_layout()
    fig.savefig(out_dir / "sample_profiles.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(profile_df.peak_load_kw, bins=50, edgecolor="k", alpha=0.7)
    ax.set(xlabel="Daily peak load (kW)", title="Peak load distribution")
    fig.tight_layout()
    fig.savefig(out_dir / "peak_load_distribution.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(profile_df.daily_energy_kwh, bins=50, edgecolor="k", alpha=0.7)
    ax.set(xlabel="Daily energy (kWh)", title="Daily energy distribution")
    fig.tight_layout()
    fig.savefig(out_dir / "daily_energy_distribution.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(profile_df.peak_slot / 4, bins=48, edgecolor="k", alpha=0.7)
    ax.set(xlabel="Peak time (hour)", title="Peak-time distribution")
    fig.tight_layout()
    fig.savefig(out_dir / "peak_time_distribution.png", dpi=200)
    plt.close(fig)

    wd = profile_df[profile_df.day_of_week < 5]
    we = profile_df[profile_df.day_of_week >= 5]
    if len(wd) and len(we):
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(hours, np.vstack(wd.profile_kw).mean(axis=0), label="Weekday")
        ax.plot(hours, np.vstack(we.profile_kw).mean(axis=0), label="Weekend")
        ax.set(xlabel="Hour", ylabel="kW", title="Weekday vs weekend mean profile")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_dir / "weekday_weekend.png", dpi=200)
        plt.close(fig)

    for season in profile_df.season.unique():
        sub = profile_df[profile_df.season == season]
        if len(sub) < 30:
            continue
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(hours, np.vstack(sub.profile_kw).mean(axis=0))
        ax.set(xlabel="Hour", ylabel="kW", title=f"Mean profile — season {season}")
        fig.tight_layout()
        fig.savefig(out_dir / f"mean_profile_season_{season}.png", dpi=200)
        plt.close(fig)


def plot_clustering_results(
    metrics: pd.DataFrame,
    centroids: pd.DataFrame,
    stability: pd.DataFrame,
    profile_df: pd.DataFrame,
    assignments: pd.DataFrame,
    normalization: str,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    sub_m = metrics[metrics.normalization == normalization]
    fig, axs = plt.subplots(1, 3, figsize=(12, 3))
    for ax, col, title in zip(
        axs,
        ["silhouette_subsample", "davies_bouldin", "calinski_harabasz"],
        ["Silhouette (subsample)", "Davies-Bouldin", "Calinski-Harabasz"],
    ):
        ax.plot(sub_m.k, sub_m[col], marker="o")
        ax.set(xlabel="K", title=title)
    fig.suptitle(f"Cluster metrics — {normalization}")
    fig.tight_layout()
    fig.savefig(out_dir / f"metrics_vs_k_{normalization}.png", dpi=200)
    plt.close(fig)

    sub_s = stability[stability.normalization == normalization]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.errorbar(
        sub_s.k,
        sub_s.seed_ARI_mean,
        yerr=sub_s.seed_ARI_std,
        marker="o",
        capsize=4,
    )
    ax.set(xlabel="K", ylabel="Mean ARI across seeds", title=f"Stability — {normalization}")
    fig.tight_layout()
    fig.savefig(out_dir / f"stability_{normalization}.png", dpi=200)
    plt.close(fig)

    hours = np.arange(96) / 4
    for k in sub_m.k.unique():
        z = centroids[
            (centroids.normalization == normalization) & (centroids.k == k)
        ]
        fig, ax = plt.subplots(figsize=(9, 4))
        for c, g in z.groupby("cluster"):
            ax.plot(hours, g.sort_values("slot").normalized_load, label=f"Cluster {c}")
        ax.set(
            xlabel="Hour",
            ylabel="Normalized load",
            title=f"Centroids K={k} — {normalization}",
        )
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_dir / f"centroids_k{k}_{normalization}.png", dpi=200)
        plt.close(fig)

        a = assignments[
            (assignments.normalization == normalization) & (assignments.k == k)
        ]
        if a.empty:
            continue
        sizes = a.cluster.value_counts().sort_index()
        fig, ax = plt.subplots(figsize=(5, 4))
        sizes.plot(kind="bar", ax=ax)
        ax.set(title=f"Cluster sizes K={k}", xlabel="Cluster")
        fig.tight_layout()
        fig.savefig(out_dir / f"cluster_sizes_k{k}_{normalization}.png", dpi=200)
        plt.close(fig)

        pdf_idx = profile_df.copy()
        pdf_idx["profile_index"] = np.arange(len(pdf_idx))
        a_loc = a.drop(columns=["city"], errors="ignore").merge(
            pdf_idx[["profile_index", "city", "profile_kw"]],
            on="profile_index",
            how="left",
        )
        for city in profile_df.city.unique():
            ac = a_loc[a_loc.city == city]
            if ac.empty:
                continue
            fig, ax = plt.subplots(figsize=(9, 4))
            for c in sorted(ac.cluster.unique()):
                rows = ac[ac.cluster == c]
                prof = np.vstack(rows.profile_kw.to_numpy())
                ax.plot(hours, prof.mean(axis=0), label=f"Cluster {c}")
            ax.set(
                xlabel="Hour",
                ylabel="kW",
                title=f"Mean kW by cluster — {city} K={k}",
            )
            ax.legend(fontsize=8)
            fig.tight_layout()
            fig.savefig(
                out_dir / f"cluster_profiles_{city}_k{k}_{normalization}.png",
                dpi=200,
            )
            plt.close(fig)

        fig, ax = plt.subplots(figsize=(9, 4))
        pdf_idx = profile_df.copy()
        pdf_idx["profile_index"] = np.arange(len(pdf_idx))
        for c in sorted(a.cluster.unique()):
            rows = a[a.cluster == c].head(3)
            merged = rows.merge(pdf_idx[["profile_index", "profile_kw"]], on="profile_index")
            for _, row in merged.iterrows():
                ax.plot(hours, row.profile_kw, alpha=0.4, lw=0.8)
        ax.set(title=f"Example profiles K={k}", xlabel="Hour", ylabel="kW")
        fig.tight_layout()
        fig.savefig(out_dir / f"examples_k{k}_{normalization}.png", dpi=200)
        plt.close(fig)


def plot_normalization_comparison(
    peak_var: float,
    energy_var: float,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(["peak", "energy"], [peak_var, energy_var])
    ax.set(ylabel="Mean row variance", title="Normalization — mean profile variance")
    fig.tight_layout()
    fig.savefig(out_dir / "normalization_variance_comparison.png", dpi=200)
    plt.close(fig)

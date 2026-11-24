#!/usr/bin/env python3
"""Append measured results from foundation run into research_log.md."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    summary_path = ROOT / "results" / "foundation_pipeline_summary.json"
    metrics_path = ROOT / "results" / "clustering" / "cluster_metrics.csv"
    stability_path = ROOT / "results" / "clustering" / "cluster_stability.csv"
    cluster_summary_path = ROOT / "results" / "clustering" / "cluster_summary.csv"
    audit_path = ROOT / "results" / "data_audit" / "audit_summary.json"
    norm_path = ROOT / "results" / "profiles" / "normalization_summary.json"
    loc_path = ROOT / "results" / "profiles" / "location_profile_summary.csv"

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    norm = json.loads(norm_path.read_text(encoding="utf-8"))
    metrics = pd.read_csv(metrics_path)
    stability = pd.read_csv(stability_path)
    csum = pd.read_csv(cluster_summary_path)
    loc = pd.read_csv(loc_path)

    meter_q = pd.read_csv(ROOT / "results" / "data_audit" / "meter_quality.csv")

    def fmt_metrics(norm: str) -> str:
        sub = metrics[metrics.normalization == norm]
        lines = []
        for _, r in sub.iterrows():
            lines.append(
                f"- K={int(r.k)}: silhouette(subsample)={r.silhouette_subsample:.4f}, "
                f"DB={r.davies_bouldin:.4f}, CH={r.calinski_harabasz:.1f}, sizes={r.cluster_sizes}"
            )
        return "\n".join(lines)

    def fmt_stability(norm: str) -> str:
        sub = stability[stability.normalization == norm]
        lines = []
        for _, r in sub.iterrows():
            lines.append(
                f"- K={int(r.k)}: ARI mean={r.seed_ARI_mean:.4f}, std={r.seed_ARI_std:.4f}, min={r.seed_ARI_min:.4f}"
            )
        return "\n".join(lines)

    # Candidate K without forcing winner
    best_sil_energy = metrics[metrics.normalization == "energy"].sort_values(
        "silhouette_subsample", ascending=False
    ).iloc[0]
    best_sil_peak = metrics[metrics.normalization == "peak"].sort_values(
        "silhouette_subsample", ascending=False
    ).iloc[0]

    human_flags = []
    if audit.get("extreme_load_kw_rows", 0) > 0:
        human_flags.append(
            f"Extreme load readings (>{audit.get('extreme_load_kw_threshold')} kW): "
            f"{audit['extreme_load_kw_rows']} rows — verify physical plausibility."
        )
    human_flags.append("Timezone semantics unresolved (naive timestamps).")
    human_flags.append(
        "Provisional primary normalization for later forecasting: daily-energy (sum) norm — requires human confirmation."
    )
    if stability.seed_ARI_min.min() < 0.5:
        human_flags.append(
            f"Low minimum seed ARI observed ({stability.seed_ARI_min.min():.3f}) — review cluster stability."
        )
    loc_comp_path = ROOT / "results" / "clustering" / "cluster_location_composition.csv"
    if loc_comp_path.exists():
        lc = pd.read_csv(loc_comp_path)
        for k in lc.k.unique():
            sub = lc[lc.k == k]
            if len(sub) and (sub.get("Mathura", pd.Series()).max() > 85 or sub.get("Bareilly", pd.Series()).max() > 85):
                human_flags.append(f"Possible location confounding at K={k} — inspect cluster_location_composition.csv")

    exec_block = f"""# Executive Summary

## Dataset Used

- {audit['rows']:,} raw 3-minute rows, {audit['unique_meters']} meters
- Rows by city: {audit['rows_by_city']}
- Raw file checksums: see `results/data_audit/audit_summary.json`

## Data Quality Findings

- Nulls in core fields: {audit['missing_values']}
- Negatives: {audit['negative_values']}
- Zero interval energy rows: {audit['zero_values'].get('interval_energy_kwh', 'N/A')}
- Extreme load rows (>{audit.get('extreme_load_kw_threshold')} kW): {audit.get('extreme_load_kw_rows', 0)}
- Mean per-meter coverage %: {meter_q.coverage_percent.mean():.2f} (median {meter_q.coverage_percent.median():.2f})
- 15-min bins complete / total: {summary['bin_stats']['bins_complete']} / {summary['bin_stats']['bins_total']}
- Malformed timestamps: {summary['bin_stats'].get('malformed_timestamps', 'N/A')}; off 3-min boundary: {summary['bin_stats'].get('off_three_minute_boundaries', 'N/A')}

## Preprocessing Decisions

- 15-min power: sum(`t_kWh`) / 0.25 h only when bin has exactly 5 unique 3-min points spanning 12 minutes
- Daily profile: 96 complete 15-min slots; no imputation
- Clustering input: meter-day profiles with positive daily energy

## Missing Data Strategy

- Missing timestamps → incomplete bins → NaN load; incomplete days excluded from profiles
- Zeros are valid measurements, not treated as missing

## Number of Valid Profiles

- Meter-days total (any completeness): {summary['profile_stats']['meter_days_total']}
- 100% complete meter-days: {summary['profile_stats']['valid_100_meter_days']}
- ≥95% slots (sensitivity count only): {summary['profile_stats']['valid_95_meter_days']}
- Profiles used in clustering (non-zero energy): {norm['profiles_for_clustering']}
- All-zero complete days excluded: {norm['all_zero_complete_days_excluded']}

## Normalization Experiments

- **Peak:** P_t / max(P_t); mean row variance = {norm['mean_row_variance_peak_norm']:.6f}
- **Energy (sum):** P_t / sum(P_t); mean row variance = {norm['mean_row_variance_energy_norm']:.6f}
- Both representations clustered for K=2..6; no single metric used to declare winner

## Clustering Algorithms

- K-Means (sklearn), Euclidean, n_init={summary['config']['kmeans_n_init']}, seeds={summary['config']['stability_seeds']}
- Joint clustering across Mathura and Bareilly meter-days

## K Values Tested

{summary['config']['k_values']}

## Clustering Metrics

**Energy normalization:**

{fmt_metrics('energy')}

**Peak normalization:**

{fmt_metrics('peak')}

Silhouette computed on subsample n={metrics['silhouette_subsample_n'].iloc[0]} (seed {summary['config']['primary_random_seed']}).

## Stability Results

**Energy:**

{fmt_stability('energy')}

**Peak:**

{fmt_stability('peak')}

## Selected / Candidate K

- Best silhouette (subsample) under **energy** norm: K={int(best_sil_energy.k)} (score={best_sil_energy.silhouette_subsample:.4f})
- Best silhouette (subsample) under **peak** norm: K={int(best_sil_peak.k)} (score={best_sil_peak.silhouette_subsample:.4f})
- Metrics may disagree across indices and normalizations; no final K forced here.

## Cluster Characteristics

See `results/clustering/cluster_summary.csv`. Sample (energy norm, K=3 if present):

```
{csum[(csum.normalization=='energy') & (csum.k==3)].to_string(index=False) if len(csum[(csum.normalization=='energy') & (csum.k==3)]) else csum.head(8).to_string(index=False)}
```

## Mathura vs Bareilly Findings

```
{loc.to_string(index=False)}
```

Location composition per cluster: `results/clustering/cluster_location_composition.csv`

## Potential Problems / Threats to Validity

- Naive timestamp timezone
- Long outage gaps (per-meter max gap minutes in meter_quality.csv)
- Joint clustering may encode location-specific shapes
- Silhouette on subsample is approximate for large N

## Decisions Requiring Human Review

- Confirm energy vs peak normalization for forecast-stage SLP features
- Choose candidate K after reviewing metrics, stability, and interpretability

## Next Recommended Step

Chronological train/validation/test split and persistence / seasonal-naive / SVR baselines (out of scope for this milestone).

---

## Step 1 — Data Audit (numerical)

- Meters: {audit['unique_meters']}
- Total rows: {audit['rows']}
- Per-meter table: `results/data_audit/meter_quality.csv`
- Location summary: `results/data_audit/location_summary.csv`

## Step 2 — Preprocessing

See leakage table above and `results/foundation_pipeline_summary.json` bin_stats.

## Step 3 — Daily Profile Construction

- Valid 96-slot profiles for clustering: {norm['profiles_for_clustering']}
- Based on **average kW** per 15-min bin (not normalized energy shape alone)

## Step 4 — Normalization

Primary **provisional** choice for later forecasting: daily-energy normalization (shape-focused; peak norm sensitive to single-slot spikes).

## Step 5 — Clustering

Outputs under `results/clustering/`.

---

# HUMAN REVIEW REQUIRED

"""

    if human_flags:
        exec_block += "\n".join(f"- {f}" for f in human_flags)
    else:
        exec_block += "\nNo unresolved methodological issues identified."

    log_path = ROOT / "research_log.md"
    text = log_path.read_text(encoding="utf-8")
    marker = "# Executive Summary"
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n\n---\n\n" + exec_block
    else:
        text = text + "\n\n" + exec_block

    env = summary["environment"]
    import re

    text = re.sub(
        r"## Environment\n\n.*?\n\n## Repository State",
        (
            "## Environment\n\n"
            f"- Python version: {env['python']}\n"
            f"- pandas {env['pandas']}, numpy {env['numpy']} "
            "(see `results/foundation_pipeline_summary.json`)\n"
            f"- OS: {env['platform']}\n"
            f"- Execution date/time: {summary['run_timestamp_utc']}\n\n"
            "## Repository State"
        ),
        text,
        count=1,
        flags=re.DOTALL,
    )

    log_path.write_text(text, encoding="utf-8")
    print("Updated", log_path)


if __name__ == "__main__":
    main()

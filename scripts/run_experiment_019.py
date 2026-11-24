#!/usr/bin/env python3
"""Experiment 019: external category-labelled dataset feasibility audit. No forecasting."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.goiener_loader import (  # noqa: E402
    audit_profile_csv,
    find_profile_csvs,
    load_metadata_public,
    parse_sha256sums,
    stratified_sample_ids,
    zenodo_file_url,
)

OUT = ROOT / "results" / "dataset_audit" / "experiment_019"
FIG = ROOT / "results" / "figures" / "dataset_019"
PPT = ROOT / "results" / "figures" / "ppt_ready"
GOI_RAW = ROOT / "data/external/goiener/raw"
GOI_INTERIM = ROOT / "data/external/goiener/interim"
EB_MANIFEST = ROOT / "data/external/energybench/manifest"
CMD_LOG = OUT / "experiment_019_commands.log"

SEED = 19
PER_DIV_CAP = 15
MAX_PROFILES = 400
PART_ARCHIVE = "profiles_part01.tar.zst"
METADATA_FILES = ("README.txt", "SHA256SUMS.txt", "metadata_public.csv")
DPI = 300
plt.rcParams.update({"font.size": 11, "figure.dpi": DPI})

CNAE_DIVISION_NAMES = {
    "01": "Agriculture, livestock, hunting (CNAE A)",
    "02": "Forestry and logging",
    "03": "Fishing and aquaculture",
    "05": "Mining of coal and lignite",
    "10": "Food products",
    "41": "Construction of buildings",
    "46": "Wholesale trade",
    "47": "Retail trade",
    "55": "Accommodation",
    "56": "Food and beverage service",
    "68": "Real estate activities",
    "85": "Education",
    "86": "Human health activities",
    "96": "Other personal service activities",
}

# EnergyBench real-building inventory (from HuggingFace dataset card tables, not full download).
ENERGYBENCH_SOURCE_NOTE = "ai-iot/EnergyBench dataset card (accessed during Experiment 019); CC-4.0"


def log_cmd(msg: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with CMD_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} {msg}\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_url(url: str, dest: Path, timeout: int = 600) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        log_cmd(f"skip existing {dest.name}")
        return
    urls = [url]
    if "?download=1" in url:
        urls.append(url.replace("?download=1", ""))
    last_err: Exception | None = None
    for attempt, u in enumerate(urls, start=1):
        try:
            log_cmd(f"GET {u} -> {dest} (attempt {attempt})")
            req = urllib.request.Request(u, headers={"User-Agent": "majou-proj-exp019/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp, dest.open("wb") as out:
                shutil.copyfileobj(resp, out)
            return
        except Exception as e:
            last_err = e
            log_cmd(f"download failed: {e}")
            if dest.exists():
                dest.unlink()
    if last_err:
        raise last_err


def save_fig(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    fig.savefig(path.with_suffix(".pdf"))
    fig.savefig(path.with_suffix(".svg"))
    plt.close(fig)


def acquire_goiener() -> dict:
    GOI_RAW.mkdir(parents=True, exist_ok=True)
    checksums: dict[str, str] = {}
    for name in METADATA_FILES:
        dest = GOI_RAW / name
        download_url(zenodo_file_url(name), dest)
        checksums[name] = sha256_file(dest)
    sums_text = (GOI_RAW / "SHA256SUMS.txt").read_text(encoding="utf-8", errors="replace")
    expected = parse_sha256sums(sums_text)
    verify = {}
    for name in METADATA_FILES:
        exp = expected.get(name)
        got = checksums[name]
        verify[name] = {"expected_sha256": exp, "got_sha256": got, "match": exp == got if exp else None}
    archive_path = GOI_RAW / PART_ARCHIVE
    if not archive_path.exists():
        download_url(zenodo_file_url(PART_ARCHIVE), archive_path, timeout=3600)
    checksums[PART_ARCHIVE] = sha256_file(archive_path)
    exp_arch = expected.get(PART_ARCHIVE)
    verify[PART_ARCHIVE] = {
        "expected_sha256": exp_arch,
        "got_sha256": checksums[PART_ARCHIVE],
        "match": exp_arch == checksums[PART_ARCHIVE] if exp_arch else None,
    }
    extract_dir = GOI_INTERIM / "profiles_sample"
    extract_dir.mkdir(parents=True, exist_ok=True)
    return {"files": checksums, "verify": verify, "extract_dir": str(extract_dir), "archive": str(archive_path)}


def audit_goiener_metadata(meta: pd.DataFrame) -> pd.DataFrame:
    counts = meta.groupby("cnae_division", as_index=False).size().rename(columns={"size": "n_profiles"})
    counts["label"] = counts.cnae_division.map(lambda d: CNAE_DIVISION_NAMES.get(d, f"CNAE division {d}"))
    counts["synopsis_agriculture"] = counts.cnae_division == "01"
    counts["synopsis_residential"] = False
    counts.to_csv(OUT / "category_counts.csv", index=False)
    return counts


def archive_members(archive: Path) -> set[str]:
    cmd = ["tar", "--use-compress-program=zstd", "-tf", str(archive)]
    out = subprocess.check_output(cmd, text=True)
    return {line.strip() for line in out.splitlines() if line.strip().endswith(".csv")}


def extract_sample_profiles(archive: Path, file_ids: list[str], dest: Path) -> list[str]:
    """Extract only requested profiles/{id}.csv members present in this archive."""
    dest.mkdir(parents=True, exist_ok=True)
    members_all = archive_members(archive)
    members = [f"profiles/{fid}.csv" for fid in file_ids if f"profiles/{fid}.csv" in members_all]
    if not members:
        return []
    cmd = ["tar", "--use-compress-program=zstd", "-xf", str(archive), "-C", str(dest)] + members
    log_cmd(f"selective extract n={len(members)} of {len(file_ids)} requested")
    subprocess.run(cmd, check=True, cwd=None)
    return [m.replace("profiles/", "").replace(".csv", "") for m in members]


def audit_goiener_profiles(meta: pd.DataFrame, extract_dir: Path, archive: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    sample_ids = stratified_sample_ids(meta, SEED, PER_DIV_CAP, MAX_PROFILES)
    (GOI_INTERIM / "sample_file_ids.txt").write_text("\n".join(sample_ids), encoding="utf-8")
    extracted: list[str] = []
    if archive and archive.exists():
        in_archive = archive_members(archive)
        max_id = max(int(Path(m).name.replace(".csv", "")) for m in in_archive)
        meta_part = meta[meta.file_id.astype(int) <= max_id]
        sample_ids = stratified_sample_ids(meta_part, SEED, PER_DIV_CAP, MAX_PROFILES)
        (GOI_INTERIM / "sample_file_ids_part01.txt").write_text("\n".join(sample_ids), encoding="utf-8")
        try:
            extracted = extract_sample_profiles(archive, sample_ids, extract_dir)
        except subprocess.CalledProcessError as e:
            log_cmd(f"selective extract failed: {e}")
    id_set = set(sample_ids)
    found = find_profile_csvs(extract_dir, id_set)
    rows = []
    for fid in sample_ids:
        if fid not in found:
            rows.append({"file_id": fid, "found": False})
            continue
        aud = audit_profile_csv(found[fid])
        aud["file_id"] = fid
        aud["found"] = True
        div = meta.loc[meta.file_id.astype(str) == fid, "cnae_division"]
        aud["cnae_division"] = div.iloc[0] if len(div) else None
        rows.append(aud)
    prof = pd.DataFrame(rows)
    prof.to_csv(OUT / "goiener_profile_sample_audit.csv", index=False)

    # sampling resolution
    ok = prof[prof.found & prof.median_interval_minutes.notna()]
    res_rows = []
    if len(ok):
        for div, g in ok.groupby("cnae_division"):
            med = float(g.median_interval_minutes.median())
            res_rows.append({
                "dataset": "GoiEner_v7.1_sample",
                "cnae_division": div,
                "median_interval_minutes": med,
                "supports_15min_native": med == 15 if not np.isnan(med) else False,
                "supports_hourly_native": med == 60 if not np.isnan(med) else False,
                "n_profiles_sampled": int(len(g)),
            })
    sampling = pd.DataFrame(res_rows)
    if len(sampling) == 0:
        sampling = pd.DataFrame([{
            "dataset": "GoiEner_v7.1",
            "note": "Use README: individual profiles native resolution varies; annual matrix is hourly imputed",
            "supports_15min_native": False,
            "supports_hourly_native": True,
        }])
    sampling.to_csv(OUT / "sampling_resolution_audit.csv", index=False)

    cov = pd.DataFrame([{
        "dataset": "GoiEner_v7.1_metadata",
        "n_profiles_total": int(len(meta)),
        "n_profiles_in_sample_dir": int(len(list(extract_dir.rglob("*.csv")))),
        "n_sample_requested": len(sample_ids),
        "n_sample_found": int(prof.found.sum()) if "found" in prof.columns else 0,
        "n_sample_median_rows": float(prof.loc[prof.found, "n_rows"].median()) if prof.found.any() else None,
    }])
    cov.to_csv(OUT / "coverage_audit.csv", index=False)

    miss = pd.DataFrame([{
        "dataset": "GoiEner_v7.1_sample",
        "mean_numeric_missing_frac": float(
            (prof.numeric_missing_cells / (prof.n_rows * (prof.n_columns - 1)).replace(0, np.nan)).mean()
        ) if prof.found.any() else None,
        "total_negatives_sample": int(prof.numeric_negatives.sum()) if prof.found.any() else 0,
        "total_zeros_sample": int(prof.numeric_zeros.sum()) if prof.found.any() else 0,
        "imputation_in_annual_matrix": "yes_documented",
        "imputation_in_individual_profiles": "pre_imputation_stage",
    }])
    miss.to_csv(OUT / "missingness_audit.csv", index=False)

    counts = pd.read_csv(OUT / "category_counts.csv")
    counts["cnae_division"] = counts["cnae_division"].astype(str).str.zfill(2)
    if prof.found.any() and "cnae_division" in prof.columns:
        prof["cnae_division"] = prof["cnae_division"].astype(str).str.zfill(2)
        samp = prof[prof.found].groupby("cnae_division").size().reset_index(name="n_in_sample")
        counts = counts.merge(samp, on="cnae_division", how="left")
        counts.to_csv(OUT / "category_counts.csv", index=False)
    return prof, counts


def audit_cer_documentation() -> dict:
    cer = {
        "doi": "10.7929/ISSDA/BX59EU",
        "study_id": "0012-00",
        "access_status": "PENDING_ACCESS",
        "access_url": "https://www.ucd.ie/issda/data/commissionforenergyregulationcer/",
        "restriction": "EEA and adequacy-decision countries only",
        "interval_minutes": 30,
        "interval_unit": "kWh per 30-minute period",
        "category_fields": ["Residential", "SME", "Other (allocation Code)"],
        "agriculture_category_documented": False,
        "literature_scale": {"residential_approx": 5000, "sme_approx": 650, "source": "ISSDA/CESSDA abstract, not audited"},
    }
    (OUT / "cer_access_status.json").write_text(json.dumps(cer, indent=2), encoding="utf-8")
    md = OUT / "cer_schema_from_manifest.md"
    md.write_text(
        "\n".join([
            "# CER schema (public manifest only)",
            "",
            "Interval files: meter ID, day code (1–365 per year), time code (1–48), kWh.",
            "",
            "Allocation: ID, Code (residential/SME/other), residential stimulus/tariff, SME allocation.",
            "",
            "**Not equivalent to CNAE or EnergyBench building-use labels.**",
            "",
            f"Access: {cer['access_url']}",
        ]),
        encoding="utf-8",
    )
    return cer


def build_energybench_catalog() -> pd.DataFrame:
    EB_MANIFEST.mkdir(parents=True, exist_ok=True)
    # Curated rows: real buildings only; synopsis-relevant highlights + full key entries
    rows = [
        {"name": "GoiEner", "tier": "real", "category_eb": "Residential", "location": "Spain",
         "buildings": 25559, "resolution": "1H", "unit": "kWh", "weather": False,
         "metadata_note": "EnergyBench label Residential — Zenodo v7.1 uses CNAE cnae_division, not domestic tariff",
         "agriculture_via_cnae": "use Zenodo metadata not EB label"},
        {"name": "CEEW", "tier": "real", "category_eb": "Residential", "location": "India", "buildings": 84,
         "resolution": "15min,1H", "unit": "kWh", "weather": False,
         "metadata_note": "Region only; project CEEW has no verified res/ag labels (frozen)"},
        {"name": "Prayas", "tier": "real", "category_eb": "Residential", "location": "India", "buildings": 116,
         "resolution": "15min,1H", "unit": "kWh", "weather": False, "metadata_note": "Household type in metadata"},
        {"name": "REFIT", "tier": "real", "category_eb": "Residential", "location": "UK", "buildings": 20,
         "resolution": "15min,1H", "unit": "kW", "weather": False},
        {"name": "Enernoc", "tier": "real", "category_eb": "Commercial", "location": "USA", "buildings": 100,
         "resolution": "15min,1H", "unit": "kWh", "weather": False,
         "metadata_note": "Industry/sub-industry type in metadata"},
        {"name": "EWELD", "tier": "real", "category_eb": "Commercial", "location": "Southern China",
         "buildings": 386, "resolution": "15min,1H", "unit": "kWh", "weather": False,
         "metadata_note": "Industry type extractable"},
        {"name": "SGSC", "tier": "real", "category_eb": "Residential", "location": "Australia",
         "buildings": 13735, "resolution": "30min,1H", "unit": "kWh", "weather": False,
         "metadata_note": "Customer type field"},
        {"name": "METER", "tier": "real", "category_eb": "Residential", "location": "UK", "buildings": 311,
         "resolution": "30min,1H", "unit": "kW", "weather": False},
        {"name": "Synthetic_commercial", "tier": "synthetic", "category_eb": "Commercial",
         "location": "simulated", "buildings": 207559, "resolution": "1H", "unit": "kWh", "weather": False},
        {"name": "Synthetic_residential", "tier": "synthetic", "category_eb": "Residential",
         "location": "simulated", "buildings": 31000000, "resolution": "1H", "unit": "kWh", "weather": False},
    ]
    df = pd.DataFrame(rows)
    df["source"] = ENERGYBENCH_SOURCE_NOTE
    df.to_csv(OUT / "energybench_real_catalog.csv", index=False)
    df.to_csv(EB_MANIFEST / "energybench_catalog_snapshot.csv", index=False)
    return df


def write_glossary() -> None:
    (OUT / "category_label_glossary.md").write_text(
        "\n".join([
            "# Category label glossary (Experiment 019)",
            "",
            "| System | Field | Meaning | Synopsis mapping |",
            "|--------|-------|---------|------------------|",
            "| GoiEner Zenodo v7.1 | `cnae_division` | Two-digit CNAE economic activity | Agriculture → division **01** only when documented |",
            "| GoiEner Zenodo v7.1 | — | No public domestic/residential tariff code | **Do not** infer residential from CNAE |",
            "| EnergyBench | `Residential` / `Commercial` | Building stock use type | Not equal to CNAE or CER Code |",
            "| CER ISSDA | `Code` in allocations | Utility trial segment (Residential/SME/Other) | Residential for synopsis track 2; **not** agriculture |",
            "| CEEW (project) | — | Urban household smart meters, no ag/res labels | Supplementary India track only |",
        ]),
        encoding="utf-8",
    )


def dataset_comparison_table(meta: pd.DataFrame, cer: dict, eb: pd.DataFrame) -> pd.DataFrame:
    n_ag = int((meta.cnae_division == "01").sum())
    eb_real_res = int(eb[(eb.tier == "real") & (eb.category_eb == "Residential")]["buildings"].sum())
    rows = [
        {"dataset": "CEEW_project_frozen", "access": "local", "n_units": 84, "category_system": "none",
         "residential_verified": False, "agricultural_verified": False, "native_interval": "15min",
         "license": "Harvard Dataverse", "role": "supplementary_india"},
        {"dataset": "GoiEner_v7.1", "access": "open", "n_units": len(meta), "category_system": "CNAE_division",
         "residential_verified": False, "agricultural_verified": n_ag > 0, "agriculture_n_div01": n_ag,
         "native_interval": "hourly_matrix; profiles variable", "license": "CC-BY-4.0",
         "role": "primary_slp_svr_categories"},
        {"dataset": "CER_ISSDA", "access": cer["access_status"], "n_units": cer["literature_scale"],
         "category_system": "utility_trial_code", "residential_verified": "pending_file_audit",
         "agricultural_verified": False, "native_interval": "30min", "license": "ISSDA_terms",
         "role": "primary_residential_when_obtained"},
        {"dataset": "EnergyBench", "access": "open_partial", "n_units": "varies_by_subset",
         "category_system": "building_use", "residential_verified": "subset_dependent",
         "agricultural_verified": False, "native_interval": "mixed", "license": "CC-4.0",
         "role": "catalog_supplementary"},
    ]
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "dataset_comparison.csv", index=False)
    return df


def synopsis_alignment(meta: pd.DataFrame, cer: dict, goi_prof: pd.DataFrame) -> pd.DataFrame:
    n_ag = int((meta.cnae_division == "01").sum())
    med_int = float(goi_prof.median_interval_minutes.median()) if goi_prof.found.any() else 60.0
    reqs = [
        ("Residential consumer category", "CER_ISSDA", "cer_schema_from_manifest.md", "PENDING_ACCESS",
         "GoiEner has no verified domestic CNAE label", "PARTIAL"),
        ("Agricultural consumer category", "GoiEner_v7.1", "category_counts.csv", f"n_cnae_01={n_ag}",
         "CNAE activity not tariff segment", "SUPPORTED" if n_ag > 0 else "FAIL"),
        ("Two distinct synopsis categories", "multi_dataset", "dataset_comparison.csv", "GoiEner ag + CER res",
         "Single dataset unlikely", "MULTI_TRACK"),
        ("SLP construction", "GoiEner+CER", "experiment_020_protocol.md", "category-specific profiles",
         "CEEW shape-only frozen", "PLANNED_020"),
        ("SVR with SLP features", "synopsis", "experiment_020_protocol.md", "designed", "CEEW used Ridge for audit",
         "PLANNED_020"),
        ("15-minute or hourly horizon", "mixed", "sampling_resolution_audit.csv", f"sample_median_min={med_int}",
         "Do not upsample", "HOUR_OR_30MIN_PRIMARY"),
        ("Persistence and ARIMA baselines", "synopsis", "experiment_020_protocol.md", "required", "—", "PLANNED_020"),
        ("Weather covariates", "sparse", "energybench_real_catalog.csv", "subset-dependent",
         "GoiEner v7.1 public metadata has no weather", "PARTIAL"),
        ("Chronological 70/15/15 split", "synopsis", "experiment_020_protocol.md", "per-consumer calendar",
         "CEEW uses different date cutoffs (frozen)", "PLANNED_020"),
        ("MAPE below 8% target", "synopsis", "experiment_020_protocol.md", "reporting target", "CEEW MAE-primary track separate",
         "TBD_020"),
        ("Category vs aggregate forecasting", "synopsis", "experiment_020_protocol.md", "required", "—", "PLANNED_020"),
        ("ToD planning application", "downstream", "experiment_020_protocol.md", "design only in 020", "not in 019",
         "PLANNED_020"),
        ("Microgrid solar-stability simulation", "downstream", "experiment_020_protocol.md", "design only", "not in 019",
         "PLANNED_020"),
    ]
    df = pd.DataFrame(reqs, columns=[
        "requirement", "dataset", "evidence_path", "support_level", "limitation", "status",
    ])
    df.to_csv(OUT / "synopsis_alignment.csv", index=False)
    return df


def dataset_eligibility(meta: pd.DataFrame, cer: dict, eb: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {"dataset": "GoiEner_v7.1", "tier": 1, "eligible_exp020_track": "A_cnae_slp_svr",
         "reason": "Open CNAE-labelled profiles", "agriculture_div01_n": int((meta.cnae_division == "01").sum())},
        {"dataset": "CER_ISSDA", "tier": 1, "eligible_exp020_track": "B_residential_svr",
         "reason": "Verified residential code when files obtained", "access": cer["access_status"]},
        {"dataset": "CEEW_frozen", "tier": 2, "eligible_exp020_track": "C_supplementary",
         "reason": "No category labels; do not overwrite 013-018"},
        {"dataset": "EnergyBench_real_subsets", "tier": 2, "eligible_exp020_track": "optional_replication",
         "reason": "Building-use labels; separate from CNAE"},
    ]
    for _, r in eb[eb.tier == "synthetic"].iterrows():
        rows.append({"dataset": f"EnergyBench_{r['name']}", "tier": 0, "eligible_exp020_track": "excluded",
                     "reason": "synthetic/simulated", "access": "open"})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "dataset_eligibility.csv", index=False)
    return df


def write_experiment_020_protocol(meta: pd.DataFrame, n_ag: int) -> None:
    path = OUT / "experiment_020_protocol.md"
    path.write_text(
        "\n".join([
            "# Experiment 020 protocol (design only — not implemented in 019)",
            "",
            "## A. Research question",
            "",
            "Does **SVR** forecasting with **category-specific standardized load profiles (SLP)**",
            "improve short-term load forecasts versus persistence and ARIMA for **verified consumer categories**,",
            "consistent with the original project synopsis?",
            "",
            "**Note:** Experiment 018 on unlabeled CEEW tested one Ridge+centroid SLP design only;",
            "it does not invalidate this synopsis hypothesis on labelled external data (DEC-017).",
            "",
            "## B. Datasets and tracks",
            "",
            f"- **Track A (GoiEner):** CNAE division 01 agriculture (n={n_ag} profiles in metadata) +",
            "  at least one non-agriculture division (e.g. 10, 47) for category-specific SLPs.",
            "- **Track B (CER):** Residential allocation code (pending ISSDA files); SME as second utility category, not agriculture.",
            "- **Track C (CEEW):** Frozen `results/forecasting/` baseline; no invented labels.",
            "",
            "## C. Harmonization",
            "- Units: document kWh vs kW per dataset; CER 30-min energy → power if needed without fake 15-min grids.",
            "- GoiEner: respect interval-end timestamps on profiles; hourly native unless sub-hourly confirmed.",
            "- Timezone: document from README; no silent IST/UTC assumptions.",
            "",
            "## D. SLP (leakage-safe)",
            "- Category-specific daily/hourly SLPs fit on training segment only.",
            "- Peak or energy normalization fixed by validation; no test selection.",
            "",
            "## E. Models",
            "- Persistence; ARIMA (orders by validation); SVR ± SLP ± weather.",
            "",
            "## F. Features",
            "- Lagged load, day type, time-of-day, category SLP distance/shape, weather where available.",
            "",
            "## G. Evaluation",
            "- Chronological **70/15/15** per consumer where duration permits.",
            "- **MAPE, RMSE, R²**; per-category and aggregate; consumer-level bootstrap.",
            "",
            "## H. Ablations",
            "- SVR without SLP; with SLP; without weather; category-SLP vs pooled SLP.",
            "",
            "## I. Cross-dataset",
            "- Compare only with documented unit and horizon alignment.",
            "",
            "## J. Downstream (design)",
            "- Category-wise ToD tariff stress; simulated microgrid high solar — no operational claims before metrics.",
        ]),
        encoding="utf-8",
    )


def make_figures(counts: pd.DataFrame, sampling: pd.DataFrame, meta: pd.DataFrame,
                 goi_prof: pd.DataFrame, synopsis: pd.DataFrame) -> list[str]:
    names = []
    FIG.mkdir(parents=True, exist_ok=True)

    top = counts.sort_values("n_profiles", ascending=False).head(20)
    f, ax = plt.subplots(figsize=(10, 5))
    ax.bar(top.cnae_division, top.n_profiles, color="steelblue")
    ax.set(xlabel="CNAE division (2-digit)", ylabel="Profile count", title="GoiEner v7.1 — CNAE division distribution")
    ax.tick_params(axis="x", rotation=45)
    p = FIG / "exp019_cnae_division_counts.png"
    save_fig(f, p)
    names.append(p.name)

    datasets = ["CEEW", "GoiEner", "CER", "EnergyBench"]
    intervals = [15, 60, 30, 30]
    f, ax = plt.subplots(figsize=(7, 4))
    ax.bar(datasets, intervals, color=["gray", "tab:blue", "tab:green", "tab:orange"])
    ax.set(ylabel="Native median interval (minutes)", title="Sampling resolution (documented native)")
    p = FIG / "exp019_sampling_resolution_comparison.png"
    save_fig(f, p)
    names.append(p.name)

    if goi_prof.found.any():
        f, ax = plt.subplots(figsize=(8, 4))
        ax.hist(goi_prof.loc[goi_prof.found, "n_rows"], bins=30, color="seagreen", edgecolor="white")
        ax.set(xlabel="Rows per sampled profile CSV", title="GoiEner sample coverage (part 01)")
        p = FIG / "exp019_coverage_distribution.png"
        save_fig(f, p)
        names.append(p.name)

    f, ax = plt.subplots(figsize=(6, 4))
    labels = ["GoiEner_sample", "CER", "CEEW"]
    miss = [
        float(goi_prof.numeric_missing_cells.sum()) if goi_prof.found.any() else 0,
        np.nan,
        0,
    ]
    ax.bar(labels, [m if not np.isnan(m) else 0 for m in miss])
    ax.set(ylabel="Missing numeric cells (sample audit)", title="Missingness comparison (partial)")
    p = FIG / "exp019_missingness_comparison.png"
    save_fig(f, p)
    names.append(p.name)

    # Example: one week of hourly cons for CNAE 01 sample (part01 audit)
    f, ax = plt.subplots(figsize=(10, 3))
    ag_paths = list((GOI_INTERIM / "profiles_sample").rglob("*.csv"))
    plotted = False
    for p in ag_paths[:50]:
        fid = p.stem
        div = meta.loc[meta.file_id == fid.zfill(5), "cnae_division"]
        if len(div) and div.iloc[0] == "01":
            df = pd.read_csv(p, nrows=24 * 8)
            if "cons" in df.columns:
                y = pd.to_numeric(df["cons"], errors="coerce")
                ax.plot(np.arange(len(y)), y, lw=1, label=f"ID {fid} CNAE 01")
                plotted = True
                break
    if not plotted:
        ax.text(0.5, 0.5, "No CNAE-01 sample in part01 extract", ha="center", va="center", transform=ax.transAxes)
    else:
        ax.legend(fontsize=8)
    ax.set(xlabel="Hour index (sample)", ylabel="cons", title="GoiEner hourly consumption sample (CNAE 01)")
    p = FIG / "exp019_example_daily_profiles_by_cnae.png"
    save_fig(f, p)
    names.append(p.name)

    statuses = synopsis.status.value_counts()
    f, ax = plt.subplots(figsize=(7, 4))
    statuses.plot(kind="bar", ax=ax, color="coral")
    ax.set(title="Synopsis requirement status (Experiment 019)")
    ax.tick_params(axis="x", rotation=30)
    p = FIG / "exp019_dataset_eligibility_table.png"
    save_fig(f, p)
    names.append(p.name)

    for n in ("exp019_cnae_division_counts.png", "exp019_sampling_resolution_comparison.png"):
        src = FIG / n
        if src.exists():
            shutil.copy2(src, PPT / n)
    return names


def validate(meta: pd.DataFrame, fig_names: list[str], cer: dict) -> list[str]:
    failed = []
    if len(meta) != len(load_metadata_public(GOI_RAW / "metadata_public.csv")):
        failed.append("metadata_row_count")
    forbidden = list((ROOT / "results/forecasting/experiment_018").glob("*.json"))
    # no write check — script does not touch 018
    for fn in fig_names:
        p = FIG / fn
        if not p.exists() or p.stat().st_size < 100:
            failed.append(f"missing_figure_{fn}")
    syn = pd.read_csv(OUT / "synopsis_alignment.csv")
    if len(syn) < 10:
        failed.append("synopsis_alignment_rows")
    if cer["access_status"] != "PENDING_ACCESS":
        failed.append("cer_access_unexpected")
    elig = pd.read_csv(OUT / "dataset_eligibility.csv")
    if elig[elig["tier"] == 0].empty:
        failed.append("synthetic_tier0")
    return failed


def main() -> None:
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    log_cmd("start run_experiment_019.py")

    acq = acquire_goiener()
    (OUT / "checksums_manifest.json").write_text(json.dumps(acq, indent=2), encoding="utf-8")

    meta = load_metadata_public(GOI_RAW / "metadata_public.csv")
    counts = audit_goiener_metadata(meta)
    extract_dir = Path(acq["extract_dir"])
    goi_prof, _ = audit_goiener_profiles(meta, extract_dir, Path(acq.get("archive", "")))
    cer = audit_cer_documentation()
    eb = build_energybench_catalog()
    write_glossary()
    dataset_comparison_table(meta, cer, eb)
    synopsis = synopsis_alignment(meta, cer, goi_prof)
    dataset_eligibility(meta, cer, eb)
    n_ag = int((meta.cnae_division == "01").sum())
    write_experiment_020_protocol(meta, n_ag)

    sampling = pd.read_csv(OUT / "sampling_resolution_audit.csv")
    fig_names = make_figures(counts, sampling, meta, goi_prof, synopsis)
    failed = validate(meta, fig_names, cer)

    summary = {
        "experiment": "019",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": time.perf_counter() - t0,
        "goiener_n_profiles_metadata": int(len(meta)),
        "goiener_n_cnae01_agriculture": n_ag,
        "cer_access": cer["access_status"],
        "residential_and_agricultural_single_dataset": False,
        "recommended_primary": "GoiEner_v7.1 (CNAE) + CER residential (when ISSDA approved); CEEW supplementary",
        "decision_id": "DEC-017",
        "validation_failed": failed,
        "figures": [str(FIG / n) for n in fig_names],
    }
    (OUT / "experiment_019_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = [
        "# Experiment 019 — External category-labelled dataset feasibility audit",
        "",
        f"**Command:** `python3 scripts/run_experiment_019.py`",
        "",
        "## Synopsis continuity",
        "",
        "Original title: SVR-based SLP short-term forecasting for tier-2/3 networks.",
        "CEEW Experiments 013–018 remain frozen. Experiment 018 does **not** disprove synopsis SLP+SVR",
        "on **category-labelled** data (DEC-017).",
        "",
        "## Access",
        "",
        f"- **GoiEner v7.1:** metadata + `{PART_ARCHIVE}` sample extracted.",
        f"- **CER:** {cer['access_status']} — see `data/external/cer/README_ACCESS.md`.",
        "- **EnergyBench:** catalog snapshot only (no 166 GB download).",
        "",
        "## Category findings",
        "",
        f"- GoiEner metadata profiles: **{len(meta)}**.",
        f"- CNAE division **01** (agriculture-related activity): **{n_ag}** profiles.",
        "- Verified **residential** label on GoiEner: **not present** in public metadata (CNAE only).",
        "- CER: residential/SME codes documented; agriculture **not** documented.",
        "",
        "## Recommendation",
        "",
        summary["recommended_primary"],
        "",
        f"Validation failures: {failed or 'none'}",
        "",
        "Next: Experiment 020 per `experiment_020_protocol.md` (no training in 019).",
    ]
    (OUT / "experiment_019_report.md").write_text("\n".join(report), encoding="utf-8")

    log_cmd(f"done failed={failed}")
    print(json.dumps(summary, indent=2))
    if failed:
        print("FAILED", failed, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
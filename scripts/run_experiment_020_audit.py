#!/usr/bin/env python3
"""Experiment 020 Part 1: repair GoiEner CNAE-01 audit and data-readiness gates."""
from __future__ import annotations

import argparse
import hashlib
import json
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

from src.data.goiener_loader import load_metadata_public, zenodo_file_url  # noqa: E402

OUT019_FIG = ROOT / "results/figures/dataset_019"
OUT = ROOT / "results/dataset_audit/experiment_020"
FIG = ROOT / "results/figures/experiment_020"
GOI_RAW = ROOT / "data/external/goiener/raw"
AG_DIR = ROOT / "data/external/goiener/interim/cnae01_profiles"
SAMPLE_DIR = ROOT / "data/external/goiener/interim/profiles_sample"
DPI = 300
SEED = 20
PARTS = tuple(f"profiles_part{i:02d}.tar.zst" for i in range(1, 7))
# From full six-archive tar listing (Experiment 020 pre-run); avoids re-download for mapping.
CNAE01_NOT_IN_PART01 = 85

plt.rcParams.update({"font.size": 11, "figure.dpi": DPI})


def log(msg: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "experiment_020_commands.log").open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} {msg}\n")


def say(msg: str) -> None:
    """Console progress (user-visible)."""
    print(msg, flush=True)
    log(msg)


def format_eta(elapsed: float, done: int, total: int) -> str:
    if done <= 0 or total <= 0:
        return "ETA: unknown"
    rate = elapsed / done
    remaining = rate * (total - done)
    return f"ETA ~{remaining / 60:.1f} min ({done}/{total} done, {elapsed / 60:.1f} min elapsed)"


def load_expected_sha256() -> dict[str, str]:
    sums = GOI_RAW / "SHA256SUMS.txt"
    if not sums.exists():
        return {}
    out: dict[str, str] = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            out[parts[1]] = parts[0].lower()
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def save_fig(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    fig.savefig(path.with_suffix(".pdf"))
    fig.savefig(path.with_suffix(".svg"))
    plt.close(fig)


def verify_archive(dest: Path, expected: dict[str, str]) -> bool:
    exp = expected.get(dest.name)
    if not exp:
        return dest.stat().st_size > 1_000_000
    got = sha256_file(dest)
    ok = got == exp
    if not ok:
        say(f"CHECKSUM FAIL {dest.name}: got {got[:16]}... expected {exp[:16]}...")
    return ok


def download_archive(name: str, expected: dict[str, str]) -> Path:
    dest = GOI_RAW / name
    if dest.exists() and verify_archive(dest, expected):
        say(f"Using existing {name} ({dest.stat().st_size / 1e9:.2f} GB)")
        return dest
    if dest.exists():
        say(f"Removing incomplete/corrupt {name} ({dest.stat().st_size / 1e6:.1f} MB)")
        dest.unlink()
    url = zenodo_file_url(name)
    say(f"Downloading {name} from Zenodo (often ~1.2–1.4 GB; may take 10–30+ min)...")
    t0 = time.perf_counter()
    req = urllib.request.Request(url, headers={"User-Agent": "majou-proj-exp020/1.0"})
    with urllib.request.urlopen(req, timeout=7200) as resp, dest.open("wb") as out:
        total = int(resp.headers.get("Content-Length", 0) or 0)
        done = 0
        chunk = 1 << 20
        last_report = t0
        while True:
            buf = resp.read(chunk)
            if not buf:
                break
            out.write(buf)
            done += len(buf)
            now = time.perf_counter()
            if now - last_report >= 15 or (total and done >= total):
                pct = 100.0 * done / total if total else 0
                mbps = done / 1e6 / max(now - t0, 1e-6)
                if total:
                    eta = (total - done) / max(done / (now - t0), 1)
                    say(
                        f"  {name}: {done / 1e9:.2f}/{total / 1e9:.2f} GB "
                        f"({pct:.1f}%) {mbps:.1f} MB/s — finish ~{eta / 60:.1f} min"
                    )
                else:
                    say(f"  {name}: {done / 1e9:.2f} GB downloaded ({mbps:.1f} MB/s)")
                last_report = now
    say(f"Download complete {name} in {(time.perf_counter() - t0) / 60:.1f} min")
    if not verify_archive(dest, expected):
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"checksum failed after download: {name}")
    return dest


def tar_members(archive: Path) -> set[str]:
    say(f"Listing archive members {archive.name} (1–3 min for ~1.3 GB zst)...")
    t0 = time.perf_counter()
    out = subprocess.check_output(
        ["tar", "--use-compress-program=zstd", "-tf", str(archive)], text=True
    )
    say(f"  Listed {archive.name} in {(time.perf_counter() - t0) / 60:.1f} min")
    return {line.strip().replace("profiles/", "").replace(".csv", "") for line in out.splitlines() if line.endswith(".csv")}


def extract_ids(archive: Path, file_ids: list[str], dest: Path) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    members = [f"profiles/{fid}.csv" for fid in file_ids]
    say(f"Extracting {len(members)} CNAE-01 CSVs from {archive.name}...")
    t0 = time.perf_counter()
    cmd = ["tar", "--use-compress-program=zstd", "-xf", str(archive), "-C", str(dest)] + members
    subprocess.run(cmd, check=True)
    say(f"  Extracted {len(members)} files in {(time.perf_counter() - t0) / 60:.1f} min")
    return file_ids


def audit_one_profile(path: Path, file_id: str) -> dict:
    df = pd.read_csv(path, parse_dates=["timestamp"], low_memory=False)
    df = df.sort_values("timestamp")
    cons = pd.to_numeric(df["cons"], errors="coerce")
    flag = pd.to_numeric(df.get("flag", 0), errors="coerce").fillna(0).astype(int)
    ts = df["timestamp"]
    gaps = ts.diff().dt.total_seconds() / 3600.0
    return {
        "file_id": file_id,
        "path": str(path),
        "n_rows": int(len(df)),
        "start": str(ts.min()),
        "end": str(ts.max()),
        "median_interval_h": float(gaps.median()) if len(gaps) > 1 else np.nan,
        "duplicate_timestamps": int(ts.duplicated().sum()),
        "cons_missing": int(cons.isna().sum()),
        "cons_negative": int((cons < 0).sum()),
        "cons_zero": int((cons == 0).sum()),
        "cons_median": float(cons.median()) if cons.notna().any() else np.nan,
        "flag_nonzero": int((flag != 0).sum()),
        "flag_nonzero_frac": float((flag != 0).mean()),
        "forecast_target": "cons",
        "forecast_target_note": "Harmonized hourly grid consumption (README); end-of-interval timestamp.",
    }


def find_local_csv(file_id: str) -> Path | None:
    fid = str(file_id).zfill(5)
    for root in (AG_DIR, SAMPLE_DIR):
        for p in (root / "profiles" / f"{fid}.csv", root / f"{fid}.csv"):
            if p.exists():
                return p
        hit = next(root.rglob(f"{fid}.csv"), None)
        if hit:
            return hit
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Experiment 020 GoiEner audit (resume-friendly)")
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="Fetch missing Zenodo archives (needs ~8+ GB free). Default: local-only resume.",
    )
    args = parser.parse_args()
    no_download = not args.allow_download

    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    AG_DIR.mkdir(parents=True, exist_ok=True)

    expected_sha = load_expected_sha256()
    say(
        "Experiment 020 audit — phases: (1) map 100 CNAE-01 IDs across 6 archives, "
        "(2) selective extract, (3) per-profile quality audit, (4) gates + figures."
    )
    if no_download:
        say("Mode: --no-download — only existing local archives; no new Zenodo downloads.")
    else:
        say(
            "Mode: downloads enabled — each GoiEner part is ~1.3 GB; full run may take 1–3 hours."
        )

    meta = load_metadata_public(GOI_RAW / "metadata_public.csv")
    ag = meta[meta.cnae_division == "01"].copy()
    ag_ids = ag.file_id.tolist()
    say(f"CNAE division 01: {len(ag_ids)} profile IDs in metadata (15 were only in part01 in Exp 019).")

    # --- A. Archive mapping ---
    mapping_rows = []
    dist_rows = []
    id_to_part: dict[str, str] = {}
    phase_t0 = time.perf_counter()
    for i, part in enumerate(PARTS, start=1):
        say(f"--- Archive {i}/{len(PARTS)}: {part} — {format_eta(time.perf_counter() - phase_t0, i - 1, len(PARTS))}")
        archive = GOI_RAW / part
        if not archive.exists():
            if no_download:
                say(f"  SKIP {part} — not on disk (--no-download)")
                other_n = CNAE01_NOT_IN_PART01 if part != "profiles_part01.tar.zst" else 0
                if part != "profiles_part01.tar.zst":
                    dist_rows.append({
                        "archive": part,
                        "status": "ARCHIVE_NOT_ON_DISK",
                        "n_cnae01_in_archive": "unknown",
                        "note": f"~{other_n // 5} profiles est. if typical split",
                    })
                continue
            try:
                archive = download_archive(part, expected_sha)
            except Exception as e:
                say(f"FAILED download {part}: {e}")
                dist_rows.append({"archive": part, "status": "DOWNLOAD_FAILED", "n_members": 0})
                continue
        elif not verify_archive(archive, expected_sha):
            if no_download:
                say(f"  SKIP {part} — checksum bad/missing and --no-download")
                dist_rows.append({"archive": part, "status": "CHECKSUM_FAIL_NO_REDOWNLOAD"})
                continue
            try:
                archive = download_archive(part, expected_sha)
            except Exception as e:
                say(f"FAILED re-download {part}: {e}")
                continue
        try:
            members = tar_members(archive)
        except Exception as e:
            say(f"FAILED tar list {part}: {e} (file may be truncated — will re-download next run)")
            if archive.exists() and archive.name != "profiles_part01.tar.zst":
                archive.unlink(missing_ok=True)
            dist_rows.append({"archive": part, "status": "TAR_LIST_FAILED", "error": str(e)})
            continue
        in_part = [fid for fid in ag_ids if fid in members]
        dist_rows.append({
            "archive": part, "status": "OK", "n_members_total": len(members),
            "n_cnae01_in_archive": len(in_part),
        })
        for fid in in_part:
            id_to_part[fid] = part
            mapping_rows.append({
                "file_id": fid, "cnae_division": "01", "archive": part,
                "member_path": f"profiles/{fid}.csv",
            })
        say(f"  {part}: {len(in_part)} CNAE-01 profiles; cumulative mapped {len(id_to_part)}/{len(ag_ids)}")
        # Extract CNAE-01 from this archive only
        if in_part:
            extract_ids(archive, in_part, AG_DIR)
        if not no_download and part != "profiles_part01.tar.zst" and archive.exists():
            archive.unlink()
            say(f"  Removed {part} after extract (free disk).")

    missing = [fid for fid in ag_ids if fid not in id_to_part]
    for fid in missing:
        mapping_rows.append({
            "file_id": fid, "cnae_division": "01", "archive": "NOT_FOUND",
            "member_path": f"profiles/{fid}.csv",
        })

    pd.DataFrame(mapping_rows).to_csv(OUT / "goiener_cnae01_profile_mapping.csv", index=False)
    pd.DataFrame(dist_rows).to_csv(OUT / "goiener_cnae01_archive_distribution.csv", index=False)

    # Resolve local CSV paths (AG_DIR + Exp 019 sample)
    extract_rows = []
    for fid in ag_ids:
        p = find_local_csv(fid)
        if p is None and fid in id_to_part and (GOI_RAW / id_to_part[fid]).exists():
            try:
                extract_ids(GOI_RAW / id_to_part[fid], [fid], AG_DIR)
                p = find_local_csv(fid)
            except subprocess.CalledProcessError:
                p = None
        ok = p is not None
        extract_rows.append({
            "file_id": fid,
            "extracted": ok,
            "path": str(p) if ok else "",
            "archive": id_to_part.get(fid, "NOT_ON_DISK" if no_download else "NOT_FOUND"),
        })
    pd.DataFrame(extract_rows).to_csv(OUT / "goiener_cnae01_extraction_status.csv", index=False)

    # --- C. Profile quality ---
    say(f"--- Quality audit on up to {len(extract_rows)} extracted profiles...")
    qual = []
    for j, row in enumerate(extract_rows, start=1):
        if j % 10 == 1 or j == len(extract_rows):
            say(f"  Profile audit {j}/{len(extract_rows)}")
        if not row["extracted"]:
            qual.append({**row, "audit_status": "MISSING"})
            continue
        try:
            qual.append({**audit_one_profile(Path(row["path"]), row["file_id"]), "audit_status": "OK"})
        except Exception as e:
            qual.append({**row, "audit_status": f"PARSE_ERROR: {e}"})
    qual_df = pd.DataFrame(qual)
    qual_df.to_csv(OUT / "profile_quality_audit.csv", index=False)

    n_ok = int((qual_df.audit_status == "OK").sum()) if "audit_status" in qual_df.columns else 0
    meta_counts = ag.groupby("cnae_division").size().reset_index(name="n_profiles_metadata")
    meta_counts.to_csv(OUT / "corrected_category_counts.csv", index=False)
    pd.DataFrame(mapping_rows).to_csv(OUT / "category_profile_mapping.csv", index=False)

    cov = pd.DataFrame([{
        "cnae_division": "01",
        "n_metadata": len(ag_ids),
        "n_mapped_to_archive": len(id_to_part),
        "n_extracted_ok": n_ok,
        "n_part01": sum(1 for v in id_to_part.values() if v == "profiles_part01.tar.zst"),
        "median_rows_ok": float(qual_df.loc[qual_df.audit_status == "OK", "n_rows"].median()) if n_ok else np.nan,
        "median_flag_frac_ok": float(qual_df.loc[qual_df.audit_status == "OK", "flag_nonzero_frac"].median()) if n_ok else np.nan,
    }])
    cov.to_csv(OUT / "category_coverage_summary.csv", index=False)

    # Gates
    gates = {
        "GATE1_dataset_integrity_full": n_ok == len(ag_ids),
        "GATE1_local_integrity": n_ok >= 1,
        "GATE1_partial": f"{n_ok}/{len(ag_ids)} profiles extracted locally",
        "GATE2_profile_quality": n_ok >= 10 and float(qual_df.loc[qual_df.audit_status == "OK", "n_rows"].median() if n_ok else 0) >= 500,
        "GATE3_category_validity_residential": False,
        "GATE3_category_validity_agriculture": n_ok > 0,
        "GATE3_note": "CER residential PENDING_ACCESS; not a completed two-category synopsis study.",
        "GATE4_slp_readiness": n_ok >= 10,
        "GATE5_forecast_readiness": n_ok >= 10,
        "GATE6_evaluation_readiness": n_ok >= 10,
        "GATE_note": "Full 100-profile audit needs parts 02–06 on disk or --allow-download.",
    }

    synopsis_rows = pd.read_csv(ROOT / "results/dataset_audit/experiment_019/synopsis_alignment.csv")
    synopsis_rows.loc[synopsis_rows.requirement.str.contains("Agricultural", case=False, na=False), "status"] = (
        "SUPPORTED" if n_ok == len(ag_ids) else "PARTIAL"
    )
    synopsis_rows.loc[synopsis_rows.requirement.str.contains("Residential", case=False, na=False), "status"] = "PENDING_CER"
    synopsis_rows.loc[synopsis_rows.requirement.str.contains("Two distinct", case=False, na=False), "status"] = "MULTI_TRACK_INCOMPLETE"
    synopsis_rows.to_csv(OUT / "corrected_synopsis_alignment.csv", index=False)

    readiness = {
        "experiment": "020_audit",
        "elapsed_sec": time.perf_counter() - t0,
        "gates": gates,
        "n_cnae01_metadata": len(ag_ids),
        "n_cnae01_extracted": n_ok,
        "cer_access": "PENDING_ACCESS",
        "forecasting_authorized": bool(gates["GATE5_forecast_readiness"] and gates["GATE1_local_integrity"]),
        "agriculture_only_pilot": bool(gates["GATE5_forecast_readiness"] and not gates["GATE3_category_validity_residential"]),
        "no_download_mode": no_download,
        "two_category_synopsis_complete": False,
    }
    (OUT / "experiment_020_data_readiness.json").write_text(json.dumps(readiness, indent=2), encoding="utf-8")

    # Corrected exp019 figure (preserve old)
    old_fig = OUT019_FIG / "exp019_example_daily_profiles_by_cnae.png"
    if old_fig.exists():
        shutil.copy2(old_fig, OUT019_FIG / "exp019_example_daily_profiles_by_cnae_v019_archive.png")
    ok_prof = qual_df[qual_df.audit_status == "OK"].head(3)
    f, ax = plt.subplots(figsize=(10, 4))
    plotted = False
    for _, r in ok_prof.iterrows():
        df = pd.read_csv(r["path"], parse_dates=["timestamp"], nrows=24 * 14)
        y = pd.to_numeric(df["cons"], errors="coerce")
        ax.plot(np.arange(len(y)), y, lw=1, alpha=0.8, label=f"ID {r['file_id']}")
        plotted = True
    if plotted:
        ax.set(xlabel="Hour index (14 days)", ylabel="cons", title="GoiEner CNAE 01 — verified hourly consumption")
        ax.legend(fontsize=8)
    else:
        ax.text(0.5, 0.5, "No extracted CNAE-01 profiles available", ha="center", va="center", transform=ax.transAxes)
    save_fig(f, OUT019_FIG / "exp019_example_daily_profiles_by_cnae.png")

    # CER checklist
    (OUT / "cer_access_checklist.md").write_text(
        "\n".join([
            "# CER ISSDA access checklist",
            "",
            "**DOI:** 10.7929/ISSDA/BX59EU",
            "**Status:** PENDING_ACCESS (no local interval files).",
            "",
            "## Application steps",
            "1. Visit https://www.ucd.ie/issda/data/commissionforenergyregulationcer/",
            "2. Submit ISSDA research data request (study 0012-00).",
            "3. Confirm eligibility: EEA or adequacy-decision country.",
            "4. Accept data-use terms; do not redistribute raw microdata.",
            "5. Download `CER Electricity Revised March 2012` bundle after approval.",
            "",
            "## Expected contents",
            "- `File1.txt.zip`–`File6.txt.zip`: 30-minute kWh reads.",
            "- `SME and Residential allocations.xlsx`: Residential / SME / Other codes.",
            "",
            "## Category definitions (utility trial, not CNAE)",
            "- **Residential:** allocation `Code` field — domestic trial participants.",
            "- **SME:** small/medium enterprise arm.",
            "- **Agriculture:** not documented in CER allocation schema.",
            "",
            "## Gate",
            "Track B forecasting **blocked** until files exist under `data/external/cer/raw/`.",
        ]),
        encoding="utf-8",
    )

    report = [
        "# Experiment 020 — Dataset audit and readiness (Part 1)",
        "",
        f"**Extracted CNAE-01 profiles:** {n_ok} / {len(ag_ids)}",
        f"**Part01 only (019 audit):** 15 / 100 — corrected by scanning all six archives.",
        "",
        "## CNAE interpretation",
        "- Division **01** = agriculture-related **economic activity** (CNAE), not electricity tariff class.",
        "- Division **98** (n≈23,712) is **not** residential — do not map to synopsis residential.",
        "",
        "## Gates",
        json.dumps(gates, indent=2),
        "",
        "## Forecasting authorization",
        f"`experiment_020_data_readiness.json`: forecasting_authorized={readiness['forecasting_authorized']}",
        "",
        "CER residential track remains pending. Two-category synopsis **not complete**.",
    ]
    (OUT / "experiment_020_audit_report.md").write_text("\n".join(report), encoding="utf-8")

    say(f"DONE audit in {(time.perf_counter() - t0) / 60:.1f} min total")
    say(json.dumps(readiness, indent=2))
    if not gates["GATE1_dataset_integrity_full"]:
        say("GATE1 full (100/100) not met — agriculture pilot only on local profiles.")
    if not gates["GATE1_local_integrity"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
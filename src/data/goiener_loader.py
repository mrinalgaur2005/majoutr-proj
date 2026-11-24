"""Read-only helpers for GoiEner Zenodo v7.1 profiles (Experiment 019)."""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

ZENODO_RECORD = "22313409"
ZENODO_BASE = f"https://zenodo.org/records/{ZENODO_RECORD}/files"


def zenodo_file_url(name: str) -> str:
    """Prefer Zenodo API /content URLs (record HTML URLs may return 5xx)."""
    return f"https://zenodo.org/api/records/{ZENODO_RECORD}/files/{name}/content"


def parse_sha256sums(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            out[parts[1]] = parts[0].lower()
    return out


def load_metadata_public(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    id_col = "file_id" if "file_id" in df.columns else "id"
    df["file_id"] = pd.to_numeric(df[id_col], errors="coerce").astype("Int64").astype(str).str.zfill(5)
    div = pd.to_numeric(df["cnae_division"], errors="coerce")
    df["cnae_division"] = div.apply(lambda x: f"{int(x):02d}" if pd.notna(x) else "NA")
    return df


def stratified_sample_ids(meta: pd.DataFrame, seed: int, per_div_cap: int = 15, max_total: int = 400) -> list[str]:
    """Sample file_id across CNAE divisions."""
    import numpy as np

    rng = np.random.default_rng(seed)
    chosen: list[str] = []
    id_col = "file_id"
    for div, g in meta.groupby("cnae_division"):
        ids = g[id_col].astype(str).tolist()
        rng.shuffle(ids)
        take = min(per_div_cap, len(ids))
        chosen.extend(ids[:take])
    if len(chosen) > max_total:
        rng.shuffle(chosen)
        chosen = chosen[:max_total]
    return chosen


def find_profile_csvs(root: Path, file_ids: set[str]) -> dict[str, Path]:
    """Map file_id to extracted CSV path (recursive search under extract dir)."""
    found: dict[str, Path] = {}
    for p in root.rglob("*.csv"):
        stem = p.stem
        if stem in file_ids:
            found[stem] = p
        else:
            m = re.search(r"(\d{5,})", stem)
            if m and m.group(1) in file_ids:
                found[m.group(1)] = p
    return found


def audit_profile_csv(path: Path) -> dict:
    """Lightweight audit of one GoiEner profile CSV."""
    with path.open(encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return {"error": "empty", "path": str(path)}
        ts_col = None
        for i, h in enumerate(header):
            hl = h.lower()
            if "timestamp" in hl or hl in ("time", "datetime", "date"):
                ts_col = i
                break
        if ts_col is None:
            ts_col = 0
        numeric_cols = [i for i in range(len(header)) if i != ts_col]
        n = 0
        dup_ts = 0
        negatives = 0
        zeros = 0
        missing = 0
        timestamps: list[str] = []
        prev_ts = None
        for row in reader:
            if not row or len(row) <= ts_col:
                continue
            n += 1
            ts = row[ts_col].strip()
            timestamps.append(ts)
            if prev_ts is not None and ts == prev_ts:
                dup_ts += 1
            prev_ts = ts
            for i in numeric_cols:
                if i >= len(row):
                    missing += 1
                    continue
                v = row[i].strip()
                if v == "" or v.lower() in ("na", "nan"):
                    missing += 1
                    continue
                try:
                    x = float(v)
                    if x < 0:
                        negatives += 1
                    if x == 0:
                        zeros += 1
                except ValueError:
                    missing += 1
        deltas_min: list[float] = []
        if len(timestamps) >= 2:
            try:
                t = pd.to_datetime(pd.Series(timestamps), errors="coerce")
                d = t.diff().dt.total_seconds() / 60.0
                deltas_min = d.dropna().tolist()
            except Exception:
                pass
        median_delta = float(pd.Series(deltas_min).median()) if deltas_min else None
        return {
            "path": str(path),
            "n_rows": n,
            "n_columns": len(header),
            "columns": header,
            "timestamp_column": header[ts_col],
            "duplicate_timestamps": dup_ts,
            "numeric_missing_cells": missing,
            "numeric_negatives": negatives,
            "numeric_zeros": zeros,
            "median_interval_minutes": median_delta,
            "first_timestamp": timestamps[0] if timestamps else None,
            "last_timestamp": timestamps[-1] if timestamps else None,
        }
"""Read original CEEW Dataverse files without changing them.

`t_kWh` is retained as interval energy. `load_kw` is its derived three-minute
average active power (interval_energy_kwh / 0.05); it is never a rename.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

RAW = Path(__file__).resolve().parents[2] / "data/raw/ceew_mathura_bareilly"
FILES = {"Bareilly": ["CEEW - Smart meter data Bareilly 2019.tab", "CEEW - Smart meter data Bareilly 2020.csv", "CEEW - Smart meter data Bareilly 2021.csv"],
         "Mathura": ["CEEW - Smart meter data Mathura 2019.csv", "CEEW - Smart meter data Mathura 2020.csv", "CEEW - Smart meter data Mathura 2021.tab"]}
RENAME = {"x_Timestamp": "timestamp", "meter": "meter_id", "t_kWh": "interval_energy_kwh",
          "z_Avg Voltage (Volt)": "voltage_v", "z_Avg Current (Amp)": "current_a", "y_Freq (Hz)": "frequency_hz"}

def iter_ceew(city: str | None = None, chunksize: int = 250_000):
    """Yield canonical raw rows in chunks; no imputation or deduplication occurs."""
    cities = [city] if city else list(FILES)
    for current_city in cities:
        for name in FILES[current_city]:
            path = RAW / name
            with path.open("r", encoding="utf-8", errors="ignore") as source:
                header = source.readline()
            sep = "\t" if "\t" in header else ","
            for df in pd.read_csv(path, sep=sep, chunksize=chunksize):
                df = df.rename(columns=RENAME)
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
                df["meter_id"] = df["meter_id"].astype(str).str.strip('"')
                df["city"] = current_city
                # Source README says consumption is reported every three minutes.
                df["load_kw"] = pd.to_numeric(df["interval_energy_kwh"], errors="coerce") / 0.05
                yield df[["timestamp", "meter_id", "interval_energy_kwh", "load_kw", "voltage_v", "current_a", "frequency_hz", "city"]]

def load_ceew(city: str | None = None) -> pd.DataFrame:
    """Materialize canonical rows, sorted chronologically. Intended for bounded analyses."""
    out = pd.concat(list(iter_ceew(city)), ignore_index=True)
    return out.sort_values(["meter_id", "timestamp"], kind="stable").reset_index(drop=True)

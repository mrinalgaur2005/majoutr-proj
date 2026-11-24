"""Chunked, read-only audit for the downloaded CEEW source files."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
import sys
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data.ceew_loader import RAW, iter_ceew

OUT = Path(__file__).resolve().parents[1] / "results/ceew"

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows=0; nulls=Counter(); negatives=Counter(); zeros=Counter(); meters=set(); cities=Counter(); ranges={}; samples=[]
    # Per-meter timestamps are collected compactly as integer ns for interval/coverage audit.
    timestamps={}
    for df in iter_ceew():
        rows += len(df); meters.update(df.meter_id.dropna().unique()); cities.update(df.city)
        for c in ["interval_energy_kwh","voltage_v","current_a","frequency_hz"]:
            x=pd.to_numeric(df[c], errors="coerce"); nulls[c]+=int(x.isna().sum()); negatives[c]+=int((x<0).sum()); zeros[c]+=int((x==0).sum())
        for city,g in df.groupby("city"):
            lo,hi=g.timestamp.min(),g.timestamp.max(); old=ranges.get(city,(lo,hi)); ranges[city]=(min(old[0],lo),max(old[1],hi))
        for m,g in df.groupby("meter_id"): timestamps.setdefault(m,[]).extend(g.timestamp.dropna().astype("int64").tolist())
        if len(samples)<10000: samples.extend(df[["interval_energy_kwh","load_kw","voltage_v","current_a"]].dropna().head(10000-len(samples)).to_dict("records"))
    per_meter=[]
    for m,vals in timestamps.items():
        s=pd.Series(sorted(vals)); d=s.diff().dropna()/60_000_000_000
        per_meter.append({"meter_id":m,"rows":len(s),"start":str(pd.to_datetime(s.iloc[0])),"end":str(pd.to_datetime(s.iloc[-1])),"duplicates":int(s.duplicated().sum()),"three_minute_intervals":int((d==3).sum()),"gaps_over_3_minutes":int((d>3).sum()),"max_gap_minutes":float(d.max()) if len(d) else 0})
    sample=pd.DataFrame(samples); apparent_kw=(sample.voltage_v*sample.current_a/1000)
    audit={"source":"Agrawal et al., Harvard Dataverse DOI 10.7910/DVN/GOCHJH","raw_directory":str(RAW),"raw_files":[{"name":p.name,"bytes":p.stat().st_size} for p in sorted(RAW.iterdir())],"rows":rows,"unique_meters":len(meters),"meters":sorted(meters),"rows_by_city":dict(cities),"timestamp_ranges":{k:{"start":str(v[0]),"end":str(v[1])} for k,v in ranges.items()},"missing_values":dict(nulls),"negative_values":dict(negatives),"zero_values":dict(zeros),"units":{"interval_energy_kwh":"kWh per documented three-minute record; derived load_kw = interval_energy_kwh / 0.05","voltage_v":"Volt","current_a":"Amp","frequency_hz":"Hz"},"empirical_energy_power_check":{"median_derived_load_kw":float(sample.load_kw.median()),"median_voltage_times_current_kw":float(apparent_kw.median()),"note":"Similar magnitudes support interval-energy interpretation; active power and apparent power need not be identical."},"consumer_category_labels":False,"feeder_or_substation_metadata":False,"weather_fields":False,"per_meter":per_meter}
    (OUT/"dataset_audit.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
    (OUT/"per_meter_coverage.csv").write_text(pd.DataFrame(per_meter).to_csv(index=False),encoding="utf-8")
    print(json.dumps({k:audit[k] for k in ["rows","unique_meters","rows_by_city","timestamp_ranges"]},indent=2))
if __name__ == "__main__": main()

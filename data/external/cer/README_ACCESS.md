# Irish CER Smart Metering Project — access (Experiment 019)

**DOI:** [10.7929/ISSDA/BX59EU](https://doi.org/10.7929/ISSDA/BX59EU)  
**Publisher:** Irish Social Science Data Archive (ISSDA), University College Dublin  
**Study:** 0012-00 — Electricity Customer Behaviour Trial, 2009–2010

## Access status

Experiment 019 did **not** download CER interval data. ISSDA restricts distribution to the EEA and countries with adequacy decisions. Request access via:

https://www.ucd.ie/issda/data/commissionforenergyregulationcer/

After approval, place files under `data/external/cer/raw/` using the folder layout described in public manifests (e.g. `CER Electricity Revised March 2012`).

## Verified from public documentation (not row counts from this repo)

- Interval reads: 30-minute **kWh** per half-hour slot (48 slots per day).
- Allocation file: meter ID, residential/SME/other code, tariff and stimulus fields.
- **Residential** and **SME** are utility trial categories — not CNAE economic-activity codes.
- **No agricultural consumer category** is documented in the allocation schema.

Do not use CER path for Experiment 019 metrics until files are present and audited.
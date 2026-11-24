# CER ISSDA access checklist

**DOI:** 10.7929/ISSDA/BX59EU
**Status:** PENDING_ACCESS (no local interval files).

## Application steps
1. Visit https://www.ucd.ie/issda/data/commissionforenergyregulationcer/
2. Submit ISSDA research data request (study 0012-00).
3. Confirm eligibility: EEA or adequacy-decision country.
4. Accept data-use terms; do not redistribute raw microdata.
5. Download `CER Electricity Revised March 2012` bundle after approval.

## Expected contents
- `File1.txt.zip`–`File6.txt.zip`: 30-minute kWh reads.
- `SME and Residential allocations.xlsx`: Residential / SME / Other codes.

## Category definitions (utility trial, not CNAE)
- **Residential:** allocation `Code` field — domestic trial participants.
- **SME:** small/medium enterprise arm.
- **Agriculture:** not documented in CER allocation schema.

## Gate
Track B forecasting **blocked** until files exist under `data/external/cer/raw/`.

## GoiEner expansion gates (022)

1. Publisher documentation for `cons` units and `flag`.
2. Approved forecast protocol v2 (metric + outlier + regime).
3. Baseline competency: learned model within pre-specified MAE margin of persistence on **validation**.
4. Disk and checksum plan for archives 02–06 (~8+ GB).
5. Human go/no-go recorded in `decision_register.md`.

**Default 022 recommendation:** NO extract until 1–3 satisfied.

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
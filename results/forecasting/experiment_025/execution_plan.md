# Execution plan — public-data-only roadmap

## Permanent constraint (DEC-025-01)

No email, ISSDA application, or publisher queries. CER **unavailable**.

## Stages

- **025 (this):** Inventory, eligibility, GoiEner 15 QC, Norwegian metadata download, compliance assessment.
- **025B (next):** Download `demand.csv`; ingest subset; timestamp/units audit; decide CONDITIONAL → PRIMARY.
- **025C:** Exploratory **labelled** forecasting on GoiEner 15 at native `cons` scale — **not** binding Exp 024 until metadata gates.
- **CEEW:** Pipeline/repro tests only (frozen 001–018).

## Removed from roadmap

- CER ISSDA submit, GoiEner author query (replaced by public-only paths).

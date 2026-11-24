# Dataset readiness and eligibility — Experiment 024

## Track A — GoiEner v7.1 (agricultural, CNAE division 01)

| Item | Status |
|------|--------|
| Profiles in metadata | 100 CNAE-01 (public Zenodo metadata) |
| Local availability | **15** (profiles_part01 only) |
| Native resolution | **1 hour** — preserve; no upsampling |
| Timestamp convention | **End of interval** (Zenodo v7.1) |
| `cons` units | **UNDOCUMENTED** — report as dataset-native quantity |
| `flag` | **UNDOCUMENTED** — retain column; sensitivity analysis only if author confirms |
| CNAE 98 | **Exclude** from residential proxy |

### Forecasting target (Track A)

- Origin index `i`: last observed row at time `t_i` (end-of-hour stamp).
- Target `y_{i+1}` = `cons` at next chronological row (H=1 hour).
- Features at `i` use `cons` and calendar at times ≤ `t_i` only.

### Scientific defensibility without unit confirmation

- **Permitted:** MAE/RMSE/WAPE/R² on raw `cons`; relative improvements vs persistence; profile-level comparisons.
- **Not permitted:** Claims in kW/kWh; MAPE with fixed ε=1 kWh scale; cross-track absolute MAE vs CER.
- **Blocked:** Archive part02–06 expansion until publisher semantics + DEC-024-04.

### Go/no-go gate (Track A)

| Gate | Requirement |
|------|-------------|
| G-A1 | Protocol v2.1 final **APPROVED** |
| G-A2 | Author reply on `cons`+`flag` **OR** human waiver for native-unit exploratory label |
| G-A3 | No download of parts 02–06 without G-A2 |

---

## Track B — CER ISSDA (residential)

| Item | Status |
|------|--------|
| DOI | 10.7929/ISSDA/BX59EU |
| Access | Package prepared; **NOT SUBMITTED** |
| Native resolution | **30 minutes** (manifest) |
| Units | **kWh per interval** (public manifest) |
| Category codes | `SME and Residential allocations.xlsx` — field `Code` |

### Residential inclusion rule

1. Join interval files to allocation table on meter ID.
2. **Include:** meters with allocation `Code` indicating **Residential** (per spreadsheet legend post-download).
3. **Exclude:** SME codes from residential analysis (separate optional SME track not in synopsis core).
4. **Exclude:** Other/non-residential codes unless registered as sensitivity.

### Post-access eligibility audit (Stage 1)

- Checksum bundle vs ISSDA receipt.
- Per-meter: row count, duplicate (day, time) keys, gap rate, coverage days.
- Minimum technical requirement: enough rows for `floor(0.85*n) > max_lag + 48` (design rule).
- Exclude meters failing >20% missing intervals in any split segment (pre-registered; adjustable only via decision register).

### QC handling

- Duplicate timestamps: keep first occurrence; log count.
- Missing intervals: **do not** synthesize rows; reduce `n_obs` for splits.
- Incomplete days: allowed; no padding.

### Go/no-go gate (Track B)

| Gate | Requirement |
|------|-------------|
| G-B1 | ISSDA approval + files under `data/external/cer/raw/` |
| G-B2 | Allocation join verified |
| G-B3 | ≥1 residential meter passes technical minimum (else track blocked) |

**Do not invent** meter counts or approval timelines.

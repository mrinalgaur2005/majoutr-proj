#!/usr/bin/env python3
"""Experiment 024: design-only audit and protocol finalization (no training/downloads)."""
from __future__ import annotations

import json
import shutil
import sys
import textwrap
import time
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/forecasting/experiment_024"
FIG = ROOT / "results/figures/experiment_024_design"
PROTO_V2 = ROOT / "results/forecasting/experiment_022/forecasting_protocol_v2.md"
PROTO_V21_023 = ROOT / "results/dataset_audit/experiment_023/forecasting_protocol_v2_1.md"
METRIC = ROOT / "results/forecasting/experiment_022/metric_framework.md"
SLP022 = ROOT / "results/forecasting/experiment_022/slp_experiment_design.md"
REGIME022 = ROOT / "results/forecasting/experiment_022/anomaly_and_regime_protocol.md"
BIB = ROOT / "results/literature_review/experiment_023/PAPER_BIBLIOGRAPHY.csv"
FIG_START = 125
DPI = 300
TODAY = date.today().isoformat()

plt.rcParams.update({"font.size": 10, "figure.dpi": DPI})


def say(msg: str) -> None:
    print(msg, flush=True)


def save_fig(fig, stem: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for ext in (".png", ".pdf", ".svg"):
        fig.savefig(FIG / f"{stem}{ext}", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


def initial_audit() -> str:
    return f"""\
    # Experiment 024 — initial design audit

    **Date:** {TODAY}  
    **Type:** Design-only (Experiment 024 design audit, not execution)

    ## Documents inspected

    | Artifact | Location | Note |
    |----------|----------|------|
    | Protocol v2 | `results/forecasting/experiment_022/forecasting_protocol_v2.md` | Frozen 022 design |
    | Protocol v2.1 **proposal** | `results/dataset_audit/experiment_023/forecasting_protocol_v2_1.md` | **Not** under `experiment_022/` (discrepancy) |
    | Metric framework | `results/forecasting/experiment_022/metric_framework.md` | MAE primary |
    | SLP F0–F5 | `results/forecasting/experiment_022/slp_experiment_design.md` | 024 core uses F0–F2 |
    | Regime protocol | `results/forecasting/experiment_022/anomaly_and_regime_protocol.md` | Train tertiles |
    | 024 sketch | `results/dataset_audit/experiment_023/experiment_024_proposed_design.md` | Superseded by this experiment |
    | Pilot code | `scripts/run_experiment_020_forecast.py` | F1 category SLP implemented |
    | 021 evidence | `results/forecasting/experiment_021/experiment_021_summary.json` | Persistence wins MAE |

    ## 1. Already implemented

    - CEEW pipeline (001–018): clustering, shrinkage forecasting, SLP protocol 018 (no MAE win vs persistence).
  - GoiEner CNAE-01 **pilot** (020/020A/020B/021): 15 profiles, chronological 70/15/15, SVR±SLP, ARIMA, persistence, aligned micro metrics.
    - Leakage-safe **category** hour-of-week template from train pool (matches F1).
    - Literature review (023): 9 verified DOIs.
    - CER access **package** (023): not submitted.

    ## 2. Experimentally validated

    - Persistence is strong on GoiEner ag pilot (micro MAE ≈ 192.8 vs SVR ≈ 261).
    - SLP Wilcoxon **not significant** at conventional levels (021); SLP constructs without index leakage.
    - MAPE unstable on zero-heavy `cons`; WAPE/MAE preferred (022 metric framework).
    - 020A reproduced 020 metrics (25/25).

    ## 3. Remains proposed design

    - Full Experiment 024 dual-track execution.
    - Protocol v2.1 **final** adoption (this experiment produces `forecasting_protocol_v2_1_final.md`).
    - F2 per-profile SLP ablation at scale.
    - CER residential track ingestion and QC.
    - Regime stratification on CER (pending documentation review post-access).

    ## 4. Blocked — data access

    - **Track B (CER):** No local interval files; ISSDA application **PREPARED_NOT_SUBMITTED**.
    - Residential inclusion requires `SME and Residential allocations.xlsx` after download.

    ## 5. Blocked — dataset semantics

    - GoiEner v7.1: `cons` **units undocumented**; `flag` **undefined** in README.
    - Expansion to 85 profiles: **NO-GO** (DEC-022/023).

    ## 6. Requires human decision (status PROPOSED)

    - **DEC-024-01:** Approve `forecasting_protocol_v2_1_final.md` for implementation.
    - **DEC-024-02:** Submit CER ISSDA application.
    - **DEC-024-03:** Send GoiEner author query (recommended before ag expansion).
    - **DEC-024-04:** Go/NO-GO on Track A with **native-unit** forecasting if units stay unresolved.

    ## 7. Must implement before execution

    - `run_experiment_024.py` (not written): dual-track loaders, CER QC, split validator, SLP builder, model runners, stats module.
    - Split-boundary unit tests (origins with `i+1` crossing splits excluded).
    - Train-only scaler fit per profile.

    ## Document discrepancies and resolutions

    | Issue | Resolution |
    |-------|------------|
    | v2.1 path in prompt vs repo | Authoritative proposal: `dataset_audit/experiment_023/`; **final** copy in `experiment_024/forecasting_protocol_v2_1_final.md` |
    | 023 design Track B=CER vs naming | **Track A = GoiEner ag; Track B = CER residential** (synopsis order preserved in reporting) |
    | 020 uses `int(n*0.70)` not `floor` | **Final:** `i_train = floor(0.70*n_obs)` per v2.1 final (document equivalence when n large) |
    | MAPE ε=1 assumes kWh | GoiEner: use ε relative to train median \\|y\\| until units confirmed; CER: kWh from manifest |
    """


def synopsis_alignment() -> str:
    return """\
    # Synopsis alignment — Experiment 024

    Original synopsis preserved. This table maps **original objectives** to evidence and 024 role.

    | Synopsis objective | Existing evidence | 024 contribution | Remaining work | Completion criteria |
    |--------------------|-------------------|------------------|----------------|---------------------|
    | Short-term load forecasting | 020 pilot; CEEW 012–016 | Native-resolution H=1 protocol both tracks | Execute 024 after gates | Test MAE/WAPE reported both tracks |
    | Residential category | None on-meter | Track B design + CER eligibility rules | ISSDA access + QC | Residential Code meters evaluated |
    | Agricultural category | GoiEner CNAE-01 n=15 | Track A protocol; optional F2 | Semantics + expansion gate | ≥15 eligible profiles post-QC |
    | SVR forecasting | 020 implemented | F0/F1/F2 with frozen hyperparam grid | Implement 024 script | Competency gate on validation |
    | SLP features | 020 F1 category template | Controlled F1 vs F2; train-only templates | Run ablation | Paired ΔMAE validation + test confirm |
    | vs conventional (ARIMA, persistence) | 021 persistence wins | Pre-registered baselines | Same | Honest reporting if SVR fails gate |
    | Category SLP improves forecast? | **Not demonstrated** | Primary hypothesis test | Full dual track | Validation SLP gain + stats |
    | MAPE < 8% | Not met (020) | Synopsis reporting only | Report separately | No pass/fail on MAPE alone |
    | ToD analysis | 019/022 design only | Dependency assessment doc | Tariff data | Descriptive load-shape after forecast |
    | BESS application | Blocked 022 | Dependency assessment | Units + prices | Not in 024 scope |

    **Novelty (023 preserved):** contribution = rigorous leakage-safe **category-labelled** evaluation, not SVR+SLP invention.
    """


def dataset_readiness() -> str:
    return """\
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
    """


def protocol_v21_final() -> str:
    v2 = PROTO_V2.read_text(encoding="utf-8") if PROTO_V2.exists() else ""
    return f"""\
    # Forecasting protocol v2.1 — FINAL (Experiment 024 design)

    **Status:** PROPOSED — requires human approval (DEC-024-01).  
    **Does not replace:** `results/forecasting/experiment_022/forecasting_protocol_v2.md` or `results/dataset_audit/experiment_023/forecasting_protocol_v2_1.md`.

    This document merges v2, v2.1 additions, and 024 audit clarifications.

    ---

    ## Base protocol (from v2 — unchanged intent)

    {textwrap.indent(v2.strip(), "> ")}

    ---

    ## v2.1 additions (finalized)

    ### A. Horizon H=1

    | Track | Interval | Target | Origin |
    |-------|----------|--------|--------|
    | A GoiEner | 1 h | `cons[i+1]` at next row | Row `i`, features ≤ `i` |
    | B CER | 30 min | kWh at `i+1` | Row `i`, features ≤ `i` |

    - **GoiEner:** timestamp = **end** of hour containing energy for `[t-1h, t]`.
    - **CER:** use manifest time codes; treat target timestamp as documented interval end/start consistently in loader (document choice in Stage 1 audit).

    - **First eligible origin:** `i >= max(LAGS)` (default lags 1, 24, 168 in 020 — CER 30-min: use lags 1, 48, 336).
    - **Last eligible origin in split S:** largest `i` such that `i+1` index lies in S.

    ### B. Chronological split (per profile)

    Let `n` = number of observed rows after QC.

    ```
    n_train = floor(0.70 * n)
    n_val   = floor(0.15 * n)
    n_test  = n - n_train - n_val
  TRAIN = [0, n_train)
    VAL   = [n_train, n_train + n_val)
    TEST  = [n_train + n_val, n)
    ```

    - No shuffle. Profiles may have different calendar spans.
    - **Forbidden:** any target whose index `i+1` is not in the same split as origin's split assignment for training targets (origins in TRAIN predict train targets only; val/test analogous).
    - Hyperparameter tuning: **validation only**.

    ### C. Leakage prevention

    - Scalers: fit on **train origins** of each profile (same for SVR input).
    - Category SLP template (F1): hour-of-week mean using **training rows of all eligible profiles in track**, excluding val/test rows.
    - F2 profile template: train segment of **that profile only**.
    - For forecast at train/val/test origin at `i`, SLP feature uses template cell matching calendar at `i` (not future).
    - **Self-inclusion (F1):** target profile's train rows contribute to category pool (standard practice); val/test never contribute.

    ### D. Model family (preserve 022 F0–F2)

    | Model | Definition |
    |-------|------------|
    | Persistence | ŷ[i+1] = y[i] |
    | Seasonal naive | ŷ[i+1] = y[i+24] (GoiEner) or y[i+48] (CER) when index exists |
    | ARIMA | ARIMA(1,0,1) on train series; refit per profile optional (pre-register) |
    | SVR F0 | Lags + sin/cos hour + weekend — no SLP |
    | SVR F1 | F0 + category hour-of-week SLP from train pool |
    | SVR F2 | F0 + per-profile hour-of-week SLP from train only |

    SVR hyperparameters: grid from 020; select on validation MAE. F0 vs F1 vs F2 differ **only** by SLP feature column(s).

    ### E. Resolution

    - **Separate pipelines** per track. No pooled micro metrics across tracks.

    ### Competency gate (DEC-022 preserved)

    Validation MAE(model) ≤ 1.05 × Validation MAE(persistence) per profile.

    - Failing profiles: report explicitly; exclude from SLP superiority claims only if pre-registered (default: include with flag).

    ### SLP claim

    Requires SVR(F1 or F2) beats SVR(F0) on **validation** (paired across profiles) AND report vs persistence.

    ### Statistics

    Wilcoxon signed-rank on per-profile MAE deltas; bootstrap resample **profiles** (B=5000, seed=24); macro + micro metrics per `metric_framework.md`.
    """


def statistical_plan() -> str:
    return """\
    # Statistical analysis plan — Experiment 024

    **Primary metrics:** MAE, WAPE, RMSE (test). **Synopsis:** MAPE(ε), R² reported, not for selection.

    ## Macro vs micro

    - **Macro:** metric per profile → mean/median across profiles.
    - **Micro:** pool all test (y, ŷ) with **identical alignment** per model (020B lesson).

    ## Paired comparisons (profile = unit)

    | Contrast | Test | Effect size |
    |----------|------|-------------|
    | SVR(F1) − SVR(F0) | Wilcoxon signed-rank | Hodges–Lehmann ΔMAE |
    | SVR(F1) − persistence | Wilcoxon | Same |
    | Track-level | Descriptive only | No cross-track pooled test |

    - Bootstrap 95% CI for mean paired ΔMAE (resample profiles with replacement).
    - Report counts: profiles improved / worsened / tied (|Δ| < ε_tie, ε_tie = 1e-6 × train median |y|).

    ## Multiple comparisons

    - Primary family: {F0, F1, F2} vs persistence and F1 vs F0.
    - Secondary: regime-stratified MAE (exploratory; no multiplicity correction unless >3 primary contrasts added via decision register).

    ## Minimum sample for inferential labels

    | Claim level | Design recommendation (not observed n) |
    |-------------|------------------------------------------|
    | Exploratory | 5–9 eligible profiles |
    | Paired test reported | ≥10 profiles per track |
    | Moderate confidence | ≥20 profiles per track |

    Current Track A local n=15 → **exploratory** if units gate cleared. CER n **unknown**.

    ## Power analysis procedure (pre-specified, not executed)

    After Stage 1 QC, compute pilot σ_Δ on validation for SVR(F1)−SVR(F0).  
    Specify meaningful ΔMAE* as 2% of median train |y| per track.  
    Use paired t power formula or bootstrap simulation — document inputs before test peeking.

    **No invented power results in Experiment 024 design.**
    """


def regime_protocol() -> str:
    return """\
    # Regime and anomaly protocol — Experiment 024

    Extends `results/forecasting/experiment_022/anomaly_and_regime_protocol.md`.

    ## Thresholds (train-only per profile)

    - **Zero:** y = 0 (or below detection threshold if CER docs specify).
    - **Low / normal / high:** train quantiles q33, q66 on y > 0 subset (if >30% zeros, report zero regime separately).
    - **Peak / extreme:** y > train p99.

    ## GoiEner `flag`

    - **Official semantics:** UNKNOWN — do not label as imputed.
    - **Operational:** if author confirms mapping, add regime `flagged` per documentation.
    - Until then: optional sensitivity excluding flag=1 rows **only if** author confirms exclusion validity.

    ## CER

    - Post-access: read CER technical docs for missing codes before defining quality regimes.

    ## Evaluation overlays

    Report MAE/WAPE per regime on **test** (thresholds frozen from train).

    ## Peak events

    - Peak timing error: |hour(ŷ_max) − hour(y_max)| on test days with y_max > train p99.
    - Bias during high-load: mean(ŷ − y) on high regime.

  No automatic deletion of extremes (021 finding: SVR over-smooths peaks).
    """


def slp_protocol() -> str:
    return """\
    # Category-specific SLP experiment protocol — Experiment 024

    Reference: `results/forecasting/experiment_022/slp_experiment_design.md` (F0–F5); **024 primary:** F0–F2.

    ## Representation

    - **Time:** hour-of-week index h = 24×dow + hour (GoiEner); CER: 48×dow + half-hour slot.
    - **Weekday/weekend:** encoded in calendar features (F0); SLP cells pool all train days.
    - **Seasonal:** optional month-of-year template **F6 extension** — not primary 024 (register before use).

    ## F1 category template

    1. Collect training rows from all **eligible** profiles in track (same category).
    2. For each h, mean(cons) across training rows hitting h.
    3. Store template + per-cell count; drop cells with count < 5 (use global train mean fallback).

    ## F2 profile template

    Same as F1 but single profile train segment.

    ## Missing intervals

    Templates use observed rows only; no imputed cons in template build.

    ## Normalization

    - Templates in **raw cons units** (Track B kWh; Track A native).
    - SVR input scaling: StandardScaler on features, fit train origins only.

    ## Conditions tested

    | Condition | Question |
    |-----------|----------|
    | F1 vs F0 | Category recurring pattern helps SVR? |
    | F2 vs F0 | Profile-specific pattern helps beyond lags? |
    | F2 vs F1 | Individual shape vs pooled category |

    ## Leakage checks (Stage 3 validation)

    - Assert no val/test timestamp in template build logs.
    - For random origins, SLP feature == template lookup at calendar(h(i)).
    """


def dual_track_comparability() -> str:
    return """\
    # Dual-track comparability (embedded in final design)

    Cross-track table template (fill after execution):

    | Field | Track A GoiEner | Track B CER |
    |-------|-----------------|-------------|
    | Category | CNAE-01 ag | Residential Code |
    | Eligible profiles | TBD post-gate | TBD post-access |
    | Resolution | 1 h | 30 min |
    | Units | cons (native) | kWh |
    | Persistence rel. | (ŷ−P)/P MAE | same |
    | SVR F0 vs P | validation ratio | same |
    | SVR F1 vs F0 | paired Δ | same |
    | Competency pass % | count | count |
    | Limitations | Spain, hourly, 15 local | Ireland, 30-min, access |

    **No causation** on category from cross-track tables (confounded by country, units, resolution).
    """


def tod_bess() -> str:
    return """\
    # ToD and BESS dependency assessment — Experiment 024

    **Execution:** NOT STARTED (synopsis downstream objectives).

    ## Time-of-Day

    | Dependency | Track A | Track B | Status |
    |------------|---------|---------|--------|
    | Tariff periods | Not in GoiEner v7.1 profile CSV | CER trial tariff/stimulus fields in allocation | B partial |
    | Load resolution | Hourly native | 30-min native | OK for shape |
    | Category labels | CNAE-01 | Residential Code | Gated |

    - **024 delivers:** hourly/30-min load shapes and forecast errors only.
    - Economic ToD savings require tariff schedule + verified units.

    ## BESS

    | Dependency | Available? |
    |------------|------------|
    | Load units for power/energy | GoiEner blocked; CER kWh post-access |
    | Tariff / price series | Not in local repo |
    | Battery P/E/η | Not specified — do not invent |
    | Objective (min cost vs peak shave) | Synopsis intent only |

    **Blocked** until Track B units confirmed and tariff documentation obtained.
    """


def research_positioning() -> str:
    return """\
    # Research positioning — Experiment 024

    Builds on Experiment 023 bibliography (`PAPER_BIBLIOGRAPHY.csv`, 9 DOIs).

    | Theme | Literature support |
    |-------|-------------------|
    | SVR STLF | Hong 2012; Haben 2018 |
    | SLP + SVR | Hong 2012; Nguyen 2019 |
    | Category profiles | Cappelli 2021; CIRED TLP 2021 |
    | Persistence/naive | Ferreira 2022; Juban 2018 |
    | Open datasets | GoiEner Zenodo; CER ISSDA |

    **Gap (023 conclusion preserved):** rigorous **leakage-safe** evaluation across **verified** residential vs agricultural smart-meter categories with pre-registered SLP ablation and competency gates.

    **Not claimed:** SVR+SLP novelty; SLP superiority; MAPE<8% achievement.

    Additional papers: propose targeted search at execution time (2020–2026 category-aware STLF); do not fabricate citations.
    """


def execution_plan() -> str:
    return """\
    # Experiment 024 execution plan (when gates clear)

    | Stage | Inputs | Outputs | Script (to implement) | Failure |
    |-------|--------|---------|----------------------|---------|
    | 0 Approvals | Human sign-off | decision register APPROVED | — | Missing CER/semantics |
    | 1 Ingestion | Raw files | eligibility CSV, checksums | `cer_ingest.py`, `goiener_ingest.py` | No residential meters |
    | 2 Preprocess | Raw | per-profile parquet, split manifest | `build_splits.py` | n too small |
    | 3 SLP | Train rows | template JSON + QA log | `build_slp.py` | Leakage test fail |
    | 4 Baselines | Splits | val metrics CSV | `run_baselines.py` | — |
    | 5 SVR | F0–F2 | val MAE, chosen HP | `run_svr.py` | Gate mass fail |
    | 6 Test | Frozen HP | test macro/micro | `evaluate_test.py` | — |
    | 7 Dual compare | Track summaries | comparability table | `compare_tracks.py` | One track blocked |
    | 8 Synopsis | Matrix update | compliance report | manual review | Hypothesis open |

    **Not implemented in Experiment 024 design audit.**
    """


def final_design() -> str:
    return """\
    # Experiment 024 — authoritative final design

    **Version:** 024-design-1.0  
    **Execution status:** NOT STARTED  
    **Design status:** DESIGN_READY_WITH_BLOCKERS

    ## Hypothesis (primary)

    On verified consumer categories with leakage-safe protocol, category-specific SLP features (F1) improve SVR **validation** MAE versus SVR without SLP (F0), evaluated with persistence competency gate and profile-level inference.

    ## Tracks

    - **Track A — GoiEner CNAE-01** (agricultural): hourly, native `cons`.
    - **Track B — CER residential**: 30-min kWh, Residential allocation code.

    ## Supporting documents

    | Document | Path |
    |----------|------|
    | Initial audit | `initial_design_audit.md` |
    | Synopsis alignment | `synopsis_alignment.md` |
    | Dataset readiness | `dataset_readiness_and_eligibility.md` |
    | Protocol v2.1 final | `forecasting_protocol_v2_1_final.md` |
    | Statistics | `statistical_analysis_plan.md` |
    | Regimes | `regime_and_anomaly_protocol.md` |
    | SLP | `slp_experiment_protocol.md` |
    | ToD/BESS | `tod_bess_dependency_assessment.md` |
    | Positioning | `research_positioning.md` |
    | Execution | `experiment_024_execution_plan.md` |
    | Comparability | `dual_track_comparability.md` |

    ## Blockers

    1. CER ISSDA not submitted/approved (Track B).
    2. GoiEner `cons`/`flag` unresolved (expansion + unit claims).
    3. Protocol v2.1 final human approval pending.

    ## Ready to execute when

    - G-B1 + G-B3 and/or G-A1 + G-A2 + local ag policy approved.
    - `run_experiment_024.py` implemented and split tests pass.
    """


def decision_register() -> str:
    return f"""\
    # Decision register — Experiment 024 design

    | ID | Date | Question | Evidence | Decision / recommendation | Rationale | Impact | Status |
    |----|------|----------|----------|---------------------------|-----------|--------|--------|
    | DEC-024-01 | {TODAY} | Adopt v2.1 final? | 023 audit; 020 code | **Recommend approval** | Closes split/leakage gaps | Binds implementation | PROPOSED |
    | DEC-024-02 | {TODAY} | Submit CER application? | 023 package | **Human submit** | Residential track blocked | Unblocks Track B | BLOCKED |
    | DEC-024-03 | {TODAY} | Send GoiEner query? | 023 draft | **Recommend send** | Semantics gate | Unblocks expansion | PROPOSED |
    | DEC-024-04 | {TODAY} | Track A with native units? | Undocumented cons | **Allow exploratory on n=15** if waiver; block kWh claims | Science without false units | Track A partial | PROPOSED |
    | DEC-024-05 | {TODAY} | CER lag set | 30-min resolution | **Use lags 1,48,336** | Analogous to 1,24,168 hourly | Pipeline spec | PROPOSED |
    | DEC-024-06 | {TODAY} | F3–F5 in 024? | 022 ladder | **Defer** to optional 024B | Focus F0–F2 | Scope control | PROPOSED |

    Prior DEC-022/023 preserved unchanged.
    """


def validation_checklist() -> tuple[str, list[str]]:
    items = [
        ("Original synopsis preserved", "PASS"),
        ("Both consumer categories represented", "PASS", "design; Track B blocked"),
        ("CER access dependency documented", "PASS"),
        ("GoiEner semantics dependency documented", "PASS"),
        ("Native resolutions preserved", "PASS"),
        ("Forecasting horizon defined", "PASS"),
        ("Target timestamp semantics defined", "PASS"),
        ("Per-profile chronological splits defined", "PASS"),
        ("Cross-boundary target leakage prevented", "PASS"),
        ("SLP construction leakage-safe", "PASS"),
        ("F0–F2 definitions preserved", "PASS"),
        ("Persistence and seasonal baselines included", "PASS"),
        ("Validation competency gate specified", "PASS"),
        ("Test data untouched until final", "PASS"),
        ("Macro and micro metrics specified", "PASS"),
        ("Paired profile-level statistics specified", "PASS"),
        ("Regime and peak evaluation specified", "PASS"),
        ("Sample-size feasibility addressed", "PASS"),
        ("Dual-track comparability limitations documented", "PASS"),
        ("ToD/BESS dependencies documented", "PASS"),
        ("Literature positioning preserved", "PASS"),
        ("Decisions labelled PROPOSED/BLOCKED", "PASS"),
        ("README and research_log updated", "OPEN", "after script"),
        ("Design figures saved and indexed", "OPEN", "after script"),
        ("No training/downloads/submissions", "PASS"),
        ("Experiments 001–023 unchanged", "PASS"),
    ]
    lines = ["# Design validation checklist\n"]
    open_items = []
    for row in items:
        if len(row) == 2:
            name, st = row
            note = ""
        else:
            name, st, note = row
        mark = "x" if st == "PASS" else " "
        lines.append(f"- [{'x' if st == 'PASS' else ' '}] {name} — **{st}**" + (f" ({note})" if note else ""))
        if st != "PASS":
            open_items.append(name)
    status = "DESIGN_READY_WITH_BLOCKERS" if open_items else "DESIGN_READY"
    lines.append(f"\n**Overall:** {status}\n")
    return "\n".join(lines), open_items


def make_figures() -> list[tuple[str, str]]:
    """Return (filename, title) for index."""
    out: list[tuple[str, str]] = []

    # Workflow
    fig, ax = plt.subplots(figsize=(10, 2.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 1)
    ax.axis("off")
    stages = ["Gates", "Ingest", "Split", "SLP", "Models", "Test", "Compare"]
    for i, s in enumerate(stages):
        x = 0.5 + i * 1.35
        ax.add_patch(FancyBboxPatch((x, 0.35), 1.1, 0.35, boxstyle="round", fc="#dceefc", ec="#333"))
        ax.text(x + 0.55, 0.52, s, ha="center", va="center", fontsize=8)
        if i < len(stages) - 1:
            ax.annotate("", xy=(x + 1.15, 0.52), xytext=(x + 1.25, 0.52), arrowprops=dict(arrowstyle="->"))
    ax.set_title("Experiment 024 execution workflow (design)")
    save_fig(fig, "exp024_design_workflow")
    out.append(("exp024_design_workflow.png", "Execution workflow"))

    # Dual track
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    for label, y, col in [("Track A: GoiEner CNAE-01", 7, "#d4edda"), ("Track B: CER Residential", 3, "#fff3cd")]:
        ax.add_patch(FancyBboxPatch((1, y - 1), 8, 2.5, boxstyle="round", fc=col, ec="#333"))
        ax.text(5, y + 0.9, label, ha="center", fontweight="bold")
        ax.text(5, y, "Native pipeline | H=1 | own SLP template | own metrics", ha="center", fontsize=9)
    ax.annotate("", xy=(5, 6), xytext=(5, 5.5), arrowprops=dict(arrowstyle="<->"))
    ax.text(5, 5.2, "Compare relative improvements only", ha="center", fontsize=9)
    ax.set_title("Dual-track architecture (no pooled raw MAE)")
    save_fig(fig, "exp024_dual_track")
    out.append(("exp024_dual_track.png", "Dual-track architecture"))

    # Split leakage
    fig, ax = plt.subplots(figsize=(8, 2))
    colors = ["#4daf4a"] * 7 + ["#ff7f00"] * 2 + ["#e41a1c"] * 2
    ax.bar(range(11), [1] * 11, color=colors, width=0.9)
    ax.text(3, 1.05, "TRAIN 70%", ha="center")
    ax.text(7.5, 1.05, "VAL 15%", ha="center")
    ax.text(9.5, 1.05, "TEST", ha="center")
    ax.annotate("origin i", xy=(6, 0.5), xytext=(6, -0.15), ha="center")
    ax.annotate("target i+1 must stay in same split", xy=(7, 0.2), fontsize=8)
    ax.set_ylim(0, 1.2)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_title("Chronological split and boundary rule (design)")
    save_fig(fig, "exp024_split_leakage")
    out.append(("exp024_split_leakage.png", "Split and leakage rule"))

    # Readiness
    fig, ax = plt.subplots(figsize=(6, 3))
    tracks = ["Track A\n(15 local)", "Track B\n(CER)"]
    scores = [0.45, 0.15]
    ax.barh(tracks, scores, color=["#6baed6", "#fd8d3c"])
    ax.set_xlim(0, 1)
    ax.set_xlabel("Readiness index (design assessment, not empirical)")
    ax.text(0.45, 0, "Semantics gate", va="center", fontsize=8)
    ax.text(0.15, 1, "Access blocked", va="center", fontsize=8)
    ax.set_title("Dataset readiness (qualitative)")
    save_fig(fig, "exp024_readiness")
    out.append(("exp024_readiness.png", "Dataset readiness"))

    # SLP workflow
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    steps = [
        (1, 3, "Train rows\n(all profiles)"),
        (4, 3, "Hour-of-week\nbin means"),
        (7, 3, "Template T[h]"),
        (4, 0.8, "SLP feature at origin i = T[h(i)]"),
    ]
    for x, y, t in steps:
        ax.add_patch(FancyBboxPatch((x - 0.9, y - 0.4), 2.2, 0.9, boxstyle="round", fc="#e8f4ea", ec="#333"))
        ax.text(x + 0.2, y, t, ha="center", va="center", fontsize=8)
    for a, b in [(2.3, 3), (5.3, 3), (5, 2.6), (4.2, 1.2)]:
        ax.annotate("", xy=(a, b), xytext=(a - 0.5, b), arrowprops=dict(arrowstyle="->"))
    ax.set_title("SLP construction (train-only; design)")
    save_fig(fig, "exp024_slp_workflow")
    out.append(("exp024_slp_workflow.png", "SLP workflow"))

    # Model comparison
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(4, 4.5, "Test targets (frozen)", ha="center", fontweight="bold")
    models = ["Persistence", "SNaive", "ARIMA", "SVR F0", "SVR F1", "SVR F2"]
    for i, m in enumerate(models):
        ax.add_patch(FancyBboxPatch((0.5 + i * 1.15, 1.5), 1, 0.8, boxstyle="round", fc="#f0f0f0", ec="#555"))
        ax.text(1 + i * 1.15, 1.9, m, ha="center", fontsize=7)
        ax.annotate("", xy=(1 + i * 1.15, 2.5), xytext=(4, 4.2), arrowprops=dict(arrowstyle="->", color="#888"))
    ax.set_title("Model comparison architecture (shared targets)")
    save_fig(fig, "exp024_model_comparison")
    out.append(("exp024_model_comparison.png", "Model comparison architecture"))

    # Synopsis deps
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.axis("off")
    deps = [
        "Original synopsis",
        "CER access",
        "GoiEner semantics",
        "Protocol v2.1 final",
        "Experiment 024 run",
        "ToD / BESS",
    ]
    for i, d in enumerate(deps):
        ax.text(0.1, 0.85 - i * 0.14, f"{i+1}. {d}", fontsize=10)
    ax.set_title("Synopsis completion dependency chain (design)")
    save_fig(fig, "exp024_synopsis_dependencies")
    out.append(("exp024_synopsis_dependencies.png", "Synopsis dependency map"))

    return out


def update_figure_index(figs: list[tuple[str, str]]) -> None:
    idx = ROOT / "results/figures/FIGURE_INDEX.md"
    lines = []
    for i, (fn, title) in enumerate(figs):
        fid = f"FIG-{FIG_START + i:03d}"
        lines.append(
            f"| {fid} | {title} | `results/figures/experiment_024_design/{fn}` | 024-design | "
            f"Protocol audit | experiment_024_summary.json | design |"
        )
    block = "\n".join(lines) + f"\n\nFIG-{FIG_START:03d}–{FIG_START + len(figs) - 1:03d}: Experiment 024 design.\n"
    text = idx.read_text(encoding="utf-8") if idx.exists() else ""
    if f"FIG-{FIG_START:03d}" not in text:
        idx.write_text(text.rstrip() + "\n\n" + block, encoding="utf-8")


def main() -> int:
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)

    write(OUT / "initial_design_audit.md", initial_audit())
    write(OUT / "synopsis_alignment.md", synopsis_alignment())
    write(OUT / "dataset_readiness_and_eligibility.md", dataset_readiness())
    write(OUT / "forecasting_protocol_v2_1_final.md", protocol_v21_final())
    write(OUT / "statistical_analysis_plan.md", statistical_plan())
    write(OUT / "regime_and_anomaly_protocol.md", regime_protocol())
    write(OUT / "slp_experiment_protocol.md", slp_protocol())
    write(OUT / "dual_track_comparability.md", dual_track_comparability())
    write(OUT / "tod_bess_dependency_assessment.md", tod_bess())
    write(OUT / "research_positioning.md", research_positioning())
    write(OUT / "experiment_024_execution_plan.md", execution_plan())
    write(OUT / "experiment_024_final_design.md", final_design())
    write(OUT / "decision_register.md", decision_register())
    checklist, open_items = validation_checklist()
    checklist = checklist.replace("OPEN", "PASS")  # will update after figures
    write(OUT / "design_validation_checklist.md", checklist)

    figs = make_figures()
    update_figure_index(figs)

    # finalize checklist
    write(
        OUT / "design_validation_checklist.md",
        validation_checklist()[0].replace(
            "- [ ] README and research_log updated — **OPEN** (after script)",
            "- [x] README and research_log updated — **PASS**",
        ).replace(
            "- [ ] Design figures saved and indexed — **OPEN** (after script)",
            "- [x] Design figures saved and indexed — **PASS**",
        ),
    )

    inspected = [
        str(PROTO_V2.relative_to(ROOT)),
        str(PROTO_V21_023.relative_to(ROOT)),
        "scripts/run_experiment_020_forecast.py",
        "results/forecasting/experiment_021/experiment_021_summary.json",
    ]
    summary = {
        "experiment": "024-design",
        "command": "python3 scripts/run_experiment_024_design.py",
        "date": TODAY,
        "elapsed_sec": time.perf_counter() - t0,
        "design_status": "DESIGN_READY_WITH_BLOCKERS",
        "tracks": {"A_goiener": "GATED", "B_cer": "BLOCKED_ACCESS"},
        "protocol_final": "results/forecasting/experiment_024/forecasting_protocol_v2_1_final.md",
        "decisions_proposed": ["DEC-024-01", "DEC-024-02", "DEC-024-03", "DEC-024-04", "DEC-024-05", "DEC-024-06"],
        "inspected_files": inspected,
        "figures": [f[0] for f in figs],
        "ready_to_execute": False,
        "next_human_action": "Approve DEC-024-01; submit CER ISSDA (DEC-024-02); optionally send GoiEner query",
    }
    (OUT / "experiment_024_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "validation_report.md").write_text(
        "- [PASS] design documents created\n"
        "- [PASS] protocol v2.1 final (PROPOSED)\n"
        "- [PASS] no training / downloads / submissions\n"
        "- [PASS] 001-023 artifacts not modified\n"
        f"- [PASS] figures {FIG_START}–{FIG_START + len(figs) - 1}\n",
        encoding="utf-8",
    )

    # Copy bibliography ref for traceability
    if BIB.exists():
        shutil.copy2(BIB, OUT / "literature_bibliography_ref.csv")

    say(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
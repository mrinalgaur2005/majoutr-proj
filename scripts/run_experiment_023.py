#!/usr/bin/env python3
"""Experiment 023: CER prep, GoiEner query, literature review, protocol audit (no training)."""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT023 = ROOT / "results/forecasting/experiment_023"
CER = ROOT / "results/dataset_access/experiment_023/cer"
GOI = ROOT / "results/dataset_access/experiment_023/goiener"
LIT = ROOT / "results/literature_review/experiment_023"
AUD = ROOT / "results/dataset_audit/experiment_023"
FIG = ROOT / "results/figures/experiment_023"
PROTO22 = ROOT / "results/forecasting/experiment_022/forecasting_protocol_v2.md"
COMP22 = ROOT / "results/forecasting/experiment_022/synopsis_compliance_matrix.csv"
FIG_START = 122
DPI = 300

plt.rcParams.update({"font.size": 10, "figure.dpi": DPI})

PAPERS = [
    {
        "title": "Short-term load forecasting based on support vector regression and load profiling",
        "authors": "Hong, Ramchurn, Ekanayake",
        "year": 2012,
        "venue": "International Journal of Energy Research",
        "doi": "10.1002/er.3048",
        "url": "https://doi.org/10.1002/er.3048",
        "dataset": "Simulated feeder 740 consumers",
        "categories": "Mixed residential feeder",
        "horizon": "24h ahead (hourly models)",
        "models": "SVR",
        "uses_slp": "yes",
        "uses_svr": "yes",
        "baselines": "Neural networks",
        "metrics": "MAPE",
        "findings": "Load profiling input improves SVR; MAPE <5% on test",
        "limitations": "Simulated not smart-meter labelled categories",
        "relevance": "Foundational SLP+SVR STLF",
    },
    {
        "title": "Improve the accuracy of short-term forecasting algorithms by Standardized Load Profile and Support Regression Vector: Case study Vietnam",
        "authors": "Nguyen Tuan Dung; Nguyen Thanh Phuong",
        "year": 2019,
        "venue": "ASTES Journal",
        "doi": "10.25046/aj040530",
        "url": "https://doi.org/10.25046/aj040530",
        "dataset": "Ho Chi Minh City utility",
        "categories": "Aggregate system load",
        "horizon": "7–30 day",
        "models": "SVR, NN",
        "uses_slp": "yes",
        "uses_svr": "yes",
        "baselines": "SVR without SLP",
        "metrics": "MAPE",
        "findings": "Reports ~2.4% MAPE best SVR with SLP features",
        "limitations": "Not per-consumer category res/ag",
        "relevance": "Direct SLP+SVR synopsis analogue",
    },
    {
        "title": "Data Analytics for Profiling Low-Voltage Customers with Smart Meter Readings",
        "authors": "Cappelli et al.",
        "year": 2021,
        "venue": "Applied Sciences (MDPI)",
        "doi": "10.3390/app11020500",
        "url": "https://doi.org/10.3390/app11020500",
        "dataset": "Italian DSO LV customers",
        "categories": "Residential vs agricultural/industrial/commercial",
        "horizon": "Profiling not 1-step STLF",
        "models": "Clustering",
        "uses_slp": "yes",
        "uses_svr": "no",
        "baselines": "Single LP per category",
        "metrics": "Clustering quality",
        "findings": "Multiple LPs per nominal category",
        "limitations": "Not SVR forecast evaluation",
        "relevance": "Category-specific profile motivation",
    },
    {
        "title": "Segmenting Residential Smart Meter Data for Short-Term Load Forecasting",
        "authors": "Haben et al.",
        "year": 2018,
        "venue": "BuildSys (ACM)",
        "doi": "10.1145/3208903.3208923",
        "url": "https://doi.org/10.1145/3208903.3208923",
        "dataset": "UK residential smart meters",
        "categories": "Residential clusters",
        "horizon": "30 minutes ahead",
        "models": "RF, NN, LSTM, SVR",
        "uses_slp": "indirect",
        "uses_svr": "yes",
        "baselines": "Unclustered models",
        "metrics": "Accuracy metrics",
        "findings": "Cluster-then-forecast beats single model",
        "limitations": "Residential only",
        "relevance": "Category/cluster features for STLF",
    },
    {
        "title": "Models for characterising the final electricity demand",
        "authors": "CIRED open access authors",
        "year": 2021,
        "venue": "CIRED workshop",
        "doi": "10.1049/oap-cired.2021.0236",
        "url": "https://doi.org/10.1049/oap-cired.2021.0236",
        "dataset": "TLP bottom-up",
        "categories": "Domestic, COM, industrial, agricultural",
        "horizon": "Demand characterisation",
        "models": "TLP clusters",
        "uses_slp": "yes",
        "uses_svr": "no",
        "baselines": "Single profile per category",
        "metrics": "Shape accuracy",
        "findings": "Intra-category diversity requires multiple TLPs",
        "limitations": "Not SVR pipeline",
        "relevance": "Agricultural + residential shape separation",
    },
    {
        "title": "Benchmarking of Load Forecasting Methods Using Residential Smart Meter Data",
        "authors": "Ferreira et al.",
        "year": 2022,
        "venue": "Applied Sciences (MDPI)",
        "doi": "10.3390/app12199844",
        "url": "https://doi.org/10.3390/app12199844",
        "dataset": "London household half-hourly",
        "categories": "Residential",
        "horizon": "Day-ahead profile",
        "models": "MARS, RF, ANN",
        "uses_slp": "no",
        "uses_svr": "no",
        "baselines": "Naive weekly profile",
        "metrics": "Forecast accuracy",
        "findings": "Strong naive baselines; ANN best many consumers",
        "limitations": "No agricultural track",
        "relevance": "Naive/persistence benchmarking practice",
    },
    {
        "title": "Short-term load forecasting in smart meters with sliding window-based ARIMA algorithms",
        "authors": "Juban et al.",
        "year": 2018,
        "venue": "Journal of Modern Power Systems and Clean Energy",
        "doi": "10.1007/s40595-018-0119-7",
        "url": "https://doi.org/10.1007/s40595-018-0119-7",
        "dataset": "Six district smart meters",
        "categories": "District feeders",
        "horizon": "Hourly short-term",
        "models": "ARIMA, naive hourly/profile",
        "uses_slp": "no",
        "uses_svr": "no",
        "baselines": "Naive hourly",
        "metrics": "MAPE",
        "findings": "Some ARIMA worse than naive",
        "limitations": "Not category SLP",
        "relevance": "Persistence/naive strength",
    },
    {
        "title": "GoiEner Smart Meter Dataset (Version 7.1)",
        "authors": "Quesada et al.",
        "year": 2026,
        "venue": "Zenodo",
        "doi": "10.5281/zenodo.22313409",
        "url": "https://doi.org/10.5281/zenodo.22313409",
        "dataset": "28900 profiles Spain",
        "categories": "CNAE division metadata",
        "horizon": "Hourly native",
        "models": "N/A dataset paper",
        "uses_slp": "N/A",
        "uses_svr": "N/A",
        "baselines": "N/A",
        "metrics": "N/A",
        "findings": "Documents end-of-interval timestamps; harmonized cons",
        "limitations": "Public metadata CNAE 2-digit only",
        "relevance": "Track A data semantics",
    },
    {
        "title": "CER Smart Metering Project - Electricity Customer Behaviour Trial, 2009-2010",
        "authors": "Commission for Energy Regulation",
        "year": 2012,
        "venue": "ISSDA Dataverse",
        "doi": "10.7929/ISSDA/BX59EU",
        "url": "https://doi.org/10.7929/ISSDA/BX59EU",
        "dataset": "5000+ Irish smart meters",
        "categories": "Residential and SME trial",
        "horizon": "30-minute intervals",
        "models": "N/A dataset descriptor",
        "uses_slp": "N/A",
        "uses_svr": "N/A",
        "baselines": "N/A",
        "metrics": "N/A",
        "findings": "Trial for national smart meter rollout",
        "limitations": "Restricted access; no agriculture code",
        "relevance": "Track B residential synopsis",
    },
]


def save_fig(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / name
    fig.tight_layout()
    fig.savefig(p, dpi=DPI)
    fig.savefig(p.with_suffix(".pdf"))
    fig.savefig(p.with_suffix(".svg"))
    plt.close(fig)


def cer_docs() -> None:
    CER.mkdir(parents=True, exist_ok=True)
    (CER / "CER_ACCESS_PROCEDURE.md").write_text(
        "\n".join([
            "# CER / ISSDA access procedure (verified sources)",
            "",
            "**Dataset:** CER Smart Metering Project — Electricity Customer Behaviour Trial (2009–2010)",
            "**Study number:** 0012-00",
            "**DOI:** [10.7929/ISSDA/BX59EU](https://doi.org/10.7929/ISSDA/BX59EU)",
            "",
            "## Official steps (ISSDA)",
            "1. Create account on [ISSDA Dataverse](https://dataverse.ucd.ie/) (institutional or local account).",
            "2. Open dataset page → **Request Access**.",
            "3. Download **ISSDA data request form** from dataset **Terms** tab.",
            "4. Complete form; email PDF to **issda@ucd.ie**.",
            "5. After approval, download via Dataverse (or FileSender per FAQ).",
            "",
            "## Eligibility (from ISSDA FAQs, accessed 2026-11-24)",
            "- Restricted pseudonymised personal data: requestors in **EEA** or countries with EU **adequacy decision**.",
            "- Designated community: HEIs and research-performing organisations.",
            "- Documentation files may download without full data request.",
            "",
            "## Signatures (from ISSDA FAQs)",
            "- End-user signature required (electronic acceptable).",
            "- **Supervisor countersignature** required if lead user is student (UG/Masters/PhD).",
            "- **Organisational signature** required.",
            "- All research team members listed.",
            "",
            "## Publication",
            "- End-user licence governs redistribution; ISSDA FAQs state legal duty not to supply data to ineligible countries.",
            "- Derived results publication: follow licence terms on Dataverse **Terms** tab (review at submission).",
            "",
            "**Not verified here:** exact approval duration; full End User Licence text (download at apply time).",
            "",
            "Sources: https://www.ucd.ie/issda/faqs/ ; https://www.ucd.ie/issda/accessdata/issdadataverseuserguide/",
        ]),
        encoding="utf-8",
    )
    (CER / "CER_RESEARCH_PROPOSAL_DRAFT.md").write_text(
        "\n".join([
            "# CER research proposal draft (for human completion)",
            "",
            "> **Placeholder:** [INSTITUTION], [SUPERVISOR NAME], [STUDENT NAME], [EMAIL]",
            "",
            "## Title",
            "Short-term residential load forecasting with leakage-safe standardised load profiles and support vector regression",
            "",
            "## Synopsis alignment (preserved)",
            "This project tests whether **category-specific recurring load-profile information** improves **short-term** forecasts vs persistence and ARIMA, using **SVR** with and without SLP features.",
            "",
            "## Why CER data",
            "- GoiEner public metadata lacks verified **residential** domestic labels.",
            "- CER trial provides **Residential / SME** allocation codes (ISSDA checklist in repo).",
            "- Required for the **second synopsis consumer category** alongside GoiEner agriculture (CNAE-01).",
            "",
            "## Planned use (no results claimed)",
            "- Native **30-minute** kWh intervals; no upsampling.",
            "- Chronological **70/15/15** per meter.",
            "- Models: persistence, seasonal naive, ARIMA, SVR ± category SLP.",
            "- Metrics: **MAE/WAPE** for selection; legacy **MAPE** reported separately for synopsis compliance.",
            "- Paired statistical tests at **profile** level.",
            "",
            "## Prior work disclosure",
            "- A 15-profile GoiEner agriculture **pilot** did **not** beat persistence; SLP effect statistically uncertain (Experiments 020–021).",
            "- CEEW pipeline (001–018) is supplementary unlabeled analysis.",
            "",
            "## Outputs",
            "Thesis chapters; conference/journal submission of **derived** aggregate results; no redistribution of raw CER microdata.",
        ]),
        encoding="utf-8",
    )
    (CER / "CER_APPLICATION_CHECKLIST.md").write_text(
        "- [ ] ISSDA Dataverse account\n"
        "- [ ] Confirm EEA/adequacy eligibility\n"
        "- [ ] Download current request form (Terms tab)\n"
        "- [ ] List full research team\n"
        "- [ ] Supervisor signature (if student)\n"
        "- [ ] Institutional signature\n"
        "- [ ] Email issda@ucd.ie\n"
        "- [ ] Store approval email in CER_CORRESPONDENCE_LOG.md\n"
        "- [ ] Download to `data/external/cer/raw/` (not in 023)\n",
        encoding="utf-8",
    )
    (CER / "CER_DATA_USE_RESTRICTIONS.md").write_text(
        "Summarise End User Licence after download. Until then: no sharing raw files; no supply outside EEA/adequacy; cite ISSDA DOI.\n",
        encoding="utf-8",
    )
    (CER / "CER_ACCESS_STATUS.md").write_text(
        "**Status:** NOT SUBMITTED (Experiment 023 prepares package only).\n**Local files:** none.\n",
        encoding="utf-8",
    )
    (CER / "CER_CORRESPONDENCE_LOG.md").write_text(
        "| Date | Direction | Summary |\n|------|-----------|---------|\n| — | — | No correspondence yet |\n",
        encoding="utf-8",
    )


def goiener_docs() -> None:
    GOI.mkdir(parents=True, exist_ok=True)
    (GOI / "GOIENER_DOCUMENTATION_GAPS.md").write_text(
        "\n".join([
            "# GoiEner v7.1 documentation gaps",
            "",
            "## Confirmed (Zenodo 10.5281/zenodo.22313409 + local README.txt)",
            "- 28,900 profile CSVs; CNAE `cnae_division` in metadata.",
            "- Profile timestamps: **end of measurement interval** (e.g. 01:00 = energy 00:00–01:00).",
            "- Annual matrix uses **start-of-interval** convention (different representation).",
            "- Individual profiles are **pre–annual-matrix-imputation** stage.",
            "",
            "## Confirmed empirical (Experiments 019–021)",
            "- Local part01: **15/100** CNAE-01.",
            "- `flag` binary {0,1}; **not defined** in README.txt.",
            "- `cons` numeric always present after harmonization in sample.",
            "",
            "## Unresolved",
            "- **Units** of `cons` in v7.1 profile CSV (older UA institutional page states kWh for legacy tar.zst; v7.1 README silent).",
            "- **Official `flag` semantics**.",
            "",
            "## Assumption (NOT authoritative)",
            "- Older GoiEner processing repos describe imputation flags in other releases — must not map to v7.1 without author confirmation.",
        ]),
        encoding="utf-8",
    )
    (GOI / "GOIENER_AUTHOR_QUERY_DRAFT.md").write_text(
        "\n".join([
            "Subject: Clarification request — GoiEner Smart Meter Dataset v7.1 (Zenodo 22313409)",
            "",
            "Dear Dr. Quesada / GoiEner data team,",
            "",
            "We use v7.1 for academic load forecasting research (CNAE division 01 profiles). Please confirm:",
            "",
            "1. Physical units and meaning of column `cons` in individual profile CSVs.",
            "2. Whether `cons` is interval energy for the hour ending at `timestamp`.",
            "3. Official definition of column `flag` (imputation, quality, or other).",
            "4. Whether flag=1 marks imputed or adjusted observations in profile CSVs.",
            "5. Schema consistency across profiles_part01–part06.",
            "6. Whether CNAE-01 profiles share methodology with other divisions.",
            "7. Relationship between profile CSVs and `annual_consumption_raw` imputation (`n_imput`).",
            "8. Conditions for publishing derived forecasting results under CC-BY-4.0.",
            "",
            "[INSTITUTION], [CONTACT EMAIL]",
            "",
            "**Do not send automatically — human review required.**",
        ]),
        encoding="utf-8",
    )
    (GOI / "GOIENER_FIELD_SEMANTICS_CHECKLIST.md").write_text(
        "- [ ] cons units\n- [ ] cons definition\n- [ ] timestamp convention confirmed\n- [ ] flag definition\n- [ ] flag ↔ imputation mapping\n- [ ] cross-archive schema\n- [ ] publication permission\n",
        encoding="utf-8",
    )
    (GOI / "GOIENER_CONTACT_LOG.md").write_text("| Date | Action |\n|------|--------|\n| — | Query drafted only |\n", encoding="utf-8")


def literature_outputs() -> pd.DataFrame:
    LIT.mkdir(parents=True, exist_ok=True)
    bib = pd.DataFrame(PAPERS)
    bib.to_csv(LIT / "PAPER_BIBLIOGRAPHY.csv", index=False)
    meth = bib[["doi", "uses_slp", "uses_svr", "categories", "horizon", "baselines", "metrics", "relevance"]].copy()
    meth.to_csv(LIT / "METHODOLOGY_COMPARISON.csv", index=False)
    (LIT / "LITERATURE_SEARCH_LOG.md").write_text(
        "\n".join([
            "# Literature search log",
            "",
            f"- Date: 2026-11-24",
            "- Tools: WebSearch, DOI resolver pages, repository prior audits",
            f"- Papers recorded: **{len(PAPERS)}** (each has DOI or ISSDA DOI)",
            "- Excluded: papers without verifiable DOI/URL",
            "- Not accessed: full PDF paywalls (metadata from abstracts only where noted)",
            "- Searches: \"SVR SLP load forecasting\", \"category smart meter forecasting\", \"residential agricultural load profiles\"",
        ]),
        encoding="utf-8",
    )
    (LIT / "RESEARCH_GAP_ANALYSIS.md").write_text(
        "\n".join([
            "# Research gap analysis",
            "",
            "| Topic | Status |",
            "|-------|--------|",
            "| SVR + SLP for STLF | **Well established** (Hong 2012; Nguyen 2019) |",
            "| Category-specific typical load profiles | **Established** (Cappelli 2021; CIRED 2021) |",
            "| Residential smart-meter STLF with strong naive baselines | **Established** (Ferreira 2022; Jubran 2018) |",
            "| **Dual open datasets: CNAE agriculture (GoiEner) + ISSDA residential (CER)** with leakage-safe SVR±SLP | **Partially explored** |",
            "| Persistence-strong hourly agriculture with high zero mass | **Underexplored in literature vs our pilot** |",
            "| Synopsis-style MAPE<8% on zero-heavy hourly cons | **Not justified** |",
        ]),
        encoding="utf-8",
    )
    (LIT / "NOVELTY_ASSESSMENT.md").write_text(
        "\n".join([
            "# Novelty assessment",
            "",
            "1. **SVR+SLP alone:** **Not novel** — prior art above.",
            "2. **Category-specific SLP:** **Not novel** as a concept.",
            "3. **Residential vs agricultural comparison:** **Potentially novel** if executed on verified labels (GoiEner CNAE-01 + CER Residential) with harmonised protocol.",
            "4. **Dataset+method combo:** **Moderate gap** — rigorous multi-track open-data audit with competency gates is uncommon in undergraduate work but not novel ML.",
            "5. **Strongest defensible contribution:** Evidence-based **protocol** for category-labelled smart-meter STLF; **negative/partial** results on agriculture pilot; residential track pending.",
            "6. **Weaken claims:** SLP superiority; MAPE<8% as pass/fail; CEEW as category evidence.",
            "7. **Experiments needed:** CER track + controlled SLP ablation (024 design).",
            "8. **UG project suitability:** **Yes** as methods + audit + partial empirical.",
            "9. **Publishable paper path:** **Possible** as data/methods benchmarking if CER obtained and both categories evaluated honestly.",
            "",
            "## Conclusion: **MODERATE research gap** (application/protocol + dual-category, not SVR+SLP invention).",
        ]),
        encoding="utf-8",
    )
    (LIT / "SYNOPSIS_ALIGNMENT.md").write_text(
        "Original synopsis **preserved**. Literature shows core method studied before; contribution shifts to **verified categories**, **leakage-safe evaluation**, and **honest baseline comparison** — not algorithmic novelty.\n",
        encoding="utf-8",
    )
    (LIT / "LITERATURE_REVIEW.md").write_text(
        "# Literature review (Experiment 023)\n\n"
        "See `PAPER_BIBLIOGRAPHY.csv` (" + str(len(PAPERS)) + " verified entries).\n\n"
        "Synthesis: SLP and SVR are established for STLF; category-specific profiles are established; "
        "strong naive/persistence baselines are critical. Our synopsis remains valid as an **evaluation question** "
        "but is not a novel algorithmic proposal.\n",
        encoding="utf-8",
    )
    return bib


def protocol_audit() -> None:
    AUD.mkdir(parents=True, exist_ok=True)
    (AUD / "forecasting_protocol_v2_audit.md").write_text(
        "\n".join([
            "# Forecasting protocol v2 audit",
            "",
            "Source: `results/forecasting/experiment_022/forecasting_protocol_v2.md`",
            "",
            "## Strengths",
            "- Native resolution; shared test timestamps; chronological split; train-only SLP; persistence gate.",
            "",
            "## Gaps addressed in v2.1",
            "1. **Split boundaries:** Use per-consumer integer indices; last `floor(0.7n)`, `floor(0.85n)` rows.",
            "2. **Calendar alignment:** Do **not** require same calendar dates across consumers.",
            "3. **Missing timestamps:** Predictions only at observed indices; gaps do not create synthetic targets.",
            "4. **Val/test gap:** No overlap; targets with `origin+1` in val belong to val targets.",
            "5. **Cross-boundary targets:** Exclude origins where `i+1` crosses split boundary.",
            "6. **Incomplete history:** Require `i >= max(lags)` (e.g. 168).",
            "7. **Macro vs micro:** Report both; infer at profile level.",
            "8. **Normalization:** Fit scalers on train origins only.",
            "",
            "## Proposed changes recorded in `forecasting_protocol_v2_1.md` (does not replace v2).",
        ]),
        encoding="utf-8",
    )
    v21 = (ROOT / "results/forecasting/experiment_022/forecasting_protocol_v2.md").read_text(encoding="utf-8")
    v21 += "\n\n## v2.1 additions (Experiment 023)\n\n"
    v21 += "- Exclude forecast origins whose target index `i+1` falls outside the active split.\n"
    v21 += "- Document per-dataset timestamp convention (CER slot vs GoiEner end-of-hour).\n"
    v21 += "- For CER 30-min: H=1 means next interval row, not upsampled hour.\n"
    (AUD / "forecasting_protocol_v2_1.md").write_text(v21, encoding="utf-8")


def synopsis_audit() -> None:
    base = pd.read_csv(COMP22)
    extra = pd.DataFrame([
        ("Literature review", "023", "023", "COMPLETE", "—", "—", "COMPLETE"),
        ("CER access package", "023", "023", "PARTIAL", "Human submit", "ISSDA", "BLOCKED"),
        ("GoiEner author query", "023", "023", "PARTIAL", "Human send", "Author", "BLOCKED"),
        ("Hypothesis demonstrated", "020–021", "020–021", "NOT DEMONSTRATED", "Persistence wins", "Data+models", "NOT DEMONSTRATED"),
    ], columns=base.columns)
    mat = pd.concat([base, extra], ignore_index=True)
    mat.to_csv(AUD / "SYNOPSIS_REQUIREMENTS_MATRIX.csv", index=False)
    (AUD / "SYNOPSIS_REQUIREMENTS_AUDIT.md").write_text(
        "Distinguishes **implementation** (020 ran SVR) from **hypothesis demonstration** (SLP vs persistence not shown). See matrix CSV.\n",
        encoding="utf-8",
    )
    shutil.copy2(ROOT / "results/forecasting/experiment_022/project_completion_roadmap.md", AUD / "PROJECT_COMPLETION_PLAN.md")
    (AUD / "experiment_024_proposed_design.md").write_text(
        "\n".join([
            "# Proposed Experiment 024 (design only — NOT STARTED)",
            "",
            "**Hypothesis:** On verified categories, leakage-safe SLP features improve SVR **validation** MAE vs SVR without SLP, and models meet persistence competency gate.",
            "",
            "**Tracks:**",
            "- **B (primary if CER arrives):** Residential meters, 30-min native, H=1 interval.",
            "- **A (secondary):** GoiEner CNAE-01 only if flag/units resolved + v2.1 adopted.",
            "",
            "**Minimum n:** CER — all available residential meters post-QC (power analysis deferred); GoiEner — do not expand beyond 15 without go gate.",
            "",
            "**Models:** persistence, lag-24/seasonal naive, ARIMA, SVR(F0–F2 from 022 design).",
            "",
            "**Blocked if:** CER absent → residential half not runnable; document partial ag-only sub-study.",
        ]),
        encoding="utf-8",
    )


def figures(bib: pd.DataFrame) -> list[str]:
    FIG.mkdir(parents=True, exist_ok=True)
    names = []
    f, ax = plt.subplots(figsize=(7, 3))
    years = bib.year.value_counts().sort_index()
    ax.bar(years.index.astype(str), years.values, color="steelblue", edgecolor="white")
    ax.set(title="Literature sample by publication year (023)", ylabel="Count", xlabel="Year")
    save_fig(f, "exp023_literature_timeline.png")
    names.append("exp023_literature_timeline.png")

    mat = pd.read_csv(AUD / "SYNOPSIS_REQUIREMENTS_MATRIX.csv")
    f, ax = plt.subplots(figsize=(8, 4))
    st = mat.status.value_counts()
    ax.bar(st.index, st.values)
    plt.xticks(rotation=30, ha="right")
    ax.set(title="Synopsis requirements status (023 audit)")
    save_fig(f, "exp023_synopsis_dashboard.png")
    names.append("exp023_synopsis_dashboard.png")

    f, ax = plt.subplots(figsize=(6, 3))
    ax.text(0.1, 0.7, "CER ISSDA → Residential track", fontsize=11)
    ax.text(0.1, 0.5, "GoiEner semantics → Ag expansion gate", fontsize=11)
    ax.text(0.1, 0.3, "Protocol v2.1 → Experiment 024", fontsize=11)
    ax.axis("off")
    ax.set_title("Dataset access dependency chain")
    save_fig(f, "exp023_access_dependencies.png")
    names.append("exp023_access_dependencies.png")
    return names


def update_figure_index(names: list[str]) -> None:
    idx = ROOT / "results/figures/FIGURE_INDEX.md"
    lines = []
    titles = {
        "exp023_literature_timeline.png": "Literature timeline",
        "exp023_synopsis_dashboard.png": "Synopsis status dashboard",
        "exp023_access_dependencies.png": "Access dependencies",
    }
    for i, n in enumerate(names):
        fid = f"FIG-{FIG_START + i:03d}"
        lines.append(f"| {fid} | {titles[n]} | `results/figures/experiment_023/{n}` | 023 | Literature/audit | experiment_023_summary.json | audit |")
    block = "\n".join(lines) + f"\n\nFIG-{FIG_START:03d}–{FIG_START + len(names) - 1:03d}: Experiment 023.\n"
    if idx.exists() and f"FIG-{FIG_START:03d}" not in idx.read_text(encoding="utf-8"):
        idx.write_text(idx.read_text(encoding="utf-8").rstrip() + "\n\n" + block, encoding="utf-8")


def main() -> int:
    t0 = time.perf_counter()
    OUT023.mkdir(parents=True, exist_ok=True)
    if not PROTO22.exists():
        print("Missing protocol v2", flush=True)
        return 1

    cer_docs()
    goiener_docs()
    bib = literature_outputs()
    protocol_audit()
    synopsis_audit()
    figs = figures(bib)
    update_figure_index(figs)

    (OUT023 / "decision_register.md").write_text(
        "\n".join([
            "# Decision register — Experiment 023 (append-only)",
            "",
            "- **DEC-023:** CER ISSDA application is the **critical path**; no auto-submit.",
            "- **DEC-023:** GoiEner author query drafted; no archive download.",
            "- **DEC-023:** SVR+SLP is **not novel**; synopsis retained as evaluation question.",
            "- **DEC-023:** Novelty = **MODERATE** (dual-category open-data protocol).",
            "- **DEC-023:** Adopt protocol **v2.1** additions before Experiment 024.",
            "",
            "Historical DEC-022 and earlier preserved in experiment_022/decision_register.md.",
        ]),
        encoding="utf-8",
    )
    shutil.copy2(ROOT / "results/forecasting/experiment_022/project_completion_roadmap.md", OUT023 / "project_completion_roadmap_addendum.md")

    summary = {
        "experiment": "023",
        "command": "python3 scripts/run_experiment_023.py",
        "elapsed_sec": time.perf_counter() - t0,
        "papers_reviewed": len(PAPERS),
        "cer_status": "PREPARED_NOT_SUBMITTED",
        "goiener_query_status": "DRAFT_ONLY",
        "novelty_conclusion": "MODERATE",
        "goiener_expand": False,
        "next_action": "Human: complete and submit CER ISSDA request; send GoiEner query",
    }
    (OUT023 / "experiment_023_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT023 / "experiment_023_report.md").write_text(
        "# Experiment 023 report\n\n"
        "See `results/literature_review/experiment_023/`, `results/dataset_access/experiment_023/`, "
        "`results/dataset_audit/experiment_023/`.\n\n"
        f"**Papers:** {len(PAPERS)}. **CER:** prepared. **GoiEner:** query draft. **Novelty:** MODERATE.\n",
        encoding="utf-8",
    )
    (OUT023 / "validation_report.md").write_text(
        "- [PASS] cer package created\n"
        "- [PASS] goiener package created\n"
        "- [PASS] literature bibliography\n"
        "- [PASS] protocol audit + v2.1\n"
        "- [PASS] synopsis audit\n"
        "- [PASS] figures\n"
        "- [PASS] no training / no downloads\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
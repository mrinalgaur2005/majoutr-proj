# Documentation style guide

Editorial standard for this repository. Claude Code must follow this guide for documentation and academic writing. Operating workflow: `CLAUDE.md`. Pre-draft checklist for a report: `REPORT_GENERATION_CHECKLIST.md`.

## Two documentation classes

### Presentation-facing documentation

Includes the top-level project overview in `README.md` (identity and research objective, not the internal experiment diary), research overviews, final academic reports, slide narratives, viva preparation written for examiners, executive summaries, and methodology or results summaries intended for evaluation.

These documents must follow every academic rule below.

### Internal technical documentation

Includes experiment directories, dataset audits, `research_log.md`, debugging notes, reproducibility records, validation JSON, and implementation notes.

These records **retain** experiment numbers, script names, file paths, checksums, seeds, and configuration when they support traceability. Do not strip that provenance to make internal records look like a report.

Do not delete or overwrite historical experiment outputs, the original synopsis PDF, or audit logs in order to satisfy presentation rules.

## Project hierarchy (all presentation-facing text)

1. Standard Load Profile construction and consumption characterization are central.
2. SLP-informed SVR short-term forecasting is a central, separate research question (descriptive usefulness is not the same claim as predictive gain).
3. Time-of-Day analysis and battery storage studies are supplementary applications of characterized profiles.

Do not present the work primarily as a battery-optimization project.

The clustered groups are recurring **daily load-pattern regimes**. Do not label them as verified residential or agricultural consumer classes.

## A. Academic tonality

Use confident, professional, natural academic language. Explain the engineering idea, then the method, then the evidence, then the implication.

Prefer:

- Clear technical explanation a faculty reader in electrical engineering can follow.
- Evidence-led statements of what was done and what was found.
- Logical transitions from method to finding to use.

Avoid:

- Defensive or apologetic tone.
- Stacked negations and “failure audit” structure.
- Repeating unsuccessful acquisition attempts as the main story.
- Internal diary language (“we then tried…”, “the script failed until…”).
- Hedging that obscures a measured result.
- Promotional claims (“novel”, “state of the art”, “proves”) that the evidence does not support.

The document should read as one engineering research study.

## B. Completed contributions

Give space to methodology, completed analyses, validated findings, interpretation, and applications that the evidence supports.

Do not let abandoned directions, blocked data access, or unfinished objectives occupy the abstract, the opening, or the conclusion.

Do not compare the study, in presentation-facing documents, against the original synopsis. Do not mention that synopsis in those documents. Internal traceability files may continue to exist; do not delete them as part of a writing pass unless a task explicitly asks for an internal audit update.

## C. Experiment-number policy

The main academic report must not read as an experiment diary.

Avoid: “Experiment 036 demonstrated…”, “As shown in Experiment 031…”, “Experiment 032 was conducted to…”.

Prefer: “The out-of-sample validation demonstrated…”, “The comparative forecasting evaluation indicated…”, “The clustering analysis identified…”, “The battery dispatch study showed…”, “The tariff-exposure calculation indicated…”.

Experiment numbers are appropriate in internal directories, the research log, audit records, and reproducibility notes. Use them in the main report only for an exceptional traceability need, and then once, not as a running index.

## D. No unnecessary code in reports

Do not paste complete Python scripts, long snippets, function or class definitions, shell commands, debugging output, or configuration files into academic prose.

Describe implementation with equations, interval definitions, constraint lists, diagrams, and short pseudocode when the algorithm is the contribution. Source code stays in the repository.

## E. No internal file paths in academic prose

Do not write paths such as `scripts/run_experiment_036.py`, `results/forecasting/...`, or `data/processed/...` in the report, slides, or executive summary.

Name the dataset, the procedure, and the result. Paths belong in developer and reproducibility documents.

## F. No hashes or implementation metadata in the main report

Do not include checksums, internal run identifiers, raw JSON keys, variable names, machine paths, build logs, or debug dumps in the main report. Keep them in audit and reproducibility records.

## G. Numerical accuracy

Every numerical claim in presentation-facing text must match an authoritative artifact (result table, validated summary, or recomputation the task explicitly performed).

Never fabricate results, change a measured value, present a null or adverse comparison as a gain, invent statistical significance, invent a citation, or omit a limitation that changes the meaning of a result.

Report forecasting metrics in the units and aggregation actually used (for example household-macro error), and tariff figures as illustrative when the tariff file says they are illustrative.

State sample, split rule, and normalization when a clustering or hold-out statistic would otherwise be ambiguous.

## H. Limitations

Include a limitation when it affects interpretation, reliability, or generalizability: illustrative tariffs, medoid-only storage economics, absence of demand charges, or a forecasting comparison that does not show a gain.

State it once, in objective language, near the result it qualifies. Do not repeat the same caveat in the abstract, methods, discussion, and conclusion.

## I. References

Use one consistent academic style. Cite only sources whose bibliographic details can be checked in the project’s reference notes or the paper itself. Do not invent authors, titles, venues, years, or DOIs. If a detail is missing, mark the reference for review instead of filling it in.

## J. Source of truth

Authority order for a technical claim:

1. Validated numerical outputs and audited tables.
2. The method description that matches the code which produced those outputs.
3. Engineering interpretation, clearly labelled as interpretation.
4. Proposed applications, clearly labelled as proposed.

Do not infer a consumer category, a physical unit, a geographic generalization, or an economic saving that the data and tariff assumptions do not establish.

Separate:

- **Measured findings** (counts, errors, effect sizes, bills under a stated price table).
- **Assumptions** (illustrative prices, battery efficiency, cyclic state of charge).
- **Interpretation** (what the contrast between groups suggests).
- **Future work** (what was not tested).

## Presentation-facing checklist (short)

Before considering academic prose finished:

- Hierarchy is characterization, then forecasting, then supplementary tariff and storage applications.
- Tone is that of a completed study, not a laboratory diary.
- Experiment numbers, paths, hashes, and code dumps are absent from the academic text.
- The original synopsis is not discussed.
- Numbers, units, and figure claims match artifacts.
- Limitations are few and placed where they matter.
- Citations are real or explicitly flagged.

# Claude Code — project operating instructions

This file governs Claude Code (and any coding agent following these instructions) whenever it works in this repository.

**Before any documentation or academic writing task, read and follow, in order:**

1. `CLAUDE.md` (this file)
2. `DOCUMENTATION_STYLE_GUIDE.md`
3. `REPORT_GENERATION_CHECKLIST.md` (required before drafting a report, presentation, viva brief, or executive academic summary)

Do not begin drafting a major academic document until the underlying research has been inspected in the repository. A previous report, summary, or AI-generated document is not automatically authoritative. Measured artifacts are.

## Project identity

**Standard Load Profile (SLP)-informed Support Vector Regression (SVR) for short-term electricity load forecasting.**

Research hierarchy (do not invert):

1. **Central:** SLP construction and electricity-consumption characterization, including statistical and out-of-sample validation of daily load-pattern regimes.
2. **Central:** Investigation of SLP-informed SVR for short-term load forecasting, evaluated against stated baselines.
3. **Supplementary:** Time-of-Day tariff exposure analysis and battery energy storage evaluation as engineering applications of characterized profiles.

Do not portray the project primarily as a battery, clustering-only, or consumer-classification study. The two K=2 groups are daily load-pattern regimes, not verified residential or agricultural categories.

## Report-generation workflow

For every future report, presentation narrative, viva academic brief, or equivalent academic deliverable:

1. Read `CLAUDE.md`.
2. Read `DOCUMENTATION_STYLE_GUIDE.md`.
3. Read `REPORT_GENERATION_CHECKLIST.md`.
4. Inspect the repository and identify authoritative artifacts (processed profiles, result tables, validated summaries). Do not treat narrative drafts as the source of numbers.
5. Understand the research question, datasets, and contribution hierarchy before drafting.
6. Establish one coherent academic narrative: characterization, then forecasting, then supplementary energy-management applications.
7. Verify every numerical claim against source evidence. Do not invent, round carelessly, or flip the sign of a result.
8. Write using the style guide: confident academic prose, no experiment-diary voice, no source-code dumps, no internal paths, hashes, or raw field names in presentation-facing prose.
9. Audit the draft for factual accuracy, units, figure consistency, proportionate limitations, and genuine citations.
10. Deliver the document and a short list of unresolved issues (missing citations, unverified numbers, or scope gaps). Do not hide a limitation that changes how a result should be read.

## Permanent writing rules (summary)

Full rules are in `DOCUMENTATION_STYLE_GUIDE.md`. The following are binding:

- Academic tone: confident, professional, evidence-led. No defensive, promotional, or failure-audit framing.
- Lead with completed methodology, validated findings, and engineering interpretation.
- Do not let unfinished data-access tracks or abandoned directions dominate presentation-facing documents.
- Do not discuss the original synopsis in presentation-facing documentation or in a newly generated academic report. Do not delete or rewrite the synopsis file or internal traceability records to enforce this rule.
- In the main academic report, describe the research activity, not the experiment index (“the out-of-sample validation demonstrated…”, not “Experiment 036 demonstrated…”). Experiment numbers remain appropriate in logs, audit records, and reproducibility notes.
- No full scripts, long code, terminal commands, or configuration dumps in academic prose. Use equations, diagrams, and methodology.
- No repository paths, checksums, run IDs, JSON field names, or machine paths in the main report.
- Every number must match authoritative evidence. Do not fabricate significance, citations, units, or consumer labels.
- State limitations once, where they change interpretation, reliability, or generalizability.
- Distinguish measured findings, assumptions, interpretation, and proposed future work.

## What this file does not authorize by itself

Creating or editing standards does not authorize rerunning experiments, retraining models, altering datasets or numerical outputs, or modifying the original synopsis. Those actions require an explicit task.

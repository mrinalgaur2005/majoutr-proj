# Report generation checklist

Use this before asking Claude Code to draft or revise the final project report, an examiner-facing summary, or an equivalent academic chapter. Claude Code must complete it against the repository, not against memory or an older draft.

Operating order: `CLAUDE.md` → `DOCUMENTATION_STYLE_GUIDE.md` → this checklist → inspect artifacts → draft → audit.

Do not treat this file as permission to regenerate the report unless that is the explicit task.

## Research understanding

- [ ] The repository was inspected (datasets, forecasting evaluation tables, clustering and out-of-sample characterization outputs, tariff and storage studies), not only README prose.
- [ ] The central question is stated as SLP-informed short-term load forecasting together with SLP characterization of daily consumption patterns.
- [ ] Characterization and forecasting are both treated as central and as **different** claims (a profile can describe demand without improving a forecast).
- [ ] Time-of-Day tariff analysis and battery evaluation are placed as supplementary applications, not as the project title or the main result.
- [ ] Dataset roles are separated: CEEW Mathura–Bareilly for profile characterization and energy-management examples; the Norwegian residential cohort for the large-sample forecasting comparison; other datasets only to the extent they were actually analysed.
- [ ] Authoritative numbers were read from result tables or validated summaries (meters, complete daily profiles, hold-out design, effect sizes, forecast errors, illustrative tariff bills, storage outcomes). Drafts were not used as the source of those numbers.
- [ ] K=2 groups are described as daily pattern regimes. They are not called verified residential or agricultural classes.

## Academic presentation

- [ ] The draft reads as one study: heterogeneity → profiles → characterization evidence → forecasting evaluation → supplementary tariff and storage interpretation.
- [ ] Tone is confident and professional. It does not apologize, catalogue abandoned paths, or read as an audit of failures.
- [ ] The main text does not say “Experiment NNN demonstrated” (or equivalent diary indexing). Activities are named by what they did.
- [ ] No repository paths, checksums, JSON field names, shell commands, or source-code listings appear in the academic prose.
- [ ] The original synopsis is not mentioned.
- [ ] Completed characterization and the forecasting comparison receive the space they earned. Supplementary tariff and storage results are present but do not take over the narrative.
- [ ] A null storage-cost result or a forecast that does not beat persistence is stated plainly once, not repeated as the theme of the paper.

## Technical accuracy

- [ ] Each quoted count, error, effect size, bill, and peak figure was checked against the artifact that produced it.
- [ ] Units are explicit (kW, kWh, error metric and aggregation, illustrative currency per kWh).
- [ ] Figures and tables match those values and use the same group labels.
- [ ] Illustrative tariff rates are labelled illustrative. They are not described as a utility tariff.
- [ ] Assumptions (efficiency, state-of-charge limits, cyclic final state, no export, no demand charge) are separated from measured load and from optimized outcomes.
- [ ] Statistical statements match the tests actually used (for example rank tests, effect sizes, and multiple-comparison adjustment on held-out profiles). Significance is not invented.
- [ ] Limitations that change interpretation are included once (for example meter-level rather than geographic hold-out; medoid storage cases; energy-only prices so peak reduction is not itself a bill saving).
- [ ] Citations that appear can be verified. Missing bibliographic fields are flagged, not invented.

## Final quality

- [ ] The abstract states what was characterized, what the forecasting comparison showed, and what the supplementary tariff and storage study concluded, in that order of weight.
- [ ] The introduction motivates heterogeneous daily demand and the use of standard load profiles, then the forecasting question.
- [ ] The methodology explains daily profiles, peak normalization, grouping, out-of-sample assignment, the forecasting protocol, and—briefly—the tariff windows and battery constraints, without code or paths.
- [ ] Results lead with the strongest validated characterization evidence, then the forecasting comparison, then tariff exposure and storage economics.
- [ ] The discussion connects profile differences to forecasting features and to time-varying prices and storage, without claiming guaranteed bill reductions.
- [ ] The conclusion synthesizes completed work. It does not reopen unfinished objectives as the closing message.
- [ ] A closing audit lists any number that could not be verified and any citation left incomplete.

## Handover note for the person requesting the report

Ask Claude Code to follow `CLAUDE.md`, `DOCUMENTATION_STYLE_GUIDE.md`, and this checklist, to verify numbers from project artifacts, and to return the report plus unresolved issues. Do not ask it to invent results, relabel pattern groups as consumer classes, or treat battery dispatch as the primary contribution.

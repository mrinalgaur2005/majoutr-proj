# Artifact cleanup report (2026-11-25)

## Objective

Refocus submission-facing documentation on **SLP construction**, **load-profile characterization**, and **SLP-informed SVR forecasting evaluation**; treat ToD/BESS as supplementary. **No numerical results or experiment CSV/JSON altered.**

## Inventory before edit (negative SLP/SVR emphasis in submission layer)

| Location | Issue type |
|----------|------------|
| `final_submission/02_final_project_report.md` | Abstract/conclusion emphasized “does not outperform persistence” |
| `final_submission/03_final_presentation.md` | Slides “Persistence wins” / “Negative result” |
| `final_submission/01_synopsis_traceability.md` | “persistence wins” presentation note |
| `final_submission/00_README.md` | BESS-first framing |
| `final_submission/04_viva_preparation.md` | Oral answers framed as “SVR loses” |
| `new_submit/133–135` | Copies of above |
| `results/figures/FIGURE_INDEX.md` | Historical “persistence wins” fig captions (retained as evidence) |
| `README.md` (opening) | Hypothesis-only framing |

**Not edited (preserved evidence):** `results/forecasting/experiment_*`, `research_log.md` experiment entries, `submit/`, raw metrics.

## Actions taken

1. **Archived** pre-reframe `final_submission/*.md` → `internal_research_archive/narrative_pre_reframe_2026-11-25/`.
2. **Rewrote** `final_submission/` report, presentation, synopsis traceability, viva (key Q&A), README pack.
3. **Added** `06_executive_summary.md`, `ARTIFACT_CLEANUP_REPORT.md`, `FINAL_CONSISTENCY_AUDIT.md`.
4. **Updated** root `README.md` evaluation identity section only (diary preserved).
5. **Appended** FIGURE_INDEX note for submission vs historical captions.
6. **Synced** `new_submit/131–137` via `scripts/build_final_submission_pack.py`.
7. **Added** `internal_research_archive/README.md`.

## Archived files list

- `internal_research_archive/narrative_pre_reframe_2026-11-25/` (6 markdown files)

## Removed from active tree

None (archive-first policy; no experiment artifacts deleted).
#!/usr/bin/env python3
"""Copy final submission docs to new_submit and verify figure paths."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
FS = ROOT / "final_submission"
NS = ROOT / "new_submit"
MAP = [
    (FS / "00_README.md", "131_final_submission_README.md"),
    (FS / "01_synopsis_traceability.md", "132_synopsis_traceability.md"),
    (FS / "02_final_project_report.md", "133_final_project_report.md"),
    (FS / "03_final_presentation.md", "134_final_presentation.md"),
    (FS / "04_viva_preparation.md", "135_viva_preparation.md"),
    (FS / "05_figure_and_evidence_index.md", "136_figure_evidence_index.md"),
]
for src, name in MAP:
    if src.exists():
        shutil.copy2(src, NS / name)
IDX = NS / "00_NEW_SUBMIT_INDEX.md"
block = """
## Final evaluation pack (submission folder)

| File | Purpose |
|------|---------|
| `131_final_submission_README.md` | Index to `final_submission/` |
| `132_synopsis_traceability.md` | Synopsis ↔ evidence |
| `133_final_project_report.md` | Full report |
| `134_final_presentation.md` | Slide deck (Markdown) |
| `135_viva_preparation.md` | Oral exam Q&A |
| `136_figure_evidence_index.md` | Figure map |

Folder: `final_submission/` (figures in `final_submission/figures/`).
"""
txt = IDX.read_text(encoding="utf-8") if IDX.exists() else ""
if "Final evaluation pack" not in txt:
    IDX.write_text(txt.rstrip() + "\n" + block.strip() + "\n", encoding="utf-8")
print("Synced", sum(1 for s, _ in MAP if s.exists()), "files to new_submit/")
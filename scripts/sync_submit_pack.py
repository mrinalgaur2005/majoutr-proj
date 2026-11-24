#!/usr/bin/env python3
"""Sync submit/ pack from root docs and recent experiment artifacts (026–028)."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBMIT = ROOT / "submit"
ROOT_README = ROOT / "README.md"
ROOT_LOG = ROOT / "research_log.md"
FIG_IDX = ROOT / "results/figures/FIGURE_INDEX.md"


def copy(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def append_if_missing(target: Path, marker: str, block: str) -> None:
    text = target.read_text(encoding="utf-8") if target.exists() else ""
    if marker in text:
        return
    target.write_text(text.rstrip() + "\n\n" + block.strip() + "\n", encoding="utf-8")


def main() -> None:
    SUBMIT.mkdir(parents=True, exist_ok=True)

    copy(
        ROOT / "results/forecasting/experiment_025/dataset_eligibility_matrix.md",
        SUBMIT / "71_exp025_eligibility.md",
    )

    ex026 = ROOT / "results/forecasting/experiment_026"
    copy(ex026 / "experiment_026_summary.json", SUBMIT / "72_exp026_summary.json")
    copy(ex026 / "README.md", SUBMIT / "72_exp026_readme.md")
    copy(ex026 / "decision_register.md", SUBMIT / "72_exp026_decisions.md")

    ex027 = ROOT / "results/forecasting/experiment_027"
    copy(ex027 / "experiment_027_summary.json", SUBMIT / "73_exp027_summary.json")
    copy(ex027 / "decision_register.md", SUBMIT / "73_exp027_decisions.md")
    copy(ex027 / "protocol_compatibility.md", SUBMIT / "73_exp027_protocol_compatibility.md")

    ex028 = ROOT / "results/forecasting/experiment_028"
    copy(ex028 / "experiment_028_summary.json", SUBMIT / "74_exp028_summary.json")
    copy(ex028 / "results_summary.md", SUBMIT / "74_exp028_report.md")
    copy(ex028 / "limitations.md", SUBMIT / "74_exp028_limitations.md")
    copy(ex028 / "protocol_deviation_register.md", SUBMIT / "74_exp028_protocol_deviations.md")
    copy(ex028 / "timestamp_robustness.json", SUBMIT / "74_exp028_timestamp_robustness.json")
    copy(ex028 / "aggregate_metrics.json", SUBMIT / "74_exp028_aggregate_metrics.json")

    fig028 = ROOT / "results/figures/experiment_028"
    for name, submit_name in (
        ("exp028_val_mae_comparison_H1_START_00.png", "75_exp028_val_mae_track_a.png"),
        ("exp028_timestamp_sensitivity_f1.png", "76_exp028_timestamp_sensitivity.png"),
        ("exp028_category_slp_heatmap.png", "77_exp028_category_slp.png"),
        ("exp028_improvement_distribution.png", "78_exp028_improvement_dist.png"),
    ):
        copy(fig028 / name, SUBMIT / submit_name)

    marker_readme = "# Experiment 023 — CER prep"
    if ROOT_README.exists():
        full = ROOT_README.read_text(encoding="utf-8")
        start = full.find(marker_readme)
        if start >= 0:
            block = full[start:]
            submit_readme = SUBMIT / "01_README.md"
            if submit_readme.exists():
                old = submit_readme.read_text(encoding="utf-8")
                cut = old.find("# Next Step")
                if cut >= 0:
                    old = old[:cut]
                submit_readme.write_text(old.rstrip() + "\n\n" + block.strip() + "\n", encoding="utf-8")

    marker_log = "## Experiment 023 — CER access"
    submit_log = SUBMIT / "02_research_log.md"
    if ROOT_LOG.exists() and submit_log.exists():
        full = ROOT_LOG.read_text(encoding="utf-8")
        sub = submit_log.read_text(encoding="utf-8")
        if marker_log in full and marker_log not in sub:
            start = full.find(marker_log)
            tail = full[start:]
            cut = sub.find("# HUMAN REVIEW REQUIRED")
            base = sub[:cut].rstrip() if cut >= 0 else sub.rstrip()
            submit_log.write_text(base + "\n\n" + tail.strip() + "\n", encoding="utf-8")
        elif "Experiment 028" not in sub and "## Experiment 028" in full:
            start = full.find("## Experiment 027")
            if start >= 0:
                submit_log.write_text(sub.rstrip() + "\n\n" + full[start:].strip() + "\n", encoding="utf-8")

    fig_block = """
| FIG-132 | Val MAE comparison | `results/figures/experiment_028/exp028_val_mae_comparison_H1_START_00.png` | 028 | Norwegian exploratory SVR | `experiment_028_summary.json` | audit |
| FIG-133 | Timestamp sensitivity | `results/figures/experiment_028/exp028_timestamp_sensitivity_f1.png` | 028 | Dual H1 mapping | `timestamp_robustness.json` | audit |
| FIG-134 | Category SLP heatmap | `results/figures/experiment_028/exp028_category_slp_heatmap.png` | 028 | Native slot template | `category_slp_native_slot_train_snapshot.npy` | paper |
| FIG-135 | SLP improvement dist | `results/figures/experiment_028/exp028_improvement_distribution.png` | 028 | Track A vs B paired | per-household metrics | audit |

FIG-132–135: Experiment 028 Norwegian residential exploratory (not Exp 024).
"""
    append_if_missing(SUBMIT / "20_FIGURE_INDEX.md", "FIG-132", fig_block)
    if FIG_IDX.exists():
        append_if_missing(FIG_IDX, "FIG-132", fig_block)

    index = SUBMIT / "00_SUBMIT_INDEX.md"
    body = """# Submit pack index (synced)

| File | Description |
|------|-------------|
| `01_README.md` | Project timeline (through Exp 028) |
| `02_research_log.md` | Scientific log (through Exp 028) |
| `71_exp025_eligibility.md` | Dataset eligibility matrix |
| `72_exp026_*` | Norwegian ingestion / readiness |
| `73_exp027_*` | Temporal semantics + P2 audit |
| `74_exp028_*` | Exploratory Norwegian SVR±SLP |
| `75–78_exp028_*.png` | Key figures |

Refresh: `python3 scripts/sync_submit_pack.py`
"""
    index.write_text(body.strip() + "\n", encoding="utf-8")
    print("submit/ pack updated.")


if __name__ == "__main__":
    main()
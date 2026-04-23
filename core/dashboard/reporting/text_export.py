from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..tui.log_console import console
from .report_model import build_usage_report
from .report_txt_format import format_usage_report_txt
from .state import DashboardRangeState


def export_txt(
    project_root: Path,
    range_state: DashboardRangeState,
    *,
    reason: str | None = None,
    font_source: str | None = None,
    font_name: str | None = None,
) -> Path:
    report = build_usage_report(range_state)
    body = format_usage_report_txt(report)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_out = project_root / f"ai_team_usage_{ts}.txt"
    txt_out.write_text(body, encoding="utf-8")
    console.print(f"[green]TXT → {txt_out}[/green]")
    if font_name or font_source or reason:
        info = []
        if font_name:
            info.append(f"Using font: {font_name}")
        if font_source:
            info.append(f"source: {font_source}")
        if reason:
            info.append(f"reason: {reason}")
        console.print(f"[yellow]saved as TXT because {' | '.join(info)}[/yellow]")
    return txt_out

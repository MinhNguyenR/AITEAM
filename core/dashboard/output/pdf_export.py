from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from core.paths import FONTS_DIR, LEGACY_ASSETS_FONTS, REPO_ROOT

from ..reporting.report_model import UsageReport, build_usage_report
from ..reporting.state import DashboardRangeState
from ..tui.log_console import console

INTER_REGULAR_FILENAME = "Inter_18pt-Regular.ttf"
INTER_BOLD_FILENAME = "Inter_24pt-Bold.ttf"


def _candidate_fonts(project_root: Optional[Path] = None) -> tuple[Optional[Path], Optional[Path], str]:
    roots: list[Path] = []
    if project_root is not None:
        roots.append(Path(project_root) / "fonts")
    roots.append(FONTS_DIR)
    roots.append(LEGACY_ASSETS_FONTS)
    roots.append(REPO_ROOT / "fonts")
    roots.append(Path(__file__).resolve().parent / "fonts")
    roots.append(Path(__file__).resolve().parents[1] / "fonts")

    for root in roots:
        reg = root / INTER_REGULAR_FILENAME
        bold = root / INTER_BOLD_FILENAME
        if reg.exists() and reg.is_file():
            return reg.resolve(), bold.resolve() if bold.exists() and bold.is_file() else None, str(root.resolve())
    return None, None, ""


def _fallback_to_txt(project_root: Path, range_state: DashboardRangeState, *, reason: str) -> Path:
    from ..reporting.text_export import export_txt

    console.print(f"[yellow]{reason}[/yellow]")
    return export_txt(project_root, range_state, reason=reason)


def _section(pdf: Any, title: str, reg: str, title_face: str) -> None:
    pdf.ln(2)
    pdf.set_font(title_face, "", 11)
    pdf.multi_cell(0, 6, title, ln=True)
    pdf.set_font(reg, "", 9)


def _build_pdf_document(
    pdf: Any,
    report: UsageReport,
    regular_path: Path,
    bold_path: Optional[Path],
    font_source: str,
) -> None:
    regular_name = "InterRegular"
    bold_name = "InterBold"
    pdf.add_font(regular_name, "", str(regular_path), uni=True)
    if bold_path and bold_path.exists():
        pdf.add_font(bold_name, "", str(bold_path), uni=True)
    else:
        pdf.add_font(bold_name, "", str(regular_path), uni=True)

    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.set_margins(14, 14, 14)
    pdf.add_page()
    title_font = bold_name if bold_path and bold_path.exists() else regular_name
    pdf.set_font(title_font, "", 16)
    pdf.cell(0, 10, "AI Team — Usage report", ln=True)
    pdf.set_font(regular_name, "", 8)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 4, f"Font: {regular_path.name} | Source: {font_source}", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    pdf.set_font(regular_name, "", 10)
    pdf.multi_cell(
        0,
        5,
        f"Range: {report.label or '(default)'}\n"
        f"From: {report.since.isoformat(timespec='minutes') if report.since else ''}\n"
        f"To: {report.until.isoformat(timespec='minutes') if report.until else ''}\n"
        f"Generated: {report.generated_at.isoformat(timespec='seconds')}",
        ln=True,
    )

    _section(pdf, "Summary (KPI)", regular_name, title_font)
    pdf.set_font(regular_name, "", 9)
    pdf.multi_cell(
        0,
        5,
        f"Total requests: {report.total_requests:,}\n"
        f"Total tokens: {report.total_tokens:,}\n"
        f"Total spend: ${report.total_spend:.5f}\n"
        f"Input / output tokens: {report.prompt_tokens:,} / {report.completion_tokens:,}\n"
        f"CLI turns: {report.cli_turns}",
        ln=True,
    )

    _section(pdf, "By role", regular_name, title_font)
    pdf.set_font(regular_name, "", 8)
    col_w = [52, 18, 28, 28]
    headers = ["Role", "Req", "Tokens", "Spend"]
    pdf.set_fill_color(230, 240, 250)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 6, h, border=1, fill=True)
    pdf.ln()
    pdf.set_fill_color(255, 255, 255)
    for r in report.by_role[:40]:
        pdf.cell(col_w[0], 6, (r.role[:28])[:28], border=1)
        pdf.cell(col_w[1], 6, str(r.requests), border=1)
        pdf.cell(col_w[2], 6, f"{r.tokens:,}", border=1)
        pdf.cell(col_w[3], 6, f"{r.cost_usd:.5f}", border=1)
        pdf.ln()

    _section(pdf, "Batches (CLI turns)", regular_name, title_font)
    pdf.set_font(regular_name, "", 7)
    cw = [14, 36, 22, 18, 18, 12]
    hdr = ["#", "Timestamp", "Mode", "In tok", "Out tok", "Req"]
    pdf.set_fill_color(230, 240, 250)
    for i, h in enumerate(hdr):
        pdf.cell(cw[i], 5, h, border=1, fill=True)
    pdf.ln()
    pdf.set_fill_color(255, 255, 255)
    for b in report.batches[:35]:
        tot = b.get("totals") or {}
        row = [
            str(b.get("batch_idx", "?")),
            str(b.get("timestamp", ""))[:19],
            str(b.get("mode", ""))[:14],
            str(int(tot.get("prompt_tokens", 0))),
            str(int(tot.get("completion_tokens", 0))),
            str(len(b.get("usage_rows") or [])),
        ]
        for i, cell in enumerate(row):
            pdf.cell(cw[i], 5, cell, border=1)
        pdf.ln()

    pdf.set_font(regular_name, "", 7)
    pdf.ln(4)
    pdf.cell(0, 5, f"Page {pdf.page_no()}", align="C")


def export_pdf(project_root: Path, range_state: DashboardRangeState) -> Path | None:
    regular_path, bold_path, font_source = _candidate_fonts(project_root)
    report = build_usage_report(range_state)

    if regular_path is None:
        _fallback_to_txt(project_root, range_state, reason="Trying font: none found -> will fallback to TXT")
        return None

    console.print(f"[cyan]Trying font: {regular_path.name} ({font_source})[/cyan]")
    try:
        from fpdf import FPDF
    except ImportError:
        _fallback_to_txt(project_root, range_state, reason="fpdf2 not installed")
        return None

    try:
        pdf = FPDF(format="A4", unit="mm")
        _build_pdf_document(pdf, report, regular_path, bold_path, font_source)
        pdf_out = project_root / f"ai_team_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf.output(str(pdf_out))
        console.print(f"[green]PDF -> {pdf_out}[/green]")
        console.print(f"[cyan]Using font: {regular_path.name} ({font_source})[/cyan]")
        return pdf_out
    except Exception as e:  # noqa: BLE001
        _fallback_to_txt(project_root, range_state, reason=f"PDF export failed: {e}")
        return None


__all__ = ["_candidate_fonts", "export_pdf"]

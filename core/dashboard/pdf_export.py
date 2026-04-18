from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from utils import tracker

from .render import console
from .state import DashboardRangeState
from .utils import default_range, safe_float, safe_int

INTER_REGULAR_FILENAME = "Inter_18pt-Regular.ttf"
INTER_BOLD_FILENAME = "Inter_24pt-Bold.ttf"


def _candidate_fonts(project_root: Optional[Path] = None) -> tuple[Optional[Path], Optional[Path], str]:
    roots: list[Path] = []
    if project_root is not None:
        roots.append(Path(project_root) / "fonts")
    roots.append(Path(__file__).resolve().parent / "fonts")
    roots.append(Path(__file__).resolve().parents[1] / "fonts")

    for root in roots:
        reg = root / INTER_REGULAR_FILENAME
        bold = root / INTER_BOLD_FILENAME
        if reg.exists() and reg.is_file():
            return reg.resolve(), bold.resolve() if bold.exists() and bold.is_file() else None, str(root.resolve())
    return None, None, ""


def _build_export_lines(range_state: DashboardRangeState, batches: list[dict], rows_all: list[dict]) -> list[str]:
    since = range_state.since
    until = range_state.until
    label = str(range_state.label or "")
    tot_r = len(rows_all)
    tot_t = sum(safe_int(r.get("total_tokens")) for r in rows_all)
    tot_c = sum(safe_float(r.get("cost_usd")) for r in rows_all)
    io_all = tracker.token_io_totals(rows_all)
    role_breakdown: dict[str, dict[str, float | int]] = {}
    for r in rows_all:
        role = str(r.get("role_key") or r.get("agent") or "unknown")
        if role not in role_breakdown:
            role_breakdown[role] = {"requests": 0, "tokens": 0, "cost": 0.0}
        role_breakdown[role]["requests"] += 1
        role_breakdown[role]["tokens"] += safe_int(r.get("total_tokens"))
        role_breakdown[role]["cost"] += safe_float(r.get("cost_usd"))
    lines = [
        "AI Team - usage report",
        f"Range: {label}",
        f"From: {since.isoformat(timespec='minutes') if since else ''}",
        f"To: {until.isoformat(timespec='minutes') if until else ''}",
        f"Total requests: {tot_r}",
        f"Total tokens: {tot_t:,}",
        f"Total spend: ${tot_c:.5f}",
        f"Input tokens: {io_all['prompt_tokens']:,}",
        f"Output tokens: {io_all['completion_tokens']:,}",
        f"CLI turns: {len(batches)}",
        "",
        "Role / model summary",
    ]
    for role, stats in sorted(role_breakdown.items(), key=lambda x: (-int(x[1]["tokens"]), str(x[0]))):
        lines.append(f"- {role}: req={int(stats['requests'])} tokens={int(stats['tokens']):,} spend=${float(stats['cost']):.5f}")
    lines.append("")
    lines.append("Batch summary")
    for batch in batches[:20]:
        tot = batch.get("totals") or {}
        lines.append(
            f"#{batch.get('batch_idx', '?')} {str(batch.get('timestamp', ''))[:19]} mode={batch.get('mode', '')} "
            f"in={int(tot.get('prompt_tokens', 0)):,} out={int(tot.get('completion_tokens', 0)):,} req={len(batch.get('usage_rows') or [])}"
        )
    return lines


def _fallback_to_txt(project_root: Path, range_state: DashboardRangeState, *, reason: str) -> Path:
    from .render import export_txt

    console.print(f"[yellow]{reason}[/yellow]")
    return export_txt(project_root, range_state, reason=reason)


def _build_pdf_document(pdf, range_state: DashboardRangeState, regular_path: Path, bold_path: Optional[Path], font_source: str) -> None:
    since = range_state.since or default_range()[0]
    until = range_state.until or default_range()[1]
    batches = tracker.summarize_tokens_by_cli_batches(since, until)
    rows_all = list(range_state.rows or [])
    pdf.add_font("Inter", "", str(regular_path), uni=True)
    if bold_path and bold_path.exists():
        pdf.add_font("Inter", "B", str(bold_path), uni=True)
    else:
        pdf.add_font("Inter", "B", str(regular_path), uni=True)
    pdf.set_auto_page_break(auto=True, margin=2)
    pdf.set_margins(2, 2, 2)
    pdf.add_page(format=(1000, 1400))
    pdf.set_font("Inter", "B", 18)
    pdf.cell(0, 10, "AI Team - usage report", ln=True)
    pdf.ln(1)
    pdf.set_font("Inter", "", 10)
    pdf.cell(0, 6, f"Using font: {regular_path.name} | Font source: {font_source}", ln=True)
    pdf.ln(1)
    pdf.set_font("Inter", "", 9)
    pdf.cell(0, 6, "Summary", ln=True)
    for line in _build_export_lines(range_state, batches, rows_all):
        pdf.cell(0, 5, line, ln=True)


def export_pdf(project_root: Path, range_state: DashboardRangeState) -> None:
    regular_path, bold_path, font_source = _candidate_fonts(project_root)
    if regular_path is None:
        return _fallback_to_txt(project_root, range_state, reason="Trying font: none found -> will fallback to TXT")

    console.print(f"[cyan]Trying font: {regular_path.name} ({font_source})[/cyan]")
    try:
        from fpdf import FPDF
    except ImportError:
        return _fallback_to_txt(project_root, range_state, reason="fpdf2 not installed")

    try:
        pdf = FPDF(format="A4", unit="mm")
        _build_pdf_document(pdf, range_state, regular_path, bold_path, font_source)
        pdf_out = project_root / f"ai_team_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf.output(str(pdf_out))
        console.print(f"[green]PDF → {pdf_out}[/green]")
        console.print(f"[cyan]Using font: {regular_path.name} ({font_source})[/cyan]")
    except Exception as e:  # noqa: BLE001 — fpdf failure modes vary; always TXT fallback
        return _fallback_to_txt(project_root, range_state, reason=f"PDF export failed: {e}")

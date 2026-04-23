"""Plain-text report: sections + fixed-width tables."""
from __future__ import annotations

from .report_model import UsageReport


def _hline(width: int) -> str:
    return "=" * width


def _ascii_table(headers: list[str], rows: list[list[str]], col_widths: list[int]) -> list[str]:
    sep = "+".join("-" * (w + 2) for w in col_widths)
    top = "+" + sep + "+"
    bot = "+" + sep + "+"
    def fmt_row(cells: list[str]) -> str:
        parts = []
        for i, c in enumerate(cells):
            w = col_widths[i]
            parts.append(str(c)[:w].ljust(w))
        return "| " + " | ".join(parts) + " |"
    out = [top, fmt_row(headers), bot]
    for r in rows:
        out.append(fmt_row(r))
    out.append(bot)
    return out


def format_usage_report_txt(report: UsageReport) -> str:
    w = 88
    lines: list[str] = []
    lines.append(_hline(w))
    lines.append(" AI TEAM — USAGE EXPORT ".center(w, "="))
    lines.append(_hline(w))
    lines.append("")
    lines.append("=== METADATA ===")
    lines.append(f"  Range label   : {report.label or '(default)'}")
    lines.append(f"  From          : {report.since.isoformat(timespec='minutes') if report.since else ''}")
    lines.append(f"  To            : {report.until.isoformat(timespec='minutes') if report.until else ''}")
    lines.append(f"  Generated     : {report.generated_at.isoformat(timespec='seconds')}")
    lines.append("")

    lines.append("=== SUMMARY (KPI) ===")
    lines.append(f"  Total requests  : {report.total_requests:,}")
    lines.append(f"  Total tokens    : {report.total_tokens:,}")
    lines.append(f"  Total spend     : ${report.total_spend:.5f}")
    lines.append(f"  Input tokens    : {report.prompt_tokens:,}")
    lines.append(f"  Output tokens   : {report.completion_tokens:,}")
    lines.append(f"  CLI turns       : {report.cli_turns}")
    lines.append("")

    lines.append("=== BY ROLE ===")
    if report.by_role:
        t = _ascii_table(
            ["Role", "Req", "Tokens", "Spend USD"],
            [[r.role, str(r.requests), f"{r.tokens:,}", f"{r.cost_usd:.5f}"] for r in report.by_role],
            [24, 6, 12, 12],
        )
        lines.extend(t)
    else:
        lines.append("  (no rows in range)")
    lines.append("")

    lines.append("=== BY ROLE / MODEL ===")
    if report.by_role_model:
        t = _ascii_table(
            ["Role", "Model", "Req", "Tokens", "Spend"],
            [
                [x.role[:20], x.model[:28], str(x.requests), f"{x.tokens:,}", f"{x.cost_usd:.5f}"]
                for x in report.by_role_model[:80]
            ],
            [22, 30, 5, 12, 12],
        )
        lines.extend(t)
        if len(report.by_role_model) > 80:
            lines.append(f"  ... +{len(report.by_role_model) - 80} more role/model rows")
    else:
        lines.append("  (no rows in range)")
    lines.append("")

    lines.append("=== BATCHES (CLI turns) ===")
    if report.batches:
        t = _ascii_table(
            ["#", "Timestamp", "Mode", "In", "Out", "Req"],
            [
                [
                    str(b.get("batch_idx", "?")),
                    str(b.get("timestamp", ""))[:19],
                    str(b.get("mode", ""))[:12],
                    str(int((b.get("totals") or {}).get("prompt_tokens", 0))),
                    str(int((b.get("totals") or {}).get("completion_tokens", 0))),
                    str(len(b.get("usage_rows") or [])),
                ]
                for b in report.batches
            ],
            [6, 20, 14, 8, 8, 5],
        )
        lines.extend(t)
        if len(report.batches) >= report.batch_display_limit:
            lines.append(f"  (showing first {report.batch_display_limit} batches)")
    else:
        lines.append("  (no batches)")
    lines.append("")

    lines.append("=== PERIOD (tracker) ===")
    for name, st in sorted(report.period_summary.items()):
        lines.append(
            f"  {name:12}  req={int(st.get('requests', 0)):,}  "
            f"tok={int(st.get('tokens', 0)):,}  spend=${float(st.get('spend', 0.0)):.5f}"
        )
    lines.append("")
    if report.raw_display_note:
        lines.append(f"=== NOTE ===\n  {report.raw_display_note}")
    lines.append(_hline(w))
    lines.append(" END OF REPORT ".center(w, "="))
    lines.append(_hline(w))
    return "\n".join(lines) + "\n"

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from rich.box import ROUNDED
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from core.cli.cli_prompt import GLOBAL_BACK, GLOBAL_EXIT, normalize_global_command
from core.cli.ui import clear_screen
from core.services import dashboard_data

from .exporters import export_excel
from .panels import dashboard_panel as _dashboard_panel
from .pdf_export import export_pdf
from .render import export_txt, header
from .state import DashboardRangeState
from .utils import paginate

HISTORY_PAGE_SIZE = 8
HISTORY_CMD_OPEN = "open"
HISTORY_CMD_EXPORT = "export"
HISTORY_CMD_EXPORT_TXT = "export txt"
HISTORY_CMD_EXPORT_PDF = "export pdf"
HISTORY_CMD_EXPORT_XLSX = "export xlsx"
HISTORY_CMD_CHECK = "check"


def _parse_positive_int(raw: str, *, min_value: int = 1, max_value: Optional[int] = None) -> Optional[int]:
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    if value < min_value:
        return None
    if max_value is not None and value > max_value:
        return None
    return value


def show_history_browser(range_state: DashboardRangeState) -> None:
    from core.cli.ui import console

    while True:
        if range_state.since is None or range_state.until is None:
            console.print("[yellow]Range không hợp lệ, dùng mặc định 1 ngày.[/yellow]")
            range_state.set_days(1)
        clear_screen()
        header("DASHBOARD — HISTORY")
        _dashboard_panel(
            "History help",
            "Nhập số ngày trực tiếp để đổi range. Ví dụ: `7`, `12`, `30`.\n"
            "Lệnh nhanh: `n` trang sau · `p` trang trước · `open` xem turn · `export txt` / `export pdf` / `export xlsx`\n"
            "Global: `back` quay lại 1 tầng · `exit` thoát về CLI chính",
            border_style="#6495ED",
        )
        _dashboard_panel("Current range", f"Đang xem: {range_state.days} ngày", border_style="#C8C8FF")
        batches = dashboard_data.summarize_tokens_by_cli_batches(range_state.since, range_state.until)
        page_slice, page, total_pages = paginate(batches, range_state.log_page, HISTORY_PAGE_SIZE)
        table = Table(box=ROUNDED, show_lines=False)
        table.add_column("#", style="cyan", justify="right", width=3)
        table.add_column("Timestamp", style="white", overflow="fold")
        table.add_column("Mode", style="magenta", width=10)
        table.add_column("Req", justify="right", width=5)
        table.add_column("Tokens", justify="right", width=10)
        table.add_column("Spend", justify="right", style="yellow", width=10)
        if not page_slice:
            table.add_row("—", "Không có history trong range này", "—", "—", "—", "—")
        else:
            for idx, b in enumerate(page_slice, start=1 + page * HISTORY_PAGE_SIZE):
                reqs = sum(int(v.get("requests", 0)) for v in (b.get("by_role") or {}).values())
                table.add_row(
                    str(idx),
                    str(b.get("timestamp", ""))[:19],
                    str(b.get("mode", "")),
                    str(reqs),
                    f"{int(b.get('totals', {}).get('total_tokens', 0)):,}",
                    f"${float(b.get('cost_usd', 0.0)):.5f}",
                )
        _dashboard_panel(f"History turns — page {page + 1}/{total_pages}", table, border_style="#C8C8FF")
        raw = normalize_global_command(Prompt.ask("History command hoặc số ngày", default=str(range_state.days)))
        if raw in (GLOBAL_EXIT, GLOBAL_BACK, "b", "q"):
            return
        if raw in ("help", "h", "?"):
            continue
        if raw in ("n", "next"):
            range_state.log_page += 1
            continue
        if raw in ("p", "prev", "previous"):
            range_state.log_page -= 1
            continue
        if raw == HISTORY_CMD_CHECK:
            page_slice, page, total_pages = paginate(batches, range_state.log_page, HISTORY_PAGE_SIZE)
            if not page_slice:
                console.print("[yellow]Không có turn để open.[/yellow]")
                continue
            raw_idx = normalize_global_command(Prompt.ask(f"Open turn (1–{len(page_slice)})", default="1"))
            idx = _parse_positive_int(raw_idx, min_value=1, max_value=len(page_slice))
            if idx is not None:
                clear_screen()
                header(f"OPEN TURN {idx}")
                _show_batch_detail(page_slice[idx - 1])
                input("[dim]Enter[/dim]")
            else:
                console.print(f"[yellow]Chỉ nhận số từ 1 đến {len(page_slice)}.[/yellow]")
                input("[dim]Enter[/dim]")
            continue
        if raw.startswith(f"{HISTORY_CMD_OPEN} "):
            suffix = raw[len(f"{HISTORY_CMD_OPEN} ") :].strip()
            turn_no = _parse_positive_int(suffix)
            if turn_no is not None:
                page_slice, page, total_pages = paginate(batches, range_state.log_page, HISTORY_PAGE_SIZE)
                if not page_slice:
                    console.print("[yellow]Không có turn để open.[/yellow]")
                    continue
                idx = turn_no - 1
                if 0 <= idx < len(page_slice):
                    clear_screen()
                    header(f"OPEN TURN {turn_no}")
                    _show_batch_detail(page_slice[idx])
                    input("[dim]Enter[/dim]")
                else:
                    console.print(f"[yellow]Turn {turn_no} không nằm trong trang hiện tại. Hãy chọn từ 1 đến {len(page_slice)}.[/yellow]")
                    input("[dim]Enter[/dim]")
                continue
        if raw == HISTORY_CMD_EXPORT:
            console.print("[cyan]Export requested: pdf with safe fallback[/cyan]")
            export_pdf(Path.cwd(), range_state)
            input("[dim]Enter[/dim]")
            continue
        if raw == HISTORY_CMD_EXPORT_TXT:
            console.print("[cyan]Export requested: txt[/cyan]")
            export_txt(Path.cwd(), range_state, reason="manual export txt")
            input("[dim]Enter[/dim]")
            continue
        if raw == HISTORY_CMD_EXPORT_PDF:
            console.print("[cyan]Export requested: pdf[/cyan]")
            export_pdf(Path.cwd(), range_state)
            input("[dim]Enter[/dim]")
            continue
        if raw == HISTORY_CMD_EXPORT_XLSX:
            console.print("[cyan]Export requested: xlsx[/cyan]")
            export_excel(Path.cwd(), range_state)
            input("[dim]Enter[/dim]")
            continue
        if raw.isdigit() and int(raw) > 0:
            range_state.set_days(int(raw))
            continue
        if raw in ("", "enter"):
            continue
        console.print("[yellow]Không hiểu lệnh. Hãy nhập số ngày như `7` hoặc lệnh `check` / `export` / `back`.[/yellow]")
        input("[dim]Enter[/dim]")


def _show_batch_detail(batch: dict[str, Any]) -> None:
    from core.cli.ui import console

    tot = batch.get("totals") or {}
    rows = batch.get("usage_rows") or []
    turn_table = Table(box=ROUNDED, show_lines=False)
    turn_table.add_column("Field", style="cyan", width=20)
    turn_table.add_column("Value", style="white", overflow="fold")
    turn_table.add_row("Turn", f"{batch.get('batch_idx', '?')} · {str(batch.get('timestamp', ''))[:19]} · {batch.get('mode', '')}")
    turn_table.add_row("Input tokens", f"{int(tot.get('prompt_tokens', 0)):,}")
    turn_table.add_row("Output tokens", f"{int(tot.get('completion_tokens', 0)):,}")
    turn_table.add_row("Total tokens", f"{int(tot.get('total_tokens', 0)):,}")
    turn_table.add_row("Spend", f"${float(batch.get('cost_usd', 0.0)):.5f}")
    turn_table.add_row("Requests", str(len(rows)))
    console.print(Panel(turn_table, title="[bold]Check turn[/bold]", border_style="#6495ED", box=ROUNDED))

    paired: dict[tuple[str, str], dict[str, float | int]] = {}
    for r in rows:
        role = str(r.get("role_key") or r.get("agent") or "unknown")
        model = str(r.get("model") or "(unknown)")
        key = (role, model)
        if key not in paired:
            paired[key] = {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0}
        bucket = paired[key]
        bucket["requests"] += 1
        bucket["prompt_tokens"] += int(r.get("prompt_tokens", 0) or 0)
        bucket["completion_tokens"] += int(r.get("completion_tokens", 0) or 0)
        bucket["cost_usd"] += float(r.get("cost_usd", 0.0) or 0.0)

    combined = Table(box=ROUNDED, show_lines=False)
    combined.add_column("Role", style="cyan", overflow="fold")
    combined.add_column("Model", style="white", overflow="fold")
    combined.add_column("Req", justify="right")
    combined.add_column("Input", justify="right")
    combined.add_column("Output", justify="right")
    combined.add_column("Spend", justify="right", style="yellow")

    if not paired:
        combined.add_row("—", "—", "—", "—", "—", "—")
    else:
        for (role, model), st in sorted(paired.items(), key=lambda x: (x[0][0], x[0][1])):
            combined.add_row(
                role,
                model,
                str(int(st.get('requests', 0))),
                f"{int(st.get('prompt_tokens', 0)):,}",
                f"{int(st.get('completion_tokens', 0)):,}",
                f"${float(st.get('cost_usd', 0.0)):.5f}",
            )
    console.print(Panel(combined, title="[bold]Role / Model[/bold]", border_style="#C8C8FF", box=ROUNDED))

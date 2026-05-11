from __future__ import annotations

import shutil
from io import StringIO
from pathlib import Path
from typing import Any, Optional

from rich.box import ROUNDED
from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice, normalize_global_command, wait_enter
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, SOFT_WHITE, clear_screen
from core.cli.python_cli.i18n import t
from core.dashboard.application import data as dashboard_data

from ..reporting.state import DashboardRangeState
from ..tui.panels import dashboard_panel as _dashboard_panel
from ..tui.render import header
from ..tui.utils import paginate

HISTORY_PAGE_SIZE = 8


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


def _new_cap(width: int) -> tuple[StringIO, RichConsole]:
    sio = StringIO()
    cap = RichConsole(file=sio, force_terminal=True, width=width, no_color=False, highlight=False, markup=True)
    return sio, cap


def _build_history_on(range_state: DashboardRangeState, out: RichConsole) -> list:
    """Render history page onto *out*. Returns the batches list for reuse."""
    header(f"{t('menu.dashboard.desc')} - {t('dash.history_label').upper()}", out=out)
    _dashboard_panel(t("dash.curr_range"), t("dash.viewing_days").format(n=range_state.days), border_style="#C8C8FF", out=out)
    batches = dashboard_data.summarize_tokens_by_cli_batches(range_state.since, range_state.until)
    page_slice, page, total_pages = paginate(batches, range_state.log_page, HISTORY_PAGE_SIZE)
    table = Table(box=ROUNDED, show_lines=False)
    table.add_column("#",                  style="cyan",    justify="right", width=3)
    table.add_column(t("dash.time"),       style="white",   overflow="fold")
    table.add_column(t("dash.model_col"),  style="magenta", width=10)
    table.add_column(t("dash.req_col"),    justify="right", width=5)
    table.add_column(t("dash.tokens"),     justify="right", width=10)
    table.add_column(t("dash.spend"),      justify="right", style="yellow", width=10)
    if not page_slice:
        table.add_row("-", t("dash.no_history"), "-", "-", "-", "-")
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
    _dashboard_panel(
        t("dash.history_turns").format(curr=page + 1, total=total_pages),
        table,
        border_style="#C8C8FF",
        out=out,
    )
    return batches


def _capture_history_ansi(range_state: DashboardRangeState) -> tuple[str, list]:
    width = shutil.get_terminal_size((120, 30)).columns
    sio, cap = _new_cap(width)
    batches = _build_history_on(range_state, cap)
    cap.print("", end="")
    return sio.getvalue() or " ", batches


def _history_total_pages(batches: list) -> int:
    return max(1, (len(batches) + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE)


def _parse_page_step(parts: list[str]) -> int | None:
    if len(parts) == 1:
        return 1
    return _parse_positive_int(parts[1])


def _move_history_page(range_state: DashboardRangeState, batches: list, delta: int) -> bool:
    target = int(range_state.log_page) + delta
    total_pages = _history_total_pages(batches)
    if target < 0 or target >= total_pages:
        return False
    range_state.log_page = target
    return True


def _do_export(range_state: DashboardRangeState, fmt: str) -> str:
    """Run export and return a one-line result message."""
    cwd = Path.cwd()
    try:
        if fmt == "xlsx":
            from ..output.exporters import export_excel
            out = export_excel(cwd, range_state)
            return f"[green]XLSX saved -> {out}[/green]"
        elif fmt == "pdf":
            from ..output.pdf_export import export_pdf
            out = export_pdf(cwd, range_state)
            if out:
                return f"[green]PDF saved -> {out}[/green]"
            return "[yellow]PDF failed -> saved as TXT fallback[/yellow]"
        elif fmt == "txt":
            from ..reporting.text_export import export_txt
            out = export_txt(cwd, range_state)
            return f"[green]TXT saved -> {out}[/green]"
    except ImportError as e:
        return f"[red]Export error: missing dependency - {e}[/red]"
    except Exception as e:
        return f"[red]Export error: {e}[/red]"
    return "[red]Unknown format[/red]"


def _show_export_menu(range_state: DashboardRangeState) -> None:
    """Show a small fullscreen export picker, run the export, show result."""
    width = shutil.get_terminal_size((120, 30)).columns
    sio, cap = _new_cap(width)
    from rich.box import SIMPLE
    from rich.style import Style

    cap.print()
    tbl = Table(box=SIMPLE, show_header=False, padding=(0, 2))
    tbl.add_column("cmd",  style=Style(color=PASTEL_CYAN, bold=True), width=14)
    tbl.add_column("desc", style=Style(color=SOFT_WHITE))
    tbl.add_row("/pdf",  "Export PDF  (falls back to TXT if fpdf2 missing)")
    tbl.add_row("/xlsx", "Export Excel (.xlsx, requires openpyxl)")
    tbl.add_row("/txt",  "Export plain text")
    cap.print(Panel(tbl, title="[bold]Export Format[/bold]", border_style=PASTEL_BLUE, box=ROUNDED))

    fmt_choice = ask_choice(
        f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]",
        ["/pdf", "/xlsx", "/txt", "/back", "/exit"],
        default="/pdf",
        context="dashboard_history",
        header_ansi=sio.getvalue(),
    )
    if fmt_choice in (GLOBAL_BACK, "/back", GLOBAL_EXIT, "/exit", ""):
        return
    fmt_map = {"/pdf": "pdf", "/xlsx": "xlsx", "/txt": "txt"}
    fmt = fmt_map.get(fmt_choice)
    if not fmt:
        return

    msg = _do_export(range_state, fmt)

    # Show result in a brief fullscreen notice
    sio2, cap2 = _new_cap(width)
    cap2.print()
    cap2.print(Panel(Text.from_markup(msg), border_style=PASTEL_BLUE, box=ROUNDED))
    ask_choice(
        f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]",
        ["/back", "/exit"],
        default="/back",
        context="dashboard_history",
        header_ansi=sio2.getvalue(),
    )


def show_history_browser(range_state: DashboardRangeState) -> None:
    from core.cli.python_cli.ui.ui import console

    while True:
        if range_state.since is None or range_state.until is None:
            range_state.set_days(1)

        ansi, batches = _capture_history_ansi(range_state)
        choice = ask_choice(
            f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]",
            ["/back", "/exit", "/next", "/prev", "n", "p", "/open", "/export", "/days"],
            default="/next",
            context="dashboard_history",
            header_ansi=ansi,
        )

        if not choice or choice.strip() == "":
            continue

        cmd = choice.lower().strip()

        # 1. Global Navigation
        if cmd == "/exit":
            raise NavToMain
        if cmd == "/back":
            return

        # 2. Pagination
        parts = cmd.split()
        head = parts[0] if parts else cmd
        if head in ("/next", "n"):
            step = _parse_page_step(parts)
            if step is None or not _move_history_page(range_state, batches, step):
                console.print(f"[yellow]Page does not exist.[/yellow]")
                wait_enter()
            continue
        if head in ("/prev", "p"):
            step = _parse_page_step(parts)
            if step is None or not _move_history_page(range_state, batches, -step):
                console.print(f"[yellow]Page does not exist.[/yellow]")
                wait_enter()
            continue

        # 3. Direct Export Handling (/export <fmt>)
        if cmd.startswith("/export"):
            parts = cmd.split()
            if len(parts) > 1:
                fmt = parts[1].replace(".", "")
                if fmt in ("pdf", "xlsx", "txt"):
                    msg = _do_export(range_state, fmt)
                    console.print(f"\n{msg}")
                    wait_enter()
                    continue
            _show_export_menu(range_state)
            continue

        # 4. Direct Range Handling (/days <n>)
        if cmd.startswith("/days"):
            parts = cmd.split()
            if len(parts) > 1:
                n = _parse_positive_int(parts[1])
                if n:
                    range_state.set_days(n)
                    continue
            # Prompt for days if not provided
            clear_screen()
            console.print(Panel(f"[bold {PASTEL_BLUE}]{t('dash.viewing_days').format(n=range_state.days)}[/]", border_style=PASTEL_BLUE))
            raw_n = Prompt.ask(f"[{PASTEL_CYAN}]{t('dash.enter_days')}[/]")
            n = _parse_positive_int(raw_n)
            if n:
                range_state.set_days(n)
            continue

        # 5. Opening a Turn (Direct number or /open)
        # Check if cmd is a number (e.g., "5") or starts with "/open"
        target_idx: Optional[int] = None
        if cmd.isdigit():
            target_idx = int(cmd)
        elif cmd.startswith("/open"):
            parts = cmd.split()
            if len(parts) > 1 and parts[1].isdigit():
                target_idx = int(parts[1])
            else:
                # Fallback to palette/prompt for index
                if not batches:
                    console.print(f"[yellow]{t('dash.no_history')}[/yellow]")
                    wait_enter()
                    continue
                from core.cli.python_cli.ui.palette_app import ask_with_palette
                default_idx = str(1 + range_state.log_page * HISTORY_PAGE_SIZE)
                try:
                    raw_idx = ask_with_palette(f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]", context="dashboard_history", default=default_idx)
                except Exception:
                    raw_idx = Prompt.ask(">", default="1")
                target_idx = _parse_positive_int(raw_idx)

        if target_idx is not None:
            if 1 <= target_idx <= len(batches):
                _show_batch_detail_fullscreen(batches[target_idx - 1])
            else:
                console.print(f"[yellow]{t('dash.invalid_turn').format(n=len(batches))}[/yellow]")
                wait_enter()
            continue

        # 6. Legacy digit handling (standalone number to set days - deprecated but kept for safety if needed)
        # Actually, let's prioritize opening turns if it's a number.
        # If it's a very large number, maybe they meant days? No, let's be consistent.
        # Use /days for days, number for turn.


def _show_batch_detail_fullscreen(batch: dict[str, Any]) -> None:
    width = shutil.get_terminal_size((120, 30)).columns
    sio, cap = _new_cap(width)

    tot  = batch.get("totals") or {}
    rows = batch.get("usage_rows") or []
    turn_table = Table(box=ROUNDED, show_lines=False)
    turn_table.add_column(t("dash.field"),  style="cyan",  width=20)
    turn_table.add_column(t("ui.value"),    style="white", overflow="fold")
    turn_table.add_row(t("dash.turn"),
        f"{batch.get('batch_idx', '?')} - {str(batch.get('timestamp', ''))[:19]} - {batch.get('mode', '')}")
    turn_table.add_row(t("dash.input_tokens"),  f"{int(tot.get('prompt_tokens', 0)):,}")
    turn_table.add_row(t("dash.output_tokens"), f"{int(tot.get('completion_tokens', 0)):,}")
    turn_table.add_row(t("dash.total_tokens"),  f"{int(tot.get('total_tokens', 0)):,}")
    turn_table.add_row(t("dash.spend"),         f"${float(batch.get('cost_usd', 0.0)):.5f}")
    turn_table.add_row(t("dash.requests"),      str(len(rows)))
    cap.print(Panel(turn_table, title=f"[bold]{t('dash.check_turn')}[/bold]", border_style="#6495ED", box=ROUNDED))

    paired: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rows:
        role  = str(r.get("role_key") or r.get("agent") or "unknown")
        model = str(r.get("model") or "(unknown)")
        key   = (role, model)
        if key not in paired:
            paired[key] = {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0}
        bucket = paired[key]
        bucket["requests"]          += 1
        bucket["prompt_tokens"]     += int(r.get("prompt_tokens", 0) or 0)
        bucket["completion_tokens"] += int(r.get("completion_tokens", 0) or 0)
        bucket["cost_usd"]          += float(r.get("cost_usd", 0.0) or 0.0)

    combined = Table(box=ROUNDED, show_lines=False)
    combined.add_column(t("info.role_name"), style="cyan",   overflow="fold")
    combined.add_column(t("dash.model_col"), style="white",  overflow="fold")
    combined.add_column(t("dash.req_col"),   justify="right")
    combined.add_column(t("dash.in_col"),    justify="right")
    combined.add_column(t("dash.out_col"),   justify="right")
    combined.add_column(t("dash.spend"),     justify="right", style="yellow")
    if not paired:
        combined.add_row("-", "-", "-", "-", "-", "-")
    else:
        for (role, model), st in sorted(paired.items(), key=lambda x: (x[0][0], x[0][1])):
            combined.add_row(
                role, model,
                str(int(st.get("requests", 0))),
                f"{int(st.get('prompt_tokens', 0)):,}",
                f"{int(st.get('completion_tokens', 0)):,}",
                f"${float(st.get('cost_usd', 0.0)):.5f}",
            )
    cap.print(Panel(combined, title=f"[bold]{t('dash.role_model')}[/bold]", border_style="#C8C8FF", box=ROUNDED))

    ask_choice(
        f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]",
        ["/back", "/exit"],
        default="/back",
        context="dashboard_history",
        header_ansi=sio.getvalue(),
    )

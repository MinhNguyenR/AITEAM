from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from rich.box import ROUNDED
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice, normalize_global_command, wait_enter
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.ui.ui import PASTEL_CYAN, clear_screen
from core.cli.python_cli.i18n import t
from core.dashboard.application import data as dashboard_data

from ..output.exporters import export_excel
from ..output.pdf_export import export_pdf
from ..reporting.state import DashboardRangeState
from ..reporting.text_export import export_txt
from ..tui.panels import dashboard_panel as _dashboard_panel
from ..tui.render import header
from ..tui.utils import paginate

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
    from core.cli.python_cli.ui.ui import console

    while True:
        if range_state.since is None or range_state.until is None:
            console.print(f"[yellow]{t('dash.invalid_range')}[/yellow]")
            range_state.set_days(1)
        clear_screen()
        header(f"{t('menu.dashboard.desc')} — {t('dash.history_label').upper()}")
        _dashboard_panel(
            t("dash.history_help"),
            t("dash.history_desc"),
            border_style="#6495ED",
        )
        _dashboard_panel(t("dash.curr_range"), t("dash.viewing_days").format(n=range_state.days), border_style="#C8C8FF")
        batches = dashboard_data.summarize_tokens_by_cli_batches(range_state.since, range_state.until)
        page_slice, page, total_pages = paginate(batches, range_state.log_page, HISTORY_PAGE_SIZE)
        table = Table(box=ROUNDED, show_lines=False)
        table.add_column("#", style="cyan", justify="right", width=3)
        table.add_column(t("dash.time"), style="white", overflow="fold")
        table.add_column(t("dash.model_col"), style="magenta", width=10)
        table.add_column(t("dash.req_col"), justify="right", width=5)
        table.add_column(t("dash.tokens"), justify="right", width=10)
        table.add_column(t("dash.spend"), justify="right", style="yellow", width=10)
        if not page_slice:
            table.add_row("—", t("dash.no_history"), "—", "—", "—", "—")
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
        _dashboard_panel(t("dash.history_turns").format(curr=page + 1, total=total_pages), table, border_style="#C8C8FF")
        choice = ask_choice(
            f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]",
            ["/back", "/exit", "/next", "/prev", "/open", "/export", "back", "exit", "n", "p", "open", "export", "check"],
            default="/back",
            context="dashboard_history"
        )
        if choice in (GLOBAL_EXIT, "/exit"):
            raise NavToMain
        if choice in (GLOBAL_BACK, "/back"):
            return

        if choice in ("/next", "n"):
            range_state.log_page += 1
            continue
        if choice in ("/prev", "p"):
            range_state.log_page = max(0, range_state.log_page - 1)
            continue
        if choice in ("/open", "open", "check"):
            if not batches:
                console.print(f"[yellow]{t('dash.no_history')}[/yellow]")
                continue
            from core.cli.python_cli.ui.palette_app import ask_with_palette
            try:
                raw_idx = normalize_global_command(
                    ask_with_palette(
                        t("dash.open_turn_prompt").format(n=len(batches)),
                        context="dashboard_history",
                        default="1",
                    )
                )
            except Exception:
                raw_idx = normalize_global_command(Prompt.ask(t("dash.open_turn_prompt").format(n=len(batches)), default="1"))
            global_idx = _parse_positive_int(raw_idx, min_value=1, max_value=len(batches))
            if global_idx is not None:
                clear_screen()
                header(t("dash.open_turn").format(n=global_idx))
                _show_batch_detail(batches[global_idx - 1])
                wait_enter()
            else:
                console.print(f"[yellow]{t('dash.invalid_turn').format(n=len(batches))}[/yellow]")
                wait_enter()
            continue
        if choice in ("/export", "export"):
            console.print(f"[cyan]{t('dash.export_pdf_fallback')}[/cyan]")
            from ..reporting.exporter import export_pdf
            export_pdf(Path.cwd(), range_state)
            wait_enter()
            continue
        
        # If they type a number directly, change days
        if choice.isdigit() and int(choice) > 0:
            range_state.set_days(int(choice))
            continue
            
        console.print(f"[yellow]{t('ui.invalid_retry')}[/yellow]")
        wait_enter()


def _show_batch_detail(batch: dict[str, Any]) -> None:
    from core.cli.python_cli.ui.ui import console

    tot = batch.get("totals") or {}
    rows = batch.get("usage_rows") or []
    turn_table = Table(box=ROUNDED, show_lines=False)
    turn_table.add_column(t("dash.field"), style="cyan", width=20)
    turn_table.add_column(t("ui.value"), style="white", overflow="fold")
    turn_table.add_row(t("dash.turn"), f"{batch.get('batch_idx', '?')} · {str(batch.get('timestamp', ''))[:19]} · {batch.get('mode', '')}")
    turn_table.add_row(t("dash.input_tokens"), f"{int(tot.get('prompt_tokens', 0)):,}")
    turn_table.add_row(t("dash.output_tokens"), f"{int(tot.get('completion_tokens', 0)):,}")
    turn_table.add_row(t("dash.total_tokens"), f"{int(tot.get('total_tokens', 0)):,}")
    turn_table.add_row(t("dash.spend"), f"${float(batch.get('cost_usd', 0.0)):.5f}")
    turn_table.add_row(t("dash.requests"), str(len(rows)))
    console.print(Panel(turn_table, title=f"[bold]{t('dash.check_turn')}[/bold]", border_style="#6495ED", box=ROUNDED))

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
    combined.add_column(t("info.role_name"), style="cyan", overflow="fold")
    combined.add_column(t("dash.model_col"), style="white", overflow="fold")
    combined.add_column(t("dash.req_col"), justify="right")
    combined.add_column(t("dash.in_col"), justify="right")
    combined.add_column(t("dash.out_col"), justify="right")
    combined.add_column(t("dash.spend"), justify="right", style="yellow")

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
    console.print(Panel(combined, title=f"[bold]{t('dash.role_model')}[/bold]", border_style="#C8C8FF", box=ROUNDED))

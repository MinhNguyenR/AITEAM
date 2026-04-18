from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.box import ROUNDED
from rich.panel import Panel
from rich.prompt import Prompt

from core.cli.cli_prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice, normalize_global_command
from core.cli.helpbox import show_help_box
from core.cli.state import load_context_state, save_context_state
from core.cli.ui import clear_screen
from utils import tracker

from .budget import show_budget_menu
from .history import show_history_browser
from .render import fmt_budget_line, header, render_wallet_usage
from .state import DashboardRangeState
from .total import show_total_browser
from .utils import default_range

DASH_CMD_HISTORY = "history"
DASH_CMD_TOTAL = "total"
DASH_CMD_BUDGET = "budget"
DEFAULT_HISTORY_DAYS = 1


def _budget_status_text(settings: dict[str, Optional[float]]) -> str:
    summary = tracker.get_dashboard_summary(
        daily_budget_usd=settings.get("daily_budget_usd"),
        monthly_budget_usd=settings.get("monthly_budget_usd"),
        yearly_budget_usd=settings.get("yearly_budget_usd"),
    )
    return "\n".join(
        [
            fmt_budget_line("DAILY", summary.budget.daily),
            fmt_budget_line("MONTHLY", summary.budget.monthly),
            fmt_budget_line("YEARLY", summary.budget.yearly),
        ]
    )


def _dashboard_panel(title: str, body: object, *, border_style: str = "#6495ED") -> None:
    from core.cli.ui import console

    console.print(Panel(body, title=f"[bold]{title}[/bold]", border_style=border_style, box=ROUNDED))


def _dashboard_input(prompt: str, *, default: str = "") -> str:
    return normalize_global_command(Prompt.ask(prompt, default=default))


def _refresh_range_state(range_state: DashboardRangeState) -> None:
    since, until = range_state.since, range_state.until
    if since is None or until is None:
        since, until = default_range(range_state.days)
        range_state.since, range_state.until = since, until
    range_state.rows = tracker.read_usage_rows_timerange(since, until)


def _load_persisted_range_state() -> DashboardRangeState:
    state = load_context_state()
    try:
        return DashboardRangeState.from_dict(state)
    except (TypeError, ValueError) as e:
        from core.cli.ui import console

        console.print(f"[yellow]Dashboard state load failed, using defaults: {e}[/yellow]")
        days = int(state.get("dashboard_history_days") or DEFAULT_HISTORY_DAYS)
        since_s = str(state.get("dashboard_history_since") or "")
        until_s = str(state.get("dashboard_history_until") or "")
        since = tracker.parse_usage_timestamp(since_s) if since_s else None
        until = tracker.parse_usage_timestamp(until_s) if until_s else None
        label = str(state.get("dashboard_history_label") or f"last {days} days")
        return DashboardRangeState(label=label, since=since, until=until, days=days)


def _persist_range_state(range_state: DashboardRangeState) -> None:
    save_context_state(range_state.to_dict())


def _show_dashboard_home(settings: dict[str, Optional[float]], range_state: DashboardRangeState) -> None:
    from core.cli.ui import console

    clear_screen()
    _refresh_range_state(range_state)
    summary = tracker.get_dashboard_summary(
        daily_budget_usd=settings.get("daily_budget_usd"),
        monthly_budget_usd=settings.get("monthly_budget_usd"),
        yearly_budget_usd=settings.get("yearly_budget_usd"),
    )
    header("OPENROUTER CONTROL PANEL")
    render_wallet_usage(summary)
    console.print(Panel(_budget_status_text(settings), title="[bold #7FFFD4]BUDGET STATUS[/bold #7FFFD4]", border_style="#6495ED", box=ROUNDED))

    batches = tracker.summarize_tokens_by_cli_batches(range_state.since, range_state.until)
    preview = batches[-3:] if len(batches) > 3 else batches
    _dashboard_panel(f"Dashboard · {len(batches)} turn · {range_state.label}", "Open dashboard summary below", border_style="#C8C8FF")
    if preview:
        from rich.table import Table

        preview_table = Table(box=ROUNDED, show_lines=False)
        preview_table.add_column("Turn", style="cyan", justify="right", width=6)
        preview_table.add_column("Timestamp", style="white")
        preview_table.add_column("Req", justify="right", width=5)
        preview_table.add_column("Tokens", justify="right", width=10)
        preview_table.add_column("Spend", justify="right", style="yellow", width=10)
        for b in preview:
            reqs = sum(int(v.get("requests", 0)) for v in (b.get("by_role") or {}).values())
            preview_table.add_row(
                str(b.get("batch_idx", "?")),
                str(b.get("timestamp", ""))[:19],
                str(reqs),
                f"{int(b.get('totals', {}).get('total_tokens', 0)):,}",
                f"${float(b.get('cost_usd', 0.0)):.5f}",
            )
        _dashboard_panel("Recent turns", preview_table, border_style="#C8C8FF")
    _dashboard_panel(
        "Lệnh",
        "1) history = xem lịch sử theo số ngày\n2) total = tổng model/role/token/request/spend\n3) budget = add/reset budget\nGlobal: `back` quay lại 1 tầng · `exit` thoát về CLI chính",
        border_style="#6495ED",
    )


def _show_dashboard_loop(settings: dict[str, Optional[float]], range_state: DashboardRangeState) -> None:
    from core.cli.ui import console

    while True:
        _show_dashboard_home(settings, range_state)
        choice = ask_choice("Chọn lệnh", ["0", "1", "2", "3", DASH_CMD_HISTORY, DASH_CMD_TOTAL, DASH_CMD_BUDGET], default="1")
        if choice == GLOBAL_EXIT:
            return
        if choice in (GLOBAL_BACK, "0"):
            return
        if choice in ("1", DASH_CMD_HISTORY):
            show_history_browser(range_state)
            _persist_range_state(range_state)
            continue
        if choice in ("2", DASH_CMD_TOTAL):
            show_total_browser(range_state)
            _persist_range_state(range_state)
            continue
        if choice in ("3", DASH_CMD_BUDGET):
            clear_screen()
            header("BUDGET")
            show_budget_menu(settings)
            _persist_range_state(range_state)
            continue
        console.print("[yellow]Không hiểu lệnh.[/yellow]")


def show_dashboard(settings: Optional[dict] = None, project_root: Optional[str] = None):
    settings = dict(settings or {})
    if project_root:
        Path(project_root).resolve()
    range_state = _load_persisted_range_state()
    if range_state.since is None or range_state.until is None:
        range_state.set_days(DEFAULT_HISTORY_DAYS)
    _show_dashboard_loop(settings, range_state)

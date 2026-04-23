from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.box import ROUNDED, SIMPLE
from rich.panel import Panel
from rich.prompt import Prompt
from rich.style import Style
from rich.table import Table
from rich.text import Text

from core.cli.cli_prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice, normalize_global_command
from core.cli.nav import NavToMain
from core.cli.state import load_context_state, save_context_state
from core.cli.chrome.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, SOFT_WHITE, BRIGHT_BLUE, clear_screen
from utils import tracker

from ..reporting.state import DashboardRangeState
from ..tui.render import fmt_budget_line, header, render_wallet_usage
from ..tui.utils import default_range
from .budget import show_budget_menu
from .history import show_history_browser
from .total import show_total_browser

DASH_CMD_HISTORY = "history"
DASH_CMD_TOTAL   = "total"
DASH_CMD_BUDGET  = "budget"
DEFAULT_HISTORY_DAYS = 1

_BORDER = PASTEL_BLUE


def _panel(title: str, body, *, border: str = _BORDER) -> None:
    from core.cli.chrome.ui import console
    console.print(Panel(body, title=f"[bold]{title}[/bold]", border_style=border, box=ROUNDED))


def _input(prompt: str, *, default: str = "") -> str:
    return normalize_global_command(Prompt.ask(prompt, default=default))


def _refresh_range(rs: DashboardRangeState) -> None:
    if rs.since is None or rs.until is None:
        rs.since, rs.until = default_range(rs.days)
    rs.rows = tracker.read_usage_rows_timerange(rs.since, rs.until)


def _load_rs() -> DashboardRangeState:
    state = load_context_state()
    try:
        return DashboardRangeState.from_dict(state)
    except (TypeError, ValueError):
        days   = int(state.get("dashboard_history_days") or DEFAULT_HISTORY_DAYS)
        since  = tracker.parse_usage_timestamp(str(state.get("dashboard_history_since") or "")) or None
        until  = tracker.parse_usage_timestamp(str(state.get("dashboard_history_until") or "")) or None
        label  = str(state.get("dashboard_history_label") or f"last {days} days")
        return DashboardRangeState(label=label, since=since, until=until, days=days)


def _persist_rs(rs: DashboardRangeState) -> None:
    save_context_state(rs.to_dict())


def _budget_text(settings: dict) -> str:
    summary = tracker.get_dashboard_summary(
        daily_budget_usd   = settings.get("daily_budget_usd"),
        monthly_budget_usd = settings.get("monthly_budget_usd"),
        yearly_budget_usd  = settings.get("yearly_budget_usd"),
    )
    return "\n".join([
        fmt_budget_line("DAILY",   summary.budget.daily),
        fmt_budget_line("MONTHLY", summary.budget.monthly),
        fmt_budget_line("YEARLY",  summary.budget.yearly),
    ])


def _show_home(settings: dict, rs: DashboardRangeState) -> None:
    from core.cli.chrome.ui import console

    clear_screen()
    _refresh_range(rs)
    summary = tracker.get_dashboard_summary(
        daily_budget_usd   = settings.get("daily_budget_usd"),
        monthly_budget_usd = settings.get("monthly_budget_usd"),
        yearly_budget_usd  = settings.get("yearly_budget_usd"),
    )
    header("DASHBOARD")
    render_wallet_usage(summary)

    # Budget status
    _panel("Budget", _budget_text(settings), border=PASTEL_BLUE)

    # Recent turns preview
    batches = tracker.summarize_tokens_by_cli_batches(rs.since, rs.until)
    preview = batches[-3:] if len(batches) > 3 else batches
    if preview:
        tbl = Table(box=SIMPLE, show_lines=False, padding=(0, 1))
        tbl.add_column("Turn",      style=Style(color=PASTEL_CYAN),   justify="right", width=6)
        tbl.add_column("Time",      style=Style(color=SOFT_WHITE),    width=20)
        tbl.add_column("Requests",  justify="right", width=8)
        tbl.add_column("Tokens",    justify="right", width=12)
        tbl.add_column("Spend",     justify="right", style="yellow",  width=12)
        for b in preview:
            reqs = sum(int(v.get("requests", 0)) for v in (b.get("by_role") or {}).values())
            tbl.add_row(
                str(b.get("batch_idx", "?")),
                str(b.get("timestamp", ""))[:19],
                str(reqs),
                f"{int(b.get('totals', {}).get('total_tokens', 0)):,}",
                f"${float(b.get('cost_usd', 0.0)):.5f}",
            )
        _panel(f"Recent  ({len(batches)} total · {rs.label})", tbl, border=PASTEL_LAVENDER)

    # Command hint
    hint = Text.assemble(
        ("  1  history  ", Style(color=PASTEL_CYAN, bold=True)),
        ("usage by day/range   ", Style(color=SOFT_WHITE, dim=True)),
        ("  2  total    ", Style(color=PASTEL_CYAN, bold=True)),
        ("aggregate by model/role   ", Style(color=SOFT_WHITE, dim=True)),
        ("  3  budget   ", Style(color=PASTEL_CYAN, bold=True)),
        ("set limits", Style(color=SOFT_WHITE, dim=True)),
    )
    console.print(hint)
    console.print()


def _loop(settings: dict, rs: DashboardRangeState) -> None:
    from core.cli.chrome.ui import console

    while True:
        _show_home(settings, rs)
        choice = ask_choice(
            f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]",
            ["0", "1", "2", "3", DASH_CMD_HISTORY, DASH_CMD_TOTAL, DASH_CMD_BUDGET],
            default="1",
        )
        if choice == GLOBAL_EXIT:
            raise NavToMain
        if choice in (GLOBAL_BACK, "0"):
            return
        if choice in ("1", DASH_CMD_HISTORY):
            show_history_browser(rs)
            _persist_rs(rs)
            continue
        if choice in ("2", DASH_CMD_TOTAL):
            show_total_browser(rs)
            _persist_rs(rs)
            continue
        if choice in ("3", DASH_CMD_BUDGET):
            clear_screen()
            header("BUDGET")
            show_budget_menu(settings)
            _persist_rs(rs)
            continue
        console.print("[yellow]Unknown command.[/yellow]")


def show_dashboard(settings: Optional[dict] = None, project_root: Optional[str] = None):
    settings = dict(settings or {})
    if project_root:
        Path(project_root).resolve()
    rs = _load_rs()
    if rs.since is None or rs.until is None:
        rs.set_days(DEFAULT_HISTORY_DAYS)
    _loop(settings, rs)

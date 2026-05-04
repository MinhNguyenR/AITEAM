from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.box import ROUNDED, SIMPLE
from rich.panel import Panel
from rich.prompt import Prompt
from rich.style import Style
from rich.table import Table
from rich.text import Text

from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice, normalize_global_command
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.shell.state import load_context_state, save_context_state
from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, SOFT_WHITE, BRIGHT_BLUE, clear_screen
from core.cli.python_cli.i18n import t
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
    from core.cli.python_cli.ui.ui import console
    console.print(Panel(body, title=f"[bold]{title}[/bold]", border_style=border, box=ROUNDED))


def _input(prompt: str, *, default: str = "") -> str:
    from core.cli.python_cli.ui.palette_app import ask_with_palette
    return normalize_global_command(ask_with_palette(prompt, context="dashboard_home", default=default))


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
        label  = str(state.get("dashboard_history_label") or t('dash.history_label_short').format(n=days))
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
        fmt_budget_line(t("dash.budget_daily").upper(),   summary.budget.daily),
        fmt_budget_line(t("dash.budget_monthly").upper(), summary.budget.monthly),
        fmt_budget_line(t("dash.budget_yearly").upper(),  summary.budget.yearly),
    ])


def _show_home(settings: dict, rs: DashboardRangeState) -> None:
    from core.cli.python_cli.ui.ui import console

    clear_screen()
    _refresh_range(rs)
    summary = tracker.get_dashboard_summary(
        daily_budget_usd   = settings.get("daily_budget_usd"),
        monthly_budget_usd = settings.get("monthly_budget_usd"),
        yearly_budget_usd  = settings.get("yearly_budget_usd"),
    )
    header(t("menu.dashboard.desc"))
    render_wallet_usage(summary)

    # Budget status
    _panel(t("dash.budget_title"), _budget_text(settings), border=PASTEL_BLUE)

    # Recent turns preview — show 3 globally latest (not range-filtered)
    batches = tracker.summarize_tokens_by_cli_batches(rs.since, rs.until)
    try:
        # Get all-time batches for "latest 3" regardless of current date range
        from datetime import datetime as _dt, timedelta as _td
        _far_past  = _dt(2000, 1, 1)
        _far_future = _dt(2100, 1, 1)
        all_batches = tracker.summarize_tokens_by_cli_batches(_far_past, _far_future)
        preview = all_batches[-3:] if len(all_batches) > 3 else all_batches
    except Exception:
        preview = batches[-3:] if len(batches) > 3 else batches
    if preview:
        tbl = Table(box=SIMPLE, show_lines=False, padding=(0, 1))
        tbl.add_column(t("dash.turn"),      style=Style(color=PASTEL_CYAN),   justify="right", width=6)
        tbl.add_column(t("dash.time"),      style=Style(color=SOFT_WHITE),    width=20)
        tbl.add_column(t("dash.requests"),  justify="right", width=12)
        tbl.add_column(t("dash.tokens"),    justify="right", width=12)
        tbl.add_column(t("dash.spend"),     justify="right", style="yellow",  width=12)
        for b in preview:
            reqs = sum(int(v.get("requests", 0)) for v in (b.get("by_role") or {}).values())
            tbl.add_row(
                str(b.get("batch_idx", "?")),
                str(b.get("timestamp", ""))[:19],
                str(reqs),
                f"{int(b.get('totals', {}).get('total_tokens', 0)):,}",
                f"${float(b.get('cost_usd', 0.0)):.5f}",
            )
        _panel(t("dash.recent_title").format(n=len(batches), label=rs.label), tbl, border=PASTEL_LAVENDER)

    # Command hint
    hint = Text.assemble(
        ("  /history  ", Style(color=PASTEL_CYAN, bold=True)),
        (f"{t('dash.history_label')}   ", Style(color=SOFT_WHITE, dim=True)),
        ("  /total    ", Style(color=PASTEL_CYAN, bold=True)),
        (f"{t('dash.total_label')}   ", Style(color=SOFT_WHITE, dim=True)),
        ("  /budget   ", Style(color=PASTEL_CYAN, bold=True)),
        (f"{t('dash.budget_label')}", Style(color=SOFT_WHITE, dim=True)),
    )
    console.print(hint)
    console.print()
    console.print(f"  [dim]/back[/dim]  {t('nav.back')}")
    console.print()


def _loop(settings: dict, rs: DashboardRangeState) -> None:
    from core.cli.python_cli.ui.ui import console

    while True:
        _show_home(settings, rs)
        choice = ask_choice(
            f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]",
            ["/back", "/exit", "/history", "/total", "/budget"],
            default="/history",
            context="dashboard_home"
        )
        if choice in (GLOBAL_EXIT, "/exit"):
            raise NavToMain
        if choice in (GLOBAL_BACK, "/back"):
            return
        if choice == "/history":
            try:
                show_history_browser(rs)
            except NavToMain:
                return  # exit dashboard; caller's NavToMain handler continues main loop
            _persist_rs(rs)
            continue
        if choice == "/total":
            show_total_browser(rs)
            _persist_rs(rs)
            continue
        if choice == "/budget":
            clear_screen()
            header(t("dash.budget_title").upper())
            show_budget_menu(settings)
            _persist_rs(rs)
            continue
        console.print(f"[yellow]{t('cmd.invalid_cmd').format(cmd=choice)}[/yellow]")


def show_dashboard(settings: Optional[dict] = None, project_root: Optional[str] = None):
    settings = dict(settings or {})
    if project_root:
        Path(project_root).resolve()
    rs = _load_rs()
    # Always recalculate since/until relative to NOW using persisted days value
    rs.set_days(rs.days)
    _loop(settings, rs)

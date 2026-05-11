from __future__ import annotations

import shutil
from io import StringIO
from typing import Optional

from rich.box import ROUNDED
from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from core.app_state.settings import save_cli_settings
from core.cli.python_cli.i18n import t
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice
from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, SOFT_WHITE, clear_screen
from utils import tracker

from ..tui.render import header

_BAR_WIDTH = 32
_FULL_BLOCK = "#"
_EMPTY_BLOCK = "-"

_PERIOD_DESC = {
    "daily": t("dash.period_daily"),
    "monthly": t("dash.period_monthly"),
    "yearly": t("dash.period_yearly"),
}


def _fmt_limit(value: Optional[float]) -> str:
    return t("dash.unlimited") if value is None else f"${value:.2f}"


def _bar(spent: float, limit: Optional[float]) -> Text:
    if limit is None or limit <= 0:
        filled, pct = 0, 0.0
    else:
        pct = min(1.0, spent / limit)
        filled = round(pct * _BAR_WIDTH)
    color = PASTEL_CYAN if limit is None else ("red" if pct >= 0.9 else "yellow" if pct >= 0.7 else "green")
    bar = Text()
    bar.append(_FULL_BLOCK * filled, style=Style(color=color, bold=True))
    bar.append(_EMPTY_BLOCK * (_BAR_WIDTH - filled), style=Style(color="#444466"))
    return bar


def _status_label(metric: tracker.BudgetMetric) -> Text:
    text = Text()
    if metric.unlimited:
        text.append(t("dash.unlimited").lower(), style=Style(color=PASTEL_CYAN, dim=True))
        return text
    pct = metric.spent_usd / metric.limit_usd if metric.limit_usd > 0 else 0
    if metric.status == "over":
        text.append(t("dash.over"), style=Style(color="red", bold=True))
    elif pct >= 0.9:
        text.append(t("dash.near"), style=Style(color="yellow", bold=True))
    else:
        text.append(t("dash.ok"), style=Style(color="green"))
    return text


def _budget_card(key: str, name: str, metric: tracker.BudgetMetric, limit: Optional[float], *, active: bool) -> Panel:
    body = Table.grid(expand=True)
    body.add_column(ratio=1)
    body.add_column(justify="right")
    body.add_row(Text(_PERIOD_DESC[key], style=Style(color="#AAB0D6")), "")
    body.add_row(Text(t("dash.spent"), style=Style(color="#8888AA")), Text(f"${metric.spent_usd:.4f}", style=Style(color=SOFT_WHITE)))
    body.add_row(Text(t("dash.limit"), style=Style(color="#8888AA")), Text(_fmt_limit(limit), style=Style(color=PASTEL_LAVENDER)))
    body.add_row(Text(t("dash.progress"), style=Style(color="#8888AA")), _bar(metric.spent_usd, limit))
    body.add_row(Text(t("dash.status"), style=Style(color="#8888AA")), _status_label(metric))
    color = "yellow" if active else PASTEL_BLUE
    title_color = "yellow" if active else PASTEL_CYAN
    return Panel(
        body,
        title=f"[bold {title_color}]{name}[/bold {title_color}]",
        border_style=color,
        box=ROUNDED,
        padding=(0, 1),
    )


def _build_budget_on(settings: dict, out: RichConsole, *, highlight: Optional[str] = None) -> None:
    daily = settings.get("daily_budget_usd")
    monthly = settings.get("monthly_budget_usd")
    yearly = settings.get("yearly_budget_usd")

    header(t("dash.budget_title").upper(), out=out)

    try:
        summary = tracker.get_dashboard_summary(
            daily_budget_usd=daily,
            monthly_budget_usd=monthly,
            yearly_budget_usd=yearly,
        )
        budget = summary.budget
        periods = [
            ("daily", t("dash.budget_daily").upper(), budget.daily, daily),
            ("monthly", t("dash.budget_monthly").upper(), budget.monthly, monthly),
            ("yearly", t("dash.budget_yearly").upper(), budget.yearly, yearly),
        ]
    except Exception:
        periods = []

    if not periods:
        return

    cards = [
        _budget_card(key, name, metric, raw_limit, active=highlight == key)
        for key, name, metric, raw_limit in periods
    ]

    grid = Table.grid(expand=True)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_row(cards[0], cards[1])
    grid.add_row(cards[2], "")
    out.print(grid)

    if highlight:
        edit = Table.grid(expand=True)
        edit.add_column(ratio=1)
        edit.add_row(Text(t("dash.edit_hint"), style=Style(color=SOFT_WHITE)))
        edit.add_row(Text(t("dash.edit_nav"), style=Style(color="#AAB0D6")))
        out.print(Panel(edit, title=f"[bold]{t('dash.edit_title')}[/bold]", border_style=PASTEL_LAVENDER, box=ROUNDED, padding=(0, 1)))


def _capture_budget_ansi(settings: dict, *, highlight: Optional[str] = None) -> str:
    width = shutil.get_terminal_size((120, 30)).columns
    sio = StringIO()
    cap = RichConsole(file=sio, force_terminal=True, width=width, no_color=False, highlight=False, markup=True)
    _build_budget_on(settings, cap, highlight=highlight)
    return sio.getvalue()


def _ask_budget_value_inline(settings: dict, key: str, current: Optional[float]) -> Optional[float]:
    from core.cli.python_cli.shell.prompt import normalize_global_command
    from core.cli.python_cli.ui.palette_app import ask_with_palette

    try:
        raw = ask_with_palette(
            ">",
            context="budget_value",
            default="",
            header_ansi=_capture_budget_ansi(settings, highlight=key),
        ).strip()
    except Exception:
        return current

    raw = normalize_global_command(raw)
    if raw in ("/back", "/exit"):
        return current
    if not raw or raw == "/unlimited":
        return None
    try:
        value = float(raw)
        if value < 0:
            raise ValueError
        return value
    except ValueError:
        return current


def _set_or_clear(settings: dict[str, Optional[float]], key: str, value: Optional[float]) -> None:
    if value is None:
        settings.pop(key, None)
    else:
        settings[key] = value


def show_budget_menu(settings: dict[str, Optional[float]]) -> None:
    while True:
        choice = ask_choice(
            ">",
            ["/back", "/exit", "/daily", "/monthly", "/yearly", "/reset"],
            default="/daily",
            context="dashboard_budget",
            header_ansi=_capture_budget_ansi(settings),
        )
        if choice == "/exit":
            raise NavToMain
        if choice == "/back":
            return
        if choice == "/daily":
            _set_or_clear(settings, "daily_budget_usd", _ask_budget_value_inline(settings, "daily", settings.get("daily_budget_usd")))
        elif choice == "/monthly":
            _set_or_clear(settings, "monthly_budget_usd", _ask_budget_value_inline(settings, "monthly", settings.get("monthly_budget_usd")))
        elif choice == "/yearly":
            _set_or_clear(settings, "yearly_budget_usd", _ask_budget_value_inline(settings, "yearly", settings.get("yearly_budget_usd")))
        elif choice == "/reset":
            settings["daily_budget_usd"] = None
            settings["monthly_budget_usd"] = None
            settings["yearly_budget_usd"] = None
        save_cli_settings(settings)

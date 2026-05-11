from __future__ import annotations

import shutil
from io import StringIO

from rich.box import ROUNDED
from rich.console import Console as RichConsole
from rich.table import Table

from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.ui.ui import PASTEL_CYAN, clear_screen
from core.cli.python_cli.i18n import t
from core.dashboard.application import data as dashboard_data
from utils import tracker

from ..reporting.state import DashboardRangeState
from ..tui.panels import dashboard_panel as _dashboard_panel
from ..tui.render import header
from ..tui.utils import paginate

TOTAL_PAGE_SIZE = 50


def _build_total_on(range_state: DashboardRangeState, out: RichConsole) -> None:
    header(f"{t('menu.dashboard.desc')} - {t('dash.total_label').upper()}", out=out)
    rows = dashboard_data.read_usage_log(last_n=8000)
    page_slice, page, total_pages = paginate(
        dashboard_data.aggregate_rows_by_role_model(rows),
        range_state.batch_page,
        TOTAL_PAGE_SIZE,
    )
    table = Table(box=ROUNDED, show_lines=False)
    table.add_column(t("info.role_name"), style="cyan")
    table.add_column(t("dash.model_col"), style="white",  overflow="fold")
    table.add_column(t("dash.requests"),  justify="right")
    table.add_column(t("dash.tokens"),    justify="right")
    table.add_column(t("dash.spend"),     justify="right", style="yellow")
    if not page_slice:
        table.add_row("-", "-", "-", "-", "-")
    else:
        for row in page_slice:
            table.add_row(
                str(row["role"]),
                str(row["model"] or "-"),
                str(row["requests"]),
                f"{int(row['tokens']):,}",
                f"${float(row['cost']):.5f}",
            )
    _dashboard_panel(
        f"{t('dash.total_label').upper()} - {t('dash.page').format(curr=page + 1, total=total_pages)}",
        table,
        border_style="#C8C8FF",
        out=out,
    )


def _capture_total_ansi(range_state: DashboardRangeState) -> str:
    width = shutil.get_terminal_size((120, 30)).columns
    sio = StringIO()
    cap = RichConsole(file=sio, force_terminal=True, width=width, no_color=False, highlight=False, markup=True)
    _build_total_on(range_state, cap)
    return sio.getvalue()


def _build_role_detail_on(role_name: str, rows: list, out: RichConsole) -> None:
    detail = tracker.aggregate_role_detail(rows, role_name)
    header(t("dash.role_detail_title").format(role=role_name.upper()), out=out)
    table = Table(box=ROUNDED, show_lines=False)
    table.add_column(t("dash.model_col"),       style="white", overflow="fold")
    table.add_column(t("dash.requests"),        justify="right")
    table.add_column(t("dash.input_real"),      justify="right", style="cyan")
    table.add_column(t("dash.input_cache_read"),justify="right", style="green")
    table.add_column(t("dash.output_real"),     justify="right", style="blue")
    table.add_column(t("dash.cache_write"),     justify="right", style="dim")
    table.add_column(t("dash.spend"),           justify="right", style="yellow")
    if not detail:
        table.add_row("—", "—", "—", "—", "—", "—", "—")
    else:
        for row in detail:
            input_real = max(0, row["input_tokens"] - row["cache_read_tokens"])
            table.add_row(
                str(row["model"] or "—"),
                str(row["requests"]),
                f"{input_real:,}",
                f"{row['cache_read_tokens']:,}",
                f"{row['output_tokens']:,}",
                f"{row['cache_write_tokens']:,}",
                f"${row['cost']:.5f}",
            )
    _dashboard_panel(
        t("dash.role_detail_title").format(role=role_name.upper()),
        table,
        border_style="#C8C8FF",
        out=out,
    )


def _capture_role_detail_ansi(role_name: str, rows: list) -> str:
    width = shutil.get_terminal_size((120, 30)).columns
    sio = StringIO()
    cap = RichConsole(file=sio, force_terminal=True, width=width, no_color=False, highlight=False, markup=True)
    _build_role_detail_on(role_name, rows, cap)
    return sio.getvalue()


def _show_role_detail(role_name: str, rows: list) -> None:
    while True:
        clear_screen()
        choice = ask_choice(
            f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]",
            ["/back", "/exit"],
            default="/back",
            context="dashboard_role_detail",
            header_ansi=_capture_role_detail_ansi(role_name, rows),
        )
        if choice == "/exit":
            raise NavToMain
        return


def show_total_browser(range_state: DashboardRangeState) -> None:
    while True:
        clear_screen()
        rows = dashboard_data.read_usage_log(last_n=8000)
        choice = ask_choice(
            f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]",
            ["/back", "/exit", "/next", "/prev", "/open"],
            default="/back",
            context="dashboard_total",
            header_ansi=_capture_total_ansi(range_state),
        )
        if choice == "/exit":
            raise NavToMain
        if choice == "/back":
            return
        if choice == "/next":
            range_state.batch_page += 1
            continue
        if choice == "/prev":
            range_state.batch_page -= 1
            continue
        if choice.startswith("/open"):
            role_name = choice[len("/open"):].strip()
            if not role_name:
                continue
            detail = tracker.aggregate_role_detail(rows, role_name)
            if not detail:
                from core.cli.python_cli.ui.ui import console
                console.print(f"[yellow]{t('dash.role_not_found').format(role=role_name)}[/yellow]")
                continue
            try:
                _show_role_detail(role_name, rows)
            except NavToMain:
                raise
            continue


__all__ = ["show_total_browser"]

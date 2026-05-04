from __future__ import annotations

from rich.box import ROUNDED
from rich.table import Table

from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.ui.ui import clear_screen
from core.cli.python_cli.i18n import t
from core.dashboard.application import data as dashboard_data

from ..reporting.state import DashboardRangeState
from ..tui.panels import dashboard_panel as _dashboard_panel
from ..tui.render import header
from ..tui.utils import paginate

TOTAL_PAGE_SIZE = 50


def show_total_browser(range_state: DashboardRangeState) -> None:

    while True:
        clear_screen()
        header(f"{t('menu.dashboard.desc')} — {t('dash.total_label').upper()}")
        _dashboard_panel(
            t("dash.total_help"),
            t("dash.total_desc"),
            border_style="#6495ED",
        )
        rows = dashboard_data.read_usage_log(last_n=8000)
        page_slice, page, total_pages = paginate(dashboard_data.aggregate_rows_by_role_model(rows), range_state.batch_page, TOTAL_PAGE_SIZE)
        table = Table(box=ROUNDED, show_lines=False)
        table.add_column(t("info.role_name"), style="cyan")
        table.add_column(t("dash.model_col"), style="white", overflow="fold")
        table.add_column(t("dash.requests"), justify="right")
        table.add_column(t("dash.tokens"), justify="right")
        table.add_column(t("dash.spend"), justify="right", style="yellow")
        if not page_slice:
            table.add_row("—", "—", "—", "—", "—")
        else:
            for row in page_slice:
                table.add_row(
                    str(row["role"]),
                    str(row["model"] or "—"),
                    str(row["requests"]),
                    f"{int(row['tokens']):,}",
                    f"${float(row['cost']):.5f}",
                )
        _dashboard_panel(f"{t('dash.total_label').upper()} — {t('dash.page').format(curr=page + 1, total=total_pages)}", table, border_style="#C8C8FF")
        choice = ask_choice(
            f"{t('dash.choose_total')}",
            ["/back", "/exit", "/next", "/prev", "back", "exit", "n", "p"],
            default="/back",
            context="dashboard_total",
        )
        if choice in (GLOBAL_EXIT, "/exit"):
            raise NavToMain
        if choice in (GLOBAL_BACK, "/back"):
            return
        if choice in ("/next", "n"):
            range_state.batch_page += 1
            continue
        if choice in ("/prev", "p"):
            range_state.batch_page -= 1
            continue


__all__ = ["show_total_browser"]

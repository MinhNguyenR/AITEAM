from __future__ import annotations

from rich.box import ROUNDED
from rich.table import Table

from core.cli.cli_prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice
from core.cli.nav import NavToMain
from core.cli.chrome.ui import clear_screen
from core.dashboard.shell import data as dashboard_data

from ..reporting.state import DashboardRangeState
from ..tui.panels import dashboard_panel as _dashboard_panel
from ..tui.render import header
from ..tui.utils import paginate

TOTAL_PAGE_SIZE = 50


def show_total_browser(range_state: DashboardRangeState) -> None:

    while True:
        clear_screen()
        header("DASHBOARD — TOTAL")
        _dashboard_panel(
            "Total help",
            "total = tổng role/model/token/request/spend\nuse n/p để qua trang\nGlobal: `back` quay lại 1 tầng · `exit` thoát về CLI chính",
            border_style="#6495ED",
        )
        rows = dashboard_data.read_usage_log(last_n=8000)
        page_slice, page, total_pages = paginate(dashboard_data.aggregate_rows_by_role_model(rows), range_state.batch_page, TOTAL_PAGE_SIZE)
        table = Table(box=ROUNDED, show_lines=False)
        table.add_column("Role", style="cyan")
        table.add_column("Model", style="white", overflow="fold")
        table.add_column("Requests", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Spend", justify="right", style="yellow")
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
        _dashboard_panel(f"TOTAL — page {page + 1}/{total_pages}", table, border_style="#C8C8FF")
        choice = ask_choice("Chọn total", ["n", "p"], default=GLOBAL_BACK)
        if choice == GLOBAL_EXIT:
            raise NavToMain
        if choice == GLOBAL_BACK:
            return
        if choice == "n":
            range_state.batch_page += 1
            continue
        if choice == "p":
            range_state.batch_page -= 1
            continue

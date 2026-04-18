from __future__ import annotations

from typing import Optional

from rich.box import ROUNDED
from rich.panel import Panel

from core.cli.cli_prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice
from core.cli.state import save_cli_settings
from core.cli.ui import clear_screen

from .render import ask_budget_value, header


def _dashboard_panel(title: str, body: str, *, border_style: str = "#6495ED") -> None:
    from core.cli.ui import console

    console.print(Panel(body, title=f"[bold]{title}[/bold]", border_style=border_style, box=ROUNDED))


def show_budget_menu(settings: dict[str, Optional[float]]) -> None:
    clear_screen()
    header("BUDGET")
    _dashboard_panel(
        "Budget help",
        "budget commands:\n d = set daily budget\n m = set monthly budget\n y = set yearly budget\n r = reset all budgets to unlimited\n back = quay lại 1 tầng · exit = thoát về CLI chính",
        border_style="#6495ED",
    )
    c = ask_choice("Chọn budget", ["d", "m", "y", "r", "0"], default="d")
    if c == GLOBAL_EXIT:
        return
    if c in (GLOBAL_BACK, "0"):
        return
    if c == "d":
        settings["daily_budget_usd"] = ask_budget_value("Daily budget", settings.get("daily_budget_usd"))
    elif c == "m":
        settings["monthly_budget_usd"] = ask_budget_value("Monthly budget", settings.get("monthly_budget_usd"))
    elif c == "y":
        settings["yearly_budget_usd"] = ask_budget_value("Yearly budget", settings.get("yearly_budget_usd"))
    elif c == "r":
        settings["daily_budget_usd"] = None
        settings["monthly_budget_usd"] = None
        settings["yearly_budget_usd"] = None
    save_cli_settings(settings)

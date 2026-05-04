from __future__ import annotations

from typing import Optional

from rich.box import ROUNDED
from rich.panel import Panel

from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.shell.state import save_cli_settings
from core.cli.python_cli.ui.ui import clear_screen
from core.cli.python_cli.i18n import t

from ..tui.render import ask_budget_value, header


def _dashboard_panel(title: str, body: str, *, border_style: str = "#6495ED") -> None:
    from core.cli.python_cli.ui.ui import console

    console.print(Panel(body, title=f"[bold]{title}[/bold]", border_style=border_style, box=ROUNDED))


def show_budget_menu(settings: dict[str, Optional[float]]) -> None:
    while True:
        clear_screen()
        header(t("dash.budget_title").upper())
        daily = settings.get("daily_budget_usd")
        monthly = settings.get("monthly_budget_usd")
        yearly = settings.get("yearly_budget_usd")
        current = (
            f" d={f'${daily:.2f}' if daily is not None else t('unit.unlimited')}"
            f"  m={f'${monthly:.2f}' if monthly is not None else t('unit.unlimited')}"
            f"  y={f'${yearly:.2f}' if yearly is not None else t('unit.unlimited')}"
        )
        _dashboard_panel(
            t("dash.budget_help"),
            t("dash.budget_desc").format(curr=current),
            border_style="#6495ED",
        )
        c = ask_choice(f"{t('nav.choose')} {t('dash.budget_label').lower()}", ["/back", "/exit", "/daily", "/monthly", "/yearly", "/reset"], default="/daily", context="dashboard_budget")
        if c in (GLOBAL_EXIT, "/exit"):
            raise NavToMain
        if c in (GLOBAL_BACK, "/back"):
            return
        if c == "/daily":
            settings["daily_budget_usd"] = ask_budget_value(t("dash.budget_daily"), settings.get("daily_budget_usd"))
        elif c == "/monthly":
            settings["monthly_budget_usd"] = ask_budget_value(t("dash.budget_monthly"), settings.get("monthly_budget_usd"))
        elif c == "/yearly":
            settings["yearly_budget_usd"] = ask_budget_value(t("dash.budget_yearly"), settings.get("yearly_budget_usd"))
        elif c == "/reset":
            settings["daily_budget_usd"] = None
            settings["monthly_budget_usd"] = None
            settings["yearly_budget_usd"] = None
        save_cli_settings(settings)

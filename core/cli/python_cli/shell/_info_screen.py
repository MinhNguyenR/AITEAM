"""Info screen: agent model list and help screen."""
from __future__ import annotations

import shutil
from io import StringIO
from typing import Optional

from rich.box import ROUNDED, SIMPLE
from rich.console import Console as RichConsole
from rich.markdown import Markdown
from rich.panel import Panel
from rich.style import Style
from rich.table import Table

from core.cli.python_cli.features.change.flow import pick_role_key_from_indexed_workers, show_role_detail
from core.cli.python_cli.shell.command_registry import help_screen_markdown
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, SOFT_WHITE, clear_screen, console, print_header
from core.cli.python_cli.ui.help_terminal import spawn_help_in_new_terminal
from core.cli.python_cli.i18n import t
from core.config import config
from core.app_state import get_cli_settings, log_system_action
from core.cli.python_cli.shell.screens.change import show_change_report


def show_info() -> None:
    def _capture_info_ansi() -> tuple[str, list[dict]]:
        width = shutil.get_terminal_size((120, 30)).columns
        sio = StringIO()
        cap = RichConsole(file=sio, force_terminal=True, width=width, no_color=False, highlight=False, markup=True)
        print_header(t("info.header"), out=cap)
        workers = config.list_workers()
        table = Table(
            box=SIMPLE, show_header=True,
            header_style=Style(color=PASTEL_CYAN, bold=True),
            border_style=PASTEL_BLUE, padding=(0, 1), expand=True,
        )
        table.add_column("#", style="dim", width=4, no_wrap=True)
        table.add_column(t("info.role_key"), style=Style(color=PASTEL_CYAN), ratio=2, overflow="fold")
        table.add_column(t("info.role_name"), style=Style(color=SOFT_WHITE), ratio=2, overflow="fold")
        table.add_column(t("info.model_col"), ratio=3, overflow="fold")
        table.add_column(t("info.active"), justify="center", width=8)
        table.add_column(t("info.price_col"), width=16, overflow="fold")
        table.add_column(t("info.ovr"), justify="center", width=8)
        for index, worker in enumerate(workers, 1):
            pricing = worker.get("pricing", {})
            inp, out = pricing.get("input", 0.0), pricing.get("output", 0.0)
            price_s = f"${inp:.2f}/${out:.2f}" if (inp or out) else "-"
            on_icon = f"[green]{t('info.on')}[/green]" if worker.get("active", True) else f"[red]{t('info.off')}[/red]"
            ovr_icon = "[yellow]M[/yellow]" if worker.get("is_overridden") else "[dim]-[/dim]"
            if worker.get("prompt_status") == "overridden":
                ovr_icon += "[cyan]P[/cyan]"
            table.add_row(str(index), worker["id"], worker["role"], worker["model"], on_icon, price_s, ovr_icon)
        cap.print(Panel(table, title=f"[bold]{t('info.models_panel')}[/bold]", border_style=PASTEL_BLUE, box=ROUNDED))
        return sio.getvalue(), workers

    def _resolve_info_choice(raw: str, workers: list[dict]) -> Optional[str]:
        raw = (raw or "").strip().lower()
        if raw == "/check change":
            return "__CHECK_CHANGE__"
        if raw in ("/back", ""):
            return "__BACK__"
        if raw == "/exit":
            raise NavToMain

        if raw.startswith("/enter "):
            raw = raw[len("/enter "):].strip()
        elif raw.startswith("/open "):
            raw = raw[len("/open "):].strip()

        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(workers):
                return workers[idx]["id"]
        else:
            for w in workers:
                if w["id"].lower() == raw or w["role"].lower() == raw:
                    return w["id"]
        return None

    while True:
        ansi, workers = _capture_info_ansi()
        try:
            from core.cli.python_cli.ui.palette_app import ask_with_palette
            raw = ask_with_palette(">", context="agent_list", default="/back", header_ansi=ansi, force_down=True)
        except (KeyboardInterrupt, EOFError):
            return
        role_key = _resolve_info_choice(raw, workers)
        if role_key == "__CHECK_CHANGE__":
            show_change_report()
            continue
        if role_key == "__BACK__":
            return
        if role_key is None:
            continue
        log_system_action("menu.info.role_detail", role_key)
        show_role_detail(role_key)


def show_help() -> None:
    settings = get_cli_settings()
    if bool(settings.get("help_external_terminal")):
        if spawn_help_in_new_terminal():
            console.print(f"[green]{t('settings.help_opened')}[/green]")
            return
        console.print(f"[yellow]{t('settings.help_failed')}[/yellow]")
    clear_screen()
    print_header(t("menu.help.desc"))
    console.print(
        Panel(
            Markdown(help_screen_markdown()),
            border_style=PASTEL_BLUE,
            padding=(1, 2),
            box=ROUNDED,
        )
    )
    console.print()
    from core.cli.python_cli.shell.prompt import ask_choice
    c = ask_choice(f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]", ["/back", "/exit"], default="/back", context="help")
    if c == "/exit":
        raise NavToMain
    clear_screen()


__all__ = ["show_info", "show_help"]

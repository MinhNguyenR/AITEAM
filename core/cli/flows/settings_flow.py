from __future__ import annotations

import time

from rich.box import ROUNDED, SIMPLE
from rich.panel import Panel
from rich.style import Style
from rich.table import Table

from core.cli.cli_prompt import ask_choice
from core.cli.nav import NavToMain
from core.cli.state import get_cli_settings, save_cli_settings
from core.cli.chrome.ui import (
    PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, SOFT_WHITE,
    clear_screen, console, print_divider,
)

_SETTING_W = 32
_VALUE_W = 28


def _settings_table(settings: dict) -> Table:
    auto_ac = settings["auto_accept_context"]
    view_mode = settings.get("workflow_view_mode", "chain")
    help_ext = bool(settings.get("help_external_terminal", False))
    aca = str(settings.get("auto_context_action", "ask"))

    tbl = Table(
        box=SIMPLE, show_header=True,
        header_style=Style(color=PASTEL_CYAN, bold=True),
        border_style=PASTEL_BLUE, padding=(0, 2),
        show_edge=True,
    )
    tbl.add_column("#", style=Style(color=PASTEL_LAVENDER, bold=True), width=4)
    tbl.add_column("Setting", style=Style(color=SOFT_WHITE), width=_SETTING_W)
    tbl.add_column("Value", width=_VALUE_W)

    tbl.add_row(
        "1",
        "Auto-accept context.md",
        f"[bold green]on[/bold green]" if auto_ac else "[dim]off[/dim]",
    )
    tbl.add_row(
        "2",
        "Workflow view",
        f"[cyan]{view_mode}[/cyan]",
    )
    tbl.add_row(
        "3",
        "Context action (post-delete)",
        _aca_display(aca),
    )
    tbl.add_row(
        "4",
        "Help: external terminal",
        "[bold green]on[/bold green]" if help_ext else "[dim]off[/dim]",
    )
    return tbl


def _aca_display(aca: str) -> str:
    return {
        "ask":     "[yellow]ask[/yellow]  (prompt after delete)",
        "accept":  "[green]accept[/green]  (auto-regenerate)",
        "decline": "[red]decline[/red]  (skip regenerate)",
    }.get(aca, f"[dim]{aca}[/dim]")


def show_settings():
    settings = get_cli_settings()
    clear_screen()
    console.print(
        Panel(
            "[bold #6495ED]SETTINGS[/bold #6495ED]",
            border_style="#6495ED", box=ROUNDED, padding=(0, 4),
        )
    )
    console.print()

    while True:
        console.print(_settings_table(settings))
        console.print()
        console.print(f"  [dim]0[/dim]  back to main menu")
        console.print()

        choice = ask_choice(
            f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]",
            ["0", "1", "2", "3", "4", "back", "exit"],
            default="0",
        )
        if choice == "exit":
            raise NavToMain
        if choice in ("0", "back"):
            return

        if choice == "1":
            settings["auto_accept_context"] = not settings["auto_accept_context"]
            save_cli_settings(settings)
            label = "on" if settings["auto_accept_context"] else "off"
            console.print(f"[green]  auto-accept context → {label}[/green]")

        elif choice == "2":
            cur = settings.get("workflow_view_mode", "chain")
            settings["workflow_view_mode"] = "list" if cur == "chain" else "chain"
            save_cli_settings(settings)
            console.print(f"[green]  workflow view → {settings['workflow_view_mode']}[/green]")

        elif choice == "3":
            cur = str(settings.get("auto_context_action", "ask"))
            opts = ["ask", "accept", "decline"]
            nxt = opts[(opts.index(cur) + 1) % len(opts)] if cur in opts else "ask"
            settings["auto_context_action"] = nxt
            save_cli_settings(settings)
            console.print(f"[green]  context action → {nxt}[/green]")

        elif choice == "4":
            settings["help_external_terminal"] = not bool(settings.get("help_external_terminal", False))
            save_cli_settings(settings)
            label = "on" if settings["help_external_terminal"] else "off"
            console.print(f"[green]  help external terminal → {label}[/green]")

        time.sleep(0.4)
        clear_screen()
        console.print(
            Panel(
                "[bold #6495ED]SETTINGS[/bold #6495ED]",
                border_style="#6495ED", box=ROUNDED, padding=(0, 4),
            )
        )
        console.print()


__all__ = ["show_settings"]

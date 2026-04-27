from __future__ import annotations

from rich.box import ROUNDED
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from core.cli.python_cli.chrome.ui import (
    BRIGHT_BLUE, PASTEL_BLUE, PASTEL_CYAN, SOFT_WHITE,
    clear_screen, console, print_logo,
)
from core.cli.python_cli.state import get_cli_settings, is_context_active
from core.cli.python_cli.choice_lists import menu_commands


def render_command_palette(context_ready: bool):
    clear_screen()
    print_logo(compact=False)

    settings = get_cli_settings()
    vm = settings.get("workflow_view_mode", "chain")
    aca = str(settings.get("auto_context_action", "ask"))
    aa_label = "auto-accept" if settings.get("auto_accept_context") else "manual"

    # Context banner
    if is_context_active() and context_ready:
        console.print(
            Panel(
                Text.assemble(
                    ("context.md ready  ", Style(color="green", bold=True)),
                    ("  type ", Style(color=PASTEL_BLUE, dim=True)),
                    ("check", Style(color=PASTEL_CYAN, bold=True)),
                    (" or ", Style(color=PASTEL_BLUE, dim=True)),
                    ("2", Style(color=PASTEL_CYAN, bold=True)),
                    (" to review", Style(color=PASTEL_BLUE, dim=True)),
                ),
                border_style="green", box=ROUNDED, padding=(0, 2),
            )
        )
        console.print()

    # Status line
    status_parts = [
        ("view:", Style(color=PASTEL_BLUE, dim=True)),
        (f" {vm}  ", Style(color=PASTEL_CYAN)),
        ("·  context:", Style(color=PASTEL_BLUE, dim=True)),
        (f" {aa_label}  ", Style(color=PASTEL_CYAN)),
        ("·  on-delete:", Style(color=PASTEL_BLUE, dim=True)),
        (f" {aca}", Style(color=PASTEL_CYAN)),
    ]
    console.print(Text.assemble(*status_parts))
    console.print()

    # Command table
    table = Table(box=None, show_header=False, show_lines=False, padding=(0, 1))
    table.add_column("Key",  style=Style(color=BRIGHT_BLUE, bold=True), width=4)
    table.add_column("Cmd",  style=Style(color=PASTEL_CYAN, bold=True), width=12)
    table.add_column("Desc", style=Style(color=SOFT_WHITE),             width=52)
    for key, cmd, desc in menu_commands():
        table.add_row(key, cmd, desc)
    console.print(table)
    console.print()


__all__ = ["render_command_palette"]

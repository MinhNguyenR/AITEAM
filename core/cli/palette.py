from __future__ import annotations

from rich.panel import Panel
from rich.style import Style
from rich.table import Table

from core.cli.ui import BRIGHT_BLUE, PASTEL_CYAN, SOFT_WHITE, clear_screen, print_header, console
from core.cli.state import get_cli_settings, is_context_active
from core.cli.choice_lists import menu_commands


def render_command_palette(context_ready: bool):
    clear_screen()
    print_header("🤖 AI TEAM BLUEPRINT", "v6.2 — Pastel Blue Edition")
    if is_context_active() and context_ready:
        console.print(
            Panel(
                f"[bold green]📄 context.md sẵn sàng![/bold green]  [{PASTEL_CYAN}]Gõ [bold]check[/bold] hoặc [bold]2[/bold] để xem.[/{PASTEL_CYAN}]",
                border_style="green",
                padding=(0, 2),
            )
        )
        console.print()
    settings = get_cli_settings()
    vm = settings.get("workflow_view_mode", "chain")
    aa_label = "✅ Auto" if settings["auto_accept_context"] else "🔍 Manual"
    console.print(f"[dim]Workflow view: {vm}  |  Context: {aa_label}[/dim]")
    console.print()

    table = Table(box=None, show_header=False, show_lines=False, padding=(0, 2))
    table.add_column("Key", style=Style(color=BRIGHT_BLUE, bold=True), width=5)
    table.add_column("Cmd", style=Style(color=PASTEL_CYAN, bold=True), width=14)
    table.add_column("Desc", style=Style(color=SOFT_WHITE), width=48)
    for key, cmd, desc in menu_commands():
        table.add_row(key, cmd, desc)
    console.print(table)
    console.print()


__all__ = ["render_command_palette"]

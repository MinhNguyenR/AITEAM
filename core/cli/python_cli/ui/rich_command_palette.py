from __future__ import annotations

import shutil
from io import StringIO

from rich.box import DOUBLE, ROUNDED
from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from core.cli.python_cli.i18n import t
from core.cli.python_cli.shell.choice_lists import menu_commands
from core.cli.python_cli.shell.state import get_cli_settings, is_context_active
from core.cli.python_cli.ui.ui import (
    BRIGHT_BLUE,
    PASTEL_BLUE,
    PASTEL_CYAN,
    SOFT_WHITE,
    _LOGO_LINES,
    clear_screen,
    console,
    print_logo,
)


_PTK_BLUE   = "bright_blue"   # vivid blue  — maps cleanly in true-color
_PTK_CYAN   = "bright_cyan"   # vivid cyan
_PTK_WHITE  = "white"         # pure white  — no blue/purple tint
_PTK_DIM    = "bright_black"  # dim/grey


def _build_menu_on(cap: RichConsole, context_ready: bool) -> None:
    """Render logo + status + command table onto *cap* (no clear_screen side-effect)."""
    logo_text = Text(justify="center")
    for line in _LOGO_LINES:
        logo_text.append(line + "\n", style=Style(color=_PTK_BLUE, bold=True))
    cap.print(Panel(logo_text, border_style=_PTK_BLUE, box=DOUBLE, padding=(1, 4)))
    cap.print()

    if is_context_active() and context_ready:
        cap.print(
            Panel(
                Text.assemble(
                    (f"{t('gate.waiting')}  ", Style(color="bright_green", bold=True)),
                    (f"  {t('nav.choose')} ", Style(color=_PTK_DIM)),
                    ("/check", Style(color=_PTK_CYAN, bold=True)),
                    (f" {t('context.subheader').lower()}", Style(color=_PTK_DIM)),
                ),
                border_style="bright_green", box=ROUNDED, padding=(0, 2),
            )
        )
        cap.print()

    settings = get_cli_settings()
    aca = str(settings.get("auto_context_action", "ask"))
    aa_label = t("settings.auto_accept") if settings.get("auto_accept_context") else t("ui.manual")
    status_parts = [
        (f"{t('status.paths').split(' ')[0].lower()}:", Style(color=_PTK_DIM)),
        (f" {aa_label}  ", Style(color=_PTK_CYAN)),
        (f"·  {t('settings.context_act')}:", Style(color=_PTK_DIM)),
        (f" {t(f'ui.{aca}')}", Style(color=_PTK_CYAN)),
    ]
    cap.print(Text.assemble(*status_parts))
    cap.print()

    table = Table(box=None, show_header=False, show_lines=False, padding=(0, 1))
    table.add_column("Prefix", style=Style(color=_PTK_DIM), width=2)
    table.add_column("Cmd", style=Style(color=_PTK_CYAN, bold=True), width=16)
    table.add_column("Desc", style=Style(color=_PTK_WHITE), width=60)
    for _, cmd, desc in menu_commands():
        table.add_row(" ", cmd, desc)
    cap.print(table)


def capture_menu_ansi(context_ready: bool = False) -> str:
    """Return the main CLI menu rendered as an ANSI string (no side-effects)."""
    width = shutil.get_terminal_size((120, 30)).columns
    sio = StringIO()
    cap = RichConsole(
        file=sio, force_terminal=True, width=width,
        no_color=False, highlight=False, markup=False,
    )
    _build_menu_on(cap, context_ready)
    return sio.getvalue()


def render_command_palette(context_ready: bool) -> None:
    """Clear screen then render the main CLI menu to the real terminal."""
    clear_screen()
    print_logo(compact=False)

    if is_context_active() and context_ready:
        console.print(
            Panel(
                Text.assemble(
                    (f"{t('gate.waiting')}  ", Style(color="green", bold=True)),
                    (f"  {t('nav.choose')} ", Style(color=PASTEL_BLUE, dim=True)),
                    ("/check", Style(color=PASTEL_CYAN, bold=True)),
                    (f" {t('context.subheader').lower()}", Style(color=PASTEL_BLUE, dim=True)),
                ),
                border_style="green", box=ROUNDED, padding=(0, 2),
            )
        )
        console.print()

    settings = get_cli_settings()
    aca = str(settings.get("auto_context_action", "ask"))
    aa_label = t("settings.auto_accept") if settings.get("auto_accept_context") else t("ui.manual")
    status_parts = [
        (f"{t('status.paths').split(' ')[0].lower()}:", Style(color=PASTEL_BLUE, dim=True)),
        (f" {aa_label}  ", Style(color=PASTEL_CYAN)),
        (f"·  {t('settings.context_act')}:", Style(color=PASTEL_BLUE, dim=True)),
        (f" {t(f'ui.{aca}')}", Style(color=PASTEL_CYAN)),
    ]
    console.print(Text.assemble(*status_parts))
    console.print()

    table = Table(box=None, show_header=False, show_lines=False, padding=(0, 1))
    table.add_column("Prefix", style=Style(color=PASTEL_BLUE, dim=True), width=2)
    table.add_column("Cmd", style=Style(color=PASTEL_CYAN, bold=True), width=16)
    table.add_column("Desc", style=Style(color=SOFT_WHITE), width=60)
    for _, cmd, desc in menu_commands():
        table.add_row(" ", cmd, desc)
    console.print(table)
    console.print()


__all__ = ["capture_menu_ansi", "render_command_palette"]

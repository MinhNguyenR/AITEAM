from __future__ import annotations

import time

from rich.box import ROUNDED, SIMPLE
from rich.panel import Panel
from rich.style import Style
from rich.table import Table

from core.cli.python_cli.shell.prompt import ask_choice
from core.cli.python_cli.shell.nav import NavToMain
from core.app_state import get_cli_settings, save_cli_settings
from core.cli.python_cli.ui.ui import (
    PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, SOFT_WHITE,
    clear_screen, console, print_divider,
)
from core.cli.python_cli.i18n import t

_SETTING_W = 32
_VALUE_W = 28


def _settings_table(settings: dict) -> Table:
    auto_ac  = settings["auto_accept_context"]
    help_ext = bool(settings.get("help_external_terminal", False))
    aca      = str(settings.get("auto_context_action", "ask"))

    tbl = Table(
        box=SIMPLE, show_header=True,
        header_style=Style(color=PASTEL_CYAN, bold=True),
        border_style=PASTEL_BLUE, padding=(0, 2),
        show_edge=True,
    )
    tbl.add_column("Cmd", style=Style(color=PASTEL_LAVENDER, bold=True), width=20)
    tbl.add_column(t('ui.setting'), style=Style(color=SOFT_WHITE), width=_SETTING_W)
    tbl.add_column(t('ui.value'), width=_VALUE_W)

    tbl.add_row(
        "/auto-accept",
        t('settings.auto_accept'),
        f"[bold green]{t('ui.on')}[/bold green]" if auto_ac else f"[dim]{t('ui.off')}[/dim]",
    )
    tbl.add_row(
        "/context-action",
        t('settings.context_act'),
        _aca_display(aca),
    )
    tbl.add_row(
        "/external-terminal",
        t('settings.help_ext'),
        f"[bold green]{t('ui.on')}[/bold green]" if help_ext else f"[dim]{t('ui.off')}[/dim]",
    )
    lang = str(settings.get("display_language", "vi"))
    lang_label = "Tiếng Việt" if lang == "vi" else "English"
    tbl.add_row(
        "/language",
        t('settings.lang'),
        f"[bold cyan]{lang}[/bold cyan]  ({lang_label})",
    )
    return tbl


def _aca_display(aca: str) -> str:
    return {
        "ask":     f"[yellow]{t('ui.ask')}[/yellow]  ({t('context.decision').lower()})",
        "accept":  f"[green]{t('ui.accept')}[/green]  ({t('context.regen_desc').lower()})",
        "decline": f"[red]{t('ui.decline')}[/red]  ({t('context.delete_desc').lower()})",
    }.get(aca, f"[dim]{aca}[/dim]")


def show_settings():
    settings = get_cli_settings()
    clear_screen()
    console.print(
        Panel(
            f"[bold #6495ED]{t('settings.header')}[/bold #6495ED]",
            border_style="#6495ED", box=ROUNDED, padding=(0, 4),
        )
    )
    console.print()

    while True:
        console.print(_settings_table(settings))
        console.print()

        choice = ask_choice(
            f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]",
            ["/back", "/exit", "/auto-accept", "/context-action", "/external-terminal", "/language"],
            default="/back",
            context="settings"
        )
        if choice in ("exit", "/exit"):
            raise NavToMain
        if choice in ("back", "/back"):
            return

        if choice == "/auto-accept":
            settings["auto_accept_context"] = not settings["auto_accept_context"]
            save_cli_settings(settings)
            label = t('ui.on') if settings["auto_accept_context"] else t('ui.off')
            console.print(f"[green]  {t('settings.auto_accept')} → {label}[/green]")

        elif choice == "/context-action":
            cur = str(settings.get("auto_context_action", "ask"))
            opts = ["ask", "accept", "decline"]
            nxt = opts[(opts.index(cur) + 1) % len(opts)] if cur in opts else "ask"
            settings["auto_context_action"] = nxt
            save_cli_settings(settings)
            label = t(f'ui.{nxt}')
            console.print(f"[green]  {t('settings.context_act')} → {label}[/green]")

        elif choice == "/external-terminal":
            settings["help_external_terminal"] = not bool(settings.get("help_external_terminal", False))
            save_cli_settings(settings)
            label = t('ui.on') if settings["help_external_terminal"] else t('ui.off')
            console.print(f"[green]  {t('settings.help_ext')} → {label}[/green]")

        elif choice == "/language":
            cur_lang = str(settings.get("display_language", "vi"))
            nxt_lang = "en" if cur_lang == "vi" else "vi"
            settings["display_language"] = nxt_lang
            save_cli_settings(settings)
            lang_label = "Tiếng Việt" if nxt_lang == "vi" else "English"
            console.print(f"[green]  {t('settings.lang')} → {nxt_lang} ({lang_label})[/green]")

        time.sleep(0.4)
        clear_screen()
        console.print(
            Panel(
                f"[bold #6495ED]{t('settings.header')}[/bold #6495ED]",
                border_style="#6495ED", box=ROUNDED, padding=(0, 4),
            )
        )
        console.print()


__all__ = ["show_settings"]

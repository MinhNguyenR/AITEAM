from __future__ import annotations

import time
from pathlib import Path
from typing import Literal

from rich.box import ROUNDED
from rich.markdown import Markdown
from rich.panel import Panel

from core.cli.python_cli.shell.prompt import ask_choice
from core.cli.python_cli.shell.safe_read import safe_read_text
from core.cli.python_cli.shell.safe_editor import run_editor_on_file
from core.cli.python_cli.features.context.common import full_context_cleanup, graphrag_drop
from core.cli.python_cli.shell.nav import NavToMain
from core.app_state import log_system_action, update_context_state
from core.cli.python_cli.ui.ui import BRIGHT_BLUE, PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, clear_screen, console, print_divider, print_header
from core.cli.python_cli.i18n import t

ContextConfirmResult = Literal["accept", "regenerate", "back", "delete"]


def confirm_context(context_path: Path) -> ContextConfirmResult:
    clear_screen()
    print_header(t("context.header"), t("context.subheader"))
    content = safe_read_text(context_path)
    lines = content.splitlines()
    line_count = len(lines)
    char_count = len(content)
    console.print(f"[{PASTEL_CYAN}]{context_path}[/{PASTEL_CYAN}]  [dim]{line_count} {t('unit.lines')} | {char_count} {t('unit.chars')}[/dim]")
    console.print()
    display_lines = lines[:120]
    display_content = "\n".join(display_lines)
    if line_count > 120:
        display_content += f"\n\n[dim]{t('context.lines_hidden').format(n=line_count - 120)}[/dim]"
    console.print(Panel(Markdown(display_content), title=f"[bold {PASTEL_CYAN}]context.md[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, padding=(1, 2), box=ROUNDED))
    console.print()
    while True:
        choice = ask_choice(
            f"[{PASTEL_CYAN}]{t('ui.choice')}[/{PASTEL_CYAN}]",
            ["/accept", "/edit", "/regenerate", "/back", "/delete", "/exit"],
            default="/accept",
            context="context_confirm",
        ).lower()
        if choice == "/exit":
            raise NavToMain
        if choice == "/accept":
            console.print(f"[bold green]{t('context.accepted')}[/bold green]")
            time.sleep(0.8)
            return "accept"
        if choice == "/edit":
            console.print(f"[dim]{t('context.opening_editor').format(path=context_path)}[/dim]")
            run_editor_on_file(context_path)
            console.print(f"[{PASTEL_CYAN}]{t('context.saved')}[/{PASTEL_CYAN}]")
            time.sleep(0.5)
            return confirm_context(context_path)
        if choice == "/regenerate":
            console.print(f"[{PASTEL_LAVENDER}]{t('context.regen_requested')}[/{PASTEL_LAVENDER}]")
            try:
                graphrag_drop(context_path)
                context_path.unlink(missing_ok=True)
                update_context_state("deleted", context_path, reason="regenerate_requested")
                log_system_action("context.delete", f"{context_path} reason=regenerate_requested")
            except OSError as e:
                console.print(f"[red]{t('context.delete_failed').format(e=e)}[/red]")
            time.sleep(0.5)
            return "regenerate"
        if choice == "/back":
            update_context_state("active", context_path, reason="review_deferred")
            log_system_action("context.review.back", str(context_path))
            console.print(f"[dim]{t('context.back_msg')}[/dim]")
            time.sleep(0.6)
            return "back"
        if choice == "/delete":
            try:
                full_context_cleanup(context_path, reason="deleted")
                console.print(f"[green]{t('context.deleted')}[/green]")
            except (OSError, ValueError, TypeError) as e:
                console.print(f"[red]{t('context.delete_error').format(e=e)}[/red]")
            time.sleep(0.6)
            return "delete"


__all__ = ["ContextConfirmResult", "confirm_context"]

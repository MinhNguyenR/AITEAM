from __future__ import annotations

from rich.box import ROUNDED
from rich.panel import Panel

from core.cli.python_cli.ui.ui import console


def show_help_box(title: str, lines: list[str]) -> None:
    body = "\n".join(lines).strip()
    console.print(Panel(body, title=f"[bold]{title}[/bold]", border_style="#6495ED", box=ROUNDED))


__all__ = ["show_help_box"]

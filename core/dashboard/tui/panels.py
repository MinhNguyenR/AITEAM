from __future__ import annotations

from typing import Any

from rich.box import ROUNDED
from rich.panel import Panel


def dashboard_panel(title: str, body: Any, *, border_style: str = "#6495ED") -> None:
    from core.cli.chrome.ui import console

    console.print(Panel(body, title=f"[bold]{title}[/bold]", border_style=border_style, box=ROUNDED))

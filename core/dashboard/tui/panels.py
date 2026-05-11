from __future__ import annotations

from typing import Any

from rich.box import ROUNDED
from rich.panel import Panel


def dashboard_panel(title: str, body: Any, *, border_style: str = "#6495ED", out=None) -> None:
    if out is None:
        from core.cli.python_cli.ui.ui import console as _c
        out = _c
    out.print(Panel(body, title=f"[bold]{title}[/bold]", border_style=border_style, box=ROUNDED))

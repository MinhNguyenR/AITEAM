"""Clarification state renderer — standalone block, completely outside leader branch."""
from __future__ import annotations

from core.cli.python_cli.i18n import t


def render_pending(sc: str, clarif: dict, elapsed: int = 0, role: str = "Leader") -> str:
    q    = clarif.get("question", t("clarify.default_q"))
    opts = clarif.get("options", [])
    c_idx = clarif.get("current_idx", 1)
    tot   = clarif.get("total", 1)

    meta = f"  [dim]({elapsed}s)[/dim]" if elapsed > 0 else ""
    lines = [
        f"[bold blue]●[/bold blue] [bold]{role}[/bold]  [bold yellow]{t('clarify.needs_info')} ({c_idx}/{tot}){meta}[/bold yellow]",
        f"  [dim]└─[/dim] {q}",
    ]
    for i, opt in enumerate(opts):
        pfx = "[dim]└─[/dim]" if i == len(opts) - 1 else "[dim]├─[/dim]"
        lines.append(f"     {pfx} [bold]{i + 1}[/bold]  {opt}")
    lines.append(
        f"     [dim]└─[/dim] [dim]{t('clarify.btw_hint')}[/dim]"
    )
    return "\n".join(lines)

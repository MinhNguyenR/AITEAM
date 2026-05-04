from __future__ import annotations

from rich.box import ROUNDED
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .. import session as ws


def inline_badge(status: str) -> str:
    st = str(status or "pending").lower()
    return {
        "pending": "[dim]PENDING[/dim]",
        "running": "[yellow]RUNNING[/yellow]",
        "complete": "[green]COMPLETE[/green]",
        "error": "[red]ERROR[/red]",
    }.get(st, "[dim]PENDING[/dim]")


def chain_step_labels() -> dict[str, str]:
    return {
        "ambassador": "Amb",
        "leader_generate": "Leader",
        "human_context_gate": "Review",
        "finalize_phase1": "Done",
        "end_failed": "Fail",
    }


def inline_workflow_renderable(tier: str, status_message: str = "", *, ui_style: str = "list"):
    nodes = ws.get_workflow_list_nodes_state()
    style = "chain" if str(ui_style).lower() == "chain" else "list"
    subtitle = status_message[:120] if status_message else "Dang chay pipeline..."
    if style == "chain":
        labels = chain_step_labels()
        chunks: list[str] = []
        for item in nodes:
            node = str(item.get("node", ""))
            st = str(item.get("status", "pending")).lower()
            short = labels.get(node, node[:8])
            if st == "complete":
                sym = f"[green]{short}[/green]"
            elif st == "running":
                sym = f"[yellow bold]{short}[/yellow bold]"
            elif st == "error":
                sym = f"[red]{short}[/red]"
            else:
                sym = f"[dim]{short}[/dim]"
            chunks.append(sym)
        body = Text.from_markup(" [dim]->[/dim] ".join(chunks) if chunks else "[dim]...[/dim]")
        return Panel(body, title=f"Workflow (chain) | tier={tier}", subtitle=subtitle, border_style="cyan", box=ROUNDED)
    table = Table(box=ROUNDED, border_style="cyan", expand=True)
    table.add_column("#", width=3, style="dim")
    table.add_column("Node", width=24)
    table.add_column("Status", width=12)
    table.add_column("Detail")
    for idx, item in enumerate(nodes, 1):
        node = str(item.get("node", ""))
        detail = str(item.get("detail", "") or "")
        if len(detail) > 80:
            detail = detail[:77] + "..."
        table.add_row(str(idx), node, inline_badge(str(item.get("status", "pending"))), detail)
    return Panel(table, title=f"Workflow (list) | tier={tier}", subtitle=subtitle, border_style="cyan", box=ROUNDED)


__all__ = ["inline_badge", "chain_step_labels", "inline_workflow_renderable"]

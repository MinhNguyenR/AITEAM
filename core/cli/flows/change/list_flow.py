from __future__ import annotations

from typing import Optional

from rich.box import ROUNDED
from rich.prompt import Prompt
from rich.style import Style
from rich.table import Table

from core.cli.flows.change.helpers import indexed_workers, price_str
from core.cli.nav import NavToMain
from core.cli.chrome.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, SOFT_WHITE, clear_screen, console, print_header


def pick_role_key_from_indexed_workers(workers: list[dict]) -> Optional[str]:
    if not workers:
        return None
    console.print()
    console.print(
        f"[{PASTEL_LAVENDER}]Nhập số 1–{len(workers)} để chi tiết / đổi model hoặc prompt | "
        f"back về menu | exit về menu chính[/{PASTEL_LAVENDER}]"
    )
    try:
        raw = Prompt.ask(f"[bold {PASTEL_CYAN}]Chọn[/bold {PASTEL_CYAN}]", default="back").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return None
    if raw in ("back", "b", ""):
        return None
    if raw == "exit":
        raise NavToMain
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(workers):
            return workers[idx]["id"]
    return None


def show_change_list() -> Optional[str]:
    clear_screen()
    print_header("🔧 MODEL REGISTRY — CHANGE")
    workers = indexed_workers()
    table = Table(box=ROUNDED, show_header=True, header_style=Style(color=PASTEL_CYAN, bold=True), border_style=PASTEL_BLUE, padding=(0, 1))
    table.add_column("#", style="dim", width=4)
    table.add_column("Role Key", style=Style(color=PASTEL_CYAN), width=20)
    table.add_column("Role", style=Style(color=SOFT_WHITE), width=26)
    table.add_column("Model", style="white", width=30)
    table.add_column("Active", justify="center", width=8)
    table.add_column("Price in/out /1M", width=20)
    table.add_column("Override", justify="center", width=10)
    for i, w in enumerate(workers, 1):
        active_icon = "[green]✅[/green]" if w.get("active", True) else "[red]❌[/red]"
        override_icon = "[yellow]✏[/yellow]" if w.get("is_overridden") else "[dim]—[/dim]"
        prompt_icon = " [cyan]P[/cyan]" if w.get("prompt_status") == "overridden" else ""
        table.add_row(
            str(i),
            w["id"],
            w["role"],
            w["model"],
            active_icon,
            price_str(w.get("pricing", {})),
            override_icon + prompt_icon,
        )
    console.print(table)
    console.print()
    console.print("[dim]Override[/dim]: ✏ model overridden  [cyan]P[/cyan] prompt overridden")
    console.print()
    console.print(f"[{PASTEL_LAVENDER}]Commands:[/{PASTEL_LAVENDER}] <số thứ tự> | back")
    try:
        raw = Prompt.ask(f"[bold {PASTEL_CYAN}]Chọn role[/bold {PASTEL_CYAN}]", default="back").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return None
    if raw in ("back", "b", ""):
        return None
    if raw == "exit":
        raise NavToMain
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(workers):
            return workers[idx]["id"]
    return None


__all__ = ["pick_role_key_from_indexed_workers", "show_change_list"]

from __future__ import annotations

from typing import Optional

from rich.box import ROUNDED
from rich.prompt import Prompt
from rich.style import Style
from rich.table import Table

from core.cli.python_cli.features.change.helpers import indexed_workers, price_str
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, SOFT_WHITE, clear_screen, console, print_header
from core.cli.python_cli.i18n import t


def pick_role_key_from_indexed_workers(workers: list[dict]) -> Optional[str]:
    if not workers:
        return None
    console.print()
    console.print(
        f"[{PASTEL_LAVENDER}]{t('nav.range_hint').format(max=len(workers))} | "
        f"{t('nav.back')} | {t('nav.exit')}[/{PASTEL_LAVENDER}]"
    )
    try:
        from core.cli.python_cli.ui.palette_app import ask_with_palette
        raw = ask_with_palette(f"{t('nav.choose')} ", context="agent_detail", default="back").strip().lower()
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
    print_header(t("info.header"))
    workers = indexed_workers()
    table = Table(box=ROUNDED, show_header=True, header_style=Style(color=PASTEL_CYAN, bold=True), border_style=PASTEL_BLUE, padding=(0, 1))
    table.add_column("#", style="dim", width=4)
    table.add_column(t("info.role_key"), style=Style(color=PASTEL_CYAN), width=20)
    table.add_column(t("info.role_name"), style=Style(color=SOFT_WHITE), width=26)
    table.add_column(t("info.model_col"), style="white", width=30)
    table.add_column(t("info.active"), justify="center", width=8)
    table.add_column(t("info.price_in") + "/" + t("info.price_out"), width=20)
    table.add_column(t("info.ovr"), justify="center", width=10)
    for i, w in enumerate(workers, 1):
        active_label = "[green]ON[/green]" if w.get("active", True) else "[red]OFF[/red]"
        override_label = "[yellow]OVR[/yellow]" if w.get("is_overridden") else "[dim]—[/dim]"
        prompt_tag = " [cyan]P[/cyan]" if w.get("prompt_status") == "overridden" else ""
        table.add_row(
            str(i),
            w["id"],
            w["role"],
            w["model"],
            active_label,
            price_str(w.get("pricing", {})),
            override_label + prompt_tag,
        )
    console.print(table)
    console.print()
    console.print(f"[dim]{t('info.ovr')}[/dim]: OVR {t('info.model_override').lower()}  [cyan]P[/cyan] {t('info.prompt_title').lower()} overridden")
    console.print()
    console.print(
        f"[{PASTEL_LAVENDER}]{t('info.cmd_label')}[/{PASTEL_LAVENDER}] "
        f"{t('nav.range_hint').format(max=len(workers))} | {t('nav.back')}"
    )
    try:
        from core.cli.python_cli.ui.palette_app import ask_with_palette
        raw = ask_with_palette(f"{t('nav.choose_role')} ", context="agent_detail", default="back").strip().lower()
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

"""Explain feature -- /explain @codebase | /explain @file path [path...]"""
from __future__ import annotations

import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.box import ROUNDED

from core.cli.python_cli.i18n import t
from core.app_state import get_cli_settings
from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, console


def run_explain(payload: str, project_root: str = "") -> None:
    """Entry point: parse payload, dispatch to @codebase or @file handler."""
    root = Path(project_root or os.getcwd())
    parts = payload.strip().split()

    if not parts or parts[0] == "@codebase":
        _explain_codebase(root)
    elif parts[0] == "@file":
        file_args = parts[1:]
        if not file_args:
            console.print(f"[dim]Usage: /explain @file path/to/file.py [more.py ...][/dim]")
            return
        _explain_files(file_args, root)
    else:
        # Treat bare paths as @file
        _explain_files(parts, root)


def _explain_codebase(root: Path) -> None:
    console.print(f"[{PASTEL_CYAN}]Explainer scanning {root.name}...[/{PASTEL_CYAN}]")
    try:
        from agents.explainer import Explainer
        exp = Explainer()
        out_path = exp.explain_codebase(root)
        console.print(Panel(
            f"[bold green]✓[/bold green] codebase.md written → [cyan]{out_path}[/cyan]",
            box=ROUNDED, border_style=PASTEL_BLUE,
        ))
    except Exception as e:
        console.print(f"[bold red]Explainer error:[/bold red] {e}")


def _explain_files(file_args: list[str], root: Path) -> None:
    console.print(f"[{PASTEL_CYAN}]Explainer reading {len(file_args)} file(s)...[/{PASTEL_CYAN}]")
    try:
        from agents.explainer import Explainer
        exp = Explainer()
        result = exp.explain_files(file_args, root)
        console.print(Panel(result, box=ROUNDED, border_style=PASTEL_BLUE, title="Explanation"))
    except Exception as e:
        console.print(f"[bold red]Explainer error:[/bold red] {e}")


def run_explainer(payload: str, project_root: str = "") -> None:
    """Annotate files in place with Explainer."""
    root = Path(project_root or os.getcwd())
    parts = [p for p in payload.strip().split() if p]
    if not parts:
        console.print("[yellow]Chưa có file chỉ định. Dùng /explainer @file path/to/file.py[/yellow]")
        return
    try:
        from agents.explainer import Explainer

        exp = Explainer()
        lang = str(get_cli_settings().get("display_language") or "vi")
        if parts[0] == "@codebase":
            selected = exp.select_codebase_files(root, limit=12)
            console.print(f"[{PASTEL_CYAN}]Explainer chọn tối đa 12 file; đã chọn {len(selected)} file.[/{PASTEL_CYAN}]")
            if not selected:
                console.print("[yellow]Không tìm thấy file phù hợp để giải thích.[/yellow]")
                return
            result = exp.annotate_files(selected, root, task_uuid="explainer", display_language=lang)
        else:
            file_args = parts[1:] if parts[0] == "@file" else [p.lstrip("@") for p in parts]
            if not file_args:
                console.print("[yellow]Chưa có file chỉ định. Dùng /explainer @file path/to/file.py[/yellow]")
                return
            result = exp.annotate_files(file_args, root, task_uuid="explainer", display_language=lang)
        changed = len(result.get("files_written", []))
        errors = result.get("errors", [])
        msg = f"[bold green]✓[/bold green] Explainer updated {changed} file(s)."
        if errors:
            msg += f"\n[yellow]{len(errors)} issue(s): {errors[:3]}[/yellow]"
        console.print(Panel(msg, box=ROUNDED, border_style=PASTEL_BLUE))
    except Exception as e:
        console.print(f"[bold red]Explainer error:[/bold red] {e}")

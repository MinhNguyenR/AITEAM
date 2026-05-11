"""Change report screen: role model/prompt/sampling override summary."""
from __future__ import annotations

import shutil
from io import StringIO

from rich.box import ROUNDED
from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.style import Style
from rich.table import Table

from core.cli.python_cli.shell.prompt import GLOBAL_EXIT, ask_choice
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, SOFT_WHITE, clear_screen, print_header
from core.cli.python_cli.i18n import t
from core.config import config
from core.app_state import get_model_overrides, get_prompt_overrides, get_sampling_overrides


def _capture_change_report_ansi() -> str:
    width = shutil.get_terminal_size((120, 30)).columns
    sio = StringIO()
    cap = RichConsole(file=sio, force_terminal=True, width=width, no_color=False, highlight=False, markup=True)
    print_header("ROLE CHANGES", out=cap)

    model_overrides = get_model_overrides()
    prompt_overrides = get_prompt_overrides()
    sampling_overrides = get_sampling_overrides()
    changed_roles = sorted(set(model_overrides) | set(prompt_overrides) | set(sampling_overrides))

    summary = Table.grid(expand=True)
    summary.add_column(ratio=1)
    summary.add_column(ratio=1)
    summary.add_row(
        Panel(f"[bold]{len(changed_roles)}[/bold]\n[dim]roles changed[/dim]", title="[bold]Total[/bold]", border_style=PASTEL_BLUE, box=ROUNDED),
        Panel(
            f"Model: [bold]{len(model_overrides)}[/bold]\nPrompt: [bold]{len(prompt_overrides)}[/bold]\nSampling: [bold]{len(sampling_overrides)}[/bold]",
            title="[bold]Types[/bold]",
            border_style=PASTEL_CYAN,
            box=ROUNDED,
        ),
    )
    cap.print(summary)

    table = Table(
        box=ROUNDED, show_header=True,
        header_style=Style(color=PASTEL_CYAN, bold=True),
        border_style=PASTEL_BLUE, padding=(0, 1), expand=True,
    )
    table.add_column("Role", style=Style(color=PASTEL_CYAN, bold=True), width=18, no_wrap=True)
    table.add_column("Role name", style=Style(color=SOFT_WHITE), ratio=1, overflow="fold")
    table.add_column("Changes", style=Style(color=SOFT_WHITE), ratio=3, overflow="fold")

    if not changed_roles:
        table.add_row("-", "-", "[dim]No role changes found.[/dim]")
    else:
        workers = {str(w["id"]).upper(): w for w in config.list_workers()}
        registry = {str(k).upper(): v for k, v in config.MODEL_REGISTRY.items()}
        for role in changed_roles:
            worker = workers.get(role, {})
            default = registry.get(role, {})
            lines: list[str] = []
            if role in model_overrides:
                lines.append(f"[bold]model[/bold]: {default.get('model', '-')} -> [yellow]{model_overrides[role]}[/yellow]")
            if role in sampling_overrides:
                samp = sampling_overrides.get(role) or {}
                default_reasoning = default.get("reasoning", {}) if isinstance(default.get("reasoning"), dict) else {}
                defaults = {
                    "temperature": default.get("temperature", "-"),
                    "top_p": default.get("top_p", "-"),
                    "max_tokens": default.get("max_tokens", "-"),
                    "reasoning_effort": default_reasoning.get("effort", "-"),
                }
                for key, value in samp.items():
                    lines.append(f"[bold]{key}[/bold]: {defaults.get(key, '-')} -> [yellow]{value}[/yellow]")
            if role in prompt_overrides:
                info = prompt_overrides.get(role) or {}
                prompt = str(info.get("prompt") or "").strip().replace("\n", " ")
                preview = prompt[:140] + ("..." if len(prompt) > 140 else "")
                updated = str(info.get("updated_at") or "-")
                lines.append(f"[bold]prompt[/bold]: custom prompt set ({updated})")
                if preview:
                    lines.append(f"[dim]{preview}[/dim]")
            table.add_row(role, str(worker.get("role") or default.get("role") or "-"), "\n".join(lines) if lines else "-")

    cap.print(Panel(table, title="[bold]Changed roles[/bold]", border_style=PASTEL_BLUE, box=ROUNDED, padding=(0, 1)))
    return sio.getvalue()


def show_change_report() -> None:
    while True:
        clear_screen()
        choice = ask_choice(
            ">",
            ["/back", "/exit"],
            default="/back",
            context="status",
            header_ansi=_capture_change_report_ansi(),
        )
        if choice in (GLOBAL_EXIT, "/exit"):
            raise NavToMain
        return


__all__ = ["show_change_report", "_capture_change_report_ansi"]

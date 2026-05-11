"""Status screen: machine/runtime info panel and workspace folder picker."""
from __future__ import annotations

import os
import platform
import shutil
import time
from io import StringIO
from pathlib import Path

from rich.box import ROUNDED
from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.style import Style
from rich.table import Table

from core.cli.python_cli.shell.prompt import ask_choice
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.ui.ui import (
    PASTEL_BLUE, PASTEL_CYAN, SOFT_WHITE,
    clear_screen, console, get_framework_config, print_header,
)
from core.cli.python_cli.i18n import t
from core.config import config


def _workspace_root() -> str:
    return str(Path.cwd().resolve())


def _build_status_table_on(cap: RichConsole) -> None:
    """Machine/runtime status page. API and role overrides live in Info."""
    from core.runtime import session as _ws
    from core.app_state import get_model_overrides, get_prompt_overrides

    fw = get_framework_config()
    snap = _ws.get_pipeline_snapshot()
    active = snap.get("active_step", "idle")
    tid = _ws.get_thread_id() or "-"

    def _cpu_name() -> str:
        if os.name == "nt":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                winreg.CloseKey(key)
                if name:
                    return name.replace("(TM)", "").replace("(R)", "").strip()
            except Exception:
                pass
            try:
                import subprocess
                res = subprocess.run(["wmic", "cpu", "get", "name"], capture_output=True, text=True, timeout=2)
                lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
                if len(lines) >= 2:
                    return lines[1].replace("(TM)", "").replace("(R)", "").strip()
            except Exception:
                pass
        return platform.processor() or platform.machine() or "-"

    def _os_name() -> str:
        sys_name = platform.system()
        if sys_name == "Windows":
            try:
                v = platform.version().split('.')
                if len(v) >= 3 and int(v[2]) >= 22000:
                    return "Windows 11"
            except Exception:
                pass
            return f"Windows {platform.release()}"
        return f"{sys_name} {platform.release()}"

    try:
        import psutil
        cpu_name = _cpu_name()
        cpu_cores = f"{psutil.cpu_count(logical=False) or '-'} physical / {psutil.cpu_count(logical=True) or '-'} logical"
        ram = psutil.virtual_memory()
        ram_avail = f"{ram.available / (1024 ** 3):.1f} GB"
        ram_total = f"{ram.total / (1024 ** 3):.1f} GB"
    except Exception:
        cpu_name = _cpu_name()
        cpu_cores = "-"
        ram_avail = "-"
        ram_total = f"{config.total_ram_gb:.1f} GB total"

    def _card(title: str, rows: list[tuple[str, str]], *, border: str = PASTEL_BLUE) -> Panel:
        body = Table.grid(expand=True)
        body.add_column(style=Style(color=PASTEL_CYAN, bold=True), width=18, no_wrap=True)
        body.add_column(style=Style(color=SOFT_WHITE), ratio=1, overflow="ellipsis", no_wrap=True)
        display_rows = rows[:5]
        while len(display_rows) < 5:
            display_rows.append(("", ""))
        for key, value in display_rows:
            body.add_row(key, value)
        return Panel(body, title=f"[bold {PASTEL_CYAN}]{title}[/bold {PASTEL_CYAN}]", border_style=border, box=ROUNDED, padding=(0, 1))

    machine = _card(t("status.block_machine"), [
        (t("status.os"), _os_name()),
        (t("status.cpu"), cpu_name),
        (t("status.cores"), cpu_cores),
        ("RAM Total", ram_total),
        ("RAM Avail", ram_avail),
    ])
    gpu = _card(t("status.block_gpu"), [
        (t("status.card"), f"[bold]{config.gpu_name}[/bold]"),
        (t("status.device"), f"[{'green' if config.device == 'cuda' else 'yellow'}]{config.device.upper()}[/]"),
        (t("status.vram_total"), f"{config.total_vram_gb:.1f} GB"),
        (t("status.vram_used"), f"[bold yellow]{config.available_vram_gb:.1f} GB[/bold yellow]"),
        ("", ""),
    ])
    runtime = _card(t("status.block_runtime"), [
        (t("status.fw"), f"{fw.get('name', 'aiteam')} v{fw.get('version', 'unknown')}"),
        (t("status.py"), f"Python {fw.get('python', 'unknown')}"),
        (t("status.pipeline"), f"[bold]{active}[/bold]"),
        (t("status.thread"), f"[dim]{tid}[/dim]"),
        ("", ""),
    ])
    workspace = _card(t("status.block_workspace"), [
        (t("status.workdir"), str(Path.cwd().resolve())),
    ])

    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_row(machine, gpu)
    grid.add_row(runtime, workspace)

    cap.print(Panel(grid, title=f"[bold {PASTEL_BLUE}]{t('status.header')}[/bold {PASTEL_BLUE}]", border_style=PASTEL_BLUE, box=ROUNDED, padding=(0, 1), expand=True))


def _capture_status_ansi() -> str:
    width = shutil.get_terminal_size((120, 30)).columns - 3
    sio = StringIO()
    cap = RichConsole(file=sio, force_terminal=True, width=width, no_color=False, highlight=False, markup=True)
    _build_status_table_on(cap)
    return sio.getvalue()


def _browse_folder(current: str) -> str | None:
    """Folder picker with Tab completion via prompt_toolkit PathCompleter."""
    cur = Path(current).resolve()
    try:
        from prompt_toolkit import prompt as pt_prompt
        from prompt_toolkit.completion import PathCompleter
        from prompt_toolkit.shortcuts import CompleteStyle
        from prompt_toolkit.styles import Style as PtStyle

        console.print(f"\n[bold #6495ED]Folder Picker[/bold #6495ED]  [dim](Tab = complete . Enter = confirm . Ctrl+C = cancel)[/dim]")
        console.print(f"[dim]Current:[/dim] [cyan]{cur}[/cyan]")
        try:
            subdirs = sorted(d.name for d in cur.iterdir() if d.is_dir() and not d.name.startswith("."))[:10]
            if subdirs:
                console.print(f"[dim]  " + "  ".join(f"[cyan]{n}[/cyan]" for n in subdirs[:5]) + ("[dim] ...[/dim]" if len(subdirs) > 5 else "") + "[/dim]")
        except OSError:
            pass
        console.print()

        result = pt_prompt(
            "  > ",
            completer=PathCompleter(only_directories=True, expanduser=True),
            default=str(cur) + os.sep,
            complete_style=CompleteStyle.MULTI_COLUMN,
            style=PtStyle.from_dict({
                "completion-menu":                    "bg:#1a1a2e #aaaaff",
                "completion-menu.completion":          "bg:#1a1a2e #ccccff",
                "completion-menu.completion.current": "bg:#2d2d5e bold #ffffff",
            }),
        ).strip().strip('"')
        if result.lower() in ("/back", "/exit"):
            return None
        return result or None
    except ImportError:
        console.print(f"[yellow]Path:[/yellow] ", end="")
        try:
            val = input().strip().strip('"')
            if val.lower() in ("/back", "/exit"):
                return None
            return val or None
        except (EOFError, KeyboardInterrupt):
            return None
    except (KeyboardInterrupt, EOFError):
        return None


def show_status() -> None:
    while True:
        clear_screen()
        c = ask_choice(
            f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]",
            ["/back", "/exit", "/edit workspace"],
            default="/back",
            context="status",
            header_ansi=_capture_status_ansi(),
        )
        if c.lower().startswith("/edit workspace"):
            new_path = _browse_folder(str(Path.cwd().resolve()))
            if not new_path:
                continue
            p = Path(new_path).expanduser()
            if p.exists() and p.is_dir():
                os.chdir(p)
                try:
                    from core.runtime import session as ws
                    ws.set_workflow_project_root(str(p.resolve()))
                except Exception:
                    pass
                console.print(f"[green]Workspace: {p.resolve()}[/green]")
                time.sleep(0.8)
                continue
            console.print(f"[red]Workspace không hợp lệ: {new_path}[/red]")
            time.sleep(1.2)
            continue
        if c == "/exit":
            raise NavToMain
        return


__all__ = ["show_status", "_workspace_root", "_capture_status_ansi"]

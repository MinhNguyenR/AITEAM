from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from aiteam_bootstrap import ensure_project_root

ensure_project_root()

import click
from rich.box import ROUNDED
from rich.markdown import Markdown
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from core.cli.ask_flow import run_ask_mode
from core.cli.cli_prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice
from core.cli.change_flow import pick_role_key_from_indexed_workers, show_role_detail
from core.cli.command_registry import HELP_SCREEN_MARKDOWN, MAIN_MENU_VALID_CHOICES, MAIN_PROMPT_LABEL
from core.cli.context_flow import find_context_md, is_no_context, show_context as _show_context_flow
from core.cli.dashboard_flow import show_dashboard
from core.cli.palette import render_command_palette
from core.cli.settings_flow import show_settings
from core.cli.help_terminal import spawn_help_in_new_terminal
from core.cli.start_flow import run_start as _run_start_flow
from core.cli.state import get_cli_settings, get_model_overrides, get_prompt_overrides, log_system_action
from core.cli.workflow.display_policy import resolve_display_policy
from core.cli.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, SOFT_WHITE, clear_screen, console, print_header
from core.config import config
from utils.env_guard import run_startup_checks


def show_status():
    clear_screen()
    with console.status("[bold cyan]Đang tải trạng thái…", spinner="dots12"):
        _ = (config.gpu_name, config.device, config.api_key_masked)
    clear_screen()
    print_header("📊 SYSTEM DASHBOARD")
    hw = Table(box=ROUNDED, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
    hw.add_column("Label", style=Style(color=PASTEL_CYAN), width=22)
    hw.add_column("Value", style="white", width=32)
    hw.add_row("GPU", f"[bold]{config.gpu_name}[/bold]")
    hw.add_row("Device", f"[{'green' if config.device == 'cuda' else 'yellow'}]{config.device.upper()}[/{'green' if config.device == 'cuda' else 'yellow'}]")
    hw.add_row("VRAM Total", f"{config.total_vram_gb:.1f} GB")
    hw.add_row("VRAM Available", f"[bold yellow]{config.available_vram_gb:.1f} GB[/bold yellow]")
    hw.add_row("RAM System", f"{config.total_ram_gb:.1f} GB")
    console.print(Panel(hw, title=f"[{PASTEL_CYAN}]🖥️ Hardware[/{PASTEL_CYAN}]", border_style=PASTEL_BLUE, box=ROUNDED))
    console.print()
    api = Table(box=ROUNDED, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
    api.add_column("Label", style=Style(color=PASTEL_CYAN), width=22)
    api.add_column("Value", style="white", width=32)
    api.add_row("API Key", config.api_key_masked)
    api.add_row("Base URL", "openrouter.ai/api/v1")
    api.add_row("Status", "[bold green]✅ Connected[/bold green]")
    api.add_row("Agents", f"{len(config.MODEL_REGISTRY)} registered")
    console.print(Panel(api, title=f"[{PASTEL_CYAN}]🔑 API[/{PASTEL_CYAN}]", border_style=PASTEL_BLUE, box=ROUNDED))
    console.print()
    from core.cli.workflow import session as _ws_paths
    from utils.file_manager import ensure_ask_data_dir, ensure_workflow_dir

    ask_db = ensure_ask_data_dir() / "ask_history.db"
    wf_log = ensure_workflow_dir() / "workflow_activity.log"
    snap = _ws_paths.get_pipeline_snapshot()
    active_step = snap.get("active_step", "idle")
    thread_id = _ws_paths.get_thread_id() or "—"
    n_model_ovr = len(get_model_overrides())
    n_prompt_ovr = len(get_prompt_overrides())
    s_table = Table(box=ROUNDED, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
    s_table.add_column("K", style=Style(color=PASTEL_CYAN), width=22)
    s_table.add_column("V", style="white", width=76, overflow="fold")
    s_table.add_row("Working dir", str(Path(os.getcwd())))
    s_table.add_row("AI-Team home", str(config.BASE_DIR))
    s_table.add_row("Cache dir", str(config.cache_root))
    s_table.add_row("Ask DB", str(ask_db))
    s_table.add_row("Workflow log", str(wf_log))
    s_table.add_row("Pipeline step", f"[bold]{active_step}[/bold]")
    s_table.add_row("Thread ID", f"[dim]{thread_id}[/dim]")
    s_table.add_row("Model overrides", str(n_model_ovr))
    s_table.add_row("Prompt overrides", str(n_prompt_ovr))
    console.print(Panel(s_table, title=f"[bold {PASTEL_CYAN}]📂 Status & Paths[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, box=ROUNDED))
    console.print()
    console.print(
        Panel(
            "[bold]Global:[/bold] [cyan]back[/cyan] = menu chính  ·  [red]exit[/red] = về menu chính",
            border_style=PASTEL_LAVENDER,
            box=ROUNDED,
        )
    )
    while True:
        c = ask_choice("Lệnh", ["back", "exit"], default="back")
        if c == "exit":
            return
        clear_screen()
        return


def show_info():
    while True:
        clear_screen()
        print_header("📋 AGENT REGISTRY")

        workers = config.list_workers()
        m_table = Table(box=ROUNDED, show_header=True, header_style=Style(color=PASTEL_CYAN, bold=True), border_style=PASTEL_BLUE, padding=(0, 1))
        m_table.add_column("#", style="dim", width=4)
        m_table.add_column("Role Key", style=Style(color=PASTEL_CYAN), width=20)
        m_table.add_column("Role", style=Style(color=SOFT_WHITE), width=26)
        m_table.add_column("Model", style="white", width=30)
        m_table.add_column("Active", justify="center", width=8)
        m_table.add_column("Price in/out /1M", width=20)
        m_table.add_column("Ovr", justify="center", width=5)
        for i, w in enumerate(workers, 1):
            pricing = w.get("pricing", {})
            inp = pricing.get("input", 0.0)
            out = pricing.get("output", 0.0)
            price_str = f"${inp:.2f}/${out:.2f}" if (inp or out) else "N/A"
            active_icon = "[green]✅[/green]" if w.get("active", True) else "[red]❌[/red]"
            ovr_icon = "[yellow]✏[/yellow]" if w.get("is_overridden") else "[dim]—[/dim]"
            if w.get("prompt_status") == "overridden":
                ovr_icon += "[cyan]P[/cyan]"
            m_table.add_row(str(i), w["id"], w["role"], w["model"], active_icon, price_str, ovr_icon)
        console.print(Panel(m_table, title=f"[bold {PASTEL_CYAN}]🤖 Models[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, box=ROUNDED))

        role_key = pick_role_key_from_indexed_workers(workers)
        if role_key is None:
            return
        log_system_action("menu.info.role_detail", role_key)
        show_role_detail(role_key)


def show_help():
    settings = get_cli_settings()
    if bool(settings.get("help_external_terminal")):
        if spawn_help_in_new_terminal():
            console.print("[green]Đã mở cửa sổ terminal mới với help.[/green]")
            return
        console.print("[yellow]Không mở được terminal mới — hiển thị help trong app.[/yellow]")
    clear_screen()
    console.print(
        Panel(
            Markdown(HELP_SCREEN_MARKDOWN),
            title=f"[bold {PASTEL_CYAN}]📖 Hướng dẫn[/bold {PASTEL_CYAN}]",
            border_style=PASTEL_BLUE,
            padding=(1, 2),
            box=ROUNDED,
        )
    )
    console.print()
    c = ask_choice("Đóng help", ["back", "exit"], default="back")
    if c == "exit":
        return


def _drain_monitor_command_queue_cli():
    """Xử lý lệnh từ Workflow Monitor (file session); chỉ chạy khi main loop quay palette."""
    from core.cli.context_flow import (
        apply_context_accept_from_monitor,
        apply_context_back_from_monitor,
        apply_context_delete_from_monitor,
        apply_context_prepare_regenerate,
    )
    from core.cli.workflow import session as ws
    from core.cli.workflow.runner import (
        rewind_to_checkpoint,
        rewind_to_last_gate,
    )
    _ALLOWED_ACTIONS = {
        "rewind_gate", "rewind_checkpoint", "regenerate", "start_workflow",
        "context_accept", "context_back", "context_delete", "context_regenerate",
    }
    for c in ws.drain_monitor_command_queue():
        act = c.get("action")
        if act not in _ALLOWED_ACTIONS:
            log_system_action("monitor.drain.ignored", f"unknown_action={str(act)[:80]}")
            continue
        pl = c.get("payload") or {}
        root = (pl.get("project_root") or "").strip() or _project_root
        log_system_action("monitor.drain", str(act))

        if act == "rewind_gate":
            ok = rewind_to_last_gate()
            console.print("[green]Đã rewind về gate gần nhất.[/green]" if ok else "[yellow]Rewind gate thất bại.[/yellow]")
        elif act == "rewind_checkpoint":
            target = pl.get("target")
            ok = rewind_to_checkpoint(target)
            console.print(f"[green]Đã rewind checkpoint {target}.[/green]" if ok else f"[yellow]Rewind checkpoint {target} thất bại.[/yellow]")
        elif act == "regenerate":
            p = (pl.get("prompt") or "").strip()
            if not p:
                console.print("[yellow]Regenerate (monitor): thiếu prompt — bỏ qua. Nhập đầy đủ trong monitor.[/yellow]")
            else:
                from core.cli.workflow.activity_log import clear_workflow_activity_log

                clear_workflow_activity_log()
                _run_start_entry(p, regenerate_prelude=p[:400])
        elif act == "start_workflow":
            p = (pl.get("prompt") or "").strip()
            if p:
                _run_start_entry(p)
            else:
                console.print("[yellow]start_workflow: thiếu prompt.[/yellow]")
        elif act == "context_accept":
            if apply_context_accept_from_monitor(root):
                console.print("[green]Đã accept context.md và resume (monitor).[/green]")
            else:
                console.print("[yellow]context_accept: không áp dụng được (thiếu file / gate).[/yellow]")
        elif act == "context_back":
            apply_context_back_from_monitor(root)
            console.print("[dim]Đã back từ review (monitor) — giữ pause gate, chưa resume.[/dim]")
        elif act == "context_delete":
            if apply_context_delete_from_monitor(root):
                console.print("[yellow]Đã xóa context (monitor). Có thể start/regenerate mới.[/yellow]")
            else:
                console.print("[dim]context_delete: không có context.[/dim]")
        elif act == "context_regenerate":
            apply_context_prepare_regenerate(root)
            p = (pl.get("prompt") or "").strip()
            if p:
                from core.cli.workflow.activity_log import clear_workflow_activity_log

                clear_workflow_activity_log()
                _run_start_entry(p, regenerate_prelude=p[:400])
            else:
                console.print("[yellow]context_regenerate: thiếu prompt sau khi xóa context.[/yellow]")


def main_loop():
    run_startup_checks(_project_root)
    clear_screen()
    t0 = time.monotonic()
    with console.status("[bold cyan]Đang tải phần cứng / cấu hình…", spinner="dots12"):
        while time.monotonic() - t0 < 3.0:
            _ = (config.gpu_name, config.device, config.total_vram_gb, config.available_vram_gb)
            time.sleep(0.08)
    clear_screen()
    while True:
        _drain_monitor_command_queue_cli()
        ctx = find_context_md(_project_root)
        render_command_palette(bool(ctx and not is_no_context(ctx)))
        try:
            choice = ask_choice(
                f"[bold {PASTEL_CYAN}]{MAIN_PROMPT_LABEL}[/bold {PASTEL_CYAN}]",
                list(MAIN_MENU_VALID_CHOICES),
                default="1",
            )
        except KeyboardInterrupt:
            console.print(f"\n[bold {PASTEL_BLUE}]👋 Tạm biệt![/bold {PASTEL_BLUE}]")
            sys.exit(0)
        if choice in ("0", "shutdown", GLOBAL_EXIT):
            console.print(f"[bold {PASTEL_BLUE}]👋 Tạm biệt![/bold {PASTEL_BLUE}]")
            sys.exit(0)
        if choice == GLOBAL_BACK:
            console.print("[dim]Đang ở menu gốc — không có cấp trên.[/dim]")
            continue
        elif choice in ("1", "start"):
            _run_start_entry("")
        elif choice in ("2", "check"):
            log_system_action("menu.check")
            _show_context_entry()
        elif choice in ("3", "status"):
            show_status()
        elif choice in ("4", "info"):
            log_system_action("menu.info")
            show_info()
        elif choice in ("5", "dashboard"):
            log_system_action("menu.dashboard")
            show_dashboard(get_cli_settings(), project_root=os.getcwd())
        elif choice in ("6", "settings"):
            log_system_action("menu.settings")
            show_settings()
        elif choice in ("7", "help"):
            show_help()
        elif choice in ("8", "workflow"):
            run_workflow()


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        main_loop()


@cli.command()
@click.argument("prompt", required=False)
def start(prompt: Optional[str]):
    _run_start_entry((prompt or "").strip())


@cli.command()
def check():
    _show_context_entry()


@cli.command()
def status():
    show_status()


@cli.command()
def info():
    show_info()


@cli.command("change")
def change_cmd():
    show_info()


@cli.command("settings")
def settings_cmd():
    show_settings()


@cli.command("dashboard")
def dashboard_cmd():
    show_dashboard(get_cli_settings(), project_root=os.getcwd())


@cli.command("workflow")
def workflow_cmd():
    run_workflow()


def run_workflow():
    from core.cli.workflow import session as ws
    from core.cli.workflow.monitor import WorkflowMonitorApp

    settings = get_cli_settings()
    policy = resolve_display_policy(settings)
    mode = policy.view_mode
    ws.set_workflow_last_view_mode(mode)
    snap = ws.get_pipeline_snapshot()
    if snap.get("ambassador_status") == "running" or snap.get("active_step") != "idle":
        console.print(f"[dim]Attach workflow view (active_step={snap.get('active_step')})[/dim]")

    if mode == "list":
        from core.cli.workflow.list_view import run_workflow_list_view

        run_workflow_list_view(_project_root)
        return
    console.print(f"[bold {PASTEL_CYAN}]Workflow Monitor ({mode} — q thoát, r refresh)...[/bold {PASTEL_CYAN}]")
    WorkflowMonitorApp(view_mode=mode).run()


def _run_start_entry(prompt: str, *, regenerate_prelude: str | None = None):
    _run_start_flow(prompt, run_ask_mode, _project_root, regenerate_prelude=regenerate_prelude)


def run_start(prompt: str):
    _run_start_entry(prompt)


def show_context():
    _show_context_entry()


def _show_context_entry():
    _show_context_flow(_project_root, _run_start_entry)

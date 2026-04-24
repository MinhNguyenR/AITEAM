from __future__ import annotations

import os
import signal
import sys
import time
import threading
from pathlib import Path

from rich.box import ROUNDED, SIMPLE
from rich.markdown import Markdown
from rich.panel import Panel
from rich.style import Style
from rich.table import Table

from core.cli.pythonCli.flows.ask_flow import run_ask_mode
from core.cli.pythonCli.cli_prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice
from core.cli.pythonCli.flows.change_flow import pick_role_key_from_indexed_workers, show_role_detail
from core.cli.pythonCli.command_registry import HELP_SCREEN_MARKDOWN, MAIN_MENU_VALID_CHOICES, MAIN_PROMPT_LABEL
from core.cli.pythonCli.flows.context_flow import find_context_md, is_no_context, show_context as _show_context_flow
from core.cli.pythonCli.flows.dashboard_flow import show_dashboard
from core.cli.pythonCli.chrome.palette import render_command_palette
from core.cli.pythonCli.flows.settings_flow import show_settings
from core.cli.pythonCli.chrome.help_terminal import spawn_help_in_new_terminal
from core.cli.pythonCli.flows.start_flow import run_start as _run_start_flow
from core.cli.pythonCli.monitor_queue_drain import drain_monitor_command_queue
from core.cli.pythonCli.nav import NavToMain
from core.cli.pythonCli.state import get_cli_settings, get_model_overrides, get_prompt_overrides, log_system_action
from core.cli.pythonCli.workflow.tui.display_policy import resolve_display_policy
from core.cli.pythonCli.chrome.ui import (
    PASTEL_BLUE, PASTEL_CYAN, SOFT_WHITE,
    clear_screen, console, get_framework_config, print_header,
)
from core.config import config
from utils.env_guard import find_active_env_path, run_startup_checks

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ctrl+C double-press state
_last_ctrl_c: float = 0.0
_CTRL_C_WINDOW = 3.0
_ctrl_c_reset_timer: threading.Timer | None = None


def is_ctrl_c_armed() -> bool:
    return (time.time() - _last_ctrl_c) < _CTRL_C_WINDOW


def _clear_ctrl_c_hint() -> None:
    try:
        if sys.stdout.isatty():
            sys.stdout.write("\r\033[2K")
            sys.stdout.flush()
    except OSError:
        pass


def _install_global_ctrl_c_handler() -> None:
    def _handler(signum, frame):  # type: ignore[no-untyped-def]
        global _last_ctrl_c, _ctrl_c_reset_timer
        now = time.time()
        if now - _last_ctrl_c < _CTRL_C_WINDOW:
            console.print(f"\n[{PASTEL_BLUE}]Goodbye.[/{PASTEL_BLUE}]")
            raise SystemExit(0)
        _last_ctrl_c = now
        console.print(
            f"\n[yellow]Press Ctrl+C again within {_CTRL_C_WINDOW:.0f}s to exit.[/yellow]"
        )
        if _ctrl_c_reset_timer:
            _ctrl_c_reset_timer.cancel()
        _ctrl_c_reset_timer = threading.Timer(_CTRL_C_WINDOW, _clear_ctrl_c_hint)
        _ctrl_c_reset_timer.daemon = True
        _ctrl_c_reset_timer.start()

    signal.signal(signal.SIGINT, _handler)


def show_status():
    clear_screen()
    print_header("SYSTEM STATUS")

    hw = Table(box=SIMPLE, show_header=True, header_style=Style(color=PASTEL_CYAN, bold=True),
               border_style=PASTEL_BLUE, padding=(0, 2))
    hw.add_column("Hardware", style=Style(color=PASTEL_BLUE), width=22)
    hw.add_column("Value", style=Style(color=SOFT_WHITE), width=36)
    hw.add_row("GPU", f"[bold]{config.gpu_name}[/bold]")
    hw.add_row("Device", f"[{'green' if config.device == 'cuda' else 'yellow'}]{config.device.upper()}[/]")
    hw.add_row("VRAM total",     f"{config.total_vram_gb:.1f} GB")
    hw.add_row("VRAM available", f"[bold yellow]{config.available_vram_gb:.1f} GB[/bold yellow]")
    hw.add_row("RAM",            f"{config.total_ram_gb:.1f} GB")
    console.print(Panel(hw, title="[bold]Hardware[/bold]", border_style=PASTEL_BLUE, box=ROUNDED))

    env_path = find_active_env_path(PROJECT_ROOT)
    env_path_s = str(env_path) if env_path else "[red]not found[/red]"

    api = Table(box=SIMPLE, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
    api.add_column("K", style=Style(color=PASTEL_BLUE), width=22)
    api.add_column("V", style=Style(color=SOFT_WHITE), width=60, overflow="fold")
    api.add_row("API key",   config.api_key_masked)
    api.add_row("ENV file",  env_path_s)
    api.add_row("Endpoint",  "openrouter.ai/api/v1")
    api.add_row("Status",    "[bold green]connected[/bold green]")
    api.add_row("Agents",    f"{len(config.MODEL_REGISTRY)} registered")
    console.print(Panel(api, title="[bold]API[/bold]", border_style=PASTEL_BLUE, box=ROUNDED))

    fw = get_framework_config()
    fw_tbl = Table(box=SIMPLE, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
    fw_tbl.add_column("K", style=Style(color=PASTEL_BLUE), width=22)
    fw_tbl.add_column("V", style=Style(color=SOFT_WHITE), width=36)
    fw_tbl.add_row("Framework", str(fw.get("name", "aiteam")))
    fw_tbl.add_row("Version", str(fw.get("version", "unknown")))
    fw_tbl.add_row("CLI runtime", f"Python {fw.get('python', 'unknown')}")
    console.print(Panel(fw_tbl, title="[bold]Framework Config[/bold]", border_style=PASTEL_BLUE, box=ROUNDED))

    from core.cli.pythonCli.workflow.runtime import session as _ws
    from utils.file_manager import ensure_ask_data_dir, ensure_workflow_dir
    ask_db  = ensure_ask_data_dir() / "ask_history.db"
    wf_log  = ensure_workflow_dir() / "workflow_activity.log"
    snap    = _ws.get_pipeline_snapshot()
    active  = snap.get("active_step", "idle")
    tid     = _ws.get_thread_id() or "—"
    n_mo    = len(get_model_overrides())
    n_po    = len(get_prompt_overrides())

    pt = Table(box=SIMPLE, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
    pt.add_column("K", style=Style(color=PASTEL_BLUE), width=22)
    pt.add_column("V", style=Style(color=SOFT_WHITE), width=76, overflow="fold")
    pt.add_row("Working dir",     str(Path(os.getcwd())))
    pt.add_row("AI-team home",    str(config.BASE_DIR))
    pt.add_row("Cache dir",       str(config.cache_root))
    pt.add_row("Ask DB",          str(ask_db))
    pt.add_row("Workflow log",    str(wf_log))
    pt.add_row("Pipeline step",   f"[bold]{active}[/bold]")
    pt.add_row("Thread ID",       f"[dim]{tid}[/dim]")
    pt.add_row("Model overrides", str(n_mo))
    pt.add_row("Prompt overrides",str(n_po))
    console.print(Panel(pt, title="[bold]Paths & State[/bold]", border_style=PASTEL_BLUE, box=ROUNDED))
    console.print()
    console.print("[dim]back · exit[/dim]")
    console.print()

    while True:
        c = ask_choice(f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]", ["back", "exit"], default="back")
        if c == "exit":
            raise NavToMain
        clear_screen()
        return


def show_info():
    while True:
        clear_screen()
        print_header("AGENT REGISTRY")

        workers = config.list_workers()
        m = Table(
            box=SIMPLE, show_header=True,
            header_style=Style(color=PASTEL_CYAN, bold=True),
            border_style=PASTEL_BLUE, padding=(0, 1),
        )
        m.add_column("#",    style="dim", width=4)
        m.add_column("Key",  style=Style(color=PASTEL_CYAN), width=20)
        m.add_column("Role", style=Style(color=SOFT_WHITE),  width=26)
        m.add_column("Model",width=30)
        m.add_column("On",   justify="center", width=4)
        m.add_column("$/1M", width=16)
        m.add_column("Ovr",  justify="center", width=5)
        for i, w in enumerate(workers, 1):
            pricing  = w.get("pricing", {})
            inp, out = pricing.get("input", 0.0), pricing.get("output", 0.0)
            price_s  = f"${inp:.2f}/${out:.2f}" if (inp or out) else "—"
            on_icon  = "[green]on[/green]"  if w.get("active", True) else "[red]off[/red]"
            ovr_icon = "[yellow]M[/yellow]" if w.get("is_overridden")     else "[dim]—[/dim]"
            if w.get("prompt_status") == "overridden":
                ovr_icon += "[cyan]P[/cyan]"
            m.add_row(str(i), w["id"], w["role"], w["model"], on_icon, price_s, ovr_icon)
        console.print(Panel(m, title="[bold]Models[/bold]", border_style=PASTEL_BLUE, box=ROUNDED))

        role_key = pick_role_key_from_indexed_workers(workers)
        if role_key is None:
            return
        log_system_action("menu.info.role_detail", role_key)
        show_role_detail(role_key)


def show_help():
    settings = get_cli_settings()
    if bool(settings.get("help_external_terminal")):
        if spawn_help_in_new_terminal():
            console.print("[green]Opened help in new terminal window.[/green]")
            return
        console.print("[yellow]Could not open new terminal — showing inline.[/yellow]")
    clear_screen()
    print_header("REFERENCE GUIDE")
    console.print(
        Panel(
            Markdown(HELP_SCREEN_MARKDOWN),
            border_style=PASTEL_BLUE,
            padding=(1, 2),
            box=ROUNDED,
        )
    )
    console.print()
    c = ask_choice(f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]", ["back", "exit"], default="back")
    if c == "exit":
        raise NavToMain


def _drain_monitor_command_queue_cli() -> None:
    drain_monitor_command_queue(PROJECT_ROOT, _run_start_entry)


def main_loop():
    run_startup_checks(PROJECT_ROOT)
    _install_global_ctrl_c_handler()
    clear_screen()
    t0 = time.monotonic()
    with console.status(f"[{PASTEL_BLUE}]Loading…[/{PASTEL_BLUE}]", spinner="dots"):
        while time.monotonic() - t0 < 2.5:
            _ = (config.gpu_name, config.device, config.total_vram_gb)
            time.sleep(0.08)
    clear_screen()

    while True:
        try:
            _drain_monitor_command_queue_cli()
            ctx = find_context_md(PROJECT_ROOT)
            render_command_palette(bool(ctx and not is_no_context(ctx)))
            choice = ask_choice(
                f"[bold {PASTEL_CYAN}]{MAIN_PROMPT_LABEL}[/bold {PASTEL_CYAN}]",
                list(MAIN_MENU_VALID_CHOICES),
                default="1",
            )
        except EOFError:
            if is_ctrl_c_armed():
                remaining = max(0.0, _CTRL_C_WINDOW - (time.time() - _last_ctrl_c))
                if remaining > 0:
                    time.sleep(remaining)
                continue
            raise
        except NavToMain:
            continue

        try:
            if choice in ("0", "shutdown", GLOBAL_EXIT):
                console.print(f"[{PASTEL_BLUE}]Goodbye.[/{PASTEL_BLUE}]")
                sys.exit(0)
            if choice == GLOBAL_BACK:
                console.print("[dim]Already at root — no parent menu.[/dim]")
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
        except NavToMain:
            continue


def run_workflow():
    from core.cli.pythonCli.workflow.runtime import session as ws
    from core.cli.pythonCli.workflow.tui.monitor_app import WorkflowMonitorApp

    settings = get_cli_settings()
    policy   = resolve_display_policy(settings)
    mode     = policy.view_mode
    ws.set_workflow_last_view_mode(mode)
    snap     = ws.get_pipeline_snapshot()
    if snap.get("ambassador_status") == "running" or snap.get("active_step") != "idle":
        console.print(f"[dim]Reconnecting to workflow (step={snap.get('active_step')})[/dim]")

    try:
        if mode == "list":
            from core.cli.pythonCli.workflow.tui.list_view import run_workflow_list_view
            run_workflow_list_view(PROJECT_ROOT)
        else:
            WorkflowMonitorApp(view_mode=mode).run()
    finally:
        clear_screen()
        try:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()
        except OSError:
            pass


def _run_start_entry(prompt: str, *, regenerate_prelude: str | None = None, force_mode: str | None = None):
    _run_start_flow(prompt, run_ask_mode, PROJECT_ROOT, regenerate_prelude=regenerate_prelude, force_mode=force_mode)


def run_start(prompt: str):
    _run_start_entry(prompt)


def show_context():
    _show_context_entry()


def _show_context_entry():
    _show_context_flow(PROJECT_ROOT, _run_start_entry)

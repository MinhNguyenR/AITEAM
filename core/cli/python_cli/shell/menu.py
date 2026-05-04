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

from core.cli.python_cli.features.ask.flow import run_ask_mode
from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice
from core.cli.python_cli.features.change.flow import pick_role_key_from_indexed_workers, show_role_detail
from core.cli.python_cli.shell.command_registry import help_screen_markdown, MAIN_MENU_VALID_CHOICES, MAIN_PROMPT_LABEL
from core.cli.python_cli.features.context.flow import find_context_md, is_no_context, show_context as _show_context_flow
from core.frontends.dashboard import show_dashboard
from core.cli.python_cli.ui.rich_command_palette import capture_menu_ansi, render_command_palette
from core.cli.python_cli.features.settings.flow import show_settings
from core.cli.python_cli.ui.help_terminal import spawn_help_in_new_terminal
from core.cli.python_cli.features.start.flow import run_start as _run_start_flow
from core.cli.python_cli.shell.monitor_queue_drain import drain_monitor_command_queue
from core.cli.python_cli.shell.nav import NavToMain
from core.app_state import (
    get_cli_settings,
    get_model_overrides,
    get_prompt_overrides,
    log_system_action,
)
from core.cli.python_cli.ui.ui import (
    PASTEL_BLUE, PASTEL_CYAN, SOFT_WHITE,
    clear_screen, console, get_framework_config, print_header,
)
from core.cli.python_cli.i18n import t
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
            console.print(f"\n[{PASTEL_BLUE}]{t('ui.goodbye')}[/{PASTEL_BLUE}]")
            raise SystemExit(0)
        _last_ctrl_c = now
        console.print(
            f"\n[yellow]{t('ui.press_ctrl_c').format(s=int(_CTRL_C_WINDOW))}[/yellow]"
        )
        if _ctrl_c_reset_timer:
            _ctrl_c_reset_timer.cancel()
        _ctrl_c_reset_timer = threading.Timer(_CTRL_C_WINDOW, _clear_ctrl_c_hint)
        _ctrl_c_reset_timer.daemon = True
        _ctrl_c_reset_timer.start()

    signal.signal(signal.SIGINT, _handler)


def show_status():
    clear_screen()
    print_header(t('status.header'))

    hw = Table(box=SIMPLE, show_header=True, header_style=Style(color=PASTEL_CYAN, bold=True),
               border_style=PASTEL_BLUE, padding=(0, 2))
    hw.add_column(t('status.hardware'), style=Style(color=PASTEL_BLUE), width=22)
    hw.add_column(t('ui.value'), style=Style(color=SOFT_WHITE), width=36)
    hw.add_row(t('status.gpu'), f"[bold]{config.gpu_name}[/bold]")
    hw.add_row(t('status.device'), f"[{'green' if config.device == 'cuda' else 'yellow'}]{config.device.upper()}[/]")
    hw.add_row(t('status.vram_total'),     f"{config.total_vram_gb:.1f} GB")
    hw.add_row(t('status.vram_avail'), f"[bold yellow]{config.available_vram_gb:.1f} GB[/bold yellow]")
    hw.add_row(t('status.ram_total'),            f"{config.total_ram_gb:.1f} GB")
    console.print(Panel(hw, title=f"[bold]{t('status.hardware')}[/bold]", border_style=PASTEL_BLUE, box=ROUNDED))

    env_path = find_active_env_path(PROJECT_ROOT)
    env_path_s = str(env_path) if env_path else "[red]not found[/red]"

    api = Table(box=SIMPLE, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
    api.add_column("K", style=Style(color=PASTEL_BLUE), width=22)
    api.add_column("V", style=Style(color=SOFT_WHITE), width=60, overflow="fold")
    api.add_row(t('status.api_key'),   config.api_key_masked)
    api.add_row(t('status.env_file'),  env_path_s)
    api.add_row(t('status.endpoint'),  "openrouter.ai/api/v1")
    api.add_row(t('status.status'),    f"[bold green]{t('status.connected')}[/bold green]")
    api.add_row(t('status.api').split(' ')[0],    t('status.agents_reg').format(n=len(config.MODEL_REGISTRY)))
    console.print(Panel(api, title=f"[bold]{t('status.api')}[/bold]", border_style=PASTEL_BLUE, box=ROUNDED))

    fw = get_framework_config()
    fw_tbl = Table(box=SIMPLE, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
    fw_tbl.add_column("K", style=Style(color=PASTEL_BLUE), width=22)
    fw_tbl.add_column("V", style=Style(color=SOFT_WHITE), width=36)
    fw_tbl.add_row(t('status.fw_name'), str(fw.get("name", "aiteam")))
    fw_tbl.add_row(t('status.fw_ver'), str(fw.get("version", "unknown")))
    fw_tbl.add_row(t('status.cli_runtime'), f"Python {fw.get('python', 'unknown')}")
    console.print(Panel(fw_tbl, title=f"[bold]{t('status.fw_config')}[/bold]", border_style=PASTEL_BLUE, box=ROUNDED))

    from core.runtime import session as _ws
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
    pt.add_row(t('status.working_dir'),     str(Path(os.getcwd())))
    pt.add_row(t('status.ai_home'),    str(config.BASE_DIR))
    pt.add_row(t('status.cache_dir'),       str(config.cache_root))
    pt.add_row(t('status.ask_db'),          str(ask_db))
    pt.add_row(t('status.wf_log'),    str(wf_log))
    pt.add_row(t('status.pipeline_step'),   f"[bold]{active}[/bold]")
    pt.add_row(t('status.thread_id'),       f"[dim]{tid}[/dim]")
    pt.add_row(t('info.model_override'), str(n_mo))
    pt.add_row(t('info.prompt_title') + " overrides", str(n_po))
    console.print(Panel(pt, title=f"[bold]{t('status.paths')}[/bold]", border_style=PASTEL_BLUE, box=ROUNDED))
    console.print()
    while True:
        c = ask_choice(f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]", ["back", "exit"], default="back", context="status")
        if c == "exit":
            raise NavToMain
        clear_screen()
        return


def show_info():
    while True:
        clear_screen()
        print_header(t("info.header"))

        workers = config.list_workers()
        m = Table(
            box=SIMPLE, show_header=True,
            header_style=Style(color=PASTEL_CYAN, bold=True),
            border_style=PASTEL_BLUE, padding=(0, 1),
        )
        m.add_column("#",    style="dim", width=4)
        m.add_column(t("info.role_key"),  style=Style(color=PASTEL_CYAN), width=20)
        m.add_column(t("info.role_name"), style=Style(color=SOFT_WHITE),  width=26)
        m.add_column(t("info.model_col"), width=30)
        m.add_column(t("info.active"), justify="center", width=8)
        m.add_column(t("info.price_col"), width=16)
        m.add_column(t("info.ovr"),  justify="center", width=8)
        for i, w in enumerate(workers, 1):
            pricing  = w.get("pricing", {})
            inp, out = pricing.get("input", 0.0), pricing.get("output", 0.0)
            price_s  = f"${inp:.2f}/${out:.2f}" if (inp or out) else "—"
            on_icon  = f"[green]{t('info.on')}[/green]"  if w.get("active", True) else f"[red]{t('info.off')}[/red]"
            ovr_icon = "[yellow]M[/yellow]" if w.get("is_overridden")     else "[dim]—[/dim]"
            if w.get("prompt_status") == "overridden":
                ovr_icon += "[cyan]P[/cyan]"
            m.add_row(str(i), w["id"], w["role"], w["model"], on_icon, price_s, ovr_icon)
        console.print(Panel(m, title=f"[bold]{t('info.models_panel')}[/bold]", border_style=PASTEL_BLUE, box=ROUNDED))

        role_key = pick_role_key_from_indexed_workers(workers)
        if role_key is None:
            return
        log_system_action("menu.info.role_detail", role_key)
        show_role_detail(role_key)


def show_help():
    settings = get_cli_settings()
    if bool(settings.get("help_external_terminal")):
        if spawn_help_in_new_terminal():
            console.print(f"[green]{t('settings.help_opened')}[/green]")
            return
        console.print(f"[yellow]{t('settings.help_failed')}[/yellow]")
    clear_screen()
    print_header(t("menu.help.desc"))
    console.print(
        Panel(
            Markdown(help_screen_markdown()),
            border_style=PASTEL_BLUE,
            padding=(1, 2),
            box=ROUNDED,
        )
    )
    console.print()
    c = ask_choice(f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]", ["back", "exit"], default="back", context="help")
    if c == "exit":
        raise NavToMain
    clear_screen()


def _drain_monitor_command_queue_cli() -> None:
    drain_monitor_command_queue(PROJECT_ROOT, _run_start_entry)


def main_loop():
    run_startup_checks(PROJECT_ROOT)
    _install_global_ctrl_c_handler()
    clear_screen()

    while True:
        try:
            _drain_monitor_command_queue_cli()
            ctx = find_context_md(PROJECT_ROOT)
            context_ready = bool(ctx and not is_no_context(ctx))
            render_command_palette(context_ready)
            choice = ask_choice(
                f"[bold {PASTEL_CYAN}]{MAIN_PROMPT_LABEL}[/bold {PASTEL_CYAN}]",
                list(MAIN_MENU_VALID_CHOICES),
                default="1",
                header_ansi=capture_menu_ansi(context_ready),
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
                console.print(f"[{PASTEL_BLUE}]{t('ui.goodbye')}[/{PASTEL_BLUE}]")
                sys.exit(0)
            if choice == GLOBAL_BACK:
                console.print(f"[dim]{t('ui.already_at_root')}[/dim]")
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
    from core.runtime import session as ws
    from core.frontends.tui import run_workflow_list_view

    snap = ws.get_pipeline_snapshot()
    if snap.get("ambassador_status") == "running" or snap.get("active_step") != "idle":
        console.print(f"[dim]{t('ui.reconnecting').format(step=snap.get('active_step'))}[/dim]")

    try:
        run_workflow_list_view(PROJECT_ROOT)
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


__all__ = ["main_loop", "show_status", "show_info", "show_help", "run_workflow"]

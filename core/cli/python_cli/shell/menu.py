"""Main menu coordinator: Ctrl+C management, main_loop, and entry-point wrappers."""
from __future__ import annotations

import os
import signal
import sys
import time
import threading

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = _PROJECT_ROOT

from core.cli.python_cli.features.ask.flow import run_ask_mode
from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice
from core.cli.python_cli.shell.command_registry import MAIN_MENU_VALID_CHOICES, MAIN_PROMPT_LABEL
from core.cli.python_cli.features.context.flow import show_context as _show_context_flow
from core.frontends.dashboard import show_dashboard
from core.cli.python_cli.ui.rich_command_palette import capture_menu_ansi
from core.cli.python_cli.features.settings.flow import show_settings
from core.cli.python_cli.features.start.flow import run_start as _run_start_flow
from core.cli.python_cli.shell.monitor_queue_drain import drain_monitor_command_queue
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.shell.screens.status import show_status, _workspace_root
from core.cli.python_cli.shell.screens.info import show_info, show_help
from core.app_state import get_cli_settings, log_system_action
from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, clear_screen, console
from core.cli.python_cli.i18n import t
from utils.env_guard import run_startup_checks

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
            clear_screen()
            console.print(f"[{PASTEL_BLUE}]{t('ui.goodbye')}[/{PASTEL_BLUE}]")
            raise SystemExit(0)
        _last_ctrl_c = now
        console.print(f"\n[yellow]{t('ui.press_ctrl_c').format(s=int(_CTRL_C_WINDOW))}[/yellow]")
        if _ctrl_c_reset_timer:
            _ctrl_c_reset_timer.cancel()
        _ctrl_c_reset_timer = threading.Timer(_CTRL_C_WINDOW, _clear_ctrl_c_hint)
        _ctrl_c_reset_timer.daemon = True
        _ctrl_c_reset_timer.start()

    signal.signal(signal.SIGINT, _handler)


def _drain_monitor_command_queue_cli() -> None:
    drain_monitor_command_queue(_workspace_root(), _run_start_entry)


def main_loop():
    run_startup_checks(_PROJECT_ROOT)
    _install_global_ctrl_c_handler()

    while True:
        try:
            _drain_monitor_command_queue_cli()
            choice = ask_choice(
                f"| [bold {PASTEL_CYAN}]{MAIN_PROMPT_LABEL}[/bold {PASTEL_CYAN}] |",
                list(MAIN_MENU_VALID_CHOICES),
                default="1",
                header_ansi=capture_menu_ansi(False),
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
            parts = choice.split(None, 1)
            cmd = parts[0].lower()
            if cmd.startswith('/'):
                cmd = cmd[1:]
            elif not cmd.isdigit():
                console.print(f"[yellow]{t('cmd.slash_required').format(cmd='/' + cmd)}[/yellow]")
                continue
            payload = parts[1] if len(parts) > 1 else ""

            if cmd in ("0", "shutdown", GLOBAL_EXIT):
                clear_screen()
                console.print(f"[{PASTEL_BLUE}]{t('ui.goodbye')}[/{PASTEL_BLUE}]")
                sys.exit(0)
            if cmd == GLOBAL_BACK:
                console.print(f"[dim]{t('ui.already_at_root')}[/dim]")
                continue
            elif cmd in ("1", "chat"):
                run_ask_mode(payload)
            elif cmd in ("2", "status"):
                show_status()
            elif cmd in ("3", "info"):
                log_system_action("menu.info")
                show_info()
            elif cmd in ("4", "dashboard"):
                log_system_action("menu.dashboard")
                show_dashboard(get_cli_settings(), project_root=_workspace_root())
            elif cmd in ("5", "settings"):
                log_system_action("menu.settings")
                show_settings()
            elif cmd in ("6", "help"):
                show_help()
            elif cmd in ("7", "workflow"):
                run_workflow()
            elif cmd == "explain":
                from core.cli.python_cli.features.explain.flow import run_explain
                run_explain(payload, project_root=_workspace_root())
            elif cmd == "explainer":
                from core.cli.python_cli.features.explain.flow import run_explainer
                run_explainer(payload, project_root=_workspace_root())
            elif cmd == "restore":
                _run_start_entry(("restore " + payload).strip(), force_mode="agent")
        except NavToMain:
            continue


def run_workflow():
    from core.runtime import session as ws
    from core.frontends.tui import run_workflow_list_view

    snap = ws.get_pipeline_snapshot()
    if snap.get("ambassador_status") == "running" or snap.get("active_step") != "idle":
        console.print(f"[dim]{t('ui.reconnecting').format(step=snap.get('active_step'))}[/dim]")

    try:
        run_workflow_list_view(_workspace_root())
    finally:
        clear_screen()
        try:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()
        except OSError:
            pass


def _run_start_entry(prompt: str, *, regenerate_prelude: str | None = None, force_mode: str | None = None):
    _run_start_flow(prompt, run_ask_mode, _workspace_root(), regenerate_prelude=regenerate_prelude, force_mode=force_mode)


def run_start(prompt: str):
    _run_start_entry(prompt)


def show_context():
    _show_context_entry()


def _show_context_entry():
    _show_context_flow(_workspace_root(), _run_start_entry)


__all__ = ["main_loop", "show_status", "show_info", "show_help", "run_workflow"]

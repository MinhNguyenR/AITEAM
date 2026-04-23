"""Run in a new terminal: `python -m core.cli.chrome.help_terminal` (see show_help external setting)."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from core.cli.cli_prompt import wait_enter

_AI_TEAM_ROOT = Path(__file__).resolve().parents[3]


def _ensure_path() -> Path:
    root = _AI_TEAM_ROOT
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def print_help_screen() -> None:
    _ensure_path()
    from core.cli.command_registry import HELP_SCREEN_MARKDOWN

    con = Console(width=None, soft_wrap=True)
    con.print(
        Panel(
            Markdown(HELP_SCREEN_MARKDOWN),
            title="[bold cyan]📖 Hướng dẫn[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )


def spawn_help_in_new_terminal() -> bool:
    """Open a new OS terminal running this module. Returns False if spawn failed."""
    root = str(_AI_TEAM_ROOT)
    exe = sys.executable
    mod = "core.cli.chrome.help_terminal"

    if sys.platform == "win32":
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        try:
            subprocess.Popen(
                [comspec, "/c", "start", "AI Team Help", exe, "-m", mod],
                cwd=root,
                close_fds=True,
            )
            return True
        except OSError:
            return False

    inner = f"cd {shlex.quote(root)} && {shlex.quote(exe)} -m {mod}; read -r -p 'Enter to close...' _"
    candidates: list[list[str]] = []
    if sys.platform == "darwin":
        script = f'tell application "Terminal" to do script {shlex.quote(inner)}'
        candidates.append(["osascript", "-e", script])
    for term, args in (
        ("gnome-terminal", ["--", "bash", "-lc", inner]),
        ("konsole", ["-e", "bash", "-lc", inner]),
        ("xfce4-terminal", ["-e", "bash", "-lc", inner]),
        ("kitty", ["bash", "-lc", inner]),
        ("alacritty", ["-e", "bash", "-lc", inner]),
        ("x-terminal-emulator", ["-e", "bash", "-lc", inner]),
    ):
        if shutil.which(term):
            candidates.append([term, *args])

    for cmd in candidates:
        try:
            subprocess.Popen(cmd, cwd=root, start_new_session=True)
            return True
        except OSError:
            continue
    return False


def main() -> None:
    print_help_screen()
    try:
        wait_enter("\nNhấn Enter để đóng cửa sổ này...")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()

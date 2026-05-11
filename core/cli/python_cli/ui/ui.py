from __future__ import annotations

import os
import subprocess
import sys

from rich.box import DOUBLE, ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.style import Style
from rich.text import Text

console = Console()

# ---------- Colour palette ------------------------------------------------------------
PASTEL_BLUE    = "#6495ED"   # cornflower blue  (primary)
PASTEL_CYAN    = "#7FFFD4"   # aquamarine       (accent)
PASTEL_LAVENDER= "#C8C8FF"   # soft lavender    (secondary)
SOFT_BLUE      = "#ADD8E6"   # light blue
BRIGHT_BLUE    = "#4169E1"   # royal blue       (headers)
SOFT_WHITE     = "#E8E8F0"   # off-white
DIM_BLUE       = "#3A3A6E"   # dark blue dim

# ---------- ASCII logo ----------------------------------------------------------------
# figlet "big" font - AI  TEAM
_LOGO_LINES = (
    r"    _    ___         _____ _____    _    __  __ ",
    r"   / \  |_ _|       |_   _| ____|  / \  |  \/  |",
    r"  / _ \  | |          | | |  _|   / _ \ | |\/| |",
    r" / ___ \ | |          | | | |___ / ___ \| |  | |",
    r"/_/   \_\|___|        |_| |_____/_/   \_\_|  |_|",
)
_LOGO_SUB = ""


def get_framework_config() -> dict[str, str]:
    import platform
    from importlib import metadata

    name = "aiteam"
    version = "0"
    loaded_from_file = False
    try:
        import tomllib
        from pathlib import Path

        root = Path(__file__).resolve().parents[3]
        with open(root / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        proj = data.get("project", {})
        name = str(proj.get("name") or name)
        version = str(proj.get("version") or version)
        loaded_from_file = True
    except (OSError, ImportError, KeyError):
        pass
    if not loaded_from_file:
        try:
            meta = metadata.metadata("aiteam")
            name = str(meta.get("Name") or name)
            version = str(meta.get("Version") or version)
        except metadata.PackageNotFoundError:
            pass
    return {
        "name": name,
        "version": version,
        "python": platform.python_version(),
    }


def _supports_ansi_clear() -> bool:
    return sys.stdout.isatty() and os.name != "nt"


def clear_screen():
    if _supports_ansi_clear():
        print("\033[2J\033[H", end="", flush=True)
        return
    try:
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "cls"], check=False, shell=False)
        else:
            subprocess.run(["clear"], check=False, shell=False)
    except OSError:
        pass


def print_logo(*, subtitle: str | None = None, compact: bool = False) -> None:
    """Print the AI-team ASCII logo in blue."""
    logo_text = Text(justify="center")
    for line in _LOGO_LINES:
        logo_text.append(line + "\n", style=Style(color=PASTEL_BLUE, bold=True))
    if subtitle:
        logo_text.append(f"\n{subtitle}", style=Style(color=PASTEL_CYAN))
    console.print(
        Panel(
            logo_text,
            border_style=BRIGHT_BLUE,
            box=DOUBLE if not compact else ROUNDED,
            padding=(1, 4) if not compact else (0, 2),
        )
    )
    console.print()


def print_divider(label: str = ""):
    if label:
        console.print(Rule(f"[{PASTEL_CYAN}]{label}[/{PASTEL_CYAN}]", style=PASTEL_BLUE))
    else:
        console.print(Rule(style=PASTEL_BLUE))


def print_header(title: str, subtitle: str = "", *, out: Console | None = None) -> None:
    sink = out or console
    body = Text(title, style=Style(color=BRIGHT_BLUE, bold=True), justify="center")
    if subtitle:
        body.append(f"\n{subtitle}", style=Style(color=PASTEL_CYAN))
    sink.print(Panel(body, box=ROUNDED, border_style=PASTEL_BLUE, padding=(0, 4)))
    sink.print()


__all__ = [
    "console",
    "PASTEL_BLUE", "PASTEL_CYAN", "PASTEL_LAVENDER",
    "SOFT_BLUE", "BRIGHT_BLUE", "SOFT_WHITE", "DIM_BLUE",
    "_LOGO_LINES", "_LOGO_SUB",
    "_supports_ansi_clear", "clear_screen",
    "print_logo", "print_divider", "print_header",
    "get_framework_config",
]

from __future__ import annotations

import os
import subprocess
import sys

from rich.box import DOUBLE
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.style import Style
from rich.text import Text

console = Console()

PASTEL_BLUE = "#6495ED"
PASTEL_CYAN = "#7FFFD4"
PASTEL_LAVENDER = "#C8C8FF"
SOFT_BLUE = "#ADD8E6"
BRIGHT_BLUE = "#4169E1"
SOFT_WHITE = "#E8E8F0"
DIM_BLUE = "#3A3A6E"


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


def print_divider(label: str = ""):
    if label:
        console.print(Rule(f"[{PASTEL_CYAN}]{label}[/{PASTEL_CYAN}]", style=PASTEL_BLUE))
    else:
        console.print(Rule(style=PASTEL_BLUE))


def print_header(title: str, subtitle: str = ""):
    body = Text(title, style=Style(color=BRIGHT_BLUE, bold=True), justify="center")
    if subtitle:
        body.append(f"\n{subtitle}", style=Style(color=PASTEL_CYAN))
    console.print(Panel(body, box=DOUBLE, border_style=PASTEL_BLUE, padding=(1, 4)))
    console.print()


__all__ = [
    "console",
    "PASTEL_BLUE",
    "PASTEL_CYAN",
    "PASTEL_LAVENDER",
    "SOFT_BLUE",
    "BRIGHT_BLUE",
    "SOFT_WHITE",
    "DIM_BLUE",
    "_supports_ansi_clear",
    "clear_screen",
    "print_divider",
    "print_header",
]

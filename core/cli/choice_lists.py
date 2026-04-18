from __future__ import annotations

from core.cli.command_registry import menu_commands

# Re-export palette rows from central registry (single source of truth).


def context_viewer_choices() -> list[str]:
    return ["back", "edit", "delete", "run", "regenerate", "exit"]


def start_mode_choices() -> list[str]:
    return ["ask", "agent", "back", "exit"]


__all__ = ["context_viewer_choices", "menu_commands", "start_mode_choices"]

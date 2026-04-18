from __future__ import annotations

import time

from rich.box import ROUNDED
from rich.prompt import Prompt

from core.cli.cli_prompt import ask_choice
from rich.style import Style
from rich.table import Table

from core.cli.state import get_cli_settings, save_cli_settings
from core.cli.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, clear_screen, console, print_divider, print_header


def show_settings():
    settings = get_cli_settings()
    clear_screen()
    print_header("⚙️  SETTINGS")
    while True:
        auto_ac = settings["auto_accept_context"]
        view_mode = settings.get("workflow_view_mode", "chain")
        help_ext = bool(settings.get("help_external_terminal", False))
        tbl = Table(box=ROUNDED, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
        tbl.add_column("Setting", style=Style(color=PASTEL_CYAN), width=28)
        tbl.add_column("Value", style="white", width=20)
        tbl.add_row("Auto-accept context.md", f"{'✅ Bật' if auto_ac else '🔍 Tắt (confirm thủ công)'}")
        tbl.add_row(
            "Workflow view mode",
            "Chain" if view_mode == "chain" else "List",
        )
        tbl.add_row("Help terminal mới", "Bật" if help_ext else "Tắt")
        console.print(tbl)
        console.print()
        print_divider("Tùy chọn")
        console.print(f"  [{PASTEL_CYAN}][1][/{PASTEL_CYAN}] Đổi auto-accept context.md")
        console.print(f"  [{PASTEL_CYAN}][2][/{PASTEL_CYAN}] Workflow view mode: chain / list")
        console.print(f"  [{PASTEL_CYAN}][3][/{PASTEL_CYAN}] Help: mở cửa sổ terminal mới khi chọn menu help (toggle)")
        console.print(f"  [{PASTEL_LAVENDER}][0][/{PASTEL_LAVENDER}] Quay lại menu chính")
        console.print()
        choice = ask_choice(f"[{PASTEL_CYAN}]Chọn[/{PASTEL_CYAN}]", ["0", "1", "2", "3", "back", "exit"], default="0")
        if choice == "exit":
            break
        if choice in ("0", "back"):
            break
        if choice == "1":
            settings["auto_accept_context"] = not auto_ac
            save_cli_settings(settings)
            label = "Bật (auto)" if settings["auto_accept_context"] else "Tắt (manual)"
            console.print(f"[green]✓ Auto-accept → {label}[/green]")
        elif choice == "2":
            settings["workflow_view_mode"] = "list" if settings.get("workflow_view_mode", "chain") == "chain" else "chain"
            save_cli_settings(settings)
            vm = settings["workflow_view_mode"]
            console.print(f"[green]✓ Workflow view mode → {vm}[/green]")
        elif choice == "3":
            settings["help_external_terminal"] = not bool(settings.get("help_external_terminal", False))
            save_cli_settings(settings)
            console.print(f"[green]✓ Help terminal mới → {'Bật' if settings['help_external_terminal'] else 'Tắt'}[/green]")
        if choice != "0":
            time.sleep(0.6)
            clear_screen()
            print_header("⚙️  SETTINGS")


__all__ = ["show_settings"]

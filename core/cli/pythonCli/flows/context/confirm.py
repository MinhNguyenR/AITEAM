from __future__ import annotations

import time
from pathlib import Path
from typing import Literal

from rich.box import ROUNDED
from rich.markdown import Markdown
from rich.panel import Panel

from core.cli.pythonCli.cli_prompt import ask_choice
from core.cli.pythonCli.safe_editor import run_editor_on_file
from core.cli.pythonCli.flows.context.common import full_context_cleanup, graphrag_drop
from core.cli.pythonCli.nav import NavToMain
from core.cli.pythonCli.state import log_system_action, update_context_state
from core.cli.pythonCli.chrome.ui import BRIGHT_BLUE, PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, clear_screen, console, print_divider, print_header

ContextConfirmResult = Literal["accept", "regenerate", "back", "delete"]


def confirm_context(context_path: Path) -> ContextConfirmResult:
    clear_screen()
    print_header("📋 CONTEXT.MD REVIEW", "Xem lại kế hoạch trước khi tiếp tục")
    content = context_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    line_count = len(lines)
    char_count = len(content)
    console.print(f"[{PASTEL_CYAN}]📁 {context_path}[/{PASTEL_CYAN}]  [dim]{line_count} lines | {char_count} chars[/dim]")
    console.print()
    display_lines = lines[:120]
    display_content = "\n".join(display_lines)
    if line_count > 120:
        display_content += f"\n\n[dim]... ({line_count - 120} lines hidden — xem file đầy đủ trong editor)[/dim]"
    console.print(Panel(Markdown(display_content), title=f"[bold {PASTEL_CYAN}]context.md[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, padding=(1, 2), box=ROUNDED))
    console.print()
    print_divider("Quyết định")
    console.print(f"  [{BRIGHT_BLUE}][A][/{BRIGHT_BLUE}] Accept  — tiếp tục pipeline")
    console.print(f"  [{PASTEL_CYAN}][E][/{PASTEL_CYAN}] Edit    — mở file trong editor")
    console.print(f"  [{PASTEL_LAVENDER}][R][/{PASTEL_LAVENDER}] Regenerate — tạo lại context.md")
    console.print("  [white][B][/white] Back    — quay menu, [bold]giữ[/bold] context.md (mục check)")
    console.print("  [red][D][/red] Delete  — xóa context.md và thoát")
    console.print()
    while True:
        choice = ask_choice(
            f"[{PASTEL_CYAN}]Lựa chọn[/{PASTEL_CYAN}]",
            ["a", "e", "r", "b", "d", "A", "E", "R", "B", "D", "exit"],
            default="a",
        ).lower()
        if choice == "exit":
            raise NavToMain
        if choice == "a":
            console.print("[bold green]✅ Accepted — pipeline tiếp tục.[/bold green]")
            time.sleep(0.8)
            return "accept"
        if choice == "e":
            console.print(f"[dim]Mở editor {context_path} ...[/dim]")
            run_editor_on_file(context_path)
            console.print(f"[{PASTEL_CYAN}]File đã được lưu. Xem lại...[/{PASTEL_CYAN}]")
            time.sleep(0.5)
            return confirm_context(context_path)
        if choice == "r":
            console.print(f"[{PASTEL_LAVENDER}]🔄 Regenerate requested.[/{PASTEL_LAVENDER}]")
            try:
                graphrag_drop(context_path)
                context_path.unlink(missing_ok=True)
                update_context_state("deleted", context_path, reason="regenerate_requested")
                log_system_action("context.delete", f"{context_path} reason=regenerate_requested")
            except OSError as e:
                console.print(f"[red]Không thể xóa context hiện tại: {e}[/red]")
            time.sleep(0.5)
            return "regenerate"
        if choice == "b":
            update_context_state("active", context_path, reason="review_deferred")
            log_system_action("context.review.back", str(context_path))
            console.print("[dim]Quay menu — context.md vẫn trên đĩa. Dùng check để xem / sửa / xóa.[/dim]")
            time.sleep(0.6)
            return "back"
        if choice == "d":
            try:
                full_context_cleanup(context_path, reason="deleted")
                console.print("[green]✓ Đã xóa context.md.[/green]")
            except (OSError, ValueError, TypeError) as e:
                console.print(f"[red]Không thể xóa: {e}[/red]")
            time.sleep(0.6)
            return "delete"


__all__ = ["ContextConfirmResult", "confirm_context"]

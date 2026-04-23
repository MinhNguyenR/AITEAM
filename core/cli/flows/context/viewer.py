from __future__ import annotations

from typing import Callable

from rich.box import ROUNDED
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from core.cli.cli_prompt import ask_choice, wait_enter
from core.cli.safe_editor import run_editor_on_file
from core.cli.flows.context.common import (
    delete_state_json_on_accept,
    find_context_md,
    full_context_cleanup,
    graphrag_drop,
)
from core.cli.nav import NavToMain
from core.cli.state import load_context_state, log_system_action, update_context_state
from core.cli.workflow.runtime import session as ws
from core.cli.workflow.runtime.runner import resume_workflow
from core.cli.chrome.ui import PASTEL_BLUE, PASTEL_CYAN, clear_screen, console, print_header
from core.cli.choice_lists import context_viewer_choices
from core.domain.delta_brief import is_no_context


def show_context(project_root: str, start_runner: Callable[[str], None]) -> None:
    clear_screen()
    print_header("📄 CONTEXT.MD VIEWER")
    state = load_context_state()
    if state.get("status") in ("completed", "deleted"):
        console.print("[dim]Không có context active.[/dim]")
        wait_enter()
        clear_screen()
        return
    ctx = find_context_md(project_root)
    if not ctx:
        console.print(
            Panel(
                f"[yellow]⚠️  Chưa có context.md nào.[/yellow]\n\nChạy [bold {PASTEL_CYAN}]start[/bold {PASTEL_CYAN}] để tạo task trước.",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        console.print()
        wait_enter()
        clear_screen()
        return
    if is_no_context(ctx):
        console.print(
            Panel(
                "[bold red]⚠️  context.md là NO_CONTEXT sentinel.[/bold red]\n\n"
                "Leader agent đã fail. Chạy lại task hoặc kiểm tra API key / model.",
                border_style="red",
                padding=(1, 2),
            )
        )
        console.print()
        wait_enter()
        clear_screen()
        return
    if ws.is_paused_for_review():
        console.print(
            Panel(
                "[bold yellow]Workflow LangGraph đang tạm dừng trước human gate.[/bold yellow]\n"
                "• [bold]back[/bold]: thoát viewer, giữ pause gate (không resume).\n"
                "• [bold]run[/bold]: chấp nhận và xóa context như luồng cũ.\n"
                "• Monitor Textual (workflow) chỉ đọc checkpoint — resume do CLI thực hiện.",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        console.print()
    content = ctx.read_text(encoding="utf-8")
    lines = content.splitlines()
    console.print(f"[{PASTEL_CYAN}]📁 {ctx}[/{PASTEL_CYAN}]  [dim]{len(lines)} lines[/dim]")
    console.print()
    display = "\n".join(lines[:150])
    if len(lines) > 150:
        display += f"\n\n[dim]... ({len(lines)-150} lines không hiển thị — mở file để đọc đầy đủ)[/dim]"
    console.print(Panel(Markdown(display), title=f"[bold {PASTEL_CYAN}]context.md[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, padding=(1, 2), box=ROUNDED))
    console.print()
    while True:
        console.print(
            f"[{PASTEL_CYAN}]Tùy chọn:[/{PASTEL_CYAN}] [bold]back[/bold] | [bold]edit[/bold] | [bold red]delete[/bold red] | "
            f"[bold green]run[/bold green] | [bold]regenerate[/bold] | [bold]exit[/bold] (về menu chính)"
        )
        choice = ask_choice("Chọn", context_viewer_choices(), default="back")
        if choice == "exit":
            clear_screen()
            raise NavToMain
        if choice == "back":
            if ws.is_paused_for_review():
                ws.set_should_finalize(False)
                ws.set_context_accept_status("deferred")
                ws.set_pipeline_paused_at_gate(True)
                ws.set_phase_paused_gate()
            clear_screen()
            return
        if choice == "edit":
            console.print(f"[dim]Mở editor {ctx} ...[/dim]")
            run_editor_on_file(ctx)
            clear_screen()
            print_header("📄 CONTEXT.MD VIEWER")
            content = ctx.read_text(encoding="utf-8")
            lines = content.splitlines()
            display = "\n".join(lines[:150])
            if len(lines) > 150:
                display += f"\n\n[dim]... ({len(lines)-150} lines không hiển thị — mở file để đọc đầy đủ)[/dim]"
            console.print(Panel(Markdown(display), title=f"[bold {PASTEL_CYAN}]context.md[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, padding=(1, 2), box=ROUNDED))
            console.print()
            continue
        if choice == "delete":
            try:
                full_context_cleanup(ctx, reason="deleted")
                console.print("[green]✓ Đã xóa context.md.[/green]")
            except (OSError, ValueError, TypeError) as e:
                console.print(f"[red]Không thể xóa context.md: {e}[/red]")
            wait_enter()
            clear_screen()
            return
        if choice == "run":
            try:
                graphrag_drop(ctx)
                ctx.unlink(missing_ok=True)
            except OSError as e:
                console.print(f"[red]Không thể xóa context.md: {e}[/red]")
            delete_state_json_on_accept(ctx)
            update_context_state("completed", ctx, reason="run_from_check")
            log_system_action("context.run", str(ctx))
            console.print("[green]✅ Context đã được Accept và workflow được thực thi.[/green]")
            if ws.is_paused_for_review():
                ws.set_should_finalize(True)
                ws.set_context_accept_status("accepted")
                resume_workflow()
            wait_enter()
            clear_screen()
            return
        if choice == "regenerate":
            try:
                graphrag_drop(ctx)
                ctx.unlink(missing_ok=True)
            except OSError as e:
                console.print(f"[red]Không thể xóa context.md: {e}[/red]")
            update_context_state("deleted", ctx, reason="regenerate_from_check")
            log_system_action("context.delete", f"{ctx} reason=regenerate_from_check")
            if ws.is_paused_for_review():
                ws.set_paused_for_review(False)
            prompt = Prompt.ask(f"[{PASTEL_CYAN}]📝 Nhập task để generate context mới[/{PASTEL_CYAN}]")
            pt = (prompt or "").strip()
            pl = pt.lower()
            if pl == "exit":
                raise NavToMain
            if pl == "back":
                clear_screen()
                return
            if pt:
                start_runner(pt)
            clear_screen()
            return


__all__ = ["show_context"]

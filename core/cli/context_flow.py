from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Callable, Literal, Optional

ContextConfirmResult = Literal["accept", "regenerate", "back", "delete"]

from rich.box import ROUNDED
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from core.cli.cli_prompt import ask_choice
from core.cli.state import load_context_state, log_system_action, update_context_state
from core.cli.workflow import session as ws
from core.cli.workflow.activity_log import clear_workflow_activity_log
from core.cli.workflow.runner import resume_workflow
from core.cli.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, BRIGHT_BLUE, clear_screen, console, print_divider, print_header
from core.cli.choice_lists import context_viewer_choices
from core.config import config
from utils.delta_brief import STATE_FILENAME
from utils.delta_brief import is_no_context
from utils.file_manager import latest_context_path, paths_for_task
from utils.logger import log_state_json_deleted_on_accept


def _graphrag_drop(context_path: Path) -> None:
    try:
        from core.storage.graphrag_store import delete_by_context_path

        delete_by_context_path(context_path)
    except ImportError:
        return
    except OSError:
        return


def find_context_md(project_root: str) -> Optional[Path]:
    latest_ctx = latest_context_path()
    if latest_ctx and latest_ctx.exists():
        return latest_ctx
    candidates = [
        config.BASE_DIR / "context.md",
        config.BASE_DIR / "data" / "context.md",
        Path(project_root).parent / "test" / "context.md",
        Path(project_root).parent / "context.md",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _state_path_for_context(context_path: Path) -> Path | None:
    state = load_context_state()
    task_uuid = str(state.get("task_uuid") or "").strip()
    if task_uuid:
        return paths_for_task(task_uuid).state_path
    candidate = context_path.parent / STATE_FILENAME
    if candidate.exists():
        return candidate
    return None


def _delete_state_json_on_accept(context_path: Path) -> None:
    state_path = _state_path_for_context(context_path)
    if not state_path:
        return
    try:
        state_path.unlink(missing_ok=True)
    except (ImportError, OSError, ValueError, TypeError):
        return
    log_state_json_deleted_on_accept(state_path)


def delete_state_json_for_context(context_path: Path) -> None:
    state_path = _state_path_for_context(context_path)
    if not state_path:
        return
    try:
        state_path.unlink(missing_ok=True)
    except (OSError, ValueError, TypeError):
        return


def _full_context_cleanup(context_path: Path, *, reason: str = "deleted") -> None:
    """Delete context.md + state.json, reset activity log and workflow session."""
    _graphrag_drop(context_path)
    try:
        context_path.unlink(missing_ok=True)
    except OSError:
        pass
    delete_state_json_for_context(context_path)
    update_context_state(reason, context_path, reason=reason)
    log_system_action("context.delete", f"{context_path} reason={reason}")
    clear_workflow_activity_log()
    ws.reset_pipeline_visual()
    ws.set_paused_for_review(False)
    ws.set_should_finalize(False)


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
            return "back"
        if choice == "a":
            console.print("[bold green]✅ Accepted — pipeline tiếp tục.[/bold green]")
            time.sleep(0.8)
            return "accept"
        if choice == "e":
            editor = os.environ.get("EDITOR", "notepad" if os.name == "nt" else "nano")
            console.print(f"[dim]Mở {editor} {context_path} ...[/dim]")
            subprocess.run([editor, str(context_path)], check=False)
            console.print(f"[{PASTEL_CYAN}]File đã được lưu. Xem lại...[/{PASTEL_CYAN}]")
            time.sleep(0.5)
            return confirm_context(context_path)
        if choice == "r":
            console.print(f"[{PASTEL_LAVENDER}]🔄 Regenerate requested.[/{PASTEL_LAVENDER}]")
            try:
                _graphrag_drop(context_path)
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
                _full_context_cleanup(context_path, reason="deleted")
                console.print("[green]✓ Đã xóa context.md.[/green]")
            except (OSError, ValueError, TypeError) as e:
                console.print(f"[red]Không thể xóa: {e}[/red]")
            time.sleep(0.6)
            return "delete"


def show_context(project_root: str, start_runner: Callable[[str], None]):
    clear_screen()
    print_header("📄 CONTEXT.MD VIEWER")
    state = load_context_state()
    if state.get("status") in ("completed", "deleted"):
        console.print("[dim]Không có context active.[/dim]")
        input("[dim]Enter[/dim]")
        clear_screen()
        return
    ctx = find_context_md(project_root)
    if not ctx:
        console.print(Panel(f"[yellow]⚠️  Chưa có context.md nào.[/yellow]\n\nChạy [bold {PASTEL_CYAN}]start[/bold {PASTEL_CYAN}] để tạo task trước.", border_style="yellow", padding=(1, 2)))
        console.print()
        input("[dim]Enter[/dim]")
        clear_screen()
        return
    if is_no_context(ctx):
        console.print(Panel("[bold red]⚠️  context.md là NO_CONTEXT sentinel.[/bold red]\n\nLeader agent đã fail. Chạy lại task hoặc kiểm tra API key / model.", border_style="red", padding=(1, 2)))
        console.print()
        input("[dim]Enter[/dim]")
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
            return
        if choice == "back":
            if ws.is_paused_for_review():
                ws.set_should_finalize(False)
                ws.set_context_accept_status("deferred")
                ws.set_pipeline_paused_at_gate(True)
                ws.set_phase_paused_gate()
            clear_screen()
            return
        if choice == "edit":
            editor = os.environ.get("EDITOR", "notepad" if os.name == "nt" else "nano")
            console.print(f"[dim]Mở {editor} {ctx} ...[/dim]")
            subprocess.run([editor, str(ctx)], check=False)
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
                _full_context_cleanup(ctx, reason="deleted")
                console.print("[green]✓ Đã xóa context.md.[/green]")
            except (OSError, ValueError, TypeError) as e:
                console.print(f"[red]Không thể xóa context.md: {e}[/red]")
            input("[dim]Enter[/dim]")
            clear_screen()
            return
        if choice == "run":
            try:
                _graphrag_drop(ctx)
                ctx.unlink(missing_ok=True)
            except OSError as e:
                console.print(f"[red]Không thể xóa context.md: {e}[/red]")
            _delete_state_json_on_accept(ctx)
            update_context_state("completed", ctx, reason="run_from_check")
            log_system_action("context.run", str(ctx))
            console.print("[green]✅ Context đã được Accept và workflow được thực thi.[/green]")
            if ws.is_paused_for_review():
                ws.set_should_finalize(True)
                ws.set_context_accept_status("accepted")
                resume_workflow()
            input("[dim]Enter[/dim]")
            clear_screen()
            return
        if choice == "regenerate":
            try:
                _graphrag_drop(ctx)
                ctx.unlink(missing_ok=True)
            except OSError as e:
                console.print(f"[red]Không thể xóa context.md: {e}[/red]")
            update_context_state("deleted", ctx, reason="regenerate_from_check")
            log_system_action("context.delete", f"{ctx} reason=regenerate_from_check")
            if ws.is_paused_for_review():
                ws.set_paused_for_review(False)
            prompt = Prompt.ask(f"[{PASTEL_CYAN}]📝 Nhập task để generate context mới[/{PASTEL_CYAN}]")
            if prompt.strip():
                start_runner(prompt.strip())
            clear_screen()
            return


def apply_context_accept_from_monitor(project_root: str) -> bool:
    """Giống check → run: xóa file, completed state, resume graph nếu đang pause."""
    ctx = find_context_md(project_root)
    if not ctx or is_no_context(ctx):
        return False
    try:
        _graphrag_drop(ctx)
        ctx.unlink(missing_ok=True)
    except OSError:
        return False
    _delete_state_json_on_accept(ctx)
    update_context_state("completed", ctx, reason="accept_from_monitor")
    log_system_action("context.accept_monitor", str(ctx))
    if ws.is_paused_for_review():
        ws.set_should_finalize(True)
        ws.set_context_accept_status("accepted")
        return bool(resume_workflow())
    return True


def apply_context_back_from_monitor(project_root: str) -> None:
    """Giống check → back: defer review, giữ pause gate."""
    ctx = find_context_md(project_root)
    if ctx:
        update_context_state("active", ctx, reason="review_deferred_monitor")
        log_system_action("context.review.back_monitor", str(ctx))
    if ws.is_paused_for_review():
        ws.set_should_finalize(False)
        ws.set_context_accept_status("deferred")
        ws.set_pipeline_paused_at_gate(True)
        ws.set_phase_paused_gate()


def apply_context_delete_from_monitor(project_root: str) -> bool:
    ctx = find_context_md(project_root)
    if not ctx:
        return False
    _full_context_cleanup(ctx, reason="delete_from_monitor")
    return True


def apply_context_prepare_regenerate(project_root: str) -> None:
    """Xóa context và reset session trước khi start/regenerate mới (payload prompt do drain xử lý)."""
    ctx = find_context_md(project_root)
    if ctx:
        _full_context_cleanup(ctx, reason="regenerate_from_monitor_prep")
    else:
        if ws.is_paused_for_review():
            ws.set_paused_for_review(False)
        clear_workflow_activity_log()
        ws.reset_pipeline_visual()


__all__ = [
    "find_context_md",
    "is_no_context",
    "confirm_context",
    "show_context",
    "ContextConfirmResult",
    "delete_state_json_for_context",
    "apply_context_accept_from_monitor",
    "apply_context_back_from_monitor",
    "apply_context_delete_from_monitor",
    "apply_context_prepare_regenerate",
]

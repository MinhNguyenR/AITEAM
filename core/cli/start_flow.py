from __future__ import annotations

from typing import Callable

from rich.box import ROUNDED
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from core.cli.ask_flow import _pick_chat_on_ask_entry, looks_like_code_intent
from core.cli.cli_prompt import ask_choice
from core.cli.context_flow import apply_context_accept_from_monitor, confirm_context, delete_state_json_for_context, find_context_md
from core.cli.choice_lists import start_mode_choices
from core.cli.state import get_cli_settings, log_system_action
from core.cli.workflow import session as ws_session
from core.cli.workflow.activity_log import clear_workflow_activity_log, list_recent_activity
from core.pipeline_state import write_task_state_json
from core.cli.workflow.runner import run_agent_graph
from core.cli.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, console
from utils.file_manager import paths_for_task
from utils.logger import workflow_event


def _looks_like_chat_intent(text: str) -> bool:
    t = text.lower().strip()
    if looks_like_code_intent(text):
        return False
    mode_like = {"agent", "ask", "chat", "help", "menu", "start"}
    if t in mode_like:
        return True
    chat_keys = ["là gì", "what is", "explain", "giải thích", "tại sao", "how", "why", "when", "where", "who", "?"]
    if any(k in t for k in chat_keys):
        return True
    code_markers = [".py", "/", "\\", "def ", "class ", "function", "error:", "traceback"]
    words = [w for w in t.split() if w]
    if len(words) <= 2 and not any(m in t for m in code_markers):
        return True
    return False


def _cleanup_declined_context(brief, project_root: str) -> None:
    ctx = find_context_md(project_root)
    if ctx and ctx.exists():
        try:
            ctx.unlink(missing_ok=True)
        except OSError:
            pass
        delete_state_json_for_context(ctx)
    else:
        try:
            paths_for_task(brief.task_uuid).state_path.unlink(missing_ok=True)
        except OSError:
            pass
    clear_workflow_activity_log()
    ws_session.reset_pipeline_visual()
    ws_session.set_paused_for_review(False)
    try:
        ws_session.set_should_finalize(False)
    except AttributeError:
        pass
    log_system_action("context.decline.cleanup", f"task_uuid={brief.task_uuid}")


def run_start(
    prompt: str,
    run_ask_mode_cb: Callable[..., None],
    project_root: str,
    *,
    regenerate_prelude: str | None = None,
):
    log_system_action("start.enter", (prompt or "")[:200])
    console.print(f"[{PASTEL_CYAN}]Mode:[/{PASTEL_CYAN}] ask | agent | back | exit")
    mode = ask_choice("Chọn mode", start_mode_choices(), default="agent")
    log_system_action("mode.select", mode)
    if mode == "back":
        return
    if mode == "exit":
        return
    if mode == "ask":
        run_ask_mode_cb((prompt or "").strip(), False)
        return

    p = (prompt or "").strip()
    if not p:
        try:
            p = Prompt.ask(f"[{PASTEL_CYAN}]📝 Nhập task[/{PASTEL_CYAN}]").strip()
        except (KeyboardInterrupt, EOFError):
            return
    if not p:
        console.print("[yellow]Bỏ qua — chưa có task.[/yellow]")
        return
    pl = p.lower()
    if pl == "exit":
        return
    if pl == "back":
        return

    is_code = looks_like_code_intent(p)
    is_question = _looks_like_chat_intent(p)

    if mode == "agent" and is_question and not is_code:
        try:
            from utils import tracker as _tr

            _tr.append_cli_batch("ask", p[:220])
        except (ImportError, OSError, ValueError):
            pass
        run_ask_mode_cb(p, True)
        return

    if mode == "ask":
        if is_code:
            console.print(
                Panel(
                    "[yellow]Ask không chạy agent hay repo; chỉ giải thích / gợi ý. "
                    "Không khẳng định đã sửa file hay chạy công cụ trên disk.[/yellow]",
                    border_style="yellow",
                    box=ROUNDED,
                )
            )
        from utils import ask_history as ah

        store = ah.load_store()
        pick = _pick_chat_on_ask_entry(store, False)
        if pick == "back":
            ah.save_store(store)
            return
        ah.save_store(store)
        run_ask_mode_cb(p, False, skip_entry_pick=True, explain_only=is_code)
        return

    try:
        from utils import tracker as _tr

        _tr.append_cli_batch("agent", p[:220])
    except (ImportError, OSError, ValueError):
        pass
    ws_session.reset_pipeline_visual()
    if regenerate_prelude:
        workflow_event("cli", "regenerate_started", regenerate_prelude[:400])
    try:
        from agents.ambassador import Ambassador

        ambassador = Ambassador()
    except ImportError as e:
        console.print(f"[bold red]❌ Import error: {e}[/bold red]")
        input("[dim]Enter để quay lại...[/dim]")
        return
    ws_session.set_pipeline_ambassador_status("running")
    workflow_event("ambassador", "enter", "parse task")
    ws_session.set_pipeline_status_message("Ambassador đang phân tích task…")
    with console.status(f"[{PASTEL_BLUE}]🔍 Phân tích task...[/{PASTEL_BLUE}]"):
        try:
            brief = ambassador.parse(p)
            log_system_action("ambassador.parse", f"tier={getattr(brief, 'tier', 'unknown')} model={getattr(brief, 'target_model', '')}")
        except (OSError, RuntimeError, ValueError, TypeError) as e:
            ws_session.set_pipeline_ambassador_error()
            console.print(f"[bold red]❌ Ambassador error: {e}[/bold red]")
            input("[dim]Enter để quay lại...[/dim]")
            return
    ws_session.set_pipeline_after_ambassador(brief)
    workflow_event("ambassador", "done", f"tier={brief.tier}")
    write_task_state_json(brief, p, project_root, source_node="ambassador")
    max_regenerate = 3
    flow_outcome: str | None = None
    settings = get_cli_settings()
    inline_progress = True
    for attempt in range(1, max_regenerate + 1):
        if attempt > 1:
            console.print(f"[{PASTEL_LAVENDER}]🔄 Regenerate attempt {attempt}/{max_regenerate}...[/{PASTEL_LAVENDER}]")
        outcome = run_agent_graph(
            brief,
            p,
            project_root,
            settings,
            inline_progress=inline_progress,
        )
        log_system_action("leader.run", f"attempt={attempt} outcome={outcome}")
        if outcome == "completed":
            flow_outcome = "accept"
            break
        if outcome == "paused":
            ctx = find_context_md(project_root)
            if not ctx or not ctx.exists():
                flow_outcome = "paused"
                break
            decision = confirm_context(ctx)
            if decision == "accept":
                if apply_context_accept_from_monitor(project_root):
                    flow_outcome = "accept"
                else:
                    flow_outcome = "paused"
                break
            if decision == "regenerate":
                ws_session.set_paused_for_review(False)
                ws_session.set_pipeline_paused_at_gate(False)
                continue
            remake = Confirm.ask(f"[{PASTEL_CYAN}]Context bị decline. Tạo lại context mới?[/{PASTEL_CYAN}]", default=True)
            if remake:
                _cleanup_declined_context(brief, project_root)
                continue
            _cleanup_declined_context(brief, project_root)
            flow_outcome = "declined"
            break
        if outcome == "failed":
            recent = list_recent_activity(limit=60, min_ts=ws_session.get_workflow_activity_min_ts() or None)
            fail_records = [
                r for r in recent if str(r.get("action", "")).lower() in {"failed", "leader_generate_failed", "graph_error"}
            ]
            if fail_records:
                last_fail = fail_records[-1]
                console.print(
                    f"[red]Lỗi node:[/red] {last_fail.get('node','?')} "
                    f"[red]action:[/red] {last_fail.get('action','?')} "
                    f"[dim]{last_fail.get('detail','')}[/dim]"
                )
            if attempt < max_regenerate:
                retry = Confirm.ask(f"[{PASTEL_CYAN}]Leader/Expert fail. Thử lại?[/{PASTEL_CYAN}]", default=True)
                if not retry:
                    break
            continue
    if flow_outcome == "accept":
        console.print()
        console.print(
            Panel(
                "[bold green]✅ Pipeline Phase 0-1 hoàn tất![/bold green]\n\ncontext.md đã hoàn thành và được dọn dẹp.\n[dim]Lịch sử vẫn còn trong actions.log.[/dim]",
                border_style="green",
                padding=(1, 2),
                box=ROUNDED,
            )
        )
    elif flow_outcome == "paused":
        pass
    elif flow_outcome == "declined":
        console.print(
            Panel(
                "[yellow]Context đã bị decline. state.json và log Ambassador của run hiện tại đã được dọn.[/yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
    else:
        console.print(
            Panel(
                "[yellow]⚠️  Không tạo được context.md sau nhiều lần thử.[/yellow]\nKiểm tra API key, model availability, hoặc thử đơn giản hóa task.",
                border_style="yellow",
                padding=(1, 2),
            )
        )
    return


__all__ = ["run_start"]

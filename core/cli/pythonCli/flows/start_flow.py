from __future__ import annotations

import sys
import threading
from typing import Callable

from rich.box import ROUNDED
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from core.cli.pythonCli.flows.ask_flow import _pick_chat_on_ask_entry, looks_like_code_intent
from core.cli.pythonCli.cli_prompt import ask_choice, wait_enter
from core.cli.pythonCli.flows.context_flow import apply_context_accept_from_monitor, confirm_context, delete_state_json_for_context, find_context_md
from core.cli.pythonCli.choice_lists import start_mode_choices
from core.cli.pythonCli.command_registry import START_MODE_BY_NUMBER
from core.cli.pythonCli.nav import NavToMain
from core.cli.pythonCli.state import get_cli_settings, log_system_action
from core.cli.pythonCli.workflow.runtime import session as ws_session
from core.cli.pythonCli.workflow.runtime.activity_log import list_recent_activity
from core.cli.pythonCli.workflow.tui.display_policy import resolve_display_policy
from core.domain.pipeline_state import write_task_state_json
from core.cli.pythonCli.workflow.runtime.runner import run_agent_graph
from core.cli.pythonCli.chrome.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, console
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


def _consume_gate_decision_from_queue(project_root: str) -> str | None:
    pending = ws_session.drain_monitor_command_queue()
    decision: str | None = None
    leftover: list = []
    for c in pending:
        act = str(c.get("action") or "")
        if act == "context_accept" and decision is None:
            decision = "accept"
        elif act == "context_back" and decision is None:
            decision = "back"
        elif act == "context_delete" and decision is None:
            decision = "delete"
        elif act == "context_regenerate" and decision is None:
            decision = "regenerate"
        elif act in ("btw_note", "new_task"):
            pass
        else:
            leftover.append(c)
    for c in leftover:
        ws_session.enqueue_monitor_command(str(c.get("action")), c.get("payload") or {})
    return decision


def _consume_new_task_from_queue() -> str | None:
    pending = ws_session.drain_monitor_command_queue()
    new_task_prompt: str | None = None
    leftover: list = []
    for c in pending:
        act = str(c.get("action") or "")
        if act == "start_workflow" and new_task_prompt is None:
            new_task_prompt = str((c.get("payload") or {}).get("prompt") or "").strip()
        else:
            leftover.append(c)
    for c in leftover:
        ws_session.enqueue_monitor_command(str(c.get("action")), c.get("payload") or {})
    return new_task_prompt or None


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
    ws_session.reset_pipeline_visual()
    ws_session.set_paused_for_review(False)
    try:
        ws_session.set_should_finalize(False)
    except AttributeError:
        pass
    log_system_action("context.decline.cleanup", f"task_uuid={brief.task_uuid}")


# ── TUI background pipeline launcher ──────────────────────────────────────────

def start_pipeline_from_tui(task_text: str, project_root: str, mode: str = "agent") -> None:
    """Start ambassador + pipeline in a daemon thread while the Textual TUI stays open.

    Communicates via ws_session state only — no console output (TUI owns terminal).
    """
    if not task_text.strip():
        return

    def _run() -> None:
        ws_session.clear_pipeline_stop()   # always clear before a new run
        ws_session.set_pipeline_run_finished(False)
        ws_session.reset_pipeline_visual()

        try:
            from agents.ambassador import Ambassador
            ambassador = Ambassador()
        except ImportError as exc:
            ws_session.set_pipeline_ambassador_error()
            workflow_event("ambassador", "failed", f"import_error: {exc}")
            ws_session.set_pipeline_run_finished(True)
            return

        ws_session.set_pipeline_ambassador_status("running")
        workflow_event("ambassador", "enter", "parse task")
        ws_session.set_pipeline_status_message("Ambassador parsing task…")

        try:
            brief = ambassador.parse(task_text)
        except Exception as exc:
            ws_session.set_pipeline_ambassador_error()
            workflow_event("ambassador", "failed", str(exc)[:200])
            ws_session.set_pipeline_run_finished(True)
            return

        ws_session.set_pipeline_after_ambassador(brief)
        workflow_event("ambassador", "done", f"tier={brief.tier}")
        amb_usage = getattr(ambassador, "last_usage_event", {}) or {}
        if amb_usage:
            workflow_event(
                "ambassador", "usage",
                (
                    f"model={amb_usage.get('model','')} "
                    f"prompt_tokens={amb_usage.get('prompt_tokens',0)} "
                    f"completion_tokens={amb_usage.get('completion_tokens',0)} "
                    f"total_tokens={amb_usage.get('total_tokens',0)} "
                    f"cost_usd={amb_usage.get('cost_usd',0.0)}"
                ),
            )

        settings = get_cli_settings()
        write_task_state_json(brief, task_text, project_root, source_node="ambassador")
        try:
            from utils import tracker as _tr
            _tr.append_cli_batch("agent", task_text[:220])
        except (ImportError, OSError, ValueError):
            pass

        try:
            run_agent_graph(brief, task_text, project_root, settings, inline_progress=False)
        except Exception:
            pass
        finally:
            ws_session.set_pipeline_run_finished(True)

    threading.Thread(target=_run, daemon=True).start()


# ── Phase helpers ──────────────────────────────────────────────────────────────

def _classify_task(prompt: str, run_ask_mode_cb: Callable, project_root: str, *, force_mode: str | None = None) -> tuple[str, str] | None:
    """Return (mode, prompt_text) or None if the user wants to exit."""
    log_system_action("start.enter", (prompt or "")[:200])

    if force_mode:
        mode = force_mode.lower()
        if mode not in ("ask", "agent"):
            mode = "agent"
        log_system_action("mode.forced", mode)
        p = (prompt or "").strip()
        if not p:
            return None
        if mode == "ask":
            run_ask_mode_cb(p, False)
            return None
        # Auto-detect questions even in forced-agent mode
        if _looks_like_chat_intent(p) and not looks_like_code_intent(p):
            try:
                from utils import tracker as _tr
                _tr.append_cli_batch("ask", p[:220])
            except (ImportError, OSError, ValueError):
                pass
            run_ask_mode_cb(p, True)
            return None
        try:
            from utils import tracker as _tr
            _tr.append_cli_batch("agent", p[:220])
        except (ImportError, OSError, ValueError):
            pass
        return mode, p

    console.print(f"[{PASTEL_CYAN}]Mode:[/{PASTEL_CYAN}] ask | agent")
    mode = ask_choice("Chọn mode", start_mode_choices(), default="agent", number_map=START_MODE_BY_NUMBER)
    log_system_action("mode.select", mode)
    if mode in ("back", "exit"):
        return None
    if mode == "ask":
        run_ask_mode_cb((prompt or "").strip(), False)
        return None

    p = (prompt or "").strip()
    if not p:
        try:
            p = Prompt.ask(f"[{PASTEL_CYAN}]📝 Nhập task[/{PASTEL_CYAN}]").strip()
        except (KeyboardInterrupt, EOFError):
            return None
    if not p:
        console.print("[yellow]Bỏ qua — chưa có task.[/yellow]")
        return None
    pl = p.lower()
    if pl == "exit":
        raise NavToMain
    if pl == "back":
        return None

    is_code = looks_like_code_intent(p)
    is_question = _looks_like_chat_intent(p)

    if mode == "agent" and is_question and not is_code:
        try:
            from utils import tracker as _tr
            _tr.append_cli_batch("ask", p[:220])
        except (ImportError, OSError, ValueError):
            pass
        run_ask_mode_cb(p, True)
        return None

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
        from core.storage import ask_history as ah
        store = ah.load_store()
        pick = _pick_chat_on_ask_entry(store, False)
        if pick == "back":
            ah.save_store(store)
            return None
        ah.save_store(store)
        run_ask_mode_cb(p, False, skip_entry_pick=True, explain_only=is_code)
        return None

    try:
        from utils import tracker as _tr
        _tr.append_cli_batch("agent", p[:220])
    except (ImportError, OSError, ValueError):
        pass
    return mode, p


def _run_ambassador(p: str):
    """Run Ambassador classification. Returns brief or None on failure."""
    ws_session.reset_pipeline_visual()
    try:
        from agents.ambassador import Ambassador
        ambassador = Ambassador()
    except ImportError as e:
        console.print(f"[bold red]❌ Import error: {e}[/bold red]")
        wait_enter("Nhấn Enter để quay lại...")
        return None
    ws_session.set_pipeline_ambassador_status("running")
    workflow_event("ambassador", "enter", "parse task")
    ws_session.set_pipeline_status_message("Ambassador đang phân tích task…")
    with console.status(f"[{PASTEL_BLUE}]🔍 Phân tích task...[/{PASTEL_BLUE}]"):
        try:
            brief = ambassador.parse(p)
            log_system_action("ambassador.parse", f"tier={getattr(brief, 'tier', 'unknown')} model={getattr(brief, 'target_model', '')}")
        except KeyboardInterrupt:
            ws_session.set_pipeline_ambassador_error()
            workflow_event("ambassador", "interrupted", "KeyboardInterrupt")
            console.print("[yellow]Đã dừng Ambassador (Ctrl+C).[/yellow]")
            try:
                from utils import tracker as _tr
                _tr.append_cli_batch("agent", f"[interrupted] {p[:200]}")
            except (ImportError, OSError, ValueError):
                pass
            return None
        except (OSError, RuntimeError, ValueError, TypeError) as e:
            ws_session.set_pipeline_ambassador_error()
            console.print(f"[bold red]❌ Ambassador error: {e}[/bold red]")
            wait_enter("Nhấn Enter để quay lại...")
            return None
    ws_session.set_pipeline_after_ambassador(brief)
    workflow_event("ambassador", "done", f"tier={brief.tier}")
    amb_usage = getattr(ambassador, "last_usage_event", {}) or {}
    if amb_usage:
        workflow_event(
            "ambassador", "usage",
            (
                f"model={amb_usage.get('model','')} "
                f"prompt_tokens={amb_usage.get('prompt_tokens',0)} "
                f"completion_tokens={amb_usage.get('completion_tokens',0)} "
                f"total_tokens={amb_usage.get('total_tokens',0)} "
                f"cost_usd={amb_usage.get('cost_usd',0.0)}"
            ),
        )
    return brief


def _run_pipeline_attempt(brief, p: str, project_root: str, settings: dict, view_mode: str) -> str:
    """Spawn pipeline thread + TUI, return outcome string."""
    ws_session.set_pipeline_run_finished(False)
    _attempt_result: dict = {"outcome": None}

    def _run(_r=_attempt_result) -> None:
        try:
            out = run_agent_graph(brief, p, project_root, settings, inline_progress=False)
            _r["outcome"] = out
        except Exception:
            _r["outcome"] = "failed"
        finally:
            ws_session.set_pipeline_run_finished(True)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    try:
        if view_mode == "list":
            from core.cli.pythonCli.workflow.tui.list_view import run_workflow_list_view
            run_workflow_list_view(project_root)
        else:
            from core.cli.pythonCli.workflow.tui.monitor_app import WorkflowMonitorApp
            WorkflowMonitorApp(view_mode=view_mode).run()
    finally:
        try:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()
        except OSError:
            pass
    t.join(timeout=3.0)
    if t.is_alive():
        return "user_exit"
    return _attempt_result.get("outcome") or "failed"


def _approval_gate(ctx, brief, project_root: str, settings: dict, attempt: int, max_regenerate: int) -> tuple[str, str | None]:
    """Handle the human review gate. Returns ("continue"|"break", flow_outcome)."""
    decision = _consume_gate_decision_from_queue(project_root)
    if decision is None:
        decision = confirm_context(ctx)
    if decision == "accept":
        flow = "accept" if apply_context_accept_from_monitor(project_root) else "paused"
        return "break", flow
    if decision == "regenerate":
        ws_session.set_paused_for_review(False)
        ws_session.set_pipeline_paused_at_gate(False)
        return "continue", None
    if decision == "back":
        return "break", "paused"
    if decision == "delete":
        from core.cli.pythonCli.flows.context.monitor_actions import apply_context_delete_from_monitor
        apply_context_delete_from_monitor(project_root)
        auto_action = str(settings.get("auto_context_action", "ask")).lower()
        if auto_action == "accept":
            ws_session.set_paused_for_review(False)
            ws_session.reset_pipeline_visual()
            return "continue", None
        if auto_action == "decline":
            return "break", "declined"
        regen = Confirm.ask(f"[{PASTEL_CYAN}]Generate lại context mới?[/{PASTEL_CYAN}]", default=True)
        if regen:
            ws_session.set_paused_for_review(False)
            ws_session.reset_pipeline_visual()
            return "continue", None
        return "break", "declined"
    remake = Confirm.ask(f"[{PASTEL_CYAN}]Context bị decline. Tạo lại context mới?[/{PASTEL_CYAN}]", default=True)
    if remake:
        _cleanup_declined_context(brief, project_root)
        return "continue", None
    _cleanup_declined_context(brief, project_root)
    return "break", "declined"


def _generate_context(brief, p: str, project_root: str, settings: dict) -> str | None:
    """Pipeline retry loop. Returns final flow_outcome."""
    policy = resolve_display_policy(settings)
    view_mode = policy.view_mode
    ws_session.set_workflow_last_view_mode(view_mode)
    max_regenerate = 3
    flow_outcome: str | None = None
    _fail_count = 0

    for attempt in range(1, max_regenerate + 1):
        if attempt > 1:
            console.print(f"[{PASTEL_LAVENDER}]🔄 Regenerate attempt {attempt}/{max_regenerate}...[/{PASTEL_LAVENDER}]")
        outcome = _run_pipeline_attempt(brief, p, project_root, settings, view_mode)
        log_system_action("leader.run", f"attempt={attempt} outcome={outcome}")

        if outcome == "user_exit":
            next_task = _consume_new_task_from_queue()
            if next_task:
                log_system_action("leader.run", f"new_task queued: {next_task[:100]}")
                return "user_exit:" + next_task
            return None

        if outcome == "completed":
            flow_outcome = "accept"
            break

        if outcome == "paused":
            ctx = find_context_md(project_root)
            if not ctx or not ctx.exists():
                flow_outcome = "paused"
                break
            ctrl, flow_outcome = _approval_gate(ctx, brief, project_root, settings, attempt, max_regenerate)
            if ctrl == "break":
                break
            continue

        if outcome == "failed":
            _fail_count += 1
            recent = list_recent_activity(limit=60, min_ts=ws_session.get_workflow_activity_min_ts() or None)
            fail_records = [r for r in recent if str(r.get("action", "")).lower() in {"failed", "leader_generate_failed", "graph_error", "interrupted"}]
            if fail_records:
                last_fail = fail_records[-1]
                console.print(
                    f"[red]Lỗi node:[/red] {last_fail.get('node','?')} "
                    f"[red]action:[/red] {last_fail.get('action','?')} "
                    f"[dim]{last_fail.get('detail','')}[/dim]"
                )
            if _fail_count == 1 and attempt < max_regenerate:
                console.print(f"[{PASTEL_LAVENDER}]🔄 Auto-retry ({attempt}/{max_regenerate})...[/{PASTEL_LAVENDER}]")
                ws_session.reset_pipeline_visual()
                continue
            console.print("[yellow]Đã hết lần thử — tự dọn dẹp state + logs.[/yellow]")
            _cleanup_declined_context(brief, project_root)
            flow_outcome = "failed_cleanup"
            break

    return flow_outcome


def _show_outcome_panel(flow_outcome: str | None) -> None:
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
    elif flow_outcome == "declined":
        console.print(
            Panel(
                "[yellow]Context đã bị decline. state.json và log Ambassador của run hiện tại đã được dọn.[/yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
    elif flow_outcome == "failed_cleanup":
        console.print(
            Panel(
                "[red]Pipeline thất bại sau khi tự retry.[/red]\nstate.json và logs đã được dọn dẹp tự động.\nKiểm tra API key, model availability, hoặc thử đơn giản hóa task.",
                border_style="red",
                padding=(1, 2),
                box=ROUNDED,
            )
        )
    elif flow_outcome not in ("paused", None):
        console.print(
            Panel(
                "[yellow]⚠️  Không tạo được context.md sau nhiều lần thử.[/yellow]\nKiểm tra API key, model availability, hoặc thử đơn giản hóa task.",
                border_style="yellow",
                padding=(1, 2),
            )
        )


# ── Entry point ────────────────────────────────────────────────────────────────

def run_start(
    prompt: str,
    run_ask_mode_cb: Callable[..., None],
    project_root: str,
    *,
    regenerate_prelude: str | None = None,
    force_mode: str | None = None,
):
    result = _classify_task(prompt, run_ask_mode_cb, project_root, force_mode=force_mode)
    if result is None:
        return
    _mode, p = result

    brief = _run_ambassador(p)
    if brief is None:
        return

    if regenerate_prelude:
        workflow_event("cli", "regenerate_started", regenerate_prelude[:400])

    settings = get_cli_settings()
    write_task_state_json(brief, p, project_root, source_node="ambassador")
    flow_outcome = _generate_context(brief, p, project_root, settings)

    if isinstance(flow_outcome, str) and flow_outcome.startswith("user_exit:"):
        next_task = flow_outcome[len("user_exit:"):]
        run_start(next_task, run_ask_mode_cb, project_root)
        return

    _show_outcome_panel(flow_outcome)

    queued_task = _consume_new_task_from_queue()
    if queued_task:
        log_system_action("task.queued.follow", queued_task[:100])
        run_start(queued_task, run_ask_mode_cb, project_root)


__all__ = ["run_start", "start_pipeline_from_tui"]

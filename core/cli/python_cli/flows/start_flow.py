"""start_flow.py — patched entry point: open TUI FIRST, ambassador runs inside.

Key change vs original:
  Original: _run_ambassador() in console → THEN open TUI
  New:      open TUI immediately → start_pipeline_from_tui() runs ambassador+graph in background

All other logic (ask mode, queue drain, outcomes) preserved.
"""
from __future__ import annotations

import logging
import sys
import threading
from typing import Callable

logger = logging.getLogger(__name__)

from rich.box import ROUNDED
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from core.cli.python_cli.flows.ask_flow import _pick_chat_on_ask_entry, looks_like_code_intent
from core.cli.python_cli.cli_prompt import ask_choice, wait_enter
from core.cli.python_cli.flows.context_flow import (
    apply_context_accept_from_monitor, confirm_context,
    delete_state_json_for_context, find_context_md,
)
from core.cli.python_cli.choice_lists import start_mode_choices
from core.cli.python_cli.command_registry import START_MODE_BY_NUMBER
from core.cli.python_cli.nav import NavToMain
from core.cli.python_cli.state import get_cli_settings, log_system_action
from core.cli.python_cli.workflow.runtime import session as ws_session
from core.cli.python_cli.workflow.runtime.activity_log import list_recent_activity
from core.cli.python_cli.workflow.tui.display_policy import resolve_display_policy
from core.domain.pipeline_state import write_task_state_json
from core.cli.python_cli.workflow.runtime.runner import run_agent_graph
from core.cli.python_cli.chrome.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, console
from utils.file_manager import paths_for_task
from utils.logger import workflow_event


def _looks_like_chat_intent(text: str) -> bool:
    t = text.lower().strip()
    if looks_like_code_intent(text):
        return False
    mode_like = {"agent", "ask", "chat", "help", "menu", "start"}
    if t in mode_like:
        return True
    chat_keys = ["là gì", "what is", "explain", "giải thích", "tại sao",
                 "how", "why", "when", "where", "who", "?"]
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
            payload = c.get("payload") or {}
            new_task_prompt = str(payload.get("prompt") or "").strip()
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




# ── Clarification helpers ─────────────────────────────────────────────────────

def _is_ambiguous_task(task_text: str) -> bool:
    """Heuristic: does this task need clarification before generation?"""
    words = task_text.strip().split()
    if len(words) > 15:
        return False  # Long tasks are usually specific enough
    text_lower = task_text.lower()
    # Tech-specific keywords = probably clear enough
    tech_clear = {
        "api", "rest", "graphql", "websocket", "cli", "script",
        "backend", "frontend", "fullstack", "monolith", "microservice",
        ".py", ".js", ".ts", "react", "vue", "angular", "svelte",
        "django", "fastapi", "flask", "express", "next", "nuxt",
        "postgres", "mysql", "mongodb", "redis", "sqlite",
        "docker", "kubernetes", "terraform", "aws", "gcp",
        "scraper", "crawler", "bot", "automation",
    }
    if any(t in text_lower for t in tech_clear):
        return False
    # Short & vague without tech indicators → probably ambiguous
    vague_words = {"code", "build", "make", "create", "write", "do", "implement"}
    task_words  = set(words[:6])
    if len(words) <= 6 and task_words & vague_words:
        return True
    return False


def _generate_clarification_qa(task_text: str, brief) -> tuple[str, list[str]]:
    """Call leader model to generate a clarification question + 2 options.
    Returns (question, [option1, option2]).
    """
    try:
        import json
        from agents._api_client import make_openai_client
        from core.config import config as _cfg
        from core.config.settings import openrouter_base_url

        key   = "LEADER_MEDIUM"
        wcfg  = _cfg.get_worker(key) or {}
        model = str(wcfg.get("model") or getattr(_cfg, "ASK_CHAT_STANDARD_MODEL", ""))
        if not model:
            raise ValueError("no model configured")

        system = (
            'Bạn phân tích task và tạo câu hỏi làm rõ. '
            'Trả về JSON hợp lệ, không markdown, format:\n'
            '{"question":"<câu hỏi ngắn>","option1":"<15 từ>","option2":"<15 từ>"}'
        )
        client = make_openai_client(_cfg.api_key, openrouter_base_url())
        resp   = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": f"Task: {task_text}\nTier: {getattr(brief, 'tier', 'MEDIUM')}"},
            ],
            max_tokens=150, temperature=0.5,
        )
        raw  = (resp.choices[0].message.content or "").strip()
        data = json.loads(raw)
        q    = data.get("question",  f"Bạn muốn '{task_text[:40]}' cụ thể là gì?")
        o1   = data.get("option1",   "Phương án MVP cơ bản")
        o2   = data.get("option2",   "Phương án đầy đủ hơn")
        return q, [o1, o2]
    except Exception:
        q  = f"Bạn muốn '{task_text[:50]}' cụ thể là gì?"
        o1 = "Phương án đơn giản, MVP"
        o2 = "Phương án đầy đủ với nhiều tính năng"
        return q, [o1, o2]

# ── TUI background pipeline launcher ─────────────────────────────────────────

def start_pipeline_from_tui(task_text: str, project_root: str, mode: str = "agent") -> None:
    """Start ambassador + pipeline in a daemon thread while TUI stays open."""
    if not task_text.strip():
        return

    def _run() -> None:
        ws_session.clear_pipeline_stop()
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

        # ── Phase 4: Clarification gate ───────────────────────────────────────
        # If task is ambiguous, pause and show UI before running leader.
        if _is_ambiguous_task(task_text):
            try:
                q, opts = _generate_clarification_qa(task_text, brief)
                ws_session.set_clarification(q, opts)
                workflow_event("clarification", "pending", f"question={q[:80]}")

                import time as _time
                _deadline = _time.time() + 600  # 10 min max wait
                while ws_session.is_clarification_pending() and _time.time() < _deadline:
                    if ws_session.is_pipeline_stop_requested():
                        ws_session.clear_clarification()
                        ws_session.set_pipeline_run_finished(True)
                        return
                    _time.sleep(0.5)

                answer = ws_session.get_clarification_answer()
                ws_session.clear_clarification()

                if answer and answer != "__skip__":
                    task_text = f"{task_text}\n\nClarification from user: {answer}"
                    workflow_event("clarification", "answered", answer[:100])
                else:
                    workflow_event("clarification", "skipped", "user skipped or timed out")
            except Exception as _ce:
                workflow_event("clarification", "error", str(_ce)[:100])
                ws_session.clear_clarification()
        # ─────────────────────────────────────────────────────────────────────

        write_task_state_json(brief, task_text, project_root, source_node="ambassador")
        try:
            from utils import tracker as _tr
            _tr.append_cli_batch("agent", task_text[:220])
        except (ImportError, OSError, ValueError):
            pass

        try:
            run_agent_graph(brief, task_text, project_root, settings, inline_progress=False)
        except Exception as e:
            logger.exception("[start_flow] pipeline run aborted: %s", e)
            try:
                ws_session.set_pipeline_graph_failed(True)
                ws_session.set_pipeline_status_message(f"pipeline error: {str(e)[:120]}")
            except Exception:
                logger.debug("[start_flow] could not set pipeline failure state", exc_info=True)
        finally:
            ws_session.set_pipeline_run_finished(True)

    threading.Thread(target=_run, daemon=True).start()


# ── TUI opener ────────────────────────────────────────────────────────────────

def _open_tui(view_mode: str, project_root: str) -> None:
    """Open the workflow TUI (blocks until TUI exits)."""
    try:
        if view_mode == "list":
            from core.cli.python_cli.workflow.tui.list_view import run_workflow_list_view
            run_workflow_list_view(project_root)
        else:
            from core.cli.python_cli.workflow.tui.monitor_app import WorkflowMonitorApp
            WorkflowMonitorApp(view_mode=view_mode).run()
    finally:
        try:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()
        except OSError:
            pass


# ── Classify task (no ambassador, just mode detection) ────────────────────────

def _classify_task(
    prompt: str,
    run_ask_mode_cb: Callable,
    project_root: str,
    *,
    force_mode: str | None = None,
) -> tuple[str, str] | None:
    log_system_action("start.enter", (prompt or "")[:200])

    if force_mode:
        mode = force_mode.lower()
        if mode not in ("ask", "agent"):
            mode = "agent"
        p = (prompt or "").strip()
        if not p:
            return None
        if mode == "ask":
            run_ask_mode_cb(p, False)
            return None
        # Auto-detect questions
        if _looks_like_chat_intent(p) and not looks_like_code_intent(p):
            try:
                from utils import tracker as _tr
                _tr.append_cli_batch("ask", p[:220])
            except (ImportError, OSError, ValueError):
                pass
            run_ask_mode_cb(p, True)
            return None
        return mode, p

    console.print(f"[{PASTEL_CYAN}]Mode:[/{PASTEL_CYAN}] ask | agent")
    mode = ask_choice("Chọn mode", start_mode_choices(), default="agent",
                      number_map=START_MODE_BY_NUMBER)
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
        return None
    pl = p.lower()
    if pl == "exit":
        raise NavToMain
    if pl == "back":
        return None

    is_code     = looks_like_code_intent(p)
    is_question = _looks_like_chat_intent(p)

    if mode == "agent" and is_question and not is_code:
        run_ask_mode_cb(p, True)
        return None

    return mode, p


# ── Entry point — open TUI FIRST ─────────────────────────────────────────────

def run_start(
    prompt: str,
    run_ask_mode_cb: Callable[..., None],
    project_root: str,
    *,
    regenerate_prelude: str | None = None,
    force_mode: str | None = None,
):
    """Main workflow entry. Opens TUI immediately — ambassador runs inside TUI."""
    result = _classify_task(prompt, run_ask_mode_cb, project_root, force_mode=force_mode)
    if result is None:
        return
    _mode, p = result

    if regenerate_prelude:
        workflow_event("cli", "regenerate_started", regenerate_prelude[:400])

    settings   = get_cli_settings()
    policy     = resolve_display_policy(settings)
    view_mode  = policy.view_mode
    ws_session.set_workflow_last_view_mode(view_mode)
    ws_session.set_workflow_project_root(project_root)

    # Start ambassador + pipeline in background THEN open TUI immediately.
    # The TUI shows ambassador running → leader → gate — no console phase.
    start_pipeline_from_tui(p, project_root, _mode)
    _open_tui(view_mode, project_root)

    # ── Post-TUI: handle queued commands ──
    queued_cmd = ws_session.drain_monitor_command_queue()
    next_task: str | None = None
    for cmd in queued_cmd:
        act = str(cmd.get("action") or "")
        if act == "start_workflow":
            payload   = cmd.get("payload") or {}
            next_task = str(payload.get("prompt") or "").strip() or None
            next_mode = str(payload.get("mode") or "agent")
            if next_task and next_mode == "ask":
                run_ask_mode_cb(next_task, True)
                return
        elif act == "btw_note":
            pass

    if next_task:
        log_system_action("task.queued.follow", next_task[:100])
        run_start(next_task, run_ask_mode_cb, project_root)


__all__ = ["run_start", "start_pipeline_from_tui", "_looks_like_chat_intent"]

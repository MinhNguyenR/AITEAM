"""start_flow.py -- patched entry point: open TUI FIRST, ambassador runs inside.


Key change vs original:
  Original: _run_ambassador() in console â†’ THEN open TUI
  New:      open TUI immediately â†’ start_pipeline_from_tui() runs ambassador+graph in background


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


from core.cli.python_cli.features.ask.flow import _pick_chat_on_ask_entry, looks_like_code_intent
from core.cli.python_cli.shell.prompt import ask_choice, wait_enter
from core.cli.python_cli.features.context.flow import (
    apply_context_accept_from_monitor, confirm_context,
    delete_state_json_for_context, find_context_md,
)
from core.cli.python_cli.shell.choice_lists import start_mode_choices
from core.cli.python_cli.shell.command_registry import START_MODE_BY_NUMBER
from core.cli.python_cli.shell.nav import NavToMain
from core.app_state import get_cli_settings, log_system_action
from core.runtime import session as ws_session
from core.cli.python_cli.workflow.runtime.persist.activity_log import list_recent_activity
from core.orchestration.pipeline_artifacts import write_task_state_json
from core.cli.python_cli.workflow.runtime.graph.runner import run_agent_graph
from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, console, clear_screen
from core.cli.python_cli.ui.rich_command_palette import capture_menu_ansi
from core.cli.python_cli.features.context.flow import find_context_md, is_no_context
from core.cli.python_cli.i18n import t
from utils.file_manager import paths_for_task
from utils.logger import workflow_event




def _looks_like_chat_intent(text: str) -> bool:
    t = text.lower().strip()
    if looks_like_code_intent(text):
        return False
    mode_like = {"agent", "ask", "chat", "help", "menu", "start"}
    if t in mode_like:
        return True
    chat_keys = ["là gì", "what is", "explain", "giải thích", "táº¡i sao",
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




# -- Clarification helpers -----------------------------------------------------
from core.cli.python_cli.features.start.clarification_helpers import is_ambiguous_task, generate_clarification_qa




from core.cli.python_cli.features.start.pipeline_runner import start_pipeline_from_tui




def _capture_start_ansi(step_title: str) -> str:
    """Minimal header for start flow steps to keep UI in full-screen mode."""
    from core.cli.python_cli.ui.ui import print_header
    from io import StringIO
    from rich.console import Console as RichConsole
    import shutil


    width = shutil.get_terminal_size((120, 30)).columns
    sio = StringIO()
    cap = RichConsole(file=sio, force_terminal=True, width=width, no_color=False, highlight=False, markup=True)


    print_header(step_title, out=cap)
    # Ensure capture is complete
    cap.print("", end="")
    sys.stdout.flush()
    return sio.getvalue() or " "




def _open_tui(view_mode: str, project_root: str) -> None:
    """Open the workflow TUI (blocks until TUI exits)."""
    try:
        from core.frontends.tui import run_workflow_list_view
        run_workflow_list_view(project_root)
    finally:
        try:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()
        except OSError:
            pass




# -- Classify task (no ambassador, just mode detection) ------------------------


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


    ctx = find_context_md(project_root)
    context_ready = bool(ctx and not is_no_context(ctx))
    ansi = capture_menu_ansi(context_ready)


    mode = ask_choice(t("ui.choose_mode"), start_mode_choices(), default="agent",
                      number_map=START_MODE_BY_NUMBER, context="start_mode",
                      header_ansi=ansi)
    log_system_action("mode.select", mode)
    if mode in ("back", "exit"):
        return None
    if mode == "ask":
        # Pass force_new_chat=False to show chat list (user request)
        run_ask_mode_cb((prompt or "").strip(), False)
        return None


    p = (prompt or "").strip()
    if not p:
        try:
            from core.cli.python_cli.ui.palette_app import ask_with_palette
            p = ask_with_palette("> ", context="main",

                                 header_ansi=ansi).strip()
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
        # Redirect to ask mode but allow chat selection
        run_ask_mode_cb(p, False)
        return None


    return mode, p




# -- Entry point -- open TUI FIRST ---------------------------------------------


def run_start(
    prompt: str,
    run_ask_mode_cb: Callable[..., None],
    project_root: str,
    *,
    regenerate_prelude: str | None = None,
    force_mode: str | None = None,
):
    """Main workflow entry. Opens TUI immediately -- ambassador runs inside TUI."""
    result = _classify_task(prompt, run_ask_mode_cb, project_root, force_mode=force_mode)
    if result is None:
        return
    _mode, p = result


    if regenerate_prelude:
        workflow_event("cli", "regenerate_started", regenerate_prelude[:400])


    ws_session.set_workflow_project_root(project_root)


    # Start ambassador + pipeline in background THEN open TUI immediately.
    # The TUI shows ambassador running â†’ leader â†’ gate -- no console phase.
    start_pipeline_from_tui(p, project_root, _mode)
    _open_tui("list", project_root)


    # -- Post-TUI: handle queued commands --
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

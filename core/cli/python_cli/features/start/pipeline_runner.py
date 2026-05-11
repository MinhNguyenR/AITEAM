import logging
import threading
from core.runtime import session as ws_session
from core.app_state.settings import get_cli_settings
from core.orchestration.pipeline_artifacts import write_task_state_json
from core.cli.python_cli.workflow.runtime.graph.runner import run_agent_graph
from utils.logger import workflow_event
from core.cli.python_cli.features.start.clarification_helpers import is_ambiguous_task, generate_clarification_qa

logger = logging.getLogger(__name__)

def start_pipeline_from_tui(task_text: str, project_root: str, mode: str = "agent", regenerate: bool = False) -> None:
    """Start ambassador + pipeline in a daemon thread while TUI stays open."""
    if not task_text.strip():
        return

    def _run() -> None:
        try:
            _run_pipeline()
        except Exception as exc:
            logger.exception("[start_flow] unexpected error in pipeline thread: %s", exc)
            try:
                ws_session.set_pipeline_graph_failed(True)
                ws_session.set_pipeline_run_finished(True)
            except Exception:
                pass

    def _run_pipeline() -> None:
        ws_session.clear_pipeline_stop()
        ws_session.transition_pipeline_begin_run()
        ws_session.reset_pipeline_visual()

        # Local copy avoids Python scoping error
        _task = task_text

        def _is_restore_request(text: str) -> bool:
            import re
            return bool(re.search(r"\b(restore|revert|undo|rollback)\b|khôi\s*phục|hoàn\s*tác", text, re.IGNORECASE))

        def _wait_for_clarification(label: str, q_list: list[dict]) -> str:
            if not q_list:
                return ""
            ws_session.set_clarification(q_list)
            workflow_event(label, "pending", f"questions={len(q_list)}")
            import time as _time
            _deadline = _time.time() + 360
            while ws_session.is_clarification_pending() and _time.time() < _deadline:
                if ws_session.is_pipeline_stop_requested():
                    ws_session.clear_clarification()
                    ws_session.set_pipeline_run_finished(True)
                    return ""
                _time.sleep(0.5)
            answer = ws_session.get_clarification_answer()
            ws_session.clear_clarification()
            return answer if answer and answer != "__skip__" else ""

        if not regenerate and _is_restore_request(_task):
            from core.domain.delta_brief import DeltaBrief
            brief = DeltaBrief(
                original_prompt=_task,
                summary="Restore code from SQLite backup",
                tier="LOW",
                target_model="",
                selected_leader="LEADER_LOW",
                parameters={"fast_path": "restore"},
                language_detected="unknown",
            )
        elif not regenerate:
            try:
                from agents.secretary import Secretary
                secretary = Secretary()
                if secretary.should_redirect_to_ask(_task):
                    ws_session.set_pipeline_redirect("ask")
                    ws_session.set_pipeline_run_finished(True)
                    return
                ws_session.set_pipeline_active_step("secretary")
                ws_session.update_workflow_node_status("secretary", "running", "Analyzing user input")
                ws_session.set_pipeline_status_message("Secretary dang phan tich input...")
                q_list = secretary.analyze_input(_task, project_root)
                answer = _wait_for_clarification("secretary_clarification", q_list)
                if answer:
                    _task = f"{_task}\n\nSecretary clarification from user:\n{answer}"
                    workflow_event("secretary_clarification", "answered", str(answer)[:100])
                else:
                    workflow_event("secretary_clarification", "skipped", "no answer or no questions")
                try:
                    ws_session.clear_secretary_substate()
                except Exception:
                    pass
                ws_session.clear_leader_stream_buffer()
            except Exception as exc:
                workflow_event("secretary_clarification", "error", str(exc)[:120])
                try:
                    ws_session.clear_secretary_substate()
                except Exception:
                    pass

            try:
                from agents.ambassador import Ambassador
                ambassador = Ambassador()
            except ImportError as exc:
                ws_session.set_pipeline_ambassador_error()
                ws_session.set_pipeline_graph_failed(True)
                ws_session.set_pipeline_status_message(f"ImportError: {str(exc)[:150]}")
                workflow_event("ambassador", "failed", f"import_error: {exc}")
                ws_session.set_pipeline_run_finished(True)
                return

            ws_session.set_pipeline_ambassador_status("running")
            ws_session.set_pipeline_active_step("ambassador")
            workflow_event("ambassador", "enter", "parse task")
            ws_session.set_pipeline_status_message("Ambassador parsing task...")

            try:
                brief = ambassador.parse(_task)
            except Exception as exc:
                ws_session.set_pipeline_ambassador_error()
                ws_session.set_pipeline_graph_failed(True)
                ws_session.set_pipeline_status_message(f"Ambassador lỗi: {str(exc)[:150]}")
                workflow_event("ambassador", "failed", str(exc)[:200])
                ws_session.set_pipeline_run_finished(True)
                return

            # Check intent routing
            if getattr(brief, "intent", "agent") == "ask":
                ws_session.set_pipeline_redirect("ask")
                ws_session.set_pipeline_run_finished(True)
                return
        else:
            # Regenerate: load brief from state.json
            import json
            import os
            from core.domain.delta_brief import DeltaBrief
            try:
                state_path = os.path.join(project_root, ".ai-team", "state.json")
                with open(state_path, "r", encoding="utf-8") as f:
                    state_data = json.load(f)

                # Mock a brief based on state.json
                brief = DeltaBrief(
                    original_prompt=state_data.get("original_prompt", _task),
                    summary="Regenerate context.md",
                    tier=state_data.get("tier", "MEDIUM"),
                    target_model="",
                    selected_leader="",
                    language_detected=state_data.get("language", "unknown")
                )
            except Exception as exc:
                ws_session.set_pipeline_graph_failed(True)
                ws_session.set_pipeline_status_message(f"Lỗi đọc state.json để regenerate: {exc}")
                ws_session.set_pipeline_run_finished(True)
                return

        if not regenerate and not (getattr(brief, "parameters", {}) or {}).get("fast_path") == "restore":
            ws_session.set_pipeline_after_ambassador(brief)
            ws_session.clear_leader_stream_buffer()
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

        # Write state.json first so Leader Clarification can read it!
        if not regenerate and not (getattr(brief, "parameters", {}) or {}).get("fast_path") == "restore":
            write_task_state_json(brief, _task, project_root, source_node="ambassador")

        # -- Phase 4: Clarification gate ---------------------------------------
        if not regenerate and not (getattr(brief, "parameters", {}) or {}).get("fast_path") == "restore" and is_ambiguous_task(_task):
            try:
                ws_session.set_pipeline_active_step("leader_generate")
                ws_session.set_leader_action("reading state.json")
                q_list = generate_clarification_qa(_task, brief, project_root)
                ws_session.clear_leader_action()
                if q_list:
                    answer = _wait_for_clarification("clarification", q_list)
                    if answer:
                        _task = f"{_task}\n\nClarification from user:\n{answer}"
                        # Re-write state.json with updated task so Leader graph gets it
                        write_task_state_json(brief, _task, project_root, source_node="ambassador")
                        workflow_event("clarification", "answered", str(answer)[:100])
                    else:
                        workflow_event("clarification", "skipped", "user skipped or timed out")
                else:
                    workflow_event("clarification", "skipped", "no questions from leader")
            except Exception as _ce:
                workflow_event("clarification", "error", str(_ce)[:100])
                ws_session.clear_clarification()
        elif regenerate:
            # Just set the reading state for the UI so it looks like it's reading state.json
            ws_session.set_pipeline_active_step("leader_generate")
            ws_session.set_leader_action("reading state.json")
            import time
            time.sleep(1.0)
            ws_session.clear_leader_action()
        # ---------------------------------------------------------------------
        try:
            from utils import tracker as _tr
            _tr.append_cli_batch("agent", _task[:220])
        except (ImportError, OSError, ValueError):
            pass

        outcome = None
        try:
            outcome = run_agent_graph(brief, _task, project_root, settings, inline_progress=False)
        except Exception as e:
            logger.exception("[start_flow] pipeline run aborted: %s", e)
            try:
                ws_session.set_pipeline_graph_failed(True)
                ws_session.set_pipeline_status_message(f"pipeline error: {str(e)[:120]}")
            except Exception:
                logger.debug("[start_flow] could not set pipeline failure state", exc_info=True)
        finally:
            # Do NOT mark finished when paused at gate -- the gate is still waiting for user input.
            # resume_workflow() will call set_pipeline_run_finished(True) after the user accepts.
            if outcome != "paused":
                ws_session.set_pipeline_run_finished(True)

    threading.Thread(target=_run, daemon=True).start()

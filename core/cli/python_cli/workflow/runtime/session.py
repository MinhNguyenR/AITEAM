"""Shared workflow session — re-export facade (backward compat)."""
import time  # keep accessible as ws.time for monkeypatching in tests
from ._session_core import (
    SESSION_FILE, WORKFLOW_PHASES, CONTEXT_ACCEPT_STATUSES,
    _ensure_dir, load_session, save_session,
    get_thread_id, set_thread_id, new_thread_id, checkpoint_db_path,
)
from .session_pause_manager import (
    set_paused_for_review, is_paused_for_review,
    set_last_node, get_context_path,
    signal_check_done, consume_check_done,
    set_should_finalize, peek_should_finalize, consume_should_finalize,
    set_interrupt_before, get_interrupt_before,
    clear_session_flags,
)
from .session_monitor_manager import (
    get_monitor_pid, set_monitor_pid, clear_monitor_pid,
)
from .session_notification import (
    set_pipeline_toast, get_pipeline_toast_text,
    push_pipeline_notification, list_active_notifications,
    dismiss_pipeline_notification, prune_stale_pipeline_notifications,
)
from .session_pipeline_state import (
    request_pipeline_stop, clear_pipeline_stop, is_pipeline_stop_requested,
    # TUI stream history persistence
    append_stream_line, get_stream_history, clear_stream_history,
    # Clarification mechanism
    set_clarification, is_clarification_pending, get_clarification,
    answer_clarification, get_clarification_answer, clear_clarification,
    get_workflow_activity_min_ts, reset_pipeline_visual,
    apply_stale_workflow_ui_if_needed,
    set_workflow_project_root, get_workflow_project_root,
    set_pipeline_status_message, get_pipeline_status_message,
    set_context_accept_status, get_context_accept_status,
    clear_leader_stream_buffer, append_leader_stream_chunk,
    set_workflow_last_view_mode, get_workflow_last_view_mode,
    set_workflow_list_nodes_state, get_workflow_list_nodes_state,
    append_workflow_list_event, get_workflow_list_timeline,
    update_workflow_node_status,
    set_pipeline_ambassador_status, set_pipeline_after_ambassador,
    set_pipeline_ambassador_error,
    touch_pipeline_busy, set_pipeline_active_step,
    set_pipeline_paused_at_gate, set_pipeline_graph_failed,
    set_pipeline_run_finished, get_pipeline_stop_phase,
    set_pipeline_stop_phase, set_phase_running, set_phase_paused_gate,
    enqueue_monitor_command, drain_monitor_command_queue,
    get_pipeline_snapshot,
)

__all__ = [
    "SESSION_FILE", "WORKFLOW_PHASES", "CONTEXT_ACCEPT_STATUSES",
    "load_session", "save_session", "get_thread_id", "set_thread_id",
    "new_thread_id", "checkpoint_db_path",
    "set_paused_for_review", "is_paused_for_review", "set_last_node",
    "get_context_path", "signal_check_done", "consume_check_done",
    "set_should_finalize", "peek_should_finalize", "consume_should_finalize",
    "set_interrupt_before", "get_interrupt_before", "clear_session_flags",
    "get_monitor_pid", "set_monitor_pid", "clear_monitor_pid",
    "set_pipeline_toast", "get_pipeline_toast_text",
    "push_pipeline_notification", "list_active_notifications",
    "dismiss_pipeline_notification", "prune_stale_pipeline_notifications",
    "request_pipeline_stop", "clear_pipeline_stop", "is_pipeline_stop_requested",
    # TUI stream history
    "append_stream_line", "get_stream_history", "clear_stream_history",
    # Clarification
    "set_clarification", "is_clarification_pending", "get_clarification",
    "answer_clarification", "get_clarification_answer", "clear_clarification",
    "get_workflow_activity_min_ts", "reset_pipeline_visual",
    "apply_stale_workflow_ui_if_needed",
    "set_workflow_project_root", "get_workflow_project_root",
    "set_pipeline_status_message", "get_pipeline_status_message",
    "set_context_accept_status", "get_context_accept_status",
    "clear_leader_stream_buffer", "append_leader_stream_chunk",
    "set_workflow_last_view_mode", "get_workflow_last_view_mode",
    "set_workflow_list_nodes_state", "get_workflow_list_nodes_state",
    "append_workflow_list_event", "get_workflow_list_timeline",
    "update_workflow_node_status",
    "set_pipeline_ambassador_status", "set_pipeline_after_ambassador",
    "set_pipeline_ambassador_error", "touch_pipeline_busy",
    "set_pipeline_active_step", "set_pipeline_paused_at_gate",
    "set_pipeline_graph_failed", "set_pipeline_run_finished",
    "get_pipeline_stop_phase", "set_pipeline_stop_phase",
    "set_phase_running", "set_phase_paused_gate",
    "enqueue_monitor_command", "drain_monitor_command_queue",
    "get_pipeline_snapshot",
]

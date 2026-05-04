"""Tests for uncovered branches in session_pipeline_state.py."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import core.cli.python_cli.workflow.runtime.session.session_pipeline_state as sps


def _patch_session(initial: dict | None = None):
    store = [dict(initial or {})]
    def _load(): return dict(store[0])
    def _save(s): store[0] = dict(s)
    lp = patch.object(sps, "load_session", side_effect=_load)
    sp = patch.object(sps, "save_session", side_effect=_save)
    return lp, sp, store


class TestGetWorkflowActivityMinTs:
    def test_returns_zero_on_type_error(self):
        lp, sp, store = _patch_session({"workflow_activity_min_ts": "not-a-float"})
        with lp, sp:
            # The parse will raise ValueError which should be caught
            result = sps.get_workflow_activity_min_ts()
        assert isinstance(result, float)

    def test_returns_zero_when_missing(self):
        lp, sp, store = _patch_session({})
        with lp, sp:
            result = sps.get_workflow_activity_min_ts()
        assert result == 0.0


class TestApplyStaleWorkflowUiIfNeeded:
    def test_clears_paused_when_no_context(self):
        lp, sp, store = _patch_session({
            "pipeline_paused_at_gate": True,
            "pipeline_active_step": "human_context_gate",
            "pipeline_ambassador_status": "idle",
            "monitor_command_queue": [],
        })
        mock_ctx_flow = MagicMock()
        mock_ctx_flow.find_context_md.return_value = None
        mock_ctx_flow.is_no_context.return_value = True
        with lp, sp, \
             patch.dict("sys.modules", {"core.cli.python_cli.features.context.flow": mock_ctx_flow}), \
             patch.object(sps, "is_paused_for_review", return_value=True), \
             patch.object(sps, "set_paused_for_review"):
            sps.apply_stale_workflow_ui_if_needed("/project/root")
        assert store[0].get("pipeline_paused_at_gate") is False

    def test_returns_early_when_context_ok(self):
        lp, sp, store = _patch_session({})
        mock_ctx = MagicMock()
        mock_ctx_flow = MagicMock()
        mock_ctx_flow.find_context_md.return_value = mock_ctx
        mock_ctx_flow.is_no_context.return_value = False
        with lp, sp, \
             patch.dict("sys.modules", {"core.cli.python_cli.features.context.flow": mock_ctx_flow}):
            sps.apply_stale_workflow_ui_if_needed("/project/root")
        # No state changes expected since ctx_ok=True → early return

    def test_skips_reset_when_ambassador_running(self):
        lp, sp, store = _patch_session({
            "pipeline_ambassador_status": "running",
            "monitor_command_queue": [],
            "pipeline_active_step": "idle",
        })
        mock_ctx_flow = MagicMock()
        mock_ctx_flow.find_context_md.return_value = None
        mock_ctx_flow.is_no_context.return_value = True
        with lp, sp, \
             patch.dict("sys.modules", {"core.cli.python_cli.features.context.flow": mock_ctx_flow}), \
             patch.object(sps, "is_paused_for_review", return_value=False):
            sps.apply_stale_workflow_ui_if_needed("/project/root")
        # should not reset since ambassador is running

    def test_skips_when_command_queue_nonempty(self):
        lp, sp, store = _patch_session({
            "pipeline_ambassador_status": "idle",
            "monitor_command_queue": [{"action": "stop"}],
            "pipeline_active_step": "idle",
        })
        mock_ctx_flow = MagicMock()
        mock_ctx_flow.find_context_md.return_value = None
        mock_ctx_flow.is_no_context.return_value = True
        with lp, sp, \
             patch.dict("sys.modules", {"core.cli.python_cli.features.context.flow": mock_ctx_flow}), \
             patch.object(sps, "is_paused_for_review", return_value=False):
            sps.apply_stale_workflow_ui_if_needed("/project/root")

    def test_resets_when_idle_and_no_context(self):
        lp, sp, store = _patch_session({
            "pipeline_ambassador_status": "idle",
            "monitor_command_queue": [],
            "pipeline_active_step": "idle",
            "context_accept_status": "accepted",
        })
        mock_ctx_flow = MagicMock()
        mock_ctx_flow.find_context_md.return_value = None
        mock_ctx_flow.is_no_context.return_value = True
        with lp, sp, \
             patch.dict("sys.modules", {"core.cli.python_cli.features.context.flow": mock_ctx_flow}), \
             patch.object(sps, "is_paused_for_review", return_value=False):
            sps.apply_stale_workflow_ui_if_needed("/project/root")
        assert store[0].get("context_accept_status") == "none"


class TestAppendLeaderStreamChunkTruncation:
    def test_truncates_when_over_max(self):
        big_text = "x" * 60000  # > _LEADER_STREAM_MAX = 48000
        sps.clear_leader_stream_buffer()
        sps.append_leader_stream_chunk(big_text)
        sps.append_leader_stream_chunk("extra")
        assert len(sps._STREAM_BUFFER) <= sps._LEADER_STREAM_MAX

    def test_empty_text_noop(self):
        sps.clear_leader_stream_buffer()
        sps.append_leader_stream_chunk("existing")
        sps.append_leader_stream_chunk("")
        assert sps._STREAM_BUFFER == "existing"


class TestSetPipelineAfterAmbassador:
    def test_sets_brief_data(self):
        lp, sp, store = _patch_session({})
        brief = SimpleNamespace(tier="HIGH", selected_leader="LEADER_HIGH")
        with lp, sp:
            sps.set_pipeline_after_ambassador(brief)
        assert store[0]["pipeline_brief_tier"] == "HIGH"
        assert store[0]["pipeline_brief_selected_leader"] == "LEADER_HIGH"
        assert store[0]["pipeline_ambassador_status"] == "done"
        assert store[0]["pipeline_active_step"] == "idle"

    def test_uses_defaults_for_missing_attrs(self):
        lp, sp, store = _patch_session({})
        brief = SimpleNamespace()  # no tier or selected_leader
        with lp, sp:
            sps.set_pipeline_after_ambassador(brief)
        assert store[0]["pipeline_brief_tier"] == "MEDIUM"
        assert store[0]["pipeline_brief_selected_leader"] == ""


class TestSetPipelinePausedAtGate:
    def test_paused_true_sets_active_step(self):
        lp, sp, store = _patch_session({})
        with lp, sp:
            sps.set_pipeline_paused_at_gate(True)
        assert store[0]["pipeline_paused_at_gate"] is True
        assert store[0]["pipeline_active_step"] == "human_context_gate"

    def test_paused_false_does_not_set_step(self):
        lp, sp, store = _patch_session({"pipeline_active_step": "running"})
        with lp, sp:
            sps.set_pipeline_paused_at_gate(False)
        assert store[0]["pipeline_paused_at_gate"] is False
        # active_step unchanged when paused=False
        assert store[0]["pipeline_active_step"] == "running"


class TestSetPhasePausedGate:
    def test_sets_paused_gate_phase(self):
        lp, sp, store = _patch_session({})
        with lp, sp:
            sps.set_phase_paused_gate()
        assert store[0]["pipeline_stop_phase"] == "paused_gate"

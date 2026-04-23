"""Tests for session_pipeline_state.py — get/set pipeline visual state."""
from unittest.mock import patch

import pytest

import core.cli.workflow.runtime.session_pipeline_state as sps


def _patch_session(initial: dict | None = None):
    """Patch load_session + save_session with an in-memory store."""
    store = [dict(initial or {})]

    def _load():
        return dict(store[0])

    def _save(s):
        store[0] = dict(s)

    lp = patch.object(sps, "load_session", side_effect=_load)
    sp = patch.object(sps, "save_session", side_effect=_save)
    return lp, sp, store


# ---------------------------------------------------------------------------
# get_workflow_activity_min_ts
# ---------------------------------------------------------------------------

class TestGetWorkflowActivityMinTs:
    def test_returns_float(self):
        lp, sp, _ = _patch_session({"workflow_activity_min_ts": 12345.0})
        with lp, sp:
            result = sps.get_workflow_activity_min_ts()
        assert result == 12345.0

    def test_missing_returns_zero(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            assert sps.get_workflow_activity_min_ts() == 0.0


# ---------------------------------------------------------------------------
# set_workflow_project_root / get_workflow_project_root
# ---------------------------------------------------------------------------

class TestWorkflowProjectRoot:
    def test_set_and_get(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.set_workflow_project_root("/my/project")
            result = sps.get_workflow_project_root()
        assert result == "/my/project"

    def test_clear_root(self):
        lp, sp, store = _patch_session({"workflow_project_root": "/old"})
        with lp, sp:
            sps.set_workflow_project_root(None)
            result = sps.get_workflow_project_root()
        assert result is None

    def test_missing_returns_none(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            assert sps.get_workflow_project_root() is None


# ---------------------------------------------------------------------------
# set_pipeline_status_message / get_pipeline_status_message
# ---------------------------------------------------------------------------

class TestPipelineStatusMessage:
    def test_set_and_get(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            sps.set_pipeline_status_message("Processing...")
            result = sps.get_pipeline_status_message()
        assert result == "Processing..."

    def test_truncates_long_message(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.set_pipeline_status_message("x" * 600)
        assert len(store[0]["pipeline_status_message"]) <= 500

    def test_empty_returns_empty(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            assert sps.get_pipeline_status_message() == ""


# ---------------------------------------------------------------------------
# set_context_accept_status / get_context_accept_status
# ---------------------------------------------------------------------------

class TestContextAcceptStatus:
    def test_valid_statuses(self):
        for status in ("none", "pending", "accepted", "deferred"):
            lp, sp, _ = _patch_session()
            with lp, sp:
                sps.set_context_accept_status(status)
                result = sps.get_context_accept_status()
            assert result == status

    def test_invalid_defaults_to_none(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            sps.set_context_accept_status("invalid")
            result = sps.get_context_accept_status()
        assert result == "none"

    def test_uppercase_normalized(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            sps.set_context_accept_status("ACCEPTED")
            result = sps.get_context_accept_status()
        assert result == "accepted"


# ---------------------------------------------------------------------------
# append_leader_stream_chunk / clear_leader_stream_buffer
# ---------------------------------------------------------------------------

class TestLeaderStreamBuffer:
    def test_append_chunks(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.append_leader_stream_chunk("hello ")
            sps.append_leader_stream_chunk("world")
        assert store[0]["leader_stream_buffer"] == "hello world"

    def test_ignores_empty_chunk(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.append_leader_stream_chunk("")
        assert store[0].get("leader_stream_buffer", "") == ""

    def test_clear_buffer(self):
        lp, sp, store = _patch_session({"leader_stream_buffer": "data"})
        with lp, sp:
            sps.clear_leader_stream_buffer()
        assert store[0]["leader_stream_buffer"] == ""
        assert store[0]["leader_stream_updated_at"] == 0.0


# ---------------------------------------------------------------------------
# set_workflow_last_view_mode / get_workflow_last_view_mode
# ---------------------------------------------------------------------------

class TestWorkflowLastViewMode:
    def test_set_list_mode(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            sps.set_workflow_last_view_mode("list")
            assert sps.get_workflow_last_view_mode() == "list"

    def test_set_chain_mode(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            sps.set_workflow_last_view_mode("chain")
            assert sps.get_workflow_last_view_mode() == "chain"

    def test_invalid_mode_defaults_chain(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            sps.set_workflow_last_view_mode("unknown")
            assert sps.get_workflow_last_view_mode() == "chain"


# ---------------------------------------------------------------------------
# set/get workflow_list_nodes_state
# ---------------------------------------------------------------------------

class TestWorkflowListNodesState:
    def test_set_and_get(self):
        lp, sp, _ = _patch_session()
        nodes = [{"node": "Leader", "status": "running"}]
        with lp, sp:
            sps.set_workflow_list_nodes_state(nodes)
            result = sps.get_workflow_list_nodes_state()
        assert result == nodes

    def test_empty_returns_empty(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            assert sps.get_workflow_list_nodes_state() == []

    def test_caps_at_30_items(self):
        lp, sp, store = _patch_session()
        nodes = [{"node": str(i)} for i in range(40)]
        with lp, sp:
            sps.set_workflow_list_nodes_state(nodes)
        assert len(store[0]["workflow_list_nodes_state"]) == 30


# ---------------------------------------------------------------------------
# append_workflow_list_event / get_workflow_list_timeline
# ---------------------------------------------------------------------------

class TestWorkflowListTimeline:
    def test_append_event(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            sps.append_workflow_list_event({"node": "A", "action": "done"})
            result = sps.get_workflow_list_timeline()
        assert len(result) == 1
        assert result[0]["node"] == "A"

    def test_limit_applied(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            for i in range(10):
                sps.append_workflow_list_event({"n": i})
            result = sps.get_workflow_list_timeline(limit=3)
        assert len(result) == 3

    def test_empty_returns_empty(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            assert sps.get_workflow_list_timeline() == []


# ---------------------------------------------------------------------------
# reset_pipeline_visual
# ---------------------------------------------------------------------------

class TestResetPipelineVisual:
    def test_resets_key_fields(self):
        lp, sp, store = _patch_session({"pipeline_active_step": "running"})
        with lp, sp:
            sps.reset_pipeline_visual()
        assert store[0]["pipeline_active_step"] == "idle"
        assert store[0]["pipeline_graph_failed"] is False
        assert store[0]["leader_stream_buffer"] == ""
        assert store[0]["pipeline_notifications"] == []

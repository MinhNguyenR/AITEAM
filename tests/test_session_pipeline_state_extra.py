"""Additional tests for session_pipeline_state.py — node status, ambassador, snapshot."""
from unittest.mock import patch

import core.cli.workflow.runtime.session_pipeline_state as sps


def _patch_session(initial: dict | None = None):
    store = [dict(initial or {})]
    def _load(): return dict(store[0])
    def _save(s): store[0] = dict(s)
    lp = patch.object(sps, "load_session", side_effect=_load)
    sp = patch.object(sps, "save_session", side_effect=_save)
    return lp, sp, store


class TestUpdateWorkflowNodeStatus:
    def test_adds_new_node(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.update_workflow_node_status("Leader", "running", "Processing")
        arr = store[0]["workflow_list_nodes_state"]
        assert len(arr) == 1
        assert arr[0]["node"] == "Leader"
        assert arr[0]["status"] == "running"

    def test_updates_existing_node(self):
        initial = {"workflow_list_nodes_state": [{"node": "Leader", "status": "pending", "detail": "", "updated_at": 0.0}]}
        lp, sp, store = _patch_session(initial)
        with lp, sp:
            sps.update_workflow_node_status("Leader", "done", "finished")
        arr = store[0]["workflow_list_nodes_state"]
        assert arr[0]["status"] == "done"

    def test_appends_to_timeline(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.update_workflow_node_status("A", "ok")
        assert "workflow_list_timeline" in store[0]
        assert len(store[0]["workflow_list_timeline"]) == 1


class TestSetPipelineAmbassadorStatus:
    def test_sets_status(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.set_pipeline_ambassador_status("done")
        assert store[0]["pipeline_ambassador_status"] == "done"

    def test_running_sets_active_step(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.set_pipeline_ambassador_status("running")
        assert store[0]["pipeline_active_step"] == "ambassador"

    def test_error_status(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.set_pipeline_ambassador_error()
        assert store[0]["pipeline_ambassador_status"] == "error"


class TestTouchPipelineBusy:
    def test_updates_busy_ts(self):
        import time
        lp, sp, store = _patch_session({"pipeline_busy_ts": 0.0})
        before = time.time()
        with lp, sp:
            sps.touch_pipeline_busy()
        assert store[0]["pipeline_busy_ts"] >= before


class TestSetPipelineActiveStep:
    def test_sets_step(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.set_pipeline_active_step("leader_generate")
        assert store[0]["pipeline_active_step"] == "leader_generate"

    def test_non_gate_clears_paused(self):
        lp, sp, store = _patch_session({"pipeline_paused_at_gate": True})
        with lp, sp:
            sps.set_pipeline_active_step("leader_generate")
        assert store[0]["pipeline_paused_at_gate"] is False


class TestPipelineGraphFailedAndFinished:
    def test_set_failed(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.set_pipeline_graph_failed(True)
        assert store[0]["pipeline_graph_failed"] is True

    def test_set_finished_clears_active_step(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.set_pipeline_run_finished(True)
        assert store[0]["pipeline_active_step"] == "idle"


class TestStopPhase:
    def test_set_valid_phase(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.set_pipeline_stop_phase("running")
        assert store[0]["pipeline_stop_phase"] == "running"

    def test_invalid_phase_defaults_idle(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.set_pipeline_stop_phase("unknown")
        assert store[0]["pipeline_stop_phase"] == "idle"

    def test_get_stop_phase(self):
        lp, sp, _ = _patch_session({"pipeline_stop_phase": "paused_gate"})
        with lp, sp:
            assert sps.get_pipeline_stop_phase() == "paused_gate"

    def test_set_phase_running(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sps.set_phase_running()
        assert store[0]["pipeline_stop_phase"] == "running"


class TestMonitorCommandQueue:
    def test_enqueue_and_drain(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            sps.enqueue_monitor_command("refresh", {"key": "val"})
            result = sps.drain_monitor_command_queue()
        assert len(result) == 1
        assert result[0]["action"] == "refresh"

    def test_drain_empty_returns_empty(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            result = sps.drain_monitor_command_queue()
        assert result == []


class TestGetPipelineSnapshot:
    def test_snapshot_has_required_keys(self):
        lp, sp, _ = _patch_session()
        with lp, sp, \
             patch.object(sps, "get_pipeline_toast_text", return_value=""), \
             patch.object(sps, "list_active_notifications", return_value=[]):
            snap = sps.get_pipeline_snapshot()
        assert "active_step" in snap
        assert "ambassador_status" in snap
        assert "graph_failed" in snap
        assert "notifications" in snap

    def test_snapshot_defaults(self):
        lp, sp, _ = _patch_session()
        with lp, sp, \
             patch.object(sps, "get_pipeline_toast_text", return_value=""), \
             patch.object(sps, "list_active_notifications", return_value=[]):
            snap = sps.get_pipeline_snapshot()
        assert snap["active_step"] == "idle"
        assert snap["graph_failed"] is False

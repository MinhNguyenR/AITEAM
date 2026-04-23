"""Tests for runner_rewind.py — _cleanup_artifacts, rewind_current, rewind_to_*."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Stub heavy module-level imports
sys.modules.setdefault("agents.team_map._team_map", MagicMock(get_graph=MagicMock()))
sys.modules.setdefault("core.cli.workflow.runtime.checkpointer", MagicMock(get_checkpointer=MagicMock()))

from core.cli.workflow.runtime.runner_rewind import (
    _cleanup_artifacts_from_target,
    _truncate_log_tail_from,
    rewind_current,
    rewind_to_checkpoint,
    rewind_to_last_gate,
)


def _make_values(uuid="task-001", task="build", project_root="/proj",
                 original_prompt="build", brief_dict=None, context_path=None,
                 leader_failed=False, last_node="leader_generate"):
    bd = brief_dict or {
        "tier": "MEDIUM",
        "task_uuid": uuid,
        "selected_leader": "LEADER_MEDIUM",
        "summary": task,
        "original_prompt": task,
        "target_model": "test-model",
        "language_detected": "python",
        "is_cuda_required": False,
        "is_hardware_bound": False,
        "complexity_score": 0.5,
        "estimated_vram_usage": None,
    }
    vals = {
        "task": task,
        "project_root": project_root,
        "original_prompt": original_prompt,
        "brief_dict": bd,
        "leader_failed": leader_failed,
        "last_node": last_node,
    }
    if context_path:
        vals["context_path"] = context_path
    return vals


class TestTruncateLogTailFrom:
    def test_calls_through(self):
        with patch("core.cli.workflow.runtime.runner_rewind.truncate_workflow_activity_from_ts") as mock_t:
            _truncate_log_tail_from(1234.5)
        mock_t.assert_called_once_with(1234.5)


class TestCleanupArtifacts:
    def test_deletes_files_from_target_node(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        (run_dir / "state.json").write_text("{}")
        (run_dir / "context.md").write_text("# content")

        mock_paths = MagicMock()
        mock_paths.run_dir = run_dir
        vals = _make_values(uuid="task-001")

        with patch("core.cli.workflow.runtime.runner_rewind.paths_for_task", return_value=mock_paths), \
             patch("core.cli.workflow.runtime.runner_rewind.workflow_event"), \
             patch("core.cli.workflow.runtime.runner_rewind.artifact_detail", return_value=""), \
             patch("core.cli.workflow.runtime.runner_rewind._truncate_log_tail_from"):
            _cleanup_artifacts_from_target(vals, "leader_generate", time.time())

        assert not (run_dir / "state.json").exists()
        assert not (run_dir / "context.md").exists()

    def test_no_task_id_returns_early(self):
        # brief_dict missing → no cleanup attempted
        with patch("core.cli.workflow.runtime.runner_rewind.paths_for_task") as mock_paths:
            _cleanup_artifacts_from_target({}, "leader_generate", time.time())
        mock_paths.assert_not_called()

    def test_unknown_target_defaults_to_leader_generate(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        (run_dir / "state.json").write_text("{}")

        mock_paths = MagicMock()
        mock_paths.run_dir = run_dir
        vals = _make_values(uuid="task-002")

        with patch("core.cli.workflow.runtime.runner_rewind.paths_for_task", return_value=mock_paths), \
             patch("core.cli.workflow.runtime.runner_rewind.workflow_event"), \
             patch("core.cli.workflow.runtime.runner_rewind.artifact_detail", return_value=""), \
             patch("core.cli.workflow.runtime.runner_rewind._truncate_log_tail_from"):
            _cleanup_artifacts_from_target(vals, "totally_unknown_node", time.time())

        # Files from leader_generate chain should be cleaned
        assert not (run_dir / "state.json").exists()

    def test_oserror_on_unlink_is_swallowed(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        mock_paths = MagicMock()
        mock_paths.run_dir = run_dir
        vals = _make_values(uuid="task-003")

        with patch("core.cli.workflow.runtime.runner_rewind.paths_for_task", return_value=mock_paths), \
             patch("core.cli.workflow.runtime.runner_rewind.workflow_event"), \
             patch("core.cli.workflow.runtime.runner_rewind.artifact_detail", return_value=""), \
             patch("core.cli.workflow.runtime.runner_rewind._truncate_log_tail_from"), \
             patch("pathlib.Path.unlink", side_effect=OSError("locked")), \
             patch("pathlib.Path.exists", return_value=True):
            _cleanup_artifacts_from_target(vals, "leader_generate", time.time())
        # Should not raise


class TestRewindCurrent:
    def test_delegates_to_resume_workflow(self):
        with patch("core.cli.workflow.runtime.runner_rewind.resume_workflow", return_value=True) as mock_r, \
             patch("core.cli.workflow.runtime.runner_rewind.workflow_event"):
            result = rewind_current()
        assert result is True
        mock_r.assert_called_once()

    def test_returns_false_when_resume_fails(self):
        with patch("core.cli.workflow.runtime.runner_rewind.resume_workflow", return_value=False), \
             patch("core.cli.workflow.runtime.runner_rewind.workflow_event"):
            result = rewind_current()
        assert result is False


class TestRewindToCheckpoint:
    def _mock_ws(self, tid="thread-1", ib=("human_context_gate",)):
        ws = sys.modules.get("core.cli.workflow.runtime.session") or MagicMock()
        ws.get_thread_id = MagicMock(return_value=tid)
        ws.get_interrupt_before = MagicMock(return_value=list(ib))
        return ws

    def test_returns_false_when_no_thread_id(self):
        with patch("core.cli.workflow.runtime.runner_rewind.ws") as mock_ws:
            mock_ws.get_thread_id.return_value = None
            result = rewind_to_checkpoint(0)
        assert result is False

    def test_returns_false_when_history_empty(self):
        mock_graph = MagicMock()
        mock_graph.get_state_history.return_value = []

        with patch("core.cli.workflow.runtime.runner_rewind.ws") as mock_ws, \
             patch("core.cli.workflow.runtime.runner_rewind.get_graph", return_value=mock_graph), \
             patch("core.cli.workflow.runtime.runner_rewind.get_checkpointer", return_value=MagicMock()):
            mock_ws.get_thread_id.return_value = "thread-1"
            mock_ws.get_interrupt_before.return_value = ["human_context_gate"]
            result = rewind_to_checkpoint(0)
        assert result is False

    def test_returns_false_for_out_of_range_index(self):
        mock_snap = SimpleNamespace(values={"brief_dict": {}}, created_at=None, ts=None)
        mock_graph = MagicMock()
        mock_graph.get_state_history.return_value = [mock_snap]

        with patch("core.cli.workflow.runtime.runner_rewind.ws") as mock_ws, \
             patch("core.cli.workflow.runtime.runner_rewind.get_graph", return_value=mock_graph), \
             patch("core.cli.workflow.runtime.runner_rewind.get_checkpointer", return_value=MagicMock()):
            mock_ws.get_thread_id.return_value = "thread-1"
            mock_ws.get_interrupt_before.return_value = []
            result = rewind_to_checkpoint(99)  # out of range
        assert result is False

    def test_returns_false_when_required_keys_missing(self):
        mock_snap = SimpleNamespace(values={"brief_dict": {"task_uuid": "x"}}, created_at=None, ts=None)
        mock_graph = MagicMock()
        mock_graph.get_state_history.return_value = [mock_snap]

        with patch("core.cli.workflow.runtime.runner_rewind.ws") as mock_ws, \
             patch("core.cli.workflow.runtime.runner_rewind.get_graph", return_value=mock_graph), \
             patch("core.cli.workflow.runtime.runner_rewind.get_checkpointer", return_value=MagicMock()):
            mock_ws.get_thread_id.return_value = "thread-1"
            mock_ws.get_interrupt_before.return_value = []
            result = rewind_to_checkpoint(0)
        assert result is False

    def test_state_history_exception_returns_false(self):
        mock_graph = MagicMock()
        mock_graph.get_state_history.side_effect = OSError("db locked")

        with patch("core.cli.workflow.runtime.runner_rewind.ws") as mock_ws, \
             patch("core.cli.workflow.runtime.runner_rewind.get_graph", return_value=mock_graph), \
             patch("core.cli.workflow.runtime.runner_rewind.get_checkpointer", return_value=MagicMock()):
            mock_ws.get_thread_id.return_value = "thread-1"
            mock_ws.get_interrupt_before.return_value = []
            result = rewind_to_checkpoint(0)
        assert result is False

    def test_string_target_matches_last_node(self):
        vals = _make_values(last_node="leader_generate")
        mock_snap = SimpleNamespace(values=vals, created_at=None, ts=None)
        mock_graph = MagicMock()
        mock_graph.get_state_history.return_value = [mock_snap]

        with patch("core.cli.workflow.runtime.runner_rewind.ws") as mock_ws, \
             patch("core.cli.workflow.runtime.runner_rewind.get_graph", return_value=mock_graph), \
             patch("core.cli.workflow.runtime.runner_rewind.get_checkpointer", return_value=MagicMock()), \
             patch("core.cli.workflow.runtime.runner_rewind.workflow_event"), \
             patch("core.cli.workflow.runtime.runner_rewind._cleanup_artifacts_from_target"), \
             patch("core.cli.workflow.runtime.runner_rewind._stream_from_values", return_value=True) as mock_stream:
            mock_ws.get_thread_id.return_value = "thread-1"
            mock_ws.get_interrupt_before.return_value = []
            result = rewind_to_checkpoint("leader_generate")

        assert result is True
        mock_stream.assert_called_once()


class TestRewindToLastGate:
    def test_returns_false_when_no_thread_id(self):
        with patch("core.cli.workflow.runtime.runner_rewind.ws") as mock_ws:
            mock_ws.get_thread_id.return_value = None
            result = rewind_to_last_gate()
        assert result is False

    def test_returns_false_when_history_empty(self):
        mock_graph = MagicMock()
        mock_graph.get_state_history.return_value = []

        with patch("core.cli.workflow.runtime.runner_rewind.ws") as mock_ws, \
             patch("core.cli.workflow.runtime.runner_rewind.get_graph", return_value=mock_graph), \
             patch("core.cli.workflow.runtime.runner_rewind.get_checkpointer", return_value=MagicMock()):
            mock_ws.get_thread_id.return_value = "t1"
            mock_ws.get_interrupt_before.return_value = []
            result = rewind_to_last_gate()
        assert result is False

    def test_returns_false_when_required_keys_missing(self):
        snap = SimpleNamespace(values={"brief_dict": {}}, created_at=None, ts=None)
        mock_graph = MagicMock()
        mock_graph.get_state_history.return_value = [snap]

        with patch("core.cli.workflow.runtime.runner_rewind.ws") as mock_ws, \
             patch("core.cli.workflow.runtime.runner_rewind.get_graph", return_value=mock_graph), \
             patch("core.cli.workflow.runtime.runner_rewind.get_checkpointer", return_value=MagicMock()):
            mock_ws.get_thread_id.return_value = "t1"
            mock_ws.get_interrupt_before.return_value = []
            result = rewind_to_last_gate()
        assert result is False

    def test_streams_from_first_checkpoint_with_context(self):
        vals = _make_values(context_path="/tmp/context.md")
        snap = SimpleNamespace(values=vals, created_at=None, ts=None)
        mock_graph = MagicMock()
        mock_graph.get_state_history.return_value = [snap]

        with patch("core.cli.workflow.runtime.runner_rewind.ws") as mock_ws, \
             patch("core.cli.workflow.runtime.runner_rewind.get_graph", return_value=mock_graph), \
             patch("core.cli.workflow.runtime.runner_rewind.get_checkpointer", return_value=MagicMock()), \
             patch("core.cli.workflow.runtime.runner_rewind.workflow_event"), \
             patch("core.cli.workflow.runtime.runner_rewind._cleanup_artifacts_from_target"), \
             patch("core.cli.workflow.runtime.runner_rewind._stream_from_values", return_value=True) as mock_stream:
            mock_ws.get_thread_id.return_value = "t1"
            mock_ws.get_interrupt_before.return_value = []
            result = rewind_to_last_gate()

        assert result is True
        mock_stream.assert_called_once()

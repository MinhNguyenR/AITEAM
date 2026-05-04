"""Tests for utils/logger.py — artifact detail and event wrappers."""
from pathlib import Path
from unittest.mock import MagicMock, patch

from utils.logger import artifact_detail, log_state_json_deleted_on_accept, log_state_json_written, workflow_event


class TestArtifactDetail:
    def test_basic(self):
        d = artifact_detail("/tmp/state.json")
        assert d["filename"] == "state.json"
        assert d["path"] == str(Path("/tmp/state.json"))
        assert d["task_id"] == ""
        assert d["producer_node"] == ""

    def test_with_kwargs(self):
        d = artifact_detail("/runs/123/state.json", task_id="abc", producer_node="leader")
        assert d["task_id"] == "abc"
        assert d["producer_node"] == "leader"

    def test_path_object(self):
        p = Path("/some/dir/context.md")
        d = artifact_detail(p)
        assert d["filename"] == "context.md"


class TestWorkflowEvent:
    def test_calls_append_workflow_activity(self):
        mock_append = MagicMock()
        with patch("utils.logger.append_workflow_activity", mock_append, create=True):
            # Need to patch the lazy import path
            import sys
            mock_mod = MagicMock()
            mock_mod.append_workflow_activity = mock_append
            with patch.dict(sys.modules, {"core.cli.python_cli.workflow.runtime.persist.activity_log": mock_mod}):
                workflow_event("leader", "done", "detail")
        mock_append.assert_called_once_with("leader", "done", "detail", level="info")

    def test_level_parameter(self):
        mock_append = MagicMock()
        import sys
        mock_mod = MagicMock()
        mock_mod.append_workflow_activity = mock_append
        with patch.dict(sys.modules, {"core.cli.python_cli.workflow.runtime.persist.activity_log": mock_mod}):
            workflow_event("node", "action", "det", level="warning")
        mock_append.assert_called_once_with("node", "action", "det", level="warning")


class TestLogStateJsonWritten:
    def test_delegates_to_workflow_event(self):
        with patch("utils.logger.workflow_event") as mock_ev:
            log_state_json_written("/tmp/state.json", node="leader_generate")
        mock_ev.assert_called_once()
        call_args = mock_ev.call_args[0]
        assert call_args[0] == "leader_generate"
        assert call_args[1] == "state_json_written"

    def test_default_node(self):
        with patch("utils.logger.workflow_event") as mock_ev:
            log_state_json_written("/tmp/state.json")
        assert mock_ev.call_args[0][0] == "ambassador"


class TestLogStateJsonDeletedOnAccept:
    def test_delegates(self):
        with patch("utils.logger.workflow_event") as mock_ev:
            log_state_json_deleted_on_accept("/tmp/state.json")
        mock_ev.assert_called_once()
        assert mock_ev.call_args[0][1] == "state_json_deleted_on_accept"

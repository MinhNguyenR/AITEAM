"""Tests for runner_rewind.py pure helpers — no LangGraph, no API."""
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Patch heavy imports before loading module
import sys
sys.modules.setdefault("agents.team_map._team_map", MagicMock(get_graph=MagicMock()))
sys.modules.setdefault("core.cli.workflow.runtime.checkpointer", MagicMock(get_checkpointer=MagicMock()))

from core.cli.workflow.runtime.runner_rewind import (
    _history_ts,
    _normalize_stream_node_key,
    _task_workspace_from_values,
)


class TestNormalizeStreamNodeKey:
    def test_string_returned_as_is(self):
        assert _normalize_stream_node_key("leader_generate") == "leader_generate"

    def test_tuple_returns_last_element(self):
        assert _normalize_stream_node_key(("a", "b", "c")) == "c"

    def test_empty_tuple_returns_empty(self):
        assert _normalize_stream_node_key(()) == ""

    def test_single_element_tuple(self):
        assert _normalize_stream_node_key(("node",)) == "node"

    def test_non_string_converted(self):
        assert _normalize_stream_node_key(42) == "42"


class TestHistoryTs:
    def test_float_returned_directly(self):
        result = _history_ts(12345.678)
        assert result == pytest.approx(12345.678)

    def test_int_converted_to_float(self):
        assert _history_ts(100) == 100.0

    def test_string_float(self):
        assert _history_ts("12345.0") == 12345.0

    def test_empty_string_returns_now(self):
        before = time.time()
        result = _history_ts("")
        after = time.time()
        assert before <= result <= after

    def test_iso_string_converts(self):
        dt = datetime(2024, 1, 15, 12, 0, 0)
        iso = dt.isoformat()
        result = _history_ts(iso)
        assert isinstance(result, float)
        assert result > 0

    def test_unparseable_string_returns_now(self):
        before = time.time()
        result = _history_ts("not-a-timestamp")
        after = time.time()
        assert before <= result <= after

    def test_other_type_returns_now(self):
        before = time.time()
        result = _history_ts(None)
        after = time.time()
        assert before <= result <= after


class TestTaskWorkspaceFromValues:
    def test_missing_brief_dict_returns_none(self):
        task_id, run_dir = _task_workspace_from_values({})
        assert task_id is None
        assert run_dir is None

    def test_non_dict_brief_dict_returns_none(self):
        task_id, run_dir = _task_workspace_from_values({"brief_dict": "bad"})
        assert task_id is None

    def test_missing_task_uuid_returns_none(self):
        task_id, run_dir = _task_workspace_from_values({"brief_dict": {}})
        assert task_id is None

    def test_valid_uuid_returns_task_id(self):
        import uuid
        uid = str(uuid.uuid4())
        with patch("core.cli.workflow.runtime.runner_rewind.paths_for_task") as mock_paths:
            mock_paths.return_value = MagicMock(run_dir=Path("/fake/dir"))
            task_id, run_dir = _task_workspace_from_values({"brief_dict": {"task_uuid": uid}})
        assert task_id == uid

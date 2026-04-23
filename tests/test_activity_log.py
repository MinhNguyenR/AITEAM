"""Tests for core/cli/workflow/runtime/activity_log.py — JSONL log helpers."""
import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

import core.cli.workflow.runtime.activity_log as al


def _patch_log(tmp_path):
    """Context manager: redirect _log_path() to a temp file."""
    log_file = tmp_path / "workflow_activity.log"
    return patch.object(al, "_log_path", return_value=log_file), log_file


class TestAppendWorkflowActivity:
    def test_creates_log_entry(self, tmp_path):
        ctx, log_file = _patch_log(tmp_path)
        with ctx:
            al.append_workflow_activity("Leader", "start", "task xyz")
        lines = log_file.read_text().splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["node"] == "Leader"
        assert rec["action"] == "start"
        assert rec["detail"] == "task xyz"

    def test_detail_dict_serializes_key_fields(self, tmp_path):
        ctx, log_file = _patch_log(tmp_path)
        with ctx:
            al.append_workflow_activity("Worker", "done", {"task_id": "t1", "status": "ok"})
        rec = json.loads(log_file.read_text().splitlines()[0])
        assert "task_id=t1" in rec["detail"]
        assert "status=ok" in rec["detail"]

    def test_oserror_on_open_is_swallowed(self, tmp_path):
        ctx, log_file = _patch_log(tmp_path)
        with ctx:
            with patch("builtins.open", side_effect=OSError("no dir")):
                al.append_workflow_activity("A", "B", "C")  # must not raise


class TestClearWorkflowActivityLog:
    def test_clears_file(self, tmp_path):
        ctx, log_file = _patch_log(tmp_path)
        with ctx:
            al.append_workflow_activity("X", "Y")
            al.clear_workflow_activity_log()
        assert log_file.read_text() == ""

    def test_missing_file_does_not_raise(self, tmp_path):
        log_file = tmp_path / "missing.log"
        with patch.object(al, "_log_path", return_value=log_file):
            al.clear_workflow_activity_log()


class TestListRecentActivity:
    def test_returns_all_records(self, tmp_path):
        ctx, log_file = _patch_log(tmp_path)
        with ctx:
            al.append_workflow_activity("A", "act1")
            al.append_workflow_activity("B", "act2")
            result = al.list_recent_activity()
        assert len(result) == 2

    def test_respects_limit(self, tmp_path):
        ctx, log_file = _patch_log(tmp_path)
        with ctx:
            for i in range(10):
                al.append_workflow_activity("N", f"act{i}")
            result = al.list_recent_activity(limit=3)
        assert len(result) == 3

    def test_min_ts_filter(self, tmp_path):
        ctx, log_file = _patch_log(tmp_path)
        now = time.time()
        with ctx:
            al.append_workflow_activity("A", "old")
            log_file.write_text(
                json.dumps({"ts": now - 100, "node": "A", "action": "old", "detail": ""}) + "\n"
                + json.dumps({"ts": now + 100, "node": "B", "action": "new", "detail": ""}) + "\n",
                encoding="utf-8",
            )
            result = al.list_recent_activity(min_ts=now)
        assert all(r["action"] == "new" for r in result)

    def test_missing_file_returns_empty(self, tmp_path):
        log_file = tmp_path / "missing.log"
        with patch.object(al, "_log_path", return_value=log_file):
            result = al.list_recent_activity()
        assert result == []

    def test_corrupt_lines_skipped(self, tmp_path):
        ctx, log_file = _patch_log(tmp_path)
        log_file.write_text("NOT JSON\n" + json.dumps({"ts": 1, "node": "X", "action": "y", "detail": ""}) + "\n")
        with ctx:
            result = al.list_recent_activity()
        assert len(result) == 1


class TestTruncateWorkflowActivity:
    def test_keeps_records_before_ts(self, tmp_path):
        ctx, log_file = _patch_log(tmp_path)
        now = time.time()
        log_file.write_text(
            json.dumps({"ts": now - 200, "node": "A", "action": "old", "detail": ""}) + "\n"
            + json.dumps({"ts": now + 200, "node": "B", "action": "new", "detail": ""}) + "\n",
            encoding="utf-8",
        )
        with ctx:
            al.truncate_workflow_activity_from_ts(now)
            result = al.list_recent_activity()
        # Records before ts_start are kept
        assert any(r["action"] == "old" for r in result)
        assert not any(r["action"] == "new" for r in result)


class TestRemoveWorkflowActivity:
    def test_removes_by_node(self, tmp_path):
        ctx, log_file = _patch_log(tmp_path)
        log_file.write_text(
            json.dumps({"ts": 1.0, "node": "Leader", "action": "a", "detail": ""}) + "\n"
            + json.dumps({"ts": 2.0, "node": "Worker", "action": "b", "detail": ""}) + "\n",
            encoding="utf-8",
        )
        with ctx:
            al.remove_workflow_activity(node="Leader", min_ts=0.0)
            result = al.list_recent_activity()
        assert all(r["node"] == "Worker" for r in result)


class TestFormatActivityLines:
    def test_basic_format(self):
        records = [{"ts": time.time(), "node": "Leader", "action": "done", "detail": "ok"}]
        with patch("core.cli.workflow.runtime.activity_log.human_text_for", return_value=""):
            with patch("core.cli.workflow.runtime.activity_log.format_action_with_badge", return_value="done"):
                lines = al.format_activity_lines(records)
        assert len(lines) == 1
        assert "Leader" in lines[0]

    def test_skips_monitor_node(self):
        records = [{"ts": time.time(), "node": "monitor", "action": "x", "detail": ""}]
        lines = al.format_activity_lines(records)
        assert lines == []

    def test_needle_filter(self):
        records = [
            {"ts": time.time(), "node": "A", "action": "found", "detail": "needle"},
            {"ts": time.time(), "node": "B", "action": "other", "detail": "haystack"},
        ]
        with patch("core.cli.workflow.runtime.activity_log.human_text_for", return_value=""):
            with patch("core.cli.workflow.runtime.activity_log.format_action_with_badge", return_value="x"):
                lines = al.format_activity_lines(records, needle="needle")
        assert len(lines) == 1

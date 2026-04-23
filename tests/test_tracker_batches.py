"""Tests for utils/tracker/tracker_batches.py — CLI batch markers."""
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestAppendCliBatch:
    def test_writes_json_line(self, tmp_path):
        p = tmp_path / "batches.jsonl"
        with patch("utils.tracker.tracker_batches.batches_path", return_value=p), \
             patch("utils.tracker.tracker_batches.invalidate_cache"):
            from utils.tracker.tracker_batches import append_cli_batch
            append_cli_batch("ask", "hello world")
        lines = p.read_text().strip().splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["kind"] == "cli_batch"
        assert rec["mode"] == "ask"
        assert rec["prompt"] == "hello world"

    def test_truncates_long_prompt(self, tmp_path):
        p = tmp_path / "batches.jsonl"
        with patch("utils.tracker.tracker_batches.batches_path", return_value=p), \
             patch("utils.tracker.tracker_batches.invalidate_cache"):
            from utils.tracker.tracker_batches import append_cli_batch
            append_cli_batch("ask", "x" * 300)
        rec = json.loads(p.read_text().strip())
        assert len(rec["prompt"]) == 220

    def test_truncates_long_mode(self, tmp_path):
        p = tmp_path / "batches.jsonl"
        with patch("utils.tracker.tracker_batches.batches_path", return_value=p), \
             patch("utils.tracker.tracker_batches.invalidate_cache"):
            from utils.tracker.tracker_batches import append_cli_batch
            append_cli_batch("a" * 30, "prompt")
        rec = json.loads(p.read_text().strip())
        assert len(rec["mode"]) == 16

    def test_oserror_swallowed(self, tmp_path):
        with patch("utils.tracker.tracker_batches.batches_path", return_value=tmp_path / "batches.jsonl"), \
             patch("builtins.open", side_effect=OSError("disk full")):
            from utils.tracker.tracker_batches import append_cli_batch
            append_cli_batch("ask", "test")  # should not raise

    def test_invalidates_cache(self, tmp_path):
        p = tmp_path / "batches.jsonl"
        mock_inv = MagicMock()
        with patch("utils.tracker.tracker_batches.batches_path", return_value=p), \
             patch("utils.tracker.tracker_batches.invalidate_cache", mock_inv):
            from utils.tracker.tracker_batches import append_cli_batch
            append_cli_batch("ask", "hi")
        mock_inv.assert_called_once_with("cli_batches:")


class TestReadCliBatchesTail:
    def _write_batches(self, path: Path, records: list) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

    def test_empty_when_no_file(self, tmp_path):
        p = tmp_path / "no_batches.jsonl"
        with patch("utils.tracker.tracker_batches.batches_path", return_value=p), \
             patch("utils.tracker.tracker_batches.cache_get", return_value=None), \
             patch("utils.tracker.tracker_batches.cache_set", side_effect=lambda k, v: v):
            from utils.tracker.tracker_batches import read_cli_batches_tail
            result = read_cli_batches_tail()
        assert result == []

    def test_reads_valid_records(self, tmp_path):
        p = tmp_path / "batches.jsonl"
        self._write_batches(p, [
            {"kind": "cli_batch", "timestamp": "2024-06-01T10:00:00", "mode": "ask", "prompt": "hi"},
            {"kind": "cli_batch", "timestamp": "2024-06-01T11:00:00", "mode": "ask", "prompt": "bye"},
        ])
        with patch("utils.tracker.tracker_batches.batches_path", return_value=p), \
             patch("utils.tracker.tracker_batches.cache_get", return_value=None), \
             patch("utils.tracker.tracker_batches.cache_set", side_effect=lambda k, v: v):
            from utils.tracker.tracker_batches import read_cli_batches_tail
            result = read_cli_batches_tail()
        assert len(result) == 2
        assert result[0]["prompt"] == "hi"

    def test_skips_non_cli_batch_records(self, tmp_path):
        p = tmp_path / "batches.jsonl"
        self._write_batches(p, [
            {"kind": "usage", "timestamp": "2024-06-01T10:00:00"},
            {"kind": "cli_batch", "timestamp": "2024-06-01T11:00:00", "mode": "ask", "prompt": "ok"},
        ])
        with patch("utils.tracker.tracker_batches.batches_path", return_value=p), \
             patch("utils.tracker.tracker_batches.cache_get", return_value=None), \
             patch("utils.tracker.tracker_batches.cache_set", side_effect=lambda k, v: v):
            from utils.tracker.tracker_batches import read_cli_batches_tail
            result = read_cli_batches_tail()
        assert len(result) == 1

    def test_skips_invalid_json_lines(self, tmp_path):
        p = tmp_path / "batches.jsonl"
        with open(p, "w") as f:
            f.write("not json\n")
            f.write(json.dumps({"kind": "cli_batch", "timestamp": "2024-06-01T10:00:00", "mode": "ask", "prompt": "x"}) + "\n")
        with patch("utils.tracker.tracker_batches.batches_path", return_value=p), \
             patch("utils.tracker.tracker_batches.cache_get", return_value=None), \
             patch("utils.tracker.tracker_batches.cache_set", side_effect=lambda k, v: v):
            from utils.tracker.tracker_batches import read_cli_batches_tail
            result = read_cli_batches_tail()
        assert len(result) == 1

    def test_returns_cached_value(self, tmp_path):
        p = tmp_path / "batches.jsonl"
        p.write_text("")  # file must exist to pass the early-return check
        cached = [{"kind": "cli_batch", "prompt": "from_cache"}]
        with patch("utils.tracker.tracker_batches.batches_path", return_value=p), \
             patch("utils.tracker.tracker_batches.cache_get", return_value=cached):
            from utils.tracker.tracker_batches import read_cli_batches_tail
            result = read_cli_batches_tail()
        assert result == cached

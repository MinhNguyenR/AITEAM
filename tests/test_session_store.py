"""Tests for core/cli/workflow/runtime/session_store.py — JSON file I/O."""
import json
import threading
from pathlib import Path
from unittest.mock import patch

from core.cli.workflow.runtime.session_store import load_session_data, save_session_data


class TestLoadSessionData:
    def test_returns_empty_when_file_missing(self, tmp_path):
        result = load_session_data(tmp_path / "no_such.json")
        assert result == {}

    def test_reads_valid_json(self, tmp_path):
        p = tmp_path / "session.json"
        p.write_text('{"key": "val", "num": 42}', encoding="utf-8")
        result = load_session_data(p)
        assert result == {"key": "val", "num": 42}

    def test_returns_empty_on_json_decode_error(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not valid json {{{{", encoding="utf-8")
        assert load_session_data(p) == {}

    def test_returns_empty_on_oserror(self, tmp_path):
        p = tmp_path / "session.json"
        p.write_text("{}", encoding="utf-8")
        with patch("pathlib.Path.read_text", side_effect=OSError("perm")):
            result = load_session_data(p)
        assert result == {}


class TestSaveSessionData:
    def test_writes_json(self, tmp_path):
        p = tmp_path / "session.json"
        save_session_data(p, {"hello": "world"})
        data = json.loads(p.read_text())
        assert data == {"hello": "world"}

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "nested" / "dir" / "session.json"
        save_session_data(p, {"x": 1})
        assert p.is_file()

    def test_roundtrip(self, tmp_path):
        p = tmp_path / "session.json"
        original = {"list": [1, 2, 3], "nested": {"a": "b"}}
        save_session_data(p, original)
        loaded = load_session_data(p)
        assert loaded == original

    def test_concurrent_writes_are_safe(self, tmp_path):
        p = tmp_path / "session.json"
        errors = []

        def write_data(i):
            try:
                save_session_data(p, {"i": i})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_data, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        # File should be valid JSON
        data = json.loads(p.read_text())
        assert "i" in data

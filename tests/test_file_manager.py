"""Tests for utils/file_manager.py — path helpers and atomic_write_text."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_config(tmp_path: Path):
    mock_cfg = MagicMock()
    mock_cfg.cache_root = tmp_path / "cache"
    return mock_cfg


class TestGetCacheRoot:
    def test_creates_dir(self, tmp_path):
        cfg = _make_config(tmp_path)
        with patch("utils.file_manager.config", cfg):
            from utils.file_manager import get_cache_root
            result = get_cache_root()
        assert result.is_dir()

    def test_returns_configured_root(self, tmp_path):
        cfg = _make_config(tmp_path)
        with patch("utils.file_manager.config", cfg):
            from utils.file_manager import get_cache_root
            result = get_cache_root()
        assert result == cfg.cache_root


class TestSafeJoin:
    def test_escape_raises(self, tmp_path):
        from utils.file_manager import _safe_join
        root = tmp_path / "root"
        root.mkdir()
        with pytest.raises(ValueError, match="escapes"):
            _safe_join(root, "..", "secret.txt")

    def test_valid_path(self, tmp_path):
        from utils.file_manager import _safe_join
        root = tmp_path / "root"
        root.mkdir()
        result = _safe_join(root, "subdir", "file.txt")
        assert str(root) in str(result)


class TestAtomicWriteText:
    def test_writes_file(self, tmp_path):
        cfg = _make_config(tmp_path)
        cache = tmp_path / "cache"
        cache.mkdir()
        cfg.cache_root = cache
        target = cache / "out.txt"
        with patch("utils.file_manager.config", cfg):
            from utils.file_manager import atomic_write_text
            atomic_write_text(target, "hello world")
        assert target.read_text() == "hello world"

    def test_rejects_outside_cache(self, tmp_path):
        cfg = _make_config(tmp_path)
        cache = tmp_path / "cache"
        cache.mkdir()
        cfg.cache_root = cache
        outside = tmp_path / "outside.txt"
        with patch("utils.file_manager.config", cfg):
            from utils.file_manager import atomic_write_text
            with pytest.raises(ValueError, match="Refuse"):
                atomic_write_text(outside, "evil")

    def test_no_tmp_file_left_on_success(self, tmp_path):
        cfg = _make_config(tmp_path)
        cache = tmp_path / "cache"
        cache.mkdir()
        cfg.cache_root = cache
        target = cache / "clean.txt"
        with patch("utils.file_manager.config", cfg):
            from utils.file_manager import atomic_write_text
            atomic_write_text(target, "data")
        tmp_files = list(cache.glob(".clean.txt.*.tmp"))
        assert tmp_files == []


class TestEnsureDirs:
    def test_ensure_run_dir(self, tmp_path):
        cfg = _make_config(tmp_path)
        cache = tmp_path / "cache"
        cache.mkdir()
        cfg.cache_root = cache
        with patch("utils.file_manager.config", cfg):
            from utils.file_manager import ensure_run_dir
            result = ensure_run_dir("task-uuid-123")
        assert result.is_dir()
        assert "task-uuid-123" in str(result)

    def test_ensure_db_dir(self, tmp_path):
        cfg = _make_config(tmp_path)
        cache = tmp_path / "cache"
        cache.mkdir()
        cfg.cache_root = cache
        with patch("utils.file_manager.config", cfg):
            from utils.file_manager import ensure_db_dir
            result = ensure_db_dir()
        assert result.is_dir()
        assert "db" in str(result)

    def test_ensure_workflow_dir(self, tmp_path):
        cfg = _make_config(tmp_path)
        cache = tmp_path / "cache"
        cache.mkdir()
        cfg.cache_root = cache
        with patch("utils.file_manager.config", cfg):
            from utils.file_manager import ensure_workflow_dir
            result = ensure_workflow_dir()
        assert result.is_dir()

    def test_ensure_ask_data_dir(self, tmp_path):
        cfg = _make_config(tmp_path)
        cache = tmp_path / "cache"
        cache.mkdir()
        cfg.cache_root = cache
        with patch("utils.file_manager.config", cfg):
            from utils.file_manager import ensure_ask_data_dir
            result = ensure_ask_data_dir()
        assert result.is_dir()


class TestPathsForTask:
    def test_returns_task_workspace(self, tmp_path):
        cfg = _make_config(tmp_path)
        cache = tmp_path / "cache"
        cache.mkdir()
        cfg.cache_root = cache
        with patch("utils.file_manager.config", cfg):
            from utils.file_manager import paths_for_task
            ws = paths_for_task("test-uuid-456")
        assert ws.task_uuid == "test-uuid-456"
        assert ws.run_dir.is_dir()
        assert "state" in ws.state_path.name or ws.state_path.suffix == ".json"
        assert ws.context_path.parent == ws.run_dir
        assert ws.validation_report_path.parent == ws.run_dir


class TestLatestContextPath:
    def test_returns_none_when_no_runs(self, tmp_path):
        cfg = _make_config(tmp_path)
        cache = tmp_path / "cache"
        cache.mkdir()
        cfg.cache_root = cache
        with patch("utils.file_manager.config", cfg):
            from utils.file_manager import latest_context_path
            result = latest_context_path()
        assert result is None

    def test_returns_latest_context(self, tmp_path):
        cfg = _make_config(tmp_path)
        cache = tmp_path / "cache"
        cache.mkdir()
        cfg.cache_root = cache
        runs = cache / "runs"
        runs.mkdir()
        run1 = runs / "run1"
        run1.mkdir()
        ctx1 = run1 / "context.md"
        ctx1.write_text("ctx1")
        run2 = runs / "run2"
        run2.mkdir()
        ctx2 = run2 / "context.md"
        ctx2.write_text("ctx2")
        # Touch run2/context.md to make it newer
        import time
        time.sleep(0.01)
        ctx2.touch()
        with patch("utils.file_manager.config", cfg):
            from utils.file_manager import latest_context_path
            result = latest_context_path()
        assert result == ctx2

    def test_ignores_non_dirs(self, tmp_path):
        cfg = _make_config(tmp_path)
        cache = tmp_path / "cache"
        cache.mkdir()
        cfg.cache_root = cache
        runs = cache / "runs"
        runs.mkdir()
        (runs / "file.txt").write_text("not a dir")
        with patch("utils.file_manager.config", cfg):
            from utils.file_manager import latest_context_path
            result = latest_context_path()
        assert result is None

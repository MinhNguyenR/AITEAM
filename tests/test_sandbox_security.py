"""Security tests: sandbox injection, path traversal, backup restore safety."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from core.sandbox.policy import is_command_safe
from core.sandbox._path_guard import resolve_under_project_root


@pytest.fixture(autouse=True)
def _isolated_code_backup_db(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_TEAM_CODE_BACKUP_DB", str(tmp_path / "code_backups.db"))


class TestCommandPolicy:
    def test_shell_chaining_blocked(self):
        for cmd in ["echo a && echo b", "echo a || echo b", "echo a; echo b"]:
            safe, reason = is_command_safe(cmd)
            assert not safe, f"should block: {cmd!r}"
            assert "chaining" in reason

    def test_pipe_blocked(self):
        safe, reason = is_command_safe("cat file | sh")
        assert not safe

    def test_backtick_blocked(self):
        safe, reason = is_command_safe("echo `id`")
        assert not safe

    def test_subshell_blocked(self):
        safe, reason = is_command_safe("echo $(id)")
        assert not safe

    def test_redirect_blocked(self):
        for cmd in ["echo hi > /tmp/x", "cat < /etc/passwd"]:
            safe, reason = is_command_safe(cmd)
            assert not safe, f"should block: {cmd!r}"

    def test_destructive_rm_blocked(self):
        safe, reason = is_command_safe("rm -rf /")
        assert not safe

    def test_allowed_pytest(self):
        safe, reason = is_command_safe("pytest tests/test_foo.py")
        assert safe

    def test_allowed_python_module(self):
        safe, reason = is_command_safe("python -m mypy path/to/file.py")
        assert safe

    def test_allowed_ruff(self):
        safe, reason = is_command_safe("ruff check .")
        assert safe

    def test_empty_command_blocked(self):
        safe, _ = is_command_safe("")
        assert not safe

    def test_unknown_prefix_blocked(self):
        safe, _ = is_command_safe("curl http://evil.com")
        assert not safe


class TestPathGuard:
    def test_relative_path_allowed(self, tmp_path):
        result = resolve_under_project_root(tmp_path, "subdir/file.py")
        assert result == (tmp_path / "subdir" / "file.py").resolve()

    def test_traversal_rejected(self, tmp_path):
        assert resolve_under_project_root(tmp_path, "../outside.py") is None

    def test_deep_traversal_rejected(self, tmp_path):
        assert resolve_under_project_root(tmp_path, "a/b/../../../../../../etc/passwd") is None

    def test_absolute_path_rejected(self, tmp_path):
        assert resolve_under_project_root(tmp_path, "/etc/passwd") is None

    def test_windows_drive_rejected(self, tmp_path):
        assert resolve_under_project_root(tmp_path, "C:/Windows/system32") is None

    def test_empty_path_rejected(self, tmp_path):
        assert resolve_under_project_root(tmp_path, "") is None

    def test_path_within_root_accepted(self, tmp_path):
        (tmp_path / "src").mkdir()
        result = resolve_under_project_root(tmp_path, "src/main.py")
        assert result is not None
        assert result.is_relative_to(tmp_path)


class TestWorkerWriteGuard:
    def test_allowed_paths_use_normalized_target(self, tmp_path, monkeypatch):
        from agents.worker import Worker

        worker = Worker()
        raw = "--- FILE: src/../other.py ---\nprint('x')\n--- END FILE ---"
        written, errors = worker._write_files(
            raw,
            str(tmp_path),
            "task",
            None,
            allowed_paths=["src/*"],
        )
        assert written == []
        assert errors
        assert not (tmp_path / "other.py").exists()


class TestRestoreSafety:
    def test_restore_backup_rejects_outside_root(self, tmp_path):
        from core.storage.code_backup import backup_file, restore_backup

        # Backup a file using a path outside the restore root
        backup_id = backup_file("/etc/passwd", "root:x:0:0", task_uuid="test-uuid")
        with pytest.raises(ValueError, match="outside project root"):
            restore_backup(backup_id, str(tmp_path))

    def test_restore_backup_within_root_succeeds(self, tmp_path):
        from core.storage.code_backup import backup_file, restore_backup

        content = "print('hello')"
        backup_id = backup_file("src/main.py", content, task_uuid="test-uuid-2")
        result = restore_backup(backup_id, str(tmp_path))
        assert result["restored_to"].startswith(str(tmp_path))
        assert (tmp_path / "src" / "main.py").read_text() == content

    def test_search_backups_empty_query_scoped_by_project(self, tmp_path):
        from core.storage.code_backup import backup_file, search_backups

        root = str(tmp_path)
        backup_file("a.py", "content-a", task_uuid="scoped-task", project_root=root)

        # Empty query with project_root should only return entries for that root
        results = search_backups("", project_root=root)
        assert all(r["file_path"] == "a.py" for r in results)

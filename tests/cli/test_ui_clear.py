from __future__ import annotations

from unittest import mock

from core.cli.python_cli.ui import ui


def test_clear_screen_uses_subprocess_when_no_ansi(monkeypatch):
    monkeypatch.setattr(ui, "_supports_ansi_clear", lambda: False)
    monkeypatch.setattr(ui.os, "name", "nt")
    with mock.patch.object(ui.subprocess, "run") as run:
        ui.clear_screen()
    run.assert_called_once_with(["cmd", "/c", "cls"], check=False, shell=False)


def test_clear_screen_unix_uses_clear(monkeypatch):
    monkeypatch.setattr(ui, "_supports_ansi_clear", lambda: False)
    monkeypatch.setattr(ui.os, "name", "posix")
    with mock.patch.object(ui.subprocess, "run") as run:
        ui.clear_screen()
    run.assert_called_once_with(["clear"], check=False, shell=False)

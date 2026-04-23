from __future__ import annotations

import pytest

from core.cli.workflow.runtime import session as ws


@pytest.fixture()
def _fresh_session(tmp_path, monkeypatch):
    sess_file = tmp_path / "workflow_session.json"
    sess_file.write_text("{}", encoding="utf-8")
    from core.cli.workflow.runtime import session_store, _session_core

    monkeypatch.setattr(session_store, "SESSION_FILE", sess_file, raising=False)
    monkeypatch.setattr(ws, "SESSION_FILE", sess_file, raising=False)
    monkeypatch.setattr(_session_core, "SESSION_FILE", sess_file, raising=False)
    yield sess_file


def test_toast_queue_fifo_rotates_per_duration(_fresh_session, monkeypatch):
    now = {"t": 1000.0}
    monkeypatch.setattr(ws.time, "time", lambda: now["t"])

    ws.set_pipeline_toast("first", seconds=3.0)
    ws.set_pipeline_toast("second", seconds=3.0)
    ws.set_pipeline_toast("third", seconds=3.0)

    assert ws.get_pipeline_toast_text() == "first"

    now["t"] = 1002.0
    assert ws.get_pipeline_toast_text() == "first"

    now["t"] = 1003.5
    assert ws.get_pipeline_toast_text() == "second"

    now["t"] = 1006.6
    assert ws.get_pipeline_toast_text() == "third"

    now["t"] = 1010.0
    assert ws.get_pipeline_toast_text() == ""


def test_toast_empty_message_ignored(_fresh_session, monkeypatch):
    now = {"t": 500.0}
    monkeypatch.setattr(ws.time, "time", lambda: now["t"])

    ws.set_pipeline_toast("", seconds=3.0)
    ws.set_pipeline_toast("   ", seconds=3.0)
    assert ws.get_pipeline_toast_text() == ""

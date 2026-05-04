"""Tests for session_monitor_manager.py — monitor PID management."""
from unittest.mock import patch
import core.cli.python_cli.workflow.runtime.session.session_monitor_manager as smm


def _patch_session(initial: dict | None = None):
    store = [dict(initial or {})]
    def _load(): return dict(store[0])
    def _save(s): store[0] = dict(s)
    lp = patch.object(smm, "load_session", side_effect=_load)
    sp = patch.object(smm, "save_session", side_effect=_save)
    return lp, sp, store


class TestGetMonitorPid:
    def test_returns_none_when_missing(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            assert smm.get_monitor_pid() is None

    def test_returns_pid_as_int(self):
        lp, sp, _ = _patch_session({"monitor_pid": 12345})
        with lp, sp:
            assert smm.get_monitor_pid() == 12345

    def test_invalid_pid_returns_none(self):
        lp, sp, _ = _patch_session({"monitor_pid": "bad"})
        with lp, sp:
            assert smm.get_monitor_pid() is None


class TestSetMonitorPid:
    def test_sets_valid_pid(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            smm.set_monitor_pid(9999)
        assert store[0]["monitor_pid"] == 9999

    def test_none_removes_key(self):
        lp, sp, store = _patch_session({"monitor_pid": 1234})
        with lp, sp:
            smm.set_monitor_pid(None)
        assert "monitor_pid" not in store[0]

    def test_zero_removes_key(self):
        lp, sp, store = _patch_session({"monitor_pid": 1234})
        with lp, sp:
            smm.set_monitor_pid(0)
        assert "monitor_pid" not in store[0]


class TestClearMonitorPid:
    def test_removes_pid(self):
        lp, sp, store = _patch_session({"monitor_pid": 1111})
        with lp, sp:
            smm.clear_monitor_pid()
        assert "monitor_pid" not in store[0]

    def test_no_error_when_already_absent(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            smm.clear_monitor_pid()

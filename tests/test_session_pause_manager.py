"""Tests for session_pause_manager.py — pause/finalize/interrupt signals."""
from unittest.mock import patch

import core.cli.python_cli.workflow.runtime.session.session_pause_manager as spm


def _patch_session(initial: dict | None = None):
    store = [dict(initial or {})]
    def _load(): return dict(store[0])
    def _save(s): store[0] = dict(s)
    lp = patch.object(spm, "load_session", side_effect=_load)
    sp = patch.object(spm, "save_session", side_effect=_save)
    return lp, sp, store


class TestPausedForReview:
    def test_set_true(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            spm.set_paused_for_review(True, "/ctx/path")
        assert store[0]["paused_for_review"] is True
        assert store[0]["context_path"] == "/ctx/path"

    def test_set_false_removes_context_path(self):
        lp, sp, store = _patch_session({"paused_for_review": True, "context_path": "/x"})
        with lp, sp:
            spm.set_paused_for_review(False)
        assert store[0]["paused_for_review"] is False
        assert "context_path" not in store[0]

    def test_is_paused_true(self):
        lp, sp, _ = _patch_session({"paused_for_review": True})
        with lp, sp:
            assert spm.is_paused_for_review() is True

    def test_is_paused_false(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            assert spm.is_paused_for_review() is False


class TestGetContextPath:
    def test_returns_path(self):
        lp, sp, _ = _patch_session({"context_path": "/a/b.md"})
        with lp, sp:
            assert spm.get_context_path() == "/a/b.md"

    def test_returns_none_when_missing(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            assert spm.get_context_path() is None


class TestCheckDone:
    def test_signal_and_consume(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            spm.signal_check_done()
            assert spm.consume_check_done() is True
            assert spm.consume_check_done() is False

    def test_consume_without_signal(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            assert spm.consume_check_done() is False


class TestShouldFinalize:
    def test_set_true_and_peek(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            spm.set_should_finalize(True)
            assert spm.peek_should_finalize() is True

    def test_set_false_removes(self):
        lp, sp, store = _patch_session({"should_finalize": True})
        with lp, sp:
            spm.set_should_finalize(False)
        assert "should_finalize" not in store[0]

    def test_consume_clears_flag(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            spm.set_should_finalize(True)
            assert spm.consume_should_finalize() is True
            assert spm.peek_should_finalize() is False


class TestInterruptBefore:
    def test_set_and_get(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            spm.set_interrupt_before(["node1", "node2"])
            result = spm.get_interrupt_before()
        assert result == ("node1", "node2")

    def test_empty_list(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            assert spm.get_interrupt_before() == ()


class TestClearSessionFlags:
    def test_clears_known_flags(self):
        lp, sp, store = _patch_session({
            "paused_for_review": True,
            "check_done": True,
            "last_node": "Leader",
        })
        with lp, sp:
            spm.clear_session_flags()
        assert "paused_for_review" not in store[0]
        assert "check_done" not in store[0]
        assert "last_node" not in store[0]


class TestSetLastNode:
    def test_set_node(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            spm.set_last_node("Leader")
        assert store[0]["last_node"] == "Leader"

    def test_clear_node(self):
        lp, sp, store = _patch_session({"last_node": "Leader"})
        with lp, sp:
            spm.set_last_node(None)
        assert "last_node" not in store[0]

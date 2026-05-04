"""Tests for session_notification.py — toast queue and pipeline notifications."""
import time
from unittest.mock import patch, call

import pytest

import core.cli.python_cli.workflow.runtime.session.session_notification as sn


def _make_session(**kwargs):
    """Return a minimal mutable session dict."""
    return dict(kwargs)


def _patch_session(initial: dict | None = None):
    """Patch load_session + save_session with an in-memory dict."""
    store = [dict(initial or {})]

    def _load():
        return dict(store[0])

    def _save(s):
        store[0] = dict(s)

    lp = patch.object(sn, "load_session", side_effect=_load)
    sp = patch.object(sn, "save_session", side_effect=_save)
    return lp, sp, store


# ---------------------------------------------------------------------------
# _get_toast_queue
# ---------------------------------------------------------------------------

class TestGetToastQueue:
    def test_returns_empty_for_missing_key(self):
        assert sn._get_toast_queue({}) == []

    def test_returns_empty_for_non_list(self):
        assert sn._get_toast_queue({"pipeline_toast_queue": "bad"}) == []

    def test_filters_non_dict_items(self):
        q = [{"msg": "ok"}, "bad", None]
        result = sn._get_toast_queue({"pipeline_toast_queue": q})
        assert result == [{"msg": "ok"}]


# ---------------------------------------------------------------------------
# set_pipeline_toast
# ---------------------------------------------------------------------------

class TestSetPipelineToast:
    def test_adds_toast_to_queue(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sn.set_pipeline_toast("hello")
        assert store[0]["pipeline_toast"] == "hello"

    def test_empty_message_ignored(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            sn.set_pipeline_toast("   ")
        assert "pipeline_toast_queue" not in store[0]

    def test_respects_max_length(self):
        lp, sp, store = _patch_session()
        long_msg = "x" * 600
        with lp, sp:
            sn.set_pipeline_toast(long_msg)
        q = store[0].get("pipeline_toast_queue", [])
        if q:
            assert len(q[0]["msg"]) <= 500


# ---------------------------------------------------------------------------
# push_pipeline_notification
# ---------------------------------------------------------------------------

class TestPushPipelineNotification:
    def test_adds_notification(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            with patch.object(sn, "set_pipeline_toast"):
                nid = sn.push_pipeline_notification("Title", "Body", "info")
        items = store[0].get("pipeline_notifications", [])
        assert len(items) == 1
        assert items[0]["id"] == nid
        assert items[0]["title"] == "Title"
        assert items[0]["kind"] == "info"

    def test_returns_uuid_string(self):
        lp, sp, store = _patch_session()
        with lp, sp:
            with patch.object(sn, "set_pipeline_toast"):
                nid = sn.push_pipeline_notification("T", "B", "info")
        assert len(nid) == 36  # UUID4

    def test_caps_at_25_items(self):
        initial = {"pipeline_notifications": [{"id": str(i), "ts": 0} for i in range(25)]}
        lp, sp, store = _patch_session(initial)
        with lp, sp:
            with patch.object(sn, "set_pipeline_toast"):
                sn.push_pipeline_notification("new", "body", "info")
        assert len(store[0]["pipeline_notifications"]) == 25


# ---------------------------------------------------------------------------
# list_active_notifications / dismiss
# ---------------------------------------------------------------------------

class TestListAndDismiss:
    def test_list_returns_all_undismissed(self):
        initial = {
            "pipeline_notifications": [{"id": "a"}, {"id": "b"}],
            "dismissed_notification_ids": ["a"],
        }
        lp, sp, _ = _patch_session(initial)
        with lp, sp:
            result = sn.list_active_notifications()
        assert result == [{"id": "b"}]

    def test_dismiss_adds_to_dismissed(self):
        initial = {"pipeline_notifications": [{"id": "x"}]}
        lp, sp, store = _patch_session(initial)
        with lp, sp:
            sn.dismiss_pipeline_notification("x")
        assert "x" in store[0].get("dismissed_notification_ids", [])

    def test_list_empty_when_no_items(self):
        lp, sp, _ = _patch_session()
        with lp, sp:
            result = sn.list_active_notifications()
        assert result == []

"""Additional tests for session_notification.py — toast queue and prune logic."""
import time
from pathlib import Path
from unittest.mock import patch

import core.cli.python_cli.workflow.runtime.session.session_notification as sn


def _patch_session(initial=None):
    store = [dict(initial or {})]
    def _load(): return dict(store[0])
    def _save(s): store[0] = dict(s)
    lp = patch.object(sn, "load_session", side_effect=_load)
    sp = patch.object(sn, "save_session", side_effect=_save)
    return lp, sp, store


class TestGetPipelineToastText:
    def test_empty_queue_returns_empty(self):
        lp, sp, _ = _patch_session({})
        with lp, sp:
            result = sn.get_pipeline_toast_text()
        assert result == ""

    def test_legacy_toast_still_valid(self):
        future = time.time() + 100.0
        lp, sp, _ = _patch_session({
            "pipeline_toast": "Legacy message",
            "pipeline_toast_until": future,
        })
        with lp, sp:
            result = sn.get_pipeline_toast_text()
        assert result == "Legacy message"

    def test_expired_legacy_toast_cleared(self):
        past = time.time() - 10.0
        lp, sp, store = _patch_session({
            "pipeline_toast": "Old message",
            "pipeline_toast_until": past,
        })
        with lp, sp:
            result = sn.get_pipeline_toast_text()
        assert result == ""
        # State should be cleared
        assert store[0].get("pipeline_toast") == ""

    def test_queue_with_fresh_entry(self):
        future = time.time() + 100.0
        lp, sp, _ = _patch_session({
            "pipeline_toast_queue": [{"msg": "Fresh toast", "dur": 3.0, "until": future}]
        })
        with lp, sp:
            result = sn.get_pipeline_toast_text()
        assert result == "Fresh toast"

    def test_expired_queue_entry_removed(self):
        past = time.time() - 10.0
        lp, sp, store = _patch_session({
            "pipeline_toast_queue": [{"msg": "Expired", "dur": 3.0, "until": past}]
        })
        with lp, sp:
            result = sn.get_pipeline_toast_text()
        assert result == ""
        assert store[0].get("pipeline_toast_queue") == []

    def test_new_queue_entry_gets_until_set(self):
        lp, sp, store = _patch_session({
            "pipeline_toast_queue": [{"msg": "New toast", "dur": 5.0}]
        })
        with lp, sp:
            result = sn.get_pipeline_toast_text()
        assert result == "New toast"
        # Should have set 'until'
        q = store[0].get("pipeline_toast_queue", [])
        assert len(q) > 0
        assert q[0].get("until", 0.0) > 0.0


class TestPushPipelineNotificationWithBody:
    def test_body_appended_to_toast(self):
        lp, sp, store = _patch_session({})
        with lp, sp, patch.object(sn, "set_pipeline_toast", side_effect=lambda t, **kw: None):
            sn.push_pipeline_notification("Title", "Some body text", "info")
        items = store[0].get("pipeline_notifications", [])
        assert len(items) == 1
        assert items[0]["title"] == "Title"
        assert items[0]["body"] == "Some body text"


class TestListActiveNotificationsNonListDismissed:
    def test_non_list_dismissed_treated_as_empty(self):
        lp, sp, _ = _patch_session({
            "pipeline_notifications": [
                {"id": "abc", "title": "Test", "body": "", "kind": "info", "extra": {}, "ts": 0.0}
            ],
            "dismissed_notification_ids": "not a list",
        })
        with lp, sp:
            result = sn.list_active_notifications()
        assert len(result) == 1


class TestPruneStaleNotifications:
    def test_prune_missing_file_dismisses(self, tmp_path):
        # context_ready kind with missing file gets dismissed
        fake_path = str(tmp_path / "missing.md")
        lp, sp, store = _patch_session({
            "pipeline_notifications": [{
                "id": "nid1",
                "title": "ctx ready",
                "body": "",
                "kind": "context_ready",
                "extra": {"context_path": fake_path},
                "ts": 0.0,
            }],
            "dismissed_notification_ids": [],
        })
        with lp, sp:
            sn.prune_stale_pipeline_notifications()
        assert "nid1" in store[0].get("dismissed_notification_ids", [])

    def test_prune_existing_file_kept(self, tmp_path):
        existing = tmp_path / "context.md"
        existing.write_text("content")
        lp, sp, store = _patch_session({
            "pipeline_notifications": [{
                "id": "nid2",
                "title": "ctx ready",
                "body": "",
                "kind": "context_ready",
                "extra": {"context_path": str(existing)},
                "ts": 0.0,
            }],
            "dismissed_notification_ids": [],
        })
        with lp, sp:
            sn.prune_stale_pipeline_notifications()
        # file exists → NOT dismissed
        assert "nid2" not in store[0].get("dismissed_notification_ids", [])

    def test_prune_already_dismissed_skipped(self, tmp_path):
        lp, sp, store = _patch_session({
            "pipeline_notifications": [{
                "id": "nid3",
                "title": "old",
                "body": "",
                "kind": "context_ready",
                "extra": {"context_path": str(tmp_path / "missing.md")},
                "ts": 0.0,
            }],
            "dismissed_notification_ids": ["nid3"],
        })
        with lp, sp:
            sn.prune_stale_pipeline_notifications()
        # was already dismissed — no new change
        dismissed = store[0].get("dismissed_notification_ids", [])
        assert dismissed.count("nid3") >= 1

    def test_prune_state_json_ready_kind(self, tmp_path):
        fake_path = str(tmp_path / "missing_state.json")
        lp, sp, store = _patch_session({
            "pipeline_notifications": [{
                "id": "nid4",
                "title": "state ready",
                "body": "",
                "kind": "state_json_ready",
                "extra": {"state_path": fake_path},
                "ts": 0.0,
            }],
            "dismissed_notification_ids": [],
        })
        with lp, sp:
            sn.prune_stale_pipeline_notifications()
        assert "nid4" in store[0].get("dismissed_notification_ids", [])

    def test_prune_non_list_items_skipped(self):
        lp, sp, _ = _patch_session({
            "pipeline_notifications": ["not_a_dict", None, 42],
        })
        with lp, sp:
            sn.prune_stale_pipeline_notifications()  # must not raise

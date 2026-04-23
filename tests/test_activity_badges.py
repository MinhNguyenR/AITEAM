"""Tests for utils/activity_badges.py — badge and human text helpers."""
from utils.activity_badges import (
    ACTION_BADGES,
    badge_for_action,
    format_action_with_badge,
    human_text_for,
)


class TestBadgeForAction:
    def test_known_action(self):
        assert badge_for_action("done") == ACTION_BADGES["done"]

    def test_unknown_action_returns_empty(self):
        assert badge_for_action("nonexistent_action_xyz") == ""

    def test_context_written(self):
        assert "CTX" in badge_for_action("context_written")

    def test_paused_review(self):
        assert "PAUSE" in badge_for_action("paused_review")


class TestHumanTextFor:
    def test_known_node_action(self):
        text = human_text_for("ambassador", "enter")
        assert len(text) > 0
        assert "Ambassador" in text

    def test_unknown_pair_returns_empty(self):
        text = human_text_for("unknown_node", "unknown_action")
        assert text == ""

    def test_detail_interpolated(self):
        text = human_text_for("ambassador", "done", detail="LOW")
        assert "LOW" in text

    def test_case_insensitive(self):
        text = human_text_for("AMBASSADOR", "ENTER")
        assert len(text) > 0


class TestFormatActionWithBadge:
    def test_known_action_includes_badge_and_action(self):
        result = format_action_with_badge("done")
        assert "done" in result
        assert ACTION_BADGES["done"] in result

    def test_unknown_action_wraps_in_cyan(self):
        result = format_action_with_badge("mystery_event")
        assert "[cyan]" in result
        assert "mystery_event" in result

    def test_empty_action(self):
        result = format_action_with_badge("")
        assert "[cyan]" in result

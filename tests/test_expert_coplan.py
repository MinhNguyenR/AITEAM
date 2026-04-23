"""Tests for Expert static/pure methods — no API calls, no file system except tempdir."""
import json
import tempfile
from pathlib import Path

import pytest

from agents.expert import Expert


# ---------------------------------------------------------------------------
# Helpers — build a lightweight Expert without calling BaseAgent.__init__
# (avoids OpenRouter connection on import)
# ---------------------------------------------------------------------------

class _MockBudget:
    session_cost = 0.0
    session_calls = 0
    is_paused = False

    def check(self): pass
    def reset(self): pass


class _MockKM:
    def search(self, *a, **kw): return []
    def save(self, *a, **kw): return ""

    @property
    def brain(self): return None


class _MockAPI:
    def __init__(self): self.history = []
    def _build_messages(self, *a, **kw): return []
    def call_api(self, *a, **kw): return ""
    def call_api_stream(self, *a, **kw): return ""


def _make_expert() -> Expert:
    """Create Expert without hitting __init__ network calls."""
    obj = object.__new__(Expert)
    obj.agent_name = "Expert"
    obj.model_name = "test-model"
    obj.system_prompt = "test"
    obj.max_tokens = 512
    obj.temperature = 0.1
    obj.budget_limit_usd = None
    obj.history = []
    obj._budget = _MockBudget()
    obj._api = _MockAPI()
    obj._km = _MockKM()
    obj._context_window = 1_000_000
    return obj


# ---------------------------------------------------------------------------
# TestExtractStatus
# ---------------------------------------------------------------------------

class TestExtractStatus:
    def test_approved(self):
        expert = _make_expert()
        report = "### Status: APPROVED\nAll good."
        assert expert._extract_status(report) == "APPROVED"

    def test_needs_revision(self):
        expert = _make_expert()
        report = "### Status: NEEDS_REVISION\nFix this."
        assert expert._extract_status(report) == "NEEDS_REVISION"

    def test_escalate(self):
        expert = _make_expert()
        report = "### Status: ESCALATE_TO_COMMANDER\nToo complex."
        assert expert._extract_status(report) == "ESCALATE_TO_COMMANDER"

    def test_no_status_line_defaults_needs_revision(self):
        expert = _make_expert()
        report = "No status header here."
        assert expert._extract_status(report) == "NEEDS_REVISION"

    def test_approved_not_confused_with_needs_revision(self):
        expert = _make_expert()
        # Line contains APPROVED but NOT NEEDS_REVISION
        report = "### Status: APPROVED\nOther text."
        assert expert._extract_status(report) == "APPROVED"

    def test_case_insensitive_approved(self):
        expert = _make_expert()
        report = "### Status: approved\n"
        assert expert._extract_status(report) == "APPROVED"

    def test_case_insensitive_escalate(self):
        expert = _make_expert()
        report = "### Status: escalate_to_commander\n"
        assert expert._extract_status(report) == "ESCALATE_TO_COMMANDER"


# ---------------------------------------------------------------------------
# TestExtractSection
# ---------------------------------------------------------------------------

class TestExtractSection:
    def test_extracts_present_section(self):
        expert = _make_expert()
        text = "### Revised Tasks\nTask 1\nTask 2\n### Other\nOther content"
        result = expert._extract_section(text, "Revised Tasks")
        assert result == "Task 1\nTask 2"

    def test_returns_none_when_absent(self):
        expert = _make_expert()
        text = "### Other Section\nContent"
        assert expert._extract_section(text, "Revised Tasks") is None

    def test_section_at_end_of_text(self):
        expert = _make_expert()
        text = "### Revised Tasks\nFinal content"
        result = expert._extract_section(text, "Revised Tasks")
        assert result == "Final content"

    def test_empty_section_body(self):
        expert = _make_expert()
        text = "### Revised Tasks\n### Other Section\ndata"
        result = expert._extract_section(text, "Revised Tasks")
        assert result == ""

    def test_multiline_content(self):
        expert = _make_expert()
        text = "### Revised Tasks\nLine1\nLine2\nLine3\n### End\n"
        result = expert._extract_section(text, "Revised Tasks")
        assert "Line1" in result and "Line3" in result


# ---------------------------------------------------------------------------
# TestReadValidationInputs
# ---------------------------------------------------------------------------

class TestReadValidationInputs:
    def test_raises_if_draft_missing(self, tmp_path):
        expert = _make_expert()
        missing = tmp_path / "nonexistent.md"
        with pytest.raises(FileNotFoundError):
            expert._read_validation_inputs(missing, tmp_path / "state.json")

    def test_returns_draft_and_state(self, tmp_path):
        expert = _make_expert()
        draft = tmp_path / "context.md"
        draft.write_text("# Draft context", encoding="utf-8")
        state = tmp_path / "state.json"
        state.write_text(json.dumps({"task": "build API"}), encoding="utf-8")

        text, data = expert._read_validation_inputs(draft, state)
        assert text == "# Draft context"
        assert data["task"] == "build API"

    def test_missing_state_returns_empty_dict(self, tmp_path):
        expert = _make_expert()
        draft = tmp_path / "context.md"
        draft.write_text("# Draft", encoding="utf-8")
        missing_state = tmp_path / "state.json"

        text, data = expert._read_validation_inputs(draft, missing_state)
        assert text == "# Draft"
        assert data == {}

    def test_corrupt_state_returns_empty_dict(self, tmp_path):
        expert = _make_expert()
        draft = tmp_path / "context.md"
        draft.write_text("# Draft", encoding="utf-8")
        state = tmp_path / "state.json"
        state.write_text("NOT JSON{{{{", encoding="utf-8")

        text, data = expert._read_validation_inputs(draft, state)
        assert text == "# Draft"
        assert data == {}

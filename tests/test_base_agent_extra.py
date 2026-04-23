"""Tests for BaseAgent utility helpers — no API calls needed."""
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.base_agent import BaseAgent, BudgetExceeded
from agents._budget_manager import BudgetManager


# ---------------------------------------------------------------------------
# Minimal concrete subclass — avoids network + config
# ---------------------------------------------------------------------------

class _FakeAgent(BaseAgent):
    def execute(self, task, **kw): return "ok"
    def format_output(self, r): return r


def _make_agent(tmp_path=None) -> _FakeAgent:
    """Build _FakeAgent with injected no-op config and no network."""
    mock_cfg = MagicMock()
    mock_cfg.api_key = "sk-test"
    mock_cfg.BASE_DIR = Path(tmp_path) if tmp_path else Path(".")
    mock_cfg.get_worker = MagicMock(return_value=None)

    with patch("agents.base_agent.OpenAI"):
        agent = _FakeAgent(
            agent_name="TestAgent",
            model_name="test-model",
            system_prompt="You are a test assistant.",
            max_tokens=512,
            temperature=0.7,
            budget_limit_usd=10.0,
            prompt_override_resolver=lambda: {},
            config_override=mock_cfg,
        )
    return agent


# ---------------------------------------------------------------------------
# TestSessionProperties
# ---------------------------------------------------------------------------

class TestSessionProperties:
    def test_session_cost_delegates_to_budget(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent._budget.session_cost = 3.5
        assert agent.session_cost == 3.5

    def test_session_cost_setter(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.session_cost = 7.0
        assert agent._budget.session_cost == 7.0

    def test_session_calls_delegates(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent._budget.session_calls = 5
        assert agent.session_calls == 5

    def test_session_calls_setter(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.session_calls = 3
        assert agent._budget.session_calls == 3

    def test_is_paused_delegates(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent._budget.is_paused = True
        assert agent.is_paused is True

    def test_is_paused_setter(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.is_paused = True
        assert agent._budget.is_paused is True


# ---------------------------------------------------------------------------
# TestResetSession
# ---------------------------------------------------------------------------

class TestResetSession:
    def test_reset_clears_history(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.history.append({"role": "user", "content": "hi"})
        agent.reset_session()
        assert agent.history == []

    def test_reset_clears_budget(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent._budget.session_cost = 5.0
        agent._budget.session_calls = 3
        agent._budget.is_paused = True
        agent.reset_session()
        assert agent._budget.session_cost == 0.0
        assert agent._budget.session_calls == 0
        assert agent._budget.is_paused is False


# ---------------------------------------------------------------------------
# TestGetSessionSummary
# ---------------------------------------------------------------------------

class TestGetSessionSummary:
    def test_summary_keys(self, tmp_path):
        agent = _make_agent(tmp_path)
        summary = agent.get_session_summary()
        assert set(summary) >= {"agent", "model", "calls", "total_cost_usd", "history_length", "is_paused"}

    def test_summary_values(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent._budget.session_cost = 1.2345
        agent._budget.session_calls = 2
        agent.history.append({"role": "user", "content": "x"})
        s = agent.get_session_summary()
        assert s["agent"] == "TestAgent"
        assert s["calls"] == 2
        assert s["total_cost_usd"] == 1.2345
        assert s["history_length"] == 1


# ---------------------------------------------------------------------------
# TestStripMarkdownFences
# ---------------------------------------------------------------------------

class TestStripMarkdownFences:
    def test_strips_json_fence(self, tmp_path):
        agent = _make_agent(tmp_path)
        assert agent._strip_markdown_fences("```json\n{}\n```") == "{}"

    def test_strips_plain_fence(self, tmp_path):
        agent = _make_agent(tmp_path)
        assert agent._strip_markdown_fences("```\nhello\n```") == "hello"

    def test_no_fence_unchanged(self, tmp_path):
        agent = _make_agent(tmp_path)
        assert agent._strip_markdown_fences("plain text") == "plain text"


# ---------------------------------------------------------------------------
# TestRemoveGreetings
# ---------------------------------------------------------------------------

class TestRemoveGreetings:
    def test_removes_sure(self, tmp_path):
        agent = _make_agent(tmp_path)
        result = agent._remove_greetings("Sure, here is the answer")
        assert not result.startswith("Sure")

    def test_removes_here_is(self, tmp_path):
        agent = _make_agent(tmp_path)
        result = agent._remove_greetings("Here is the solution:")
        assert "Here is the" not in result

    def test_plain_text_unchanged(self, tmp_path):
        agent = _make_agent(tmp_path)
        text = "The algorithm works as follows:"
        assert agent._remove_greetings(text) == text


# ---------------------------------------------------------------------------
# TestReadProjectFile
# ---------------------------------------------------------------------------

class TestReadProjectFile:
    def test_rejects_absolute_path(self, tmp_path):
        agent = _make_agent(tmp_path)
        result = agent.read_project_file("/etc/passwd")
        assert result is None

    def test_rejects_path_traversal(self, tmp_path):
        agent = _make_agent(tmp_path)
        result = agent.read_project_file("../../../etc/passwd")
        assert result is None

    def test_reads_existing_file(self, tmp_path):
        agent = _make_agent(tmp_path)
        f = tmp_path / "notes.txt"
        f.write_text("hello", encoding="utf-8")
        result = agent.read_project_file("notes.txt")
        assert result == "hello"

    def test_returns_none_for_missing(self, tmp_path):
        agent = _make_agent(tmp_path)
        assert agent.read_project_file("nonexistent.txt") is None


# ---------------------------------------------------------------------------
# TestLogAction (OSError resilience)
# ---------------------------------------------------------------------------

class TestLogAction:
    def test_log_action_oserror_does_not_crash(self, tmp_path):
        agent = _make_agent(tmp_path)
        # Point data_dir to an unwritable scenario by patching open
        with patch("builtins.open", side_effect=OSError("permission denied")):
            agent.log_action("test decision", "test action")  # must not raise

    def test_log_action_writes_entry(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.log_action("my decision", "my action", cost=0.01)
        changelog = tmp_path / "changelog.md"
        assert changelog.exists()
        content = changelog.read_text(encoding="utf-8")
        assert "my decision" in content
        assert "my action" in content


# ---------------------------------------------------------------------------
# TestBudgetExceededException
# ---------------------------------------------------------------------------

class TestBudgetExceededException:
    def test_budget_exceeded_is_exception(self):
        exc = BudgetExceeded("test")
        assert isinstance(exc, Exception)

    def test_budget_exceeded_message(self):
        exc = BudgetExceeded("Agent X paused: cost $5.0000 exceeds limit $3.00")
        assert "Agent X" in str(exc)

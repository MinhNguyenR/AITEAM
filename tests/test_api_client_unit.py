"""Tests for agents/_api_client.py — all API calls mocked."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agents._api_client import APIClient
from agents._budget_manager import BudgetManager
from agents.base_agent import BudgetExceeded


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_budget(limit=10.0, cost=0.0, paused=False):
    bm = BudgetManager("TestAgent", budget_limit_usd=limit)
    bm.session_cost = cost
    bm.is_paused = paused
    return bm


def _make_usage(prompt=100, completion=50):
    u = SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion)
    return u


def _make_resp(content="hello", finish_reason="stop", usage=None):
    choice = SimpleNamespace(
        message=SimpleNamespace(content=content),
        finish_reason=finish_reason,
    )
    return SimpleNamespace(choices=[choice], usage=usage or _make_usage())


def _make_client(budget=None) -> APIClient:
    budget = budget or _make_budget()
    return APIClient(
        client=MagicMock(),
        agent_name="TestAgent",
        model_name="test-model",
        max_tokens=512,
        temperature=0.5,
        registry_role_key="TEST",
        history=[],
        budget=budget,
        stream_chunk_callback=None,
    )


# ---------------------------------------------------------------------------
# TestBuildMessages
# ---------------------------------------------------------------------------

class TestBuildMessages:
    def test_includes_system_role(self):
        c = _make_client()
        msgs = c._build_messages("hello", None, "default system")
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "default system"

    def test_system_prompt_overrides_default(self):
        c = _make_client()
        msgs = c._build_messages("hello", "override system", "default system")
        assert msgs[0]["content"] == "override system"

    def test_user_message_last(self):
        c = _make_client()
        msgs = c._build_messages("my query", None, "sys")
        assert msgs[-1]["role"] == "user"
        assert msgs[-1]["content"] == "my query"

    def test_history_injected(self):
        c = _make_client()
        c.history.append({"role": "user", "content": "prev"})
        msgs = c._build_messages("now", None, "sys")
        assert any(m["content"] == "prev" for m in msgs)


# ---------------------------------------------------------------------------
# TestHandleResponseContent
# ---------------------------------------------------------------------------

class TestHandleResponseContent:
    def test_returns_content_on_stop(self):
        c = _make_client()
        resp = _make_resp(content="  answer  ", finish_reason="stop")
        result = c._handle_response_content(resp, 0, 512)
        assert result == "answer"

    def test_returns_none_on_length_not_last_retry(self):
        c = _make_client()
        resp = _make_resp(content="partial", finish_reason="length")
        result = c._handle_response_content(resp, 0, 512)
        assert result is None

    def test_raises_on_length_at_last_retry(self):
        from core.config.constants import API_MAX_RETRIES
        c = _make_client()
        resp = _make_resp(content="partial", finish_reason="length")
        with pytest.raises(ValueError, match="truncated"):
            c._handle_response_content(resp, API_MAX_RETRIES - 1, 512)

    def test_returns_none_on_empty_content(self):
        c = _make_client()
        resp = _make_resp(content="", finish_reason="stop")
        result = c._handle_response_content(resp, 0, 512)
        assert result is None


# ---------------------------------------------------------------------------
# TestCallApi (mocked LLM)
# ---------------------------------------------------------------------------

class TestCallApi:
    def test_returns_content_on_success(self):
        c = _make_client()
        resp = _make_resp("Great answer!", finish_reason="stop")
        with patch("agents._api_client.chat_completions_create", return_value=resp):
            with patch("agents._api_client.ensure_dashboard_budget_available"):
                with patch.object(c, "_compute_call_cost", return_value=0.001):
                    result = c.call_api(
                        "test prompt",
                        model="m",
                        max_tokens=512,
                        temperature=0.5,
                        system_prompt=None,
                        default_system="sys",
                    )
        assert result == "Great answer!"

    def test_paused_agent_skips_call(self):
        budget = _make_budget(paused=True)
        c = _make_client(budget=budget)
        result = c.call_api(
            "test", model="m", max_tokens=512, temperature=0.5,
            system_prompt=None, default_system="sys",
        )
        assert "PAUSED" in result

    def test_history_updated_on_success(self):
        c = _make_client()
        resp = _make_resp("answer", finish_reason="stop")
        with patch("agents._api_client.chat_completions_create", return_value=resp):
            with patch("agents._api_client.ensure_dashboard_budget_available"):
                with patch.object(c, "_compute_call_cost", return_value=0.0):
                    c.call_api(
                        "user prompt", model="m", max_tokens=512,
                        temperature=0.5, system_prompt=None, default_system="sys",
                    )
        assert any(m["content"] == "user prompt" for m in c.history)
        assert any(m["content"] == "answer" for m in c.history)

    def test_budget_cost_incremented(self):
        c = _make_client()
        resp = _make_resp("ok", finish_reason="stop")
        with patch("agents._api_client.chat_completions_create", return_value=resp):
            with patch("agents._api_client.ensure_dashboard_budget_available"):
                with patch.object(c, "_compute_call_cost", return_value=0.005):
                    c.call_api(
                        "x", model="m", max_tokens=512, temperature=0.5,
                        system_prompt=None, default_system="sys",
                    )
        assert c._budget.session_cost == pytest.approx(0.005)


# ---------------------------------------------------------------------------
# TestAggregateStream
# ---------------------------------------------------------------------------

class TestAggregateStream:
    def _make_chunk(self, delta=None, usage=None):
        d = SimpleNamespace(content=delta)
        choice = SimpleNamespace(delta=d)
        return SimpleNamespace(choices=[choice], usage=usage)

    def test_joins_chunks(self):
        c = _make_client()
        chunks = [
            self._make_chunk("hel"),
            self._make_chunk("lo"),
            self._make_chunk("!"),
        ]
        content, _, _ = c._aggregate_stream(iter(chunks))
        assert content == "hello!"

    def test_skips_none_delta(self):
        c = _make_client()
        chunks = [self._make_chunk(None), self._make_chunk("hi")]
        content, _, _ = c._aggregate_stream(iter(chunks))
        assert content == "hi"

    def test_stream_callback_called(self):
        calls = []
        budget = _make_budget()
        c = APIClient(
            client=MagicMock(),
            agent_name="A",
            model_name="m",
            max_tokens=512,
            temperature=0.5,
            registry_role_key="A",
            history=[],
            budget=budget,
            stream_chunk_callback=calls.append,
        )
        chunks = [self._make_chunk("x"), self._make_chunk("y")]
        c._aggregate_stream(iter(chunks))
        assert calls == ["x", "y"]

    def test_empty_stream_returns_empty(self):
        c = _make_client()
        content, p, comp = c._aggregate_stream(iter([]))
        assert content == ""
        assert p == 0
        assert comp == 0

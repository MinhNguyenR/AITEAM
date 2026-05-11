"""Tests for agents/_api_client.py — call_api_stream and _compute_call_cost."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agents.support._api_client import APIClient
from agents.support._budget_manager import BudgetManager
from agents.base_agent import BudgetExceeded


def _make_budget(limit=10.0, cost=0.0, paused=False):
    bm = BudgetManager("StreamAgent", budget_limit_usd=limit)
    bm.session_cost = cost
    bm.is_paused = paused
    return bm


def _make_client(budget=None, callback=None) -> APIClient:
    budget = budget or _make_budget()
    return APIClient(
        client=MagicMock(),
        agent_name="StreamAgent",
        model_name="test-model",
        max_tokens=512,
        temperature=0.5,
        registry_role_key="TEST",
        history=[],
        budget=budget,
        stream_chunk_callback=callback,
    )


def _make_chunk(content=None, usage=None):
    choice = SimpleNamespace(
        delta=SimpleNamespace(content=content),
        finish_reason="stop" if content is None else None,
    )
    chunk = SimpleNamespace(choices=[choice] if choice else [], usage=usage)
    return chunk


class TestCallApiStreamPaused:
    def test_returns_paused_message(self):
        c = _make_client(budget=_make_budget(paused=True))
        result = c.call_api_stream(
            "hello", model="test", max_tokens=512, temperature=0.5,
            system_prompt=None, default_system="sys",
        )
        assert "[PAUSED]" in result


class TestCallApiStreamBudgetExceeded:
    def test_budget_exceeded_returns_paused(self):
        from utils.budget_guard import DashboardBudgetExceeded
        c = _make_client()
        with patch("agents.support._api_client.ensure_dashboard_budget_available",
                   side_effect=DashboardBudgetExceeded("exceeded")):
            result = c.call_api_stream(
                "hello", model="test", max_tokens=512, temperature=0.5,
                system_prompt=None, default_system="sys",
            )
        assert "[PAUSED]" in result


class TestCallApiStreamSuccess:
    def _make_chunks(self, contents):
        chunks = []
        usage = SimpleNamespace(prompt_tokens=50, completion_tokens=30)
        for i, c in enumerate(contents):
            choice = SimpleNamespace(delta=SimpleNamespace(content=c), finish_reason=None)
            usage_val = usage if i == len(contents) - 1 else None
            chunks.append(SimpleNamespace(choices=[choice], usage=usage_val))
        return iter(chunks)

    def test_success_returns_content(self):
        c = _make_client()
        chunks = self._make_chunks(["Hello ", "world"])
        with patch("agents.support._api_client.ensure_dashboard_budget_available"), \
             patch("agents.support._api_client.chat_completions_create_stream", return_value=chunks), \
             patch.object(c, "_compute_call_cost", return_value=0.001):
            result = c.call_api_stream(
                "user prompt", model="test", max_tokens=512, temperature=0.5,
                system_prompt=None, default_system="sys",
            )
        assert result == "Hello world"
        # History updated
        assert any(m["content"] == "user prompt" for m in c.history)

    def test_stream_with_callback(self):
        received = []
        callback = lambda delta: received.append(delta)
        c = _make_client(callback=callback)
        chunks = self._make_chunks(["chunk1", "chunk2"])
        with patch("agents.support._api_client.ensure_dashboard_budget_available"), \
             patch("agents.support._api_client.chat_completions_create_stream", return_value=chunks), \
             patch.object(c, "_compute_call_cost", return_value=0.001):
            result = c.call_api_stream(
                "prompt", model="test", max_tokens=512, temperature=0.5,
                system_prompt=None, default_system="sys",
            )
        assert "chunk1" in received
        assert "chunk2" in received

    def test_empty_stream_retries_then_raises(self):
        c = _make_client()
        empty_chunks = iter([])

        def make_empty(*a, **kw):
            return iter([])

        with patch("agents.support._api_client.ensure_dashboard_budget_available"), \
             patch("agents.support._api_client.chat_completions_create_stream", side_effect=make_empty), \
             patch("agents.support._api_client.time.sleep"):
            with pytest.raises((ValueError, RuntimeError)):
                c.call_api_stream(
                    "prompt", model="test", max_tokens=512, temperature=0.5,
                    system_prompt=None, default_system="sys",
                )

    def test_rate_limit_error_retries(self):
        c = _make_client()
        call_count = 0

        def make_rate_limit(*a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("429 rate limit exceeded")
            return iter([
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))],
                    usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
                )
            ])

        with patch("agents.support._api_client.ensure_dashboard_budget_available"), \
             patch("agents.support._api_client.chat_completions_create_stream", side_effect=make_rate_limit), \
             patch("agents.support._api_client.time.sleep"), \
             patch.object(c, "_compute_call_cost", return_value=0.001):
            result = c.call_api_stream(
                "prompt", model="test", max_tokens=512, temperature=0.5,
                system_prompt=None, default_system="sys",
            )
        assert result == "ok"


class TestAggregateStreamWithUsageChunks:
    def test_usage_from_chunk(self):
        c = _make_client()
        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50)
        chunks = [
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="text"))],
                usage=usage,
            )
        ]
        content, prompt_tok, completion_tok, *_ = c._aggregate_stream(iter(chunks))
        assert content == "text"
        assert prompt_tok == 100
        assert completion_tok == 50

    def test_chunk_without_usage(self):
        c = _make_client()
        chunks = [
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="hello"))],
                usage=None,
            )
        ]
        content, prompt_tok, completion_tok, *_ = c._aggregate_stream(iter(chunks))
        assert content == "hello"
        assert prompt_tok == 0

    def test_callback_exception_swallowed(self):
        def bad_callback(delta):
            raise RuntimeError("callback error")

        c = _make_client(callback=bad_callback)
        chunks = [
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="text"))],
                usage=None,
            )
        ]
        content, *_ = c._aggregate_stream(iter(chunks))
        assert content == "text"  # must not raise

    def test_no_session_session_lookuperror_fallback(self):
        c = _make_client(callback=None)  # No callback, uses session
        chunks = [
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="data"))],
                usage=None,
            )
        ]
        import sys
        mock_ws = MagicMock()
        mock_ws.append_leader_stream_chunk = MagicMock(side_effect=LookupError("no monitor"))
        with patch.dict(sys.modules, {"core.cli.python_cli.workflow.runtime.session": mock_ws}):
            content, *_ = c._aggregate_stream(iter(chunks))
        assert content == "data"  # LookupError should be caught, not raised


class TestComputeCallCost:
    def test_basic_cost(self):
        import sys
        c = _make_client()
        mock_tracker = MagicMock()
        mock_tracker.compute_cost_usd = MagicMock(return_value=0.005)
        mock_cfg = MagicMock()
        mock_cfg.get_worker.return_value = None
        with patch.dict(sys.modules, {"utils.tracker": mock_tracker}), \
             patch.dict(sys.modules, {"core.config": MagicMock(config=mock_cfg)}):
            cost = c._compute_call_cost(100, 50, "test-model")
        assert isinstance(cost, float)

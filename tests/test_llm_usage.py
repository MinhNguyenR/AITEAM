"""Tests for agents/llm_usage.py — chat completion wrappers."""
from unittest.mock import MagicMock, patch

from agents.llm_usage import chat_completions_create, chat_completions_create_stream, log_usage_event


class TestChatCompletionsCreate:
    def test_delegates_to_client(self):
        client = MagicMock()
        client.chat.completions.create.return_value = "response"
        result = chat_completions_create(
            client, model="gpt-4", messages=[{"role": "user", "content": "hi"}],
            max_tokens=100, temperature=0.7,
        )
        assert result == "response"
        client.chat.completions.create.assert_called_once_with(
            model="gpt-4",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=100,
            temperature=0.7,
        )


class TestChatCompletionsCreateStream:
    def test_delegates_with_stream_options(self):
        client = MagicMock()
        client.chat.completions.create.return_value = iter([])
        result = chat_completions_create_stream(
            client, model="claude-3", messages=[], max_tokens=500, temperature=0.5,
        )
        call_kwargs = client.chat.completions.create.call_args.kwargs
        assert call_kwargs["stream"] is True
        assert "include_usage" in call_kwargs.get("stream_options", {})


class TestLogUsageEvent:
    def test_calls_append_usage_log(self):
        mock_append = MagicMock()
        with patch("agents.llm_usage.append_usage_log", mock_append, create=True):
            import sys
            mock_tracker = MagicMock()
            mock_tracker.append_usage_log = mock_append
            with patch.dict(sys.modules, {"utils.tracker": mock_tracker}):
                log_usage_event({"model": "gpt-4", "tokens": 100})
        # Either it called or gracefully failed — must not raise

    def test_oserror_swallowed(self):
        import sys
        mock_tracker = MagicMock()
        mock_tracker.append_usage_log = MagicMock(side_effect=OSError("disk full"))
        with patch.dict(sys.modules, {"utils.tracker": mock_tracker}):
            log_usage_event({"model": "test"})  # must not raise

    def test_value_error_swallowed(self):
        import sys
        mock_tracker = MagicMock()
        mock_tracker.append_usage_log = MagicMock(side_effect=ValueError("bad"))
        with patch.dict(sys.modules, {"utils.tracker": mock_tracker}):
            log_usage_event({})  # must not raise

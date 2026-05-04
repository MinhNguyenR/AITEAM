from __future__ import annotations

import json
import unittest.mock
from pathlib import Path

from agents.base_agent import BaseAgent
from core.cli.python_cli.shell.state import log_system_action
from core.config.settings import mask_api_key
from core.storage.knowledge_store import _vault_wrap
from utils.env_guard import redact_for_display
from utils.input_validator import (
    MAX_PROMPT_CHARS,
    PromptInvalid,
    PromptTooLong,
    validate_user_prompt,
)


class _DummyAgent(BaseAgent):
    def __init__(self, extra_search_roots=None):
        super().__init__(
            agent_name="Dummy",
            model_name="test-model",
            system_prompt="system",
            max_tokens=16,
            temperature=0.0,
            extra_search_roots=extra_search_roots,
        )

    def execute(self, task: str) -> str:
        return task

    def format_output(self, response: str) -> str:
        return response


def test_redact_for_display_masks_secrets():
    text = "OPENROUTER_API_KEY=sk-or-v1-abcdef1234567890abcdef NINE_ROUTER_API_KEY=sk-1234567890abcdef123456"
    redacted = redact_for_display(text)
    assert "REDACTED" in redacted
    assert "abcdef1234567890" not in redacted


def test_mask_api_key_shows_only_suffix(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-1234567890abcdef1234567890abcdef")
    masked = mask_api_key()
    assert masked.startswith("***...")
    assert masked.endswith("cdef")
    assert "12345678" not in masked


def test_log_system_action_redacts_detail(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    log_system_action("test.action", "OPENROUTER_API_KEY=sk-or-v1-abcdef1234567890abcdef")
    log_file = Path(tmp_path) / ".ai-team" / "actions.log"
    data = log_file.read_text(encoding="utf-8").strip().splitlines()
    rec = json.loads(data[-1])
    assert "REDACTED" in rec["detail"]
    assert "abcdef1234567890" not in rec["detail"]


def test_vault_wrap_auto_creates_key_and_encrypts(monkeypatch, tmp_path):
    monkeypatch.delenv("AI_TEAM_VAULT_KEY", raising=False)
    from core.config import Config
    from core.storage.knowledge.sqlite_repository import _vault_unwrap as _unwrap

    monkeypatch.setattr(Config, "BASE_DIR", tmp_path, raising=False)

    wrapped = _vault_wrap(b"compressed-bytes")
    assert wrapped != b"compressed-bytes"
    assert wrapped.startswith(b"AITEAMF1")
    assert (tmp_path / "vault.key").is_file()
    assert _unwrap(wrapped, tmp_path) == b"compressed-bytes"


def test_read_project_file_rejects_traversal(tmp_path):
    agent = _DummyAgent(extra_search_roots=[tmp_path])
    assert agent.read_project_file("../secret.txt") is None


# ── input_validator tests ────────────────────────────────────────────────────

def test_validate_prompt_returns_stripped():
    assert validate_user_prompt("  hello  ") == "hello"


def test_validate_prompt_max_length():
    long_text = "x" * (MAX_PROMPT_CHARS + 1)
    try:
        validate_user_prompt(long_text)
        assert False, "expected PromptTooLong"
    except PromptTooLong:
        pass


def test_validate_prompt_null_bytes():
    try:
        validate_user_prompt("hello\x00world")
        assert False, "expected PromptInvalid"
    except PromptInvalid:
        pass


def test_validate_prompt_empty():
    try:
        validate_user_prompt("   ")
        assert False, "expected PromptInvalid"
    except PromptInvalid:
        pass


def test_validate_prompt_valid():
    result = validate_user_prompt("Write a unit test for my Python function")
    assert result == "Write a unit test for my Python function"


# ── ssl verify test ──────────────────────────────────────────────────────────

def test_ssl_verify_flag():
    with unittest.mock.patch("requests.get") as mock_get:
        mock_get.return_value = unittest.mock.MagicMock(
            status_code=200,
            json=lambda: {"data": {"total_credits": 10.0, "usage": 2.0}},
            raise_for_status=lambda: None,
        )
        from utils.tracker.tracker_openrouter import fetch_wallet
        fetch_wallet()
        _, kwargs = mock_get.call_args
        assert kwargs.get("verify") is True


# ── log_action OSError test ──────────────────────────────────────────────────

def test_log_action_oserror_is_warned(tmp_path, monkeypatch):
    agent = _DummyAgent()
    agent.data_dir = tmp_path / "data"
    with unittest.mock.patch("builtins.open", side_effect=OSError("disk full")):
        with unittest.mock.patch.object(agent.__class__.__bases__[0], "_changelog_lock"):
            # Should not raise; OSError must be caught and logged as warning
            try:
                agent.log_action("test decision", "test action")
            except OSError:
                assert False, "log_action must not propagate OSError"

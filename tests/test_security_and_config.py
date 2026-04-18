from __future__ import annotations

import json
from pathlib import Path

from agents.base_agent import BaseAgent
from core.cli.state import log_system_action
from core.config.settings import mask_api_key
from core.storage.knowledge_store import _vault_wrap
from utils.env_guard import redact_for_display


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


def test_vault_wrap_warns_and_falls_back_when_key_missing(monkeypatch, caplog):
    monkeypatch.delenv("AI_TEAM_VAULT_KEY", raising=False)
    with caplog.at_level("WARNING"):
        wrapped = _vault_wrap(b"compressed-bytes")
    assert wrapped == b"compressed-bytes"
    assert any("unencrypted" in record.message for record in caplog.records)


def test_read_project_file_rejects_traversal(tmp_path):
    agent = _DummyAgent(extra_search_roots=[tmp_path])
    assert agent.read_project_file("../secret.txt") is None

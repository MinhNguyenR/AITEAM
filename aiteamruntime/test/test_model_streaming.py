from __future__ import annotations

import sys
import types
from dataclasses import dataclass

from aiteamruntime.integrations.trackaiteam import model


@dataclass
class _Delta:
    reasoning: str | None = None
    content: str | None = None


@dataclass
class _Choice:
    delta: _Delta


@dataclass
class _Chunk:
    choices: list[_Choice]
    usage: object | None = None


class _FakeCompletions:
    def __init__(self, capture: dict) -> None:
        self.capture = capture
        self.calls = 0

    def create(self, **kwargs):
        self.capture.update(kwargs)
        self.calls += 1
        yield _Chunk([_Choice(_Delta(reasoning="think "))])
        yield _Chunk([_Choice(_Delta(content='{"ok": true}'))])


class _FakeClient:
    capture: dict = {}

    def __init__(self, **_kwargs) -> None:
        self.chat = types.SimpleNamespace(completions=_FakeCompletions(self.capture))


def test_stream_with_reasoning_uses_registry_reasoning_and_preserves_messages(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=_FakeClient))

    deltas: list[dict] = []
    reasoning, content, messages = model.stream_with_reasoning(
        role_key="LEADER_MEDIUM",
        messages=[
            {"role": "user", "content": "plan"},
            {"role": "assistant", "content": "old", "reasoning_content": "old thinking"},
        ],
        max_tokens=25,
        on_delta=deltas.append,
    )

    assert reasoning == "think "
    assert content == '{"ok": true}'
    assert messages[-1]["reasoning_content"] == "think "
    assert _FakeClient.capture["extra_body"]["reasoning"]["effort"] == "high"
    assert _FakeClient.capture["extra_body"]["reasoning"]["summary"] == "detailed"
    assert _FakeClient.capture["temperature"] == 1.0
    assert _FakeClient.capture["messages"][1]["reasoning_content"] == "old thinking"
    assert [item["type"] for item in deltas] == ["reasoning", "content", "done"]


def test_chat_json_repairs_malformed_json_without_reasoning(monkeypatch) -> None:
    class RepairCompletions:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) == 1:
                yield _Chunk([_Choice(_Delta(content='{"ok": "unterminated'))])
            else:
                yield _Chunk([_Choice(_Delta(content='{"ok": true}'))])

    completions = RepairCompletions()

    class RepairClient:
        def __init__(self, **_kwargs) -> None:
            self.chat = types.SimpleNamespace(completions=completions)

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=RepairClient))

    result = model.chat_json(role_key="AMBASSADOR", system="return json", user="task", max_tokens=50)

    assert result == {"ok": True}
    assert completions.calls[0]["response_format"] == {"type": "json_object"}
    assert completions.calls[0]["extra_body"]["reasoning"]["effort"] == "medium"
    assert completions.calls[1]["response_format"] == {"type": "json_object"}
    assert "extra_body" not in completions.calls[1]

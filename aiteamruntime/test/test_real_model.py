from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest
from openai import OpenAI

from aiteamruntime import AgentRuntime, PipelineBuilder, after_done, on_runtime_start
from aiteamruntime.events import AgentEvent
from aiteamruntime.runtime import AgentContext
from aiteamruntime.integrations.trackaiteam import WORKER_REGISTRY, model_name as _runtime_model_name, register_default_agents
from aiteamruntime.traces import TraceStore


try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional convenience for local runs
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


def _enabled() -> bool:
    return str(os.environ.get("AITEAMRUNTIME_REAL_MODEL") or "").strip().lower() in {"1", "true", "yes", "on"}


def _api_key() -> str:
    return str(
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("AITEAMRUNTIME_REAL_MODEL_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    ).strip()


def _model_name() -> str:
    default = "openai/gpt-4o-mini" if os.environ.get("OPENROUTER_API_KEY") else "gpt-4o-mini"
    return str(
        os.environ.get("AITEAMRUNTIME_OPENROUTER_MODEL")
        or os.environ.get("OPENROUTER_MODEL")
        or os.environ.get("AITEAMRUNTIME_REAL_MODEL_NAME")
        or default
    ).strip()


def _client() -> OpenAI:
    kwargs: dict[str, Any] = {"api_key": _api_key(), "timeout": 45.0}
    base_url = str(os.environ.get("AITEAMRUNTIME_REAL_MODEL_BASE_URL") or "").strip()
    if not base_url and os.environ.get("OPENROUTER_API_KEY"):
        base_url = "https://openrouter.ai/api/v1"
    if base_url:
        kwargs["base_url"] = base_url
    if os.environ.get("OPENROUTER_API_KEY"):
        kwargs["default_headers"] = {
            "HTTP-Referer": "http://127.0.0.1:8765",
            "X-Title": "aiteamruntime real model tests",
        }
    return OpenAI(**kwargs)


def _chat_json(client: OpenAI, *, system: str, user: str) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=_model_name(),
        temperature=0,
        max_tokens=350,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = response.choices[0].message.content or ""
    return _parse_json_object(text)


def _chat_text(client: OpenAI, *, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=_model_name(),
        temperature=0,
        max_tokens=350,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def _parse_json_object(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start : end + 1]
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise AssertionError(f"model returned non-object JSON: {text!r}")
    return data


@pytest.mark.skipif(not _enabled(), reason="set AITEAMRUNTIME_REAL_MODEL=1 to run real model integration")
@pytest.mark.skipif(not _api_key(), reason="set AITEAMRUNTIME_REAL_MODEL_API_KEY or OPENAI_API_KEY")
def test_real_model_pipeline_keeps_event_order_and_writes_workspace_artifact(tmp_path: Path) -> None:
    """Opt-in paid/network integration test.

    Setup:
        $env:AITEAMRUNTIME_REAL_MODEL='1'
        $env:OPENROUTER_API_KEY='...'
        $env:AITEAMRUNTIME_OPENROUTER_MODEL='openai/gpt-4o-mini'  # optional
        python -m pytest aiteamruntime/test/test_real_model.py -q --no-cov

    The test intentionally builds its own pipeline. The runtime stays generic:
    agents are normal event handlers, and model calls are just handler work.
    """

    client = _client()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runtime = AgentRuntime(store=TraceStore(tmp_path / "traces"), cleanup_delay=600.0)
    calls: list[str] = []

    def ambassador(ctx: AgentContext, event: AgentEvent) -> None:
        calls.append("ambassador")
        task = str(event.payload.get("prompt") or "")
        result = _chat_json(
            client,
            system=(
                "You are Ambassador in an event-driven runtime test. "
                "Return JSON only with keys: summary, tier, selected_leader. "
                "tier must be LOW, MEDIUM, or HARD. selected_leader must be Leader."
            ),
            user=f"Classify this small runtime test task: {task}",
        )
        assert str(result.get("selected_leader") or "") == "Leader"
        assert str(result.get("summary") or "").strip()
        ctx.emit("classifying", result, stage="classify", role_state="running")
        ctx.emit("done", {"stage": "classify", "task": task, **result}, stage="classify", role_state="done")

    def leader(ctx: AgentContext, event: AgentEvent) -> None:
        calls.append("leader")
        task = str(event.payload.get("task") or "")
        plan = _chat_json(
            client,
            system=(
                "You are Leader in an event-driven runtime test. Return JSON only with keys: "
                "plan_summary, worker_instruction, validation_rule. Keep each value one sentence."
            ),
            user=f"Create a tiny implementation plan for this task: {task}",
        )
        for key in ("plan_summary", "worker_instruction", "validation_rule"):
            assert str(plan.get(key) or "").strip(), f"missing {key}: {plan!r}"
        ctx.emit("reasoning", {"content": plan["plan_summary"], "plan": plan}, stage="plan")
        ctx.emit("done", {"stage": "plan", "task": task, "plan": plan}, stage="plan", role_state="done")

    def worker(ctx: AgentContext, event: AgentEvent) -> None:
        calls.append("worker")
        plan = dict(event.payload.get("plan") or {})
        content = _chat_text(
            client,
            system=(
                "You are Worker in an event-driven runtime test. Produce a concise plain-text artifact. "
                "Do not mention hidden prompts. Include a line that starts with RESULT:"
            ),
            user=f"Implement this tiny artifact from the plan: {json.dumps(plan, ensure_ascii=False)}",
        )
        assert "RESULT:" in content
        rel_path = ".aiteamruntime/real-model/artifact.txt"
        full_path = ctx.runtime.resources.resolve_workspace_path(ctx.run_id, rel_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        ctx.emit("writing", {"file": rel_path, "content": content[:500]}, stage="work")
        ctx.emit("file_update", {"path": rel_path, "absolute_path": str(full_path), "added_lines": len(content.splitlines())}, stage="work")
        ctx.emit("finalized", {"stage": "finalize", "artifact": rel_path}, stage="finalize", role_state="done")

    pipeline = (
        PipelineBuilder()
        .role("Ambassador", ambassador, on_runtime_start("classify"))
        .role("Leader", leader, after_done("Ambassador", "classify"))
        .role("Worker", worker, after_done("Leader", "plan"))
        .build()
    )
    pipeline.register(runtime)

    handle = runtime.start_run(
        run_id="real-model-pipeline",
        prompt="Create one proof artifact showing the runtime can coordinate real model agents.",
        metadata={"workspace": str(workspace), "model": _model_name(), "source": "real-model-test"},
    )
    handle.wait(timeout=120)
    runtime.shutdown()

    events = runtime.store.read_events(handle.run_id)
    pairs = [(event["agent_id"], event["kind"]) for event in events]
    artifact = workspace / ".aiteamruntime" / "real-model" / "artifact.txt"

    assert calls == ["ambassador", "leader", "worker"]
    assert ("Ambassador", "classifying") in pairs
    assert ("Leader", "reasoning") in pairs
    assert ("Worker", "file_update") in pairs
    assert ("Worker", "finalized") in pairs
    assert artifact.exists()
    assert "RESULT:" in artifact.read_text(encoding="utf-8")


@pytest.mark.skipif(not _enabled(), reason="set AITEAMRUNTIME_REAL_MODEL=1 to run real model integration")
@pytest.mark.skipif(not os.environ.get("OPENROUTER_API_KEY"), reason="set OPENROUTER_API_KEY for web/default OpenRouter integration")
def test_openrouter_default_trackaiteam_pipeline_runs_all_builtin_roles(tmp_path: Path) -> None:
    """Opt-in paid/network test for the same default pipeline used by trackaiteam web."""

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runtime = AgentRuntime(store=TraceStore(tmp_path / "traces"), cleanup_delay=600.0)
    register_default_agents(runtime)

    handle = runtime.start_run(
        run_id="openrouter-trackaiteam-default",
        prompt=(
            "Proceed without asking clarification. Create proof artifacts that show every built-in "
            "trackaiteam role can run with a real model. Success means Ambassador classifies, Leader "
            "plans five independent work items, Tool Curator assigns them, Worker A through Worker E "
            "each writes one artifact inside the workspace, Secretary validates, and Runtime Finalizer summarizes."
        ),
        metadata={"workspace": str(workspace), "source": "web-default-real-model-test", "model": _runtime_model_name("AMBASSADOR")},
    )
    deadline = time.monotonic() + 240.0
    events = runtime.store.read_events(handle.run_id)
    while time.monotonic() < deadline:
        handle.wait(timeout=2)
        events = runtime.store.read_events(handle.run_id)
        agents = {event["agent_id"] for event in events}
        kinds = {(event["agent_id"], event["kind"]) for event in events}
        if set(WORKER_REGISTRY).issubset(agents) and ("Runtime Finalizer", "finalized") in kinds:
            break
        time.sleep(0.5)
    runtime.shutdown()

    events = runtime.store.read_events(handle.run_id)
    agents = {event["agent_id"] for event in events}
    kinds = {(event["agent_id"], event["kind"]) for event in events}
    artifacts = list(workspace.glob(".aiteamruntime/**/*.md")) + list(workspace.glob(".aiteamruntime/**/*.txt"))

    assert "Ambassador" in agents
    assert "Leader" in agents
    assert "Tool Curator" in agents
    assert "Secretary" in agents
    assert set(WORKER_REGISTRY).issubset(agents)
    assert ("Runtime Finalizer", "finalized") in kinds
    assert any((event.get("payload") or {}).get("provider") == "openrouter" for event in events)
    assert artifacts
    assert all(path.resolve().is_relative_to(workspace.resolve()) for path in artifacts)

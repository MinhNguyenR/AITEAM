from __future__ import annotations

from aiteamruntime import AgentContract, AgentRuntime, GovernorLimits, PipelineBuilder, on_event
from aiteamruntime.events import AgentEvent
from aiteamruntime.runtime import AgentContext
from aiteamruntime.traces import TraceStore


_OK_SCHEMA = {
    "type": "object",
    "required": ["ok"],
    "properties": {"ok": {"type": "boolean"}},
}


def _runtime(tmp_path, **kwargs) -> AgentRuntime:
    return AgentRuntime(store=TraceStore(tmp_path / "traces"), cleanup_delay=0, idle_timeout=0, **kwargs)


def test_contract_blocks_invalid_output_and_requests_repair(tmp_path) -> None:
    runtime = _runtime(tmp_path)

    def bad_agent(ctx: AgentContext, event: AgentEvent) -> None:
        ctx.emit("done", {"wrong": True}, stage="bad")

    PipelineBuilder().on_start(
        "BadAgent",
        bad_agent,
        contract=AgentContract(output_schema=_OK_SCHEMA, output_kinds=frozenset({"done"})),
    ).build().register(runtime)

    handle = runtime.start_run(run_id="contract-invalid", prompt="schema")
    handle.wait(timeout=3)
    events = runtime.store.read_events("contract-invalid")
    runtime.shutdown()

    assert any(event["kind"] == "schema_repair_requested" for event in events)
    assert not any(event["agent_id"] == "BadAgent" and event["kind"] == "done" for event in events)


def test_secretary_schema_repair_is_guarded_from_infinite_loop(tmp_path) -> None:
    runtime = _runtime(tmp_path)

    def secretary(ctx: AgentContext, event: AgentEvent) -> None:
        ctx.emit("done", {"still_wrong": True}, stage="repair")

    PipelineBuilder().on_start(
        "Secretary",
        secretary,
        contract=AgentContract(output_schema=_OK_SCHEMA, output_kinds=frozenset({"done"})),
    ).build().register(runtime)

    handle = runtime.start_run(run_id="secretary-loop-guard", prompt="schema")
    handle.wait(timeout=3)
    events = runtime.store.read_events("secretary-loop-guard")
    runtime.shutdown()

    assert any(event["kind"] == "schema_error" for event in events)
    assert not any(event["kind"] == "schema_repair_requested" for event in events)


def test_hydration_injects_ref_content_only_for_handler_not_trace(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "note.txt").write_text("real workspace content", encoding="utf-8")
    runtime = _runtime(tmp_path)
    seen: list[str] = []

    def producer(ctx: AgentContext, event: AgentEvent) -> None:
        ref_id = ctx.ref_file("note.txt", metadata={"purpose": "test"})
        ctx.emit("done", {"refs": [{"id": ref_id}], "note": "lightweight only"}, stage="produce")

    def consumer(ctx: AgentContext, event: AgentEvent) -> None:
        ref_id = event.payload["refs"][0]["id"]
        seen.append(event.payload["_hydrated"][ref_id]["content"])
        ctx.emit("finalized", {"ok": True}, stage="finalize")

    (
        PipelineBuilder()
        .on_start("Producer", producer)
        .after_done("Consumer", consumer, after_agent_id="Producer", after_stage="produce")
        .build()
        .register(runtime)
    )

    handle = runtime.start_run(run_id="hydrate", prompt="refs", metadata={"workspace": str(workspace)})
    handle.wait(timeout=3)
    events = runtime.store.read_events("hydrate")
    runtime.shutdown()

    assert seen == ["real workspace content"]
    assert any(event["kind"] == "hydrated" for event in events)
    assert "real workspace content" not in "\n".join(str(event.get("payload") or {}) for event in events)


def test_governor_freezes_run_from_model_token_usage_after_response(tmp_path) -> None:
    runtime = _runtime(
        tmp_path,
        governor_defaults=GovernorLimits(max_events=100, max_runtime_seconds=30, max_model_tokens=5),
    )

    def spender(ctx: AgentContext, event: AgentEvent) -> None:
        ctx.emit("model_response", {"total_tokens": 10}, stage="model")
        ctx.emit("done", {"stage": "after-budget"}, stage="after-budget")

    PipelineBuilder().on_start("Spender", spender).build().register(runtime)

    handle = runtime.start_run(run_id="quota", prompt="budget")
    handle.wait(timeout=3)
    events = runtime.store.read_events("quota")
    runtime.shutdown()

    assert any(event["kind"] == "model_response" for event in events)
    assert any(event["kind"] == "quota_exceeded" for event in events)
    assert not any(event["agent_id"] == "Spender" and event["kind"] == "done" for event in events)


def test_overseer_aborts_work_item_after_repeated_failures(tmp_path) -> None:
    runtime = _runtime(tmp_path)

    def planner(ctx: AgentContext, event: AgentEvent) -> None:
        ctx.emit("assigned", {"id": "wi-1", "title": "fail", "assigned_worker": "Worker A"}, stage="work")

    def worker(ctx: AgentContext, event: AgentEvent) -> None:
        for _ in range(3):
            ctx.emit("worker_failed", {"work_item_id": "wi-1", "reason": "boom"}, status="error", work_item_id="wi-1")

    (
        PipelineBuilder()
        .on_start("Planner", planner)
        .role("Worker A", worker, on_event("assigned", agent_id="Planner", stage="work"))
        .build()
        .register(runtime)
    )

    handle = runtime.start_run(run_id="overseer", prompt="fail")
    handle.wait(timeout=3)
    events = runtime.store.read_events("overseer")
    runtime.shutdown()

    assert len([event for event in events if event["kind"] == "overseer_action"]) >= 3
    assert any(event["kind"] == "abort_task" and event["work_item_id"] == "wi-1" for event in events)

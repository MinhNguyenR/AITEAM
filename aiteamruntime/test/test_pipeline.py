from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aiteamruntime import AgentRuntime, PipelineBuilder, after_done, node_done_stage, on_runtime_start
from aiteamruntime.events import AgentEvent
from aiteamruntime.runtime import AgentContext
from aiteamruntime.traces import TraceStore
from aiteamruntime.web.server import make_server
from aiteamruntime.test.workflows import register_default_agents


def test_pipeline_builder_registers_user_defined_flow(tmp_path) -> None:
    runtime = AgentRuntime(store=TraceStore(tmp_path / "traces"))
    calls: list[str] = []

    def first(ctx: AgentContext, event: AgentEvent) -> None:
        calls.append("first")
        ctx.emit("done", {"stage": "first"}, stage="first")

    def second(ctx: AgentContext, event: AgentEvent) -> None:
        calls.append("second")
        ctx.emit("finalized", {"stage": "finalize"}, stage="finalize")

    pipeline = (
        PipelineBuilder()
        .role("First", first, on_runtime_start("classify"))
        .role("Second", second, after_done("First", "first"))
        .build()
    )
    pipeline.register(runtime)
    handle = runtime.start_run(run_id="builder-test", prompt="library flow")
    handle.wait(timeout=3)
    runtime.shutdown()

    assert calls == ["first", "second"]


def test_pipeline_node_runs_roles_sequentially_and_emits_done_gate(tmp_path) -> None:
    runtime = AgentRuntime(store=TraceStore(tmp_path / "traces"))
    calls: list[str] = []

    def ambassador(ctx: AgentContext, event: AgentEvent) -> None:
        calls.append("ambassador")
        ctx.emit("reasoning", {"from": "ambassador"}, stage="classify")

    def leader(ctx: AgentContext, event: AgentEvent) -> None:
        calls.append("leader")
        ctx.emit("reasoning", {"from": "leader"}, stage="plan")

    def final(ctx: AgentContext, event: AgentEvent) -> None:
        calls.append("final")
        ctx.emit("finalized", {"from": "final"}, stage="finalize")

    pipeline = (
        PipelineBuilder()
        .node("intake", on_runtime_start("classify"), mode="sequential")
        .role("Ambassador", ambassador)
        .role("Leader", leader)
        .end()
        .after_node("Final", final, node_id="intake")
        .build()
    )
    pipeline.register(runtime)
    handle = runtime.start_run(run_id="node-sequential", prompt="node flow")
    handle.wait(timeout=3)
    runtime.shutdown()

    events = runtime.store.read_events("node-sequential")
    assert calls == ["ambassador", "leader", "final"]
    assert any(event["agent_id"] == "node:intake" and event["stage"] == node_done_stage("intake") for event in events)


def test_pipeline_node_can_release_roles_in_parallel(tmp_path) -> None:
    runtime = AgentRuntime(store=TraceStore(tmp_path / "traces"))
    calls: set[str] = set()

    def worker_a(ctx: AgentContext, event: AgentEvent) -> None:
        calls.add("a")
        ctx.emit("reading", {"worker": "a"}, stage="work")

    def worker_b(ctx: AgentContext, event: AgentEvent) -> None:
        calls.add("b")
        ctx.emit("reading", {"worker": "b"}, stage="work")

    pipeline = (
        PipelineBuilder()
        .node("work", on_runtime_start("classify"), mode="parallel")
        .role("Worker A", worker_a)
        .role("Worker B", worker_b)
        .end()
        .build()
    )
    pipeline.register(runtime)
    handle = runtime.start_run(run_id="node-parallel", prompt="parallel node")
    handle.wait(timeout=3)
    runtime.shutdown()

    events = runtime.store.read_events("node-parallel")
    assert calls == {"a", "b"}
    assert any(event["agent_id"] == "node:work" and event["stage"] == node_done_stage("work") for event in events)


def test_pipeline_node_depends_on_waits_for_parent_node(tmp_path) -> None:
    runtime = AgentRuntime(store=TraceStore(tmp_path / "traces"))
    calls: list[str] = []

    def parent(ctx: AgentContext, event: AgentEvent) -> None:
        calls.append("parent")

    def child(ctx: AgentContext, event: AgentEvent) -> None:
        calls.append("child")

    pipeline = (
        PipelineBuilder()
        .node("child", on_runtime_start("classify"), mode="sequential", depends_on=("parent",))
        .role("Child", child)
        .end()
        .node("parent", on_runtime_start("classify"), mode="sequential")
        .role("Parent", parent)
        .end()
        .build()
    )
    pipeline.register(runtime)
    handle = runtime.start_run(run_id="node-dependency", prompt="node dependency")
    handle.wait(timeout=3)
    runtime.shutdown()

    assert calls == ["parent", "child"]


def test_pipeline_node_resource_lock_is_released_after_join(tmp_path) -> None:
    runtime = AgentRuntime(store=TraceStore(tmp_path / "traces"))

    def first(ctx: AgentContext, event: AgentEvent) -> None:
        ctx.emit("reading", {"node": "first"})

    def second(ctx: AgentContext, event: AgentEvent) -> None:
        ctx.emit("reading", {"node": "second"})

    pipeline = (
        PipelineBuilder()
        .node("first", on_runtime_start("classify"), requires_resources=("shared",))
        .role("First", first)
        .end()
        .node("second", on_runtime_start("classify"), depends_on=("first",), requires_resources=("shared",))
        .role("Second", second)
        .end()
        .build()
    )
    pipeline.register(runtime)
    handle = runtime.start_run(run_id="node-lock-release", prompt="node lock release")
    handle.wait(timeout=3)

    events = runtime.store.read_events("node-lock-release")
    runtime.shutdown()

    assert not runtime.locks.snapshot()["held"]
    assert [event["kind"] for event in events].count("node_released") == 2


def test_sqlite_trace_store_persists_runs_across_instances(tmp_path) -> None:
    store = TraceStore(tmp_path / "traces")
    runtime = AgentRuntime(store=store)

    def role(ctx: AgentContext, event: AgentEvent) -> None:
        ctx.emit("finalized", {"ok": True}, stage="finalize")

    PipelineBuilder().on_start("One", role).build().register(runtime)
    handle = runtime.start_run(run_id="sqlite-persist", prompt="sqlite persistence")
    handle.wait(timeout=3)
    runtime.shutdown()

    reloaded = TraceStore(tmp_path / "traces")
    try:
        runs = reloaded.list_runs()
        events = reloaded.read_events("sqlite-persist")
    finally:
        reloaded.shutdown()

    assert any(run["run_id"] == "sqlite-persist" for run in runs)
    assert any(event["kind"] == "finalized" for event in events)


def test_web_pipeline_requires_workspace_and_rejects_missing_model(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("AITEAMRUNTIME_REAL_MODEL_API_KEY", raising=False)
    monkeypatch.setenv("AITEAMRUNTIME_DISABLE_REAL_MODEL", "1")
    store = TraceStore(tmp_path / "traces")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    server = make_server("127.0.0.1", 0, store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    base = f"http://{host}:{port}"
    try:
        pipelines = json.loads(urlopen(f"{base}/pipelines", timeout=3).read())
        assert pipelines[0]["pipeline_id"] == "trackaiteam"
        fs_view = json.loads(urlopen(f"{base}/fs?path={workspace}", timeout=3).read())
        assert Path(fs_view["current"]) == workspace.resolve()

        create_pipeline = Request(
            f"{base}/pipelines",
            data=json.dumps({"name": "Empty Pipeline"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        pipeline = json.loads(urlopen(create_pipeline, timeout=3).read())
        runs_after_pipeline = json.loads(urlopen(f"{base}/runs", timeout=3).read())
        assert not any((run.get("metadata") or {}).get("pipeline_id") == pipeline["pipeline_id"] for run in runs_after_pipeline)
        missing_workspace = Request(
            f"{base}/runs",
            data=json.dumps({"task": "write workspace artifact", "pipeline_id": pipeline["pipeline_id"]}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urlopen(missing_workspace, timeout=3)
        except HTTPError as exc:
            assert exc.code == 400
        else:
            raise AssertionError("missing workspace accepted")

        update_pipeline = Request(
            f"{base}/pipelines/{pipeline['pipeline_id']}",
            data=json.dumps({"workspace": str(workspace)}).encode(),
            headers={"Content-Type": "application/json"},
            method="PATCH",
        )
        updated = json.loads(urlopen(update_pipeline, timeout=3).read())
        assert updated["workspace"] == str(workspace)

        create_run = Request(
            f"{base}/runs",
            data=json.dumps(
                {
                    "task": "write workspace artifact",
                    "pipeline_id": pipeline["pipeline_id"],
                    "workspace": str(workspace),
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urlopen(create_run, timeout=3)
        except HTTPError as exc:
            assert exc.code == 409
            payload = json.loads(exc.read())
            assert payload["error"] == "model provider is not ready"
        else:
            raise AssertionError("missing model provider accepted")
        create_run_again = Request(
            f"{base}/runs",
            data=json.dumps(
                {
                    "task": "write workspace artifact",
                    "pipeline_id": pipeline["pipeline_id"],
                    "workspace": str(workspace),
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urlopen(create_run_again, timeout=3)
        except HTTPError as exc:
            assert exc.code == 409
        else:
            raise AssertionError("missing model provider accepted")
    finally:
        server.shutdown()
        server.server_close()

    assert not list(Path(workspace).glob(".aiteamruntime/**/*.txt"))

    reloaded_server = make_server("127.0.0.1", 0, store)
    thread = threading.Thread(target=reloaded_server.serve_forever, daemon=True)
    thread.start()
    host, port = reloaded_server.server_address[:2]
    try:
        persisted = json.loads(urlopen(f"http://{host}:{port}/pipelines", timeout=3).read())
    finally:
        reloaded_server.shutdown()
        reloaded_server.server_close()
    assert any(item["pipeline_id"] == pipeline["pipeline_id"] and item["workspace"] == str(workspace) for item in persisted)


def test_web_answer_rejects_missing_model_provider(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("AITEAMRUNTIME_REAL_MODEL_API_KEY", raising=False)
    monkeypatch.setenv("AITEAMRUNTIME_DISABLE_REAL_MODEL", "1")
    store = TraceStore(tmp_path / "traces")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store.start_run("pending-question", {"workspace": str(workspace), "task": "build"})
    store.append(
        AgentEvent(
            "pending-question",
            "Ambassador",
            "question",
            {"question": "Clarify target", "task": "build", "tier": "MEDIUM"},
            status="waiting",
            stage="classify",
        )
    )
    server = make_server("127.0.0.1", 0, store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    base = f"http://{host}:{port}"
    try:
        answer = Request(
            f"{base}/runs/pending-question/answers",
            data=json.dumps({"answer": "Create a workspace artifact and validate it."}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urlopen(answer, timeout=3)
        except HTTPError as exc:
            assert exc.code == 409
            payload = json.loads(exc.read())
            assert payload["error"] == "model provider is not ready"
        else:
            raise AssertionError("answer accepted without model provider")
    finally:
        server.shutdown()
        server.server_close()


def test_react_project_setup_gate_runs_before_workers(tmp_path) -> None:
    store = TraceStore(tmp_path / "traces")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runtime = AgentRuntime(store=store, cleanup_delay=600.0)
    register_default_agents(runtime)

    handle = runtime.start_run(
        run_id="react-setup-gate",
        prompt="Create a React app proof project in this empty workspace.",
        metadata={"workspace": str(workspace)},
    )
    deadline = time.time() + 10.0
    events = store.read_events(handle.run_id)
    while time.time() < deadline:
        handle.wait(timeout=1)
        events = store.read_events(handle.run_id)
        if any(event["kind"] == "assigned" for event in events):
            break
        time.sleep(0.1)
    runtime.shutdown()

    kinds = [(event["sequence"], event["agent_id"], event["kind"], event["stage"]) for event in events]
    first_setup_requested = min(seq for seq, _agent, kind, _stage in kinds if kind == "setup_requested")
    first_setup_done = min(seq for seq, _agent, kind, _stage in kinds if kind == "setup_done")
    first_assigned = min(seq for seq, _agent, kind, _stage in kinds if kind == "assigned")
    first_worker_read = min(
        (seq for seq, agent, kind, stage in kinds if agent.startswith("Worker ") and kind == "reading" and stage == "work"),
        default=999999,
    )

    assert first_setup_requested < first_setup_done
    assert first_setup_done < first_assigned
    assert first_setup_done < first_worker_read
    assert (workspace / "package.json").exists()
    assert (workspace / "src" / "App.jsx").exists()
    assert (workspace / "index.html").exists()
    assert (workspace / ".aiteamruntime_setup.json").exists()
    setup_done = next(event for event in events if event["kind"] == "setup_done")
    assert "Secretary created Vite React project scaffold" in (setup_done["payload"].get("output") or "")
    assert "package.json" in (setup_done["payload"].get("creates") or [])

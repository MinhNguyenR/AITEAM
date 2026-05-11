from __future__ import annotations

import json
import time
import threading
from collections import Counter
from urllib.request import urlopen

from aiteamruntime.demo import run_demo
from aiteamruntime.events import AgentEvent
from aiteamruntime.runtime import AgentRuntime, AgentSpec
from aiteamruntime.test.workflows import register_default_agents
from aiteamruntime.traces import TraceStore
from aiteamruntime.web.server import make_server


def test_default_agents_trigger_parallel_trace(tmp_path):
    store = TraceStore(tmp_path)
    runtime = AgentRuntime(store=store)
    register_default_agents(runtime)

    handle = runtime.start_run(run_id="r1", prompt="implement a small change")
    handle.wait(timeout=5)
    runtime.shutdown()

    events = store.read_events("r1")
    pairs = [(e["agent_id"], e["kind"]) for e in events]
    assert ("Ambassador", "classifying") in pairs
    assert ("Leader", "reasoning") in pairs
    assert ("Worker A", "terminal_requested") in pairs
    assert ("Secretary", "terminal_result") in pairs
    assert ("Tool Curator", "file_create") in pairs


def test_demo_writes_index_and_events(tmp_path):
    run_id = run_demo(trace_root=str(tmp_path), run_id="demo-test")
    store = TraceStore(tmp_path)
    assert run_id == "demo-test"
    assert store.list_runs()[0]["run_id"] == "demo-test"
    assert len(store.read_events("demo-test")) >= 10


def test_trace_store_recovers_single_object_index(tmp_path):
    (tmp_path / "index.json").write_text(
        "\ufeff" + json.dumps({"run_id": "single-run", "events": 3}),
        encoding="utf-8",
    )
    store = TraceStore(tmp_path)
    runs = store.list_runs()
    assert len(runs) == 1
    assert runs[0]["run_id"] == "single-run"
    assert runs[0]["events"] == 3


def test_trace_web_endpoints_include_summary(tmp_path):
    store = TraceStore(tmp_path)
    runtime = AgentRuntime(store=store)
    register_default_agents(runtime)
    handle = runtime.start_run(run_id="web-test", prompt="trace web")
    handle.wait(timeout=5)
    runtime.shutdown()

    server = make_server("127.0.0.1", 0, store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        health = json.loads(urlopen(f"http://{host}:{port}/health", timeout=3).read())
        runs = json.loads(urlopen(f"http://{host}:{port}/runs", timeout=3).read())
        events = json.loads(urlopen(f"http://{host}:{port}/runs/web-test/events", timeout=3).read())
        summary = json.loads(urlopen(f"http://{host}:{port}/runs/web-test/summary", timeout=3).read())
        resources = json.loads(urlopen(f"http://{host}:{port}/runs/web-test/resources", timeout=3).read())
        agents = json.loads(urlopen(f"http://{host}:{port}/runs/web-test/agents", timeout=3).read())
    finally:
        server.shutdown()
        server.server_close()

    assert health["ok"] is True
    assert runs[0]["run_id"] == "web-test"
    assert events
    assert summary["events"] == len(events)
    assert "Leader" in summary["agents"]
    assert "file_events" in resources
    assert any(row["agent_id"] == "Leader" for row in agents)


def test_event_metadata_and_validation():
    event = AgentEvent("run", "agent", "reading")
    assert event.event_id
    assert event.correlation_id
    assert event.to_dict()["sequence"] == 0

    try:
        AgentEvent("run", "agent", "not-a-kind")
    except ValueError as exc:
        assert "unknown agent event kind" in str(exc)
    else:
        raise AssertionError("invalid event kind accepted")


def test_file_lock_blocks_second_agent_same_path(tmp_path):
    store = TraceStore(tmp_path)
    runtime = AgentRuntime(store=store)

    def trigger(event):
        return event.agent_id == "runtime" and event.kind == "classifying"

    def first(ctx, event):
        ctx.emit("writing", {"file": "same.py"})
        time.sleep(0.05)
        ctx.emit("file_update", {"path": "same.py", "added_lines": 1})
        ctx.emit("done", {"stage": "worker"})

    def second(ctx, event):
        ctx.emit("writing", {"file": "same.py"})
        ctx.emit("file_update", {"path": "same.py", "added_lines": 2})
        ctx.emit("done", {"stage": "worker"})

    runtime.register(AgentSpec("Worker A", first, trigger))
    runtime.register(AgentSpec("Worker B", second, trigger))
    handle = runtime.start_run(run_id="file-lock", prompt="collision")
    handle.wait(timeout=5)
    runtime.shutdown()

    events = store.read_events("file-lock")
    blocked = [e for e in events if e["kind"] == "blocked" and e["payload"].get("resource_type") == "file"]
    updates = [e for e in events if e["kind"] == "file_update" and e["payload"].get("path") == "same.py"]
    assert blocked
    assert len(updates) == 1


def test_duplicate_terminal_command_does_not_run_twice(tmp_path):
    store = TraceStore(tmp_path)
    runtime = AgentRuntime(store=store)

    def trigger(event):
        return event.agent_id == "runtime" and event.kind == "classifying"

    def requester(ctx, event):
        ctx.request_terminal("pytest -q", cwd=".")
        ctx.emit("done", {"stage": "worker"})

    def secretary(ctx, event):
        ctx.emit("terminal_running", {"command": event.payload["command"], "cwd": event.payload.get("cwd", ".")})
        time.sleep(0.02)
        ctx.emit("terminal_result", {"command": event.payload["command"], "cwd": event.payload.get("cwd", "."), "exit_code": 0})
        ctx.emit("done", {"stage": "secretary"})

    runtime.register(AgentSpec("Worker A", requester, trigger))
    runtime.register(AgentSpec("Worker B", requester, trigger))
    runtime.register(AgentSpec("Secretary", secretary, lambda event: event.kind == "terminal_requested"))
    handle = runtime.start_run(run_id="terminal-dedupe", prompt="terminal")
    handle.wait(timeout=5)
    runtime.shutdown()

    events = store.read_events("terminal-dedupe")
    counts = Counter(e["kind"] for e in events)
    assert counts["terminal_running"] == 1
    assert counts["terminal_result"] == 1
    assert any(e["kind"] == "blocked" and e["payload"].get("resource_type") == "terminal" for e in events)


def test_trigger_event_idempotency(tmp_path):
    store = TraceStore(tmp_path)
    runtime = AgentRuntime(store=store)
    calls = {"count": 0}

    def handler(ctx, event):
        calls["count"] += 1
        ctx.emit("done", {"stage": "handled"})

    runtime.register(AgentSpec("Once", handler, lambda event: event.kind == "question"))
    event = runtime.emit("idem", "tester", "question", {"q": "run once"})
    runtime._dispatch(event)
    runtime.wait(run_id="idem", timeout=5)
    runtime.shutdown()

    assert calls["count"] == 1


def test_runtime_aborts_cross_agent_loop(tmp_path):
    store = TraceStore(tmp_path)
    runtime = AgentRuntime(store=store, max_trigger_depth=4, max_events_per_run=50)

    def a(ctx, event):
        ctx.emit("question", {"from": "a"})

    def b(ctx, event):
        ctx.emit("question", {"from": "b"})

    runtime.register(AgentSpec("A", a, lambda event: event.agent_id == "runtime" and event.kind == "classifying" or event.agent_id == "B" and event.kind == "question"))
    runtime.register(AgentSpec("B", b, lambda event: event.agent_id == "A" and event.kind == "question"))
    handle = runtime.start_run(run_id="loop", prompt="loop")
    handle.wait(timeout=5)
    runtime.shutdown()

    events = store.read_events("loop")
    assert any(e["kind"] == "abort" for e in events)
    assert runtime.run_state("loop") == "cleaned"

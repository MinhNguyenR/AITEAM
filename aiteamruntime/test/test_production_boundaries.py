from __future__ import annotations

import inspect
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import threading

from aiteamruntime.events import AgentEvent
from aiteamruntime.runtime import AgentRuntime, AgentSpec, WorkItem
from aiteamruntime.traces import TraceStore
from aiteamruntime.web import server as web_server


def test_web_and_public_agents_do_not_import_test_workflow() -> None:
    import aiteamruntime.agents as agents

    assert "aiteamruntime.test" not in inspect.getsource(web_server)
    assert "aiteamruntime.test" not in inspect.getsource(agents)


def test_web_run_creation_rejects_missing_model_provider(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("AITEAMRUNTIME_REAL_MODEL_API_KEY", raising=False)
    monkeypatch.setenv("AITEAMRUNTIME_DISABLE_REAL_MODEL", "1")
    store = TraceStore(tmp_path / "traces")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    server = web_server.make_server("127.0.0.1", 0, store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        req = Request(
            f"http://{host}:{port}/runs",
            data=json.dumps({"task": "real model only", "workspace": str(workspace)}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urlopen(req, timeout=3)
        except HTTPError as exc:
            assert exc.code == 409
            payload = json.loads(exc.read())
            assert payload["model"]["ok"] is False
        else:
            raise AssertionError("web accepted a production run without a real model provider")
    finally:
        server.shutdown()
        server.server_close()


def test_worker_write_outside_allowed_paths_is_blocked(tmp_path) -> None:
    runtime = AgentRuntime(store=TraceStore(tmp_path / "traces"))
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    def writer(ctx, event):
        ctx.emit("writing", {"file": "blocked.txt", "work_item_id": "wi-1"}, stage="work", work_item_id="wi-1")
        ctx.emit("done", {"stage": "work", "work_item_id": "wi-1"}, stage="work", work_item_id="wi-1")

    runtime.register(AgentSpec("Worker A", writer, lambda event: event.kind == "assigned"))
    handle = runtime.start_run(run_id="allowed-paths", prompt="test", metadata={"workspace": str(workspace)})
    with runtime._lock:
        run = runtime._runs[handle.run_id]
        run.work_items["wi-1"] = WorkItem(id="wi-1", title="write", assigned_worker="Worker A", allowed_paths=["allowed.txt"])
    runtime.emit(
        handle.run_id,
        "Tool Curator",
        "assigned",
        {"work_item": {"id": "wi-1", "title": "write", "assigned_worker": "Worker A", "allowed_paths": ["allowed.txt"]}},
        work_item_id="wi-1",
        assignment={"id": "wi-1", "title": "write", "assigned_worker": "Worker A", "allowed_paths": ["allowed.txt"]},
    )
    handle.wait(timeout=3)
    runtime.shutdown()

    events = runtime.store.read_events(handle.run_id)
    assert any(event["kind"] == "blocked" and event["payload"].get("reason") == "path is outside work item allowed_paths" for event in events)
    assert not (workspace / "blocked.txt").exists()

from __future__ import annotations

from types import SimpleNamespace

from core.cli.python_cli.workflow.runtime.graph import runner


class _DummyLive:
    def __init__(self, *args, **kwargs):
        self.updates = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def update(self, renderable):
        self.updates.append(renderable)


class _DummyWs:
    def __init__(self):
        self.render_calls = []

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None

    def new_thread_id(self):
        return "tid-1"

    def get_pipeline_status_message(self):
        return ""

    def is_pipeline_stop_requested(self):
        return False

    def get_workflow_list_nodes_state(self):
        return []


def test_run_agent_graph_inline_progress_passes_ui_style(monkeypatch):
    dummy_ws = _DummyWs()
    monkeypatch.setattr(runner, "ws", dummy_ws)
    monkeypatch.setattr(runner, "Live", _DummyLive)
    monkeypatch.setattr(runner, "get_checkpointer", lambda: object())

    def _renderable(_tier, _msg, *, ui_style="list"):
        dummy_ws.render_calls.append(ui_style)
        return f"style={ui_style}"

    monkeypatch.setattr(runner, "inline_workflow_renderable", _renderable)

    class _Graph:
        def stream(self, _init, _config):
            yield {"leader_generate": {"ok": True}}
            yield {"leader_generate": {"ok": True}}

        def get_state(self, _config):
            return SimpleNamespace(next=("human_context_gate",), values={"context_path": "context.md"})

    monkeypatch.setattr(runner, "get_graph", lambda _cp, interrupt_before=(): _Graph())
    monkeypatch.setattr(runner, "update_context_state", lambda *args, **kwargs: None)

    brief = SimpleNamespace(tier="MEDIUM", model_dump=lambda: {}, task_uuid="t1")
    outcome = runner.run_agent_graph(
        brief,
        "task",
        ".",
        {"auto_accept_context": False},
        inline_progress=True,
    )

    assert outcome == "paused"
    assert dummy_ws.render_calls
    assert all(style == "list" for style in dummy_ws.render_calls)

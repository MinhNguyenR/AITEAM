from __future__ import annotations

import time

import core.cli.python_cli.workflow.tui.monitor.core._render_mixin as render_mixin
import core.cli.python_cli.workflow.tui.monitor.helpers as monitor_helpers
from core.cli.python_cli.workflow.tui.monitor.core._render_mixin import _RenderMixin


class _DummyRender(_RenderMixin):
    pass


def test_active_role_cards_render_substates_independent_of_active_step(monkeypatch):
    monkeypatch.setattr(monitor_helpers, "_parse_token_counts_for_node", lambda node: (0, 0))
    monkeypatch.setattr(
        render_mixin,
        "_get_role_display",
        lambda node: {"worker": "Worker", "secretary": "Secretary"}.get(node, node),
    )

    app = _DummyRender()
    app._state_start_times = {"worker": time.time(), "secretary": time.time()}
    app._attempt_count = 1
    app._reasoning_acc = ""
    app._reasoning_active = False
    app._leader_substate_start = time.time()
    app._ambassador_substate = ""
    app._ambassador_detail = ""
    app._leader_session_substate = ""
    app._leader_session_detail = ""
    app._curator_substate = ""
    app._curator_detail = ""
    app._worker_substate = "reading"
    app._worker_detail = ""
    app._worker_reading_files = ["src/app.py"]
    app._worker_using_cmd = ""
    app._secretary_substate = "using"
    app._secretary_detail = "pytest"
    app._secretary_commands = []
    app._explainer_substate = ""
    app._explainer_detail = ""

    rendered = app._render_active_role_cards("leader_generate", "*", "", {})

    assert "Worker" in rendered
    assert "src/app.py" in rendered
    assert "Secretary" in rendered
    assert "pytest" in rendered

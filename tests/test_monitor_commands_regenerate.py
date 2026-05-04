from __future__ import annotations

import sys
from unittest.mock import patch

from core.cli.python_cli.workflow.tui.monitor.commands.mixin import _CommandsMixin
from core.cli.python_cli.workflow.tui.monitor.core._constants import _GATE_REGEN, _GATE_WAITING


class _DummyCmdApp(_CommandsMixin):
    def __init__(self):
        self._log_mode = False
        self._task_mode_pending = None
        self._clarif_mode = False
        self._clarif_data = {}
        self._exit_confirm_mode = False
        self._post_delete_mode = True
        self._ask_thinking = False
        self._gate_state = ""
        self._attempt_count = 1
        self._last_active_step = "leader_generate"
        self._shown_file_events = ["x"]
        self._leader_substate = "generating"
        self._completed_nodes = {"leader_generate", "human_context_gate", "finalize_phase1"}
        self._last_task_text = "do task"
        self._pipeline_pending = False
        self._spin = 0
        self._scroll_offset = 0
        self._app = None

    def _write(self, *args, **kwargs):
        return None

    def _set_live(self, _msg):
        return None

    def _do_new_task(self, *args, **kwargs):
        return None

    def _start_decline_countdown(self):
        self._countdown_started = True

    def _close_log(self):
        return None

    def _do_cleanup_exit(self):
        return None


def test_post_delete_no_regenerate_sets_waiting():
    app = _DummyCmdApp()
    app._countdown_started = False
    app._handle_cmd("n")
    assert app._gate_state == _GATE_WAITING
    assert app._countdown_started is True


def test_post_delete_yes_regenerate_sets_regen_and_pending():
    app = _DummyCmdApp()
    mock_start_flow = type("StartFlowMock", (), {"start_pipeline_from_tui": lambda *a, **k: None})()
    with patch("core.cli.python_cli.workflow.runtime.session.reset_pipeline_visual"), patch(
        "core.cli.python_cli.workflow.runtime.session.set_pipeline_run_finished"
    ), patch.dict("sys.modules", {"core.cli.python_cli.features.start.flow": mock_start_flow}):
        app._handle_cmd("y")
    assert app._gate_state == _GATE_REGEN
    assert app._attempt_count == 2
    assert app._pipeline_pending is True

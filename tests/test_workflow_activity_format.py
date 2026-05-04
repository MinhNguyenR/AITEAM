from __future__ import annotations

from core.cli.python_cli.workflow.runtime.persist.activity_log import format_activity_lines


def test_format_activity_lines_collapses_immediate_duplicates():
    records = [
        {"ts": 100.0, "node": "leader_generate", "action": "enter", "detail": "phaseA"},
        {"ts": 100.8, "node": "leader_generate", "action": "enter", "detail": "phaseA"},
        {"ts": 103.0, "node": "leader_generate", "action": "enter", "detail": "phaseA"},
    ]
    lines = format_activity_lines(records, "")
    assert len(lines) == 2


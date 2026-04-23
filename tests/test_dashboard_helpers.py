from __future__ import annotations

from datetime import datetime

from core.dashboard.reporting.state import DashboardRangeState
from core.dashboard.tui.utils import default_range, paginate, safe_float, safe_int, sort_rows_chronological


def test_safe_int_and_float():
    assert safe_int("3") == 3
    assert safe_int(None) == 0
    assert safe_float("2.5") == 2.5
    assert safe_float(None) == 0.0


def test_default_range_window():
    anchor = datetime(2026, 4, 16, 12, 0, 0)
    since, until = default_range(1, anchor)
    assert until == anchor
    assert since == datetime(2026, 4, 15, 12, 0, 0)


def test_paginate_clamps_and_slices():
    items = list(range(10))
    page_slice, page, total = paginate(items, page=99, page_size=4)
    assert total == 3
    assert page == 2
    assert page_slice == [8, 9]


def test_sort_rows_chronological():
    rows = [
        {"timestamp": "2026-04-16T12:05:00"},
        {"timestamp": "2026-04-16T12:01:00"},
        {"timestamp": "2026-04-16T12:03:00"},
    ]
    sorted_rows = sort_rows_chronological(rows)
    assert [r["timestamp"] for r in sorted_rows] == [
        "2026-04-16T12:01:00",
        "2026-04-16T12:03:00",
        "2026-04-16T12:05:00",
    ]


def test_dashboard_range_state_defaults():
    state = DashboardRangeState(label="x")
    assert state.rows == []
    assert state.log_page == 0
    assert state.batch_page == 0
    assert state.explorer_batch_page == 0

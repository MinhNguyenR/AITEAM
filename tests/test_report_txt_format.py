"""Tests for core/dashboard/reporting/report_txt_format.py — ASCII text export."""
from datetime import datetime

from core.dashboard.reporting.report_model import RoleAgg, RoleModelAgg, UsageReport
from core.dashboard.reporting.report_txt_format import _ascii_table, _hline, format_usage_report_txt


def _make_report(**kwargs) -> UsageReport:
    defaults = dict(
        label="test",
        since=datetime(2024, 6, 1, 0, 0, 0),
        until=datetime(2024, 6, 7, 23, 59, 59),
        generated_at=datetime(2024, 6, 8, 12, 0, 0),
        total_requests=5,
        total_tokens=1000,
        total_spend=0.015,
        prompt_tokens=800,
        completion_tokens=200,
        cli_turns=2,
        by_role=[],
        by_role_model=[],
        batches=[],
        raw_rows=[],
        period_summary={},
    )
    defaults.update(kwargs)
    return UsageReport(**defaults)


class TestHline:
    def test_width(self):
        line = _hline(20)
        assert len(line) == 20
        assert all(c == "=" for c in line)


class TestAsciiTable:
    def test_basic(self):
        rows = _ascii_table(["Col A", "Col B"], [["val1", "val2"]], [10, 10])
        assert len(rows) > 0
        combined = "\n".join(rows)
        assert "Col A" in combined
        assert "val1" in combined

    def test_header_row_first(self):
        rows = _ascii_table(["H"], [["r1"], ["r2"]], [5])
        assert "H" in rows[1]
        # Separator above and below header
        assert rows[0].startswith("+")
        assert rows[2].startswith("+")

    def test_truncates_long_cell(self):
        rows = _ascii_table(["H"], [["x" * 20]], [5])
        # cell should be truncated to width=5
        content_line = rows[3]
        inner = content_line[2:-2]  # strip "| " and " |"
        assert len(inner.strip()) <= 5


class TestFormatUsageReportTxt:
    def test_basic_structure(self):
        r = _make_report()
        out = format_usage_report_txt(r)
        assert "AI TEAM" in out
        assert "METADATA" in out
        assert "SUMMARY" in out
        assert out.endswith("\n")

    def test_includes_label(self):
        r = _make_report(label="my custom label")
        out = format_usage_report_txt(r)
        assert "my custom label" in out

    def test_no_rows_shows_empty_message(self):
        r = _make_report(by_role=[], by_role_model=[])
        out = format_usage_report_txt(r)
        assert "(no rows in range)" in out

    def test_by_role_table_shown(self):
        r = _make_report(by_role=[
            RoleAgg(role="AMBASSADOR", requests=3, tokens=500, cost_usd=0.01),
        ])
        out = format_usage_report_txt(r)
        assert "AMBASSADOR" in out
        assert "BY ROLE" in out

    def test_by_role_model_table_shown(self):
        r = _make_report(by_role_model=[
            RoleModelAgg(role="LEADER", model="claude-3-haiku", requests=2, tokens=300, cost_usd=0.005),
        ])
        out = format_usage_report_txt(r)
        assert "LEADER" in out
        assert "claude-3-haiku" in out
        assert "BY ROLE / MODEL" in out

    def test_by_role_model_truncation_message(self):
        many = [
            RoleModelAgg(role=f"role{i}", model=f"model{i}", requests=1, tokens=10, cost_usd=0.0)
            for i in range(85)
        ]
        r = _make_report(by_role_model=many)
        out = format_usage_report_txt(r)
        assert "+5 more" in out

    def test_batches_table_shown(self):
        r = _make_report(batches=[
            {
                "batch_idx": 1,
                "timestamp": "2024-06-01T10:00:00",
                "mode": "ask",
                "totals": {"prompt_tokens": 100, "completion_tokens": 50},
                "usage_rows": [{"x": 1}, {"x": 2}],
            }
        ])
        out = format_usage_report_txt(r)
        assert "BATCHES" in out
        assert "2024-06-01" in out

    def test_no_batches_shows_message(self):
        r = _make_report(batches=[])
        out = format_usage_report_txt(r)
        assert "(no batches)" in out

    def test_raw_display_note_included(self):
        r = _make_report(raw_display_note="export lists up to 5000 raw rows")
        out = format_usage_report_txt(r)
        assert "export lists up to 5000 raw rows" in out

    def test_period_summary_rows(self):
        r = _make_report(period_summary={
            "daily": {"requests": 5, "tokens": 100, "spend": 0.001},
            "monthly": {"requests": 50, "tokens": 1000, "spend": 0.01},
        })
        out = format_usage_report_txt(r)
        assert "daily" in out or "monthly" in out

    def test_batch_display_limit_message(self):
        batches = [
            {"batch_idx": i, "timestamp": "2024-06-01T10:00:00", "mode": "ask",
             "totals": {}, "usage_rows": []}
            for i in range(40)
        ]
        r = _make_report(batches=batches, batch_display_limit=40)
        out = format_usage_report_txt(r)
        assert "showing first 40" in out

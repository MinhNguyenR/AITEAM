from __future__ import annotations

from pathlib import Path

from core.dashboard.output.pdf_export import export_pdf
from core.dashboard.reporting.state import DashboardRangeState


def test_export_pdf_falls_back_without_font(monkeypatch, tmp_path: Path):
    fake_range = DashboardRangeState(label="test")
    fake_range.rows = []

    called = {"fonts": []}

    class FakeFPDF:
        def set_auto_page_break(self, auto=True, margin=12):
            called["auto_page_break"] = (auto, margin)

        def add_font(self, name, style, path, uni=True):
            called["fonts"].append((name, style, path, uni))

        def set_font(self, name, style, size):
            called.setdefault("set_font", []).append((name, style, size))
            self.font_family = name

        def cell(self, *args, **kwargs):
            called.setdefault("cell", 0)
            called["cell"] += 1

        def multi_cell(self, *args, **kwargs):
            called.setdefault("multi_cell", 0)
            called["multi_cell"] += 1

        def ln(self, *args, **kwargs):
            pass

        def add_page(self):
            called["add_page"] = called.get("add_page", 0) + 1

        def output(self, path):
            called["output"] = path

    monkeypatch.setattr("fpdf.FPDF", FakeFPDF)
    monkeypatch.setattr("core.dashboard.output.pdf_export.Path", Path)
    monkeypatch.setattr("core.dashboard.output.pdf_export._candidate_fonts", lambda project_root=None: (None, None, "txt"))
    monkeypatch.setattr("utils.tracker.summarize_tokens_by_cli_batches", lambda s, u: [])
    monkeypatch.setattr("utils.tracker.read_usage_rows_timerange", lambda s, u: [])
    monkeypatch.setattr("utils.tracker.get_period_usage", lambda: {})
    monkeypatch.setattr("utils.tracker.token_io_totals", lambda rows: {"prompt_tokens": 0, "completion_tokens": 0})

    export_pdf(tmp_path, fake_range)

    assert "add_page" not in called
    assert called["fonts"] == []
    txt_files = list(tmp_path.glob("ai_team_usage_*.txt"))
    assert txt_files and txt_files[0].suffix == ".txt"

from __future__ import annotations

from pathlib import Path

from core.dashboard.output.pdf_export import export_pdf
from core.dashboard.reporting.state import DashboardRangeState


class DummyTracker:
    pass


def test_export_pdf_uses_existing_times_font(monkeypatch, tmp_path: Path):
    font_path = tmp_path / "times.ttf"
    font_path.write_bytes(b"dummy-font")

    fake_range = DashboardRangeState(label="test")
    fake_range.rows = []

    called = {}

    class FakeFPDF:
        def __init__(self, *args, **kwargs):
            pass

        def set_auto_page_break(self, auto=True, margin=12):
            called["auto_page_break"] = (auto, margin)

        def set_margins(self, *args):
            pass

        def add_font(self, name, style, path, uni=True):
            called.setdefault("fonts", []).append((name, style, path, uni))

        def set_font(self, name, style, size):
            called.setdefault("set_font", []).append((name, style, size))

        def set_text_color(self, *args):
            pass

        def set_fill_color(self, *args):
            pass

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

        def page_no(self):
            return 1

        def get_x(self):
            return 10.0

        def output(self, path):
            called["output"] = path

    import sys
    _pdf_mod = sys.modules["core.dashboard.output.pdf_export"]
    monkeypatch.setattr("fpdf.FPDF", FakeFPDF)
    monkeypatch.setattr(_pdf_mod, "Path", Path)
    monkeypatch.setattr(_pdf_mod, "_candidate_fonts", lambda project_root=None: (font_path, None, "test"))
    monkeypatch.setattr("utils.tracker.summarize_tokens_by_cli_batches", lambda s, u: [])
    monkeypatch.setattr("utils.tracker.read_usage_rows_timerange", lambda s, u: [])
    monkeypatch.setattr("utils.tracker.get_period_usage", lambda: {})
    monkeypatch.setattr("utils.tracker.token_io_totals", lambda rows: {"prompt_tokens": 0, "completion_tokens": 0})

    export_pdf(tmp_path, fake_range)

    assert called["add_page"] == 1
    assert called.get("fonts")
    assert called["output"].endswith(".pdf")

"""Tests for core/dashboard/shell/history.py pure helpers."""
import sys
from unittest.mock import MagicMock

# Stub heavy UI imports
_STUBS = {
    "rich.box": MagicMock(ROUNDED=MagicMock()),
    "rich.panel": MagicMock(Panel=MagicMock()),
    "rich.prompt": MagicMock(Prompt=MagicMock()),
    "rich.table": MagicMock(Table=MagicMock()),
    "core.cli.cli_prompt": MagicMock(GLOBAL_BACK="back", GLOBAL_EXIT="exit",
                                     normalize_global_command=lambda x: x, wait_enter=MagicMock()),
    "core.cli.nav": MagicMock(NavToMain=Exception),
    "core.cli.chrome.ui": MagicMock(clear_screen=MagicMock(), console=MagicMock()),
    "core.services": MagicMock(),
    "core.services.dashboard_data": MagicMock(),
    "core.dashboard.shell.data": MagicMock(),
    "core.dashboard.output.exporters": MagicMock(export_excel=MagicMock()),
    "core.dashboard.output.pdf_export": MagicMock(export_pdf=MagicMock()),
    "core.dashboard.reporting.state": MagicMock(DashboardRangeState=MagicMock()),
    "core.dashboard.reporting.text_export": MagicMock(export_txt=MagicMock()),
    "core.dashboard.tui.panels": MagicMock(dashboard_panel=MagicMock()),
    "core.dashboard.tui.render": MagicMock(header=MagicMock()),
    "core.dashboard.tui.utils": MagicMock(paginate=MagicMock(return_value=([], 0, 1))),
}
for mod, mock in _STUBS.items():
    sys.modules.setdefault(mod, mock)

from core.dashboard.shell.history import _parse_positive_int


class TestParsePositiveInt:
    def test_valid_int(self):
        assert _parse_positive_int("5") == 5

    def test_with_whitespace(self):
        assert _parse_positive_int("  7  ") == 7

    def test_invalid_string_returns_none(self):
        assert _parse_positive_int("abc") is None

    def test_zero_returns_none(self):
        assert _parse_positive_int("0") is None

    def test_negative_returns_none(self):
        assert _parse_positive_int("-1") is None

    def test_max_value_enforced(self):
        assert _parse_positive_int("100", max_value=50) is None

    def test_within_max_value_ok(self):
        assert _parse_positive_int("30", max_value=50) == 30

    def test_min_value_enforced(self):
        assert _parse_positive_int("3", min_value=5) is None

    def test_exactly_min_value_ok(self):
        assert _parse_positive_int("5", min_value=5) == 5

    def test_float_string_invalid(self):
        assert _parse_positive_int("3.5") is None

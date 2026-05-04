"""PTK/Rich palette colors aligned with core.cli.python_cli.ui.ui."""
from __future__ import annotations

from core.cli.python_cli.ui.ui import PASTEL_CYAN, SOFT_WHITE

# Panel background (dark); keep contrast with workflow TUI
PALETTE_BG = "#1a1b2e"
PALETTE_DESC = "#565f89"
PALETTE_CMD_BOLD = f"bold {PASTEL_CYAN}"
PALETTE_CMD_TAIL = f"fg:{SOFT_WHITE}"
PALETTE_FRAME_FG = PASTEL_CYAN

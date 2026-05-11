"""Formatting helpers for leader context output."""
from __future__ import annotations

import re
from typing import Optional


def strip_clarification_blocks(response: str) -> str:
    return re.sub(r'\[CLARIFICATION\].*?\[/CLARIFICATION\]', '', response, flags=re.DOTALL).strip()


def trim_to_context_start(response: str) -> str:
    h1 = re.search(r"^# .+", response, re.MULTILINE)
    if h1:
        return response[h1.start():].strip()

    markers = ("## 1. DIRECTORY", "## 1.", "# 1.", "## 1 ", "# 1 ")
    best: Optional[tuple[int, str]] = None
    for marker in markers:
        idx = response.find(marker)
        if idx != -1 and (best is None or idx < best[0]):
            best = (idx, marker)
    if best:
        return response[best[0]:].strip()

    section = re.search(r"^#{1,2}\s*1[\.)]\s*\S", response, re.MULTILINE)
    if section:
        return response[section.start():].strip()
    return response.strip()

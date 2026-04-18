"""Ensure repository root is on sys.path (scripts, tests, non-editable runs)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def ensure_project_root() -> Path:
    r = str(_ROOT)
    if r not in sys.path:
        sys.path.insert(0, r)
    return _ROOT

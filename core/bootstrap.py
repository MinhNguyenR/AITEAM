"""Repo root on sys.path for scripts, tests, and non-editable runs."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def ensure_project_root() -> Path:
    r = str(REPO_ROOT)
    if r not in sys.path:
        sys.path.insert(0, r)
    return REPO_ROOT


__all__ = ["REPO_ROOT", "ensure_project_root"]

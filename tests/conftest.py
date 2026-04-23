from __future__ import annotations

from pathlib import Path

from core.bootstrap import ensure_project_root

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ensure_project_root()

"""Stable paths under the repository root (resources, docs, etc.)."""

from __future__ import annotations

from core.bootstrap import REPO_ROOT

RESOURCES_DIR = REPO_ROOT / "core" / "resources"
FONTS_DIR = RESOURCES_DIR / "fonts"
DOCS_DIR = REPO_ROOT / "docs"
LEGACY_ASSETS_FONTS = REPO_ROOT / "assets" / "fonts"

__all__ = ["REPO_ROOT", "RESOURCES_DIR", "FONTS_DIR", "DOCS_DIR", "LEGACY_ASSETS_FONTS"]

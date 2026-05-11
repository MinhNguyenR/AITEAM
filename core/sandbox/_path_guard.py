"""Shared helper: resolve a relative path safely under a project root."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_under_project_root(root: str | Path, rel: str) -> Path | None:
    """Return resolved absolute path of *rel* only if it stays inside *root*.

    Returns None (security violation) when:
    - *rel* is absolute (any OS)
    - *rel* uses Windows drive letters (C:, D:, ...)
    - *rel* traverses outside *root* via ``..``
    - the resolved path is a symlink that points outside *root*
    """
    rel_str = str(rel or "").strip().replace("\\", "/")
    if not rel_str:
        return None

    # Reject absolute paths
    if rel_str.startswith("/") or rel_str.startswith("\\"):
        return None

    # Reject Windows drive letters (e.g. C:, D:)
    if len(rel_str) >= 2 and rel_str[1] == ":":
        return None

    root_resolved = Path(root).resolve()
    candidate = (root_resolved / rel_str).resolve()

    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None

    # If it's a symlink, verify the link target also stays under root
    if candidate.is_symlink():
        try:
            link_target = Path(os.readlink(str(candidate))).resolve()
            link_target.relative_to(root_resolved)
        except (ValueError, OSError):
            return None

    return candidate


__all__ = ["resolve_under_project_root"]

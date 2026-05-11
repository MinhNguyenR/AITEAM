"""Helpers for per-project virtual environments."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def project_venv_path(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / ".venv"


def project_python(project_root: str | Path) -> Path:
    venv = project_venv_path(project_root)
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def project_bin_dir(project_root: str | Path) -> Path:
    venv = project_venv_path(project_root)
    return venv / ("Scripts" if os.name == "nt" else "bin")


def ensure_project_venv(project_root: str | Path) -> Path:
    root = Path(project_root).resolve()
    venv = project_venv_path(root)
    py = project_python(root)
    if py.exists():
        return venv
    subprocess.run([sys.executable, "-m", "venv", str(venv)], cwd=str(root), check=False, timeout=180)
    return venv


def venv_env_overrides(project_root: str | Path) -> dict[str, str]:
    venv = ensure_project_venv(project_root)
    bin_dir = project_bin_dir(project_root)
    old_path = os.environ.get("PATH", "")
    return {
        "VIRTUAL_ENV": str(venv),
        "PATH": str(bin_dir) + os.pathsep + old_path,
    }


__all__ = ["ensure_project_venv", "project_bin_dir", "project_python", "project_venv_path", "venv_env_overrides"]

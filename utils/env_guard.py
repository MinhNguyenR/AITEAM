"""Best-effort .env exposure checks and secret redaction for logs/UI."""

from __future__ import annotations

import logging
import os
import re
import stat
from pathlib import Path

from utils.file_manager import get_cache_root

logger = logging.getLogger(__name__)


def _dotenv_paths(project_root: Path) -> list[Path]:
    out: list[Path] = []
    for name in (".env", ".env.local"):
        p = project_root / name
        if p.is_file():
            out.append(p)
    home_env = Path.home() / ".ai-team" / ".env"
    if home_env.is_file():
        out.append(home_env)
    return out


def warn_if_env_permissions_unsafe(project_root: str | Path | None = None) -> None:
    root = Path(project_root or os.getcwd()).resolve()
    for p in _dotenv_paths(root):
        try:
            mode = p.stat().st_mode
        except OSError:
            continue
        if os.name != "nt":
            if mode & stat.S_IROTH or mode & stat.S_IWOTH:
                logger.warning("[env_guard] %s is world-readable or world-writable — tighten chmod", p)
                try:
                    os.chmod(p, 0o600)
                    logger.info("[env_guard] tightened %s to 600", p)
                except OSError as chmod_err:
                    logger.warning("[env_guard] could not chmod %s: %s", p, chmod_err)


def redact_for_display(text: str) -> str:
    if not text:
        return text
    s = re.sub(r"\bsk-or-v1-[a-zA-Z0-9_-]{20,}\b", "sk-or-v1-***REDACTED***", text)
    s = re.sub(r"\bsk-[a-zA-Z0-9]{20,}\b", "sk-***REDACTED***", s)
    s = re.sub(r"\bAI_TEAM_VAULT_KEY\s*=\s*\S+", "AI_TEAM_VAULT_KEY=***REDACTED***", s)
    return s


def find_active_env_path(project_root: str | Path | None = None) -> Path | None:
    """Return the .env file that is active for the project, or None."""
    root = Path(project_root or os.getcwd()).resolve()
    candidate = root / ".env"
    if candidate.is_file():
        return candidate
    home_env = Path.home() / ".ai-team" / ".env"
    if home_env.is_file():
        return home_env
    return None


def run_startup_checks(project_root: str | Path | None = None) -> None:
    root = Path(project_root or os.getcwd()).resolve()
    warn_if_env_permissions_unsafe(root)
    # Project-root .env takes priority: remove non-root duplicates
    root_env = root / ".env"
    if root_env.is_file():
        home_env = Path.home() / ".ai-team" / ".env"
        if home_env.is_file():
            try:
                home_env.unlink()
                logger.info("[env_guard] removed %s — project root .env takes priority", home_env)
            except OSError as exc:
                logger.warning("[env_guard] could not remove %s: %s", home_env, exc)
    if os.name != "nt":
        cache_root = get_cache_root()
        try:
            mode = cache_root.stat().st_mode
            if mode & stat.S_IROTH or mode & stat.S_IWOTH:
                logger.warning("[env_guard] %s is world-readable or world-writable — tighten chmod", cache_root)
        except OSError:
            pass


__all__ = ["find_active_env_path", "redact_for_display", "run_startup_checks", "warn_if_env_permissions_unsafe"]

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Any


def normalize_file_path(path: str) -> str:
    raw = str(path or "").strip().replace("\\", "/")
    if not raw:
        return ""
    try:
        return Path(raw).as_posix().lower()
    except Exception:
        return raw.lower()


def normalize_terminal_key(command: str, cwd: str = "") -> str:
    cmd = " ".join(str(command or "").strip().split())
    where = normalize_file_path(cwd or ".")
    return f"{where}::{cmd.lower()}"


@dataclass
class ResourceDecision:
    allowed: bool
    resource_type: str
    key: str
    owner_agent_id: str = ""
    reason: str = ""
    reused_payload: dict[str, Any] | None = None


class ResourceManager:
    """Run-scoped resource coordination for standalone agent runtime."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._file_locks: dict[tuple[str, str], str] = {}
        self._terminal_active: dict[tuple[str, str], str] = {}
        self._terminal_results: dict[tuple[str, str], dict[str, Any]] = {}
        self._workspace_roots: dict[str, Path] = {}

    def set_workspace(self, run_id: str, workspace: str | Path) -> ResourceDecision:
        try:
            root = Path(workspace).expanduser().resolve()
        except OSError as exc:
            return ResourceDecision(False, "workspace", str(workspace), reason=str(exc))
        if not root.exists() or not root.is_dir():
            return ResourceDecision(False, "workspace", str(root), reason="workspace does not exist")
        with self._lock:
            self._workspace_roots[run_id] = root
        return ResourceDecision(True, "workspace", str(root), "runtime")

    def workspace_for(self, run_id: str) -> str:
        with self._lock:
            root = self._workspace_roots.get(run_id)
        return str(root) if root is not None else ""

    def resolve_workspace_path(self, run_id: str, path: str) -> Path:
        raw = Path(str(path or ""))
        with self._lock:
            root = self._workspace_roots.get(run_id)
        if root is None:
            return raw
        full = raw if raw.is_absolute() else root / raw
        return full.resolve()

    def _workspace_decision(self, run_id: str, agent_id: str, path: str) -> ResourceDecision | None:
        with self._lock:
            root = self._workspace_roots.get(run_id)
        if root is None or not path:
            return None
        try:
            full = self.resolve_workspace_path(run_id, path)
            full.relative_to(root)
        except (OSError, ValueError):
            return ResourceDecision(False, "workspace", str(path), agent_id, "path is outside selected workspace")
        return None

    def acquire_file(self, run_id: str, agent_id: str, path: str) -> ResourceDecision:
        outside = self._workspace_decision(run_id, agent_id, path)
        if outside is not None:
            return outside
        key = normalize_file_path(path)
        if not key:
            return ResourceDecision(True, "file", key, agent_id)
        with self._lock:
            owner = self._file_locks.get((run_id, key))
            if owner and owner != agent_id:
                return ResourceDecision(False, "file", key, owner, "file locked by another agent")
            self._file_locks[(run_id, key)] = agent_id
            return ResourceDecision(True, "file", key, agent_id)

    def release_agent(self, run_id: str, agent_id: str) -> None:
        with self._lock:
            for key, owner in list(self._file_locks.items()):
                if key[0] == run_id and owner == agent_id:
                    self._file_locks.pop(key, None)

    def release_run(self, run_id: str) -> None:
        """Drop every resource mapping for a finished/aborted run."""
        with self._lock:
            for key in list(self._file_locks):
                if key[0] == run_id:
                    self._file_locks.pop(key, None)
            for key in list(self._terminal_active):
                if key[0] == run_id:
                    self._terminal_active.pop(key, None)
            for key in list(self._terminal_results):
                if key[0] == run_id:
                    self._terminal_results.pop(key, None)
            self._workspace_roots.pop(run_id, None)

    def request_terminal(self, run_id: str, agent_id: str, command: str, cwd: str = ".") -> ResourceDecision:
        key = normalize_terminal_key(command, cwd)
        if key.endswith("::"):
            return ResourceDecision(True, "terminal", key, agent_id)
        with self._lock:
            completed = self._terminal_results.get((run_id, key))
            if completed is not None:
                return ResourceDecision(
                    False,
                    "terminal",
                    key,
                    reason="terminal result already available",
                    reused_payload=completed,
                )
            owner = self._terminal_active.get((run_id, key))
            if owner and owner != agent_id:
                return ResourceDecision(False, "terminal", key, owner, "terminal command already running")
            self._terminal_active[(run_id, key)] = agent_id
            return ResourceDecision(True, "terminal", key, agent_id)

    def complete_terminal(self, run_id: str, command: str, cwd: str = ".", payload: dict[str, Any] | None = None) -> None:
        key = normalize_terminal_key(command, cwd)
        with self._lock:
            self._terminal_active.pop((run_id, key), None)
            self._terminal_results[(run_id, key)] = dict(payload or {})

    def snapshot(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            files = [
                {"path": key, "owner_agent_id": owner}
                for (rid, key), owner in self._file_locks.items()
                if rid == run_id
            ]
            terminal_active = [
                {"key": key, "owner_agent_id": owner}
                for (rid, key), owner in self._terminal_active.items()
                if rid == run_id
            ]
            terminal_completed = [
                {"key": key, "result": result}
                for (rid, key), result in self._terminal_results.items()
                if rid == run_id
            ]
            workspace = str(self._workspace_roots.get(run_id) or "")
        return {
            "workspace": workspace,
            "file_locks": files,
            "terminal_active": terminal_active,
            "terminal_completed": terminal_completed,
        }

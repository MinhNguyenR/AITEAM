from __future__ import annotations

from pathlib import Path
from typing import Any

from core.runtime import session as ws


_ROLE_TO_SUBSTATE = {
    "ambassador": ws.set_ambassador_substate,
    "leader_generate": ws.set_leader_substate,
    "tool_curator": ws.set_curator_substate,
    "secretary": ws.set_secretary_substate,
    "secretary_setup": ws.set_secretary_substate,
}


class RuntimeMonitorBridge:
    """Translate ai-team runtime events into the existing workflow monitor state."""

    def __init__(self, *, run_id: str, project_root: str) -> None:
        self.run_id = str(run_id)
        self.project_root = str(project_root)

    def started(
        self,
        node: str,
        detail: str = "",
        *,
        role: str = "",
        substate: str = "",
        artifacts: list[dict[str, Any] | str] | None = None,
        event_kind: str = "",
        work_item_id: str = "",
    ) -> None:
        self._publish(node, "running", detail, role=role, substate=substate or "reading", artifacts=artifacts, event_kind=event_kind, work_item_id=work_item_id, active=True)

    def progress(
        self,
        node: str,
        substate: str,
        detail: str = "",
        *,
        role: str = "",
        artifacts: list[dict[str, Any] | str] | None = None,
        event_kind: str = "",
        work_item_id: str = "",
    ) -> None:
        self._publish(node, "running", detail, role=role, substate=substate, artifacts=artifacts, event_kind=event_kind, work_item_id=work_item_id, active=True)

    def done(
        self,
        node: str,
        detail: str = "",
        *,
        role: str = "",
        artifacts: list[dict[str, Any] | str] | None = None,
        event_kind: str = "",
        work_item_id: str = "",
    ) -> None:
        self._publish(node, "done", detail, role=role, artifacts=artifacts, event_kind=event_kind, work_item_id=work_item_id, active=False)

    def error(
        self,
        node: str,
        detail: str = "",
        *,
        role: str = "",
        artifacts: list[dict[str, Any] | str] | None = None,
        event_kind: str = "error",
        work_item_id: str = "",
    ) -> None:
        self._publish(node, "error", detail, role=role, artifacts=artifacts, event_kind=event_kind, work_item_id=work_item_id, active=False)

    def artifact(self, path: str | Path, *, node: str, kind: str, producer: str) -> dict[str, Any]:
        return artifact_ref(path, kind=kind, producer=producer, run_id=self.run_id, project_root=self.project_root)

    def ingest_artifact(self, artifact: dict[str, Any], *, kind: str, producer: str, embed: bool | None = None) -> None:
        path = Path(str(artifact.get("path") or ""))
        if not path.exists() or not path.is_file():
            return
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        try:
            from core.storage.graphrag_store import upsert_context_snapshot

            upsert_context_snapshot(
                self.run_id,
                text,
                kind=kind,
                path=str(path),
                metadata={"producer": producer, "artifact_hash": artifact.get("hash"), "workspace": self.project_root},
                embed=embed,
            )
        except Exception:
            pass
        try:
            from core.storage.memory_coordinator import MemoryCoordinator

            MemoryCoordinator().on_workflow_step(
                self.run_id,
                {
                    "node": producer,
                    "kind": kind,
                    "artifact": {
                        "path": artifact.get("path"),
                        "hash": artifact.get("hash"),
                        "size": artifact.get("size"),
                    },
                },
            )
        except Exception:
            pass

    def _publish(
        self,
        node: str,
        status: str,
        detail: str = "",
        *,
        role: str = "",
        substate: str = "",
        artifacts: list[dict[str, Any] | str] | None = None,
        event_kind: str = "",
        work_item_id: str = "",
        active: bool | None = None,
    ) -> None:
        node = str(node)
        _set_role_substate(node, substate, detail)
        ws.update_workflow_node_state(
            node,
            status=status,
            detail=detail,
            role=role,
            substate=substate,
            artifacts=artifacts,
            event_kind=event_kind,
            run_id=self.run_id,
            work_item_id=work_item_id,
            active=active,
        )


def artifact_ref(path: str | Path, *, kind: str, producer: str, run_id: str, project_root: str = "") -> dict[str, Any]:
    p = Path(path)
    try:
        resolved = p.resolve()
    except OSError:
        resolved = p
    size = 0
    digest = ""
    try:
        if resolved.is_file():
            size = resolved.stat().st_size
            from aiteamruntime.resources.workspace import ResourceManager

            digest = ResourceManager.file_hash(resolved)
    except OSError:
        pass
    rel = str(resolved)
    if project_root:
        try:
            rel = resolved.relative_to(Path(project_root).resolve()).as_posix()
        except ValueError:
            rel = str(resolved)
    return {
        "path": str(resolved),
        "display_path": rel,
        "kind": kind,
        "producer": producer,
        "run_id": run_id,
        "hash": digest,
        "size": size,
    }


def _set_role_substate(node: str, substate: str, detail: str) -> None:
    if not substate:
        return
    key = node.lower()
    if key in {"worker", "restore_worker"} or key.startswith("worker_") or key.startswith("worker") or key == "designer":
        ws.set_worker_substate(node.upper() if node.islower() else node, substate, detail)
        return
    setter = _ROLE_TO_SUBSTATE.get(key)
    if setter:
        setter(substate, detail)


__all__ = ["RuntimeMonitorBridge", "artifact_ref"]

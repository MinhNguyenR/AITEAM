from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any

from .contracts import dual_payload
from .events import AgentEvent


@dataclass
class AgentContext:
    runtime: "AgentRuntime"
    run_id: str
    agent_id: str
    trigger_event: AgentEvent | None = None

    def emit(
        self,
        kind: str,
        payload: dict[str, Any] | None = None,
        *,
        status: str = "ok",
        stage: str = "",
        work_item_id: str = "",
        resource_key: str = "",
        duration_ms: int = 0,
        role_state: str = "",
        assignment: dict[str, Any] | None = None,
        retry_of: str = "",
    ) -> AgentEvent:
        return self.runtime.emit(
            self.run_id,
            self.agent_id,
            kind,
            payload or {},
            status=status,
            parent_event=self.trigger_event,
            stage=stage,
            work_item_id=work_item_id,
            resource_key=resource_key,
            duration_ms=duration_ms,
            role_state=role_state,
            assignment=assignment,
            retry_of=retry_of,
        )

    def is_aborted(self) -> bool:
        return self.runtime.is_aborted(self.run_id)

    def request_terminal(self, command: str, *, cwd: str = ".", payload: dict[str, Any] | None = None) -> AgentEvent:
        body = {"command": command, "cwd": cwd}
        body.update(dict(payload or {}))
        return self.emit("terminal_requested", body)

    def emit_dual(
        self,
        kind: str,
        *,
        ui_message: str = "",
        system_command: str = "",
        data: dict[str, Any] | None = None,
        refs: list[dict[str, Any]] | None = None,
        schema_version: str = "",
        **kwargs: Any,
    ) -> AgentEvent:
        contract = self.runtime._contract_for(self.agent_id)
        version = schema_version or (contract.version if contract is not None else "v1")
        return self.emit(
            kind,
            dual_payload(
                ui_message=ui_message,
                system_command=system_command,
                data=data,
                refs=refs,
                schema_version=version,
            ),
            **kwargs,
        )

    def ref_file(
        self,
        path: str,
        *,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        return self.runtime.references.create_file_ref(self.run_id, path, content=content, metadata=metadata)

    def hydrate(self, ref_id: str) -> dict[str, Any]:
        return self.runtime.references.hydrate(
            self.run_id,
            ref_id,
            workspace=self.runtime.resources.workspace_for(self.run_id),
        )


@dataclass
class RunHandle:
    run_id: str
    runtime: "AgentRuntime"
    started_at: float = field(default_factory=time.time)

    def wait(self, timeout: float | None = None) -> None:
        self.runtime.wait(run_id=self.run_id, timeout=timeout)

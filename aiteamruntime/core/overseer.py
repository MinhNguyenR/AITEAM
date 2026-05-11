from __future__ import annotations

from dataclasses import dataclass, field

from .events import AgentEvent


@dataclass
class OverseerPolicy:
    max_failures: int = 3
    escalate_after: int = 2


@dataclass
class OverseerState:
    policy: OverseerPolicy = field(default_factory=OverseerPolicy)
    failures: dict[str, int] = field(default_factory=dict)

    def record_failure(self, event: AgentEvent) -> tuple[str, int]:
        local_key = event.work_item_id or str((event.payload or {}).get("work_item_id") or "") or event.event_id
        key = f"{event.run_id}:{local_key}"
        count = self.failures.get(key, 0) + 1
        self.failures[key] = count
        if count >= self.policy.max_failures:
            return "abort_task", count
        if count >= self.policy.escalate_after:
            return "escalate", count
        return "reassign", count


__all__ = ["OverseerPolicy", "OverseerState"]

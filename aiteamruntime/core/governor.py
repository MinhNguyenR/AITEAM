from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from .events import AgentEvent


@dataclass
class GovernorLimits:
    max_events: int = 1000
    max_runtime_seconds: float = 120.0
    max_model_tokens: int = 100_000
    max_terminal_seconds: float = 180.0
    max_schema_repairs: int = 3


@dataclass
class GovernorState:
    limits: GovernorLimits
    started_at: float
    events: int = 0
    model_tokens: int = 0
    terminal_ms: int = 0
    frozen: bool = False
    reason: str = ""

    def check_pre_publish(self, *, event_count: int, now: float) -> str:
        if self.frozen:
            return self.reason or "run frozen"
        if self.limits.max_events and event_count > self.limits.max_events:
            return f"max events exceeded: {event_count}/{self.limits.max_events}"
        if self.limits.max_runtime_seconds and now - self.started_at > self.limits.max_runtime_seconds:
            return f"max runtime exceeded: {now - self.started_at:.2f}s/{self.limits.max_runtime_seconds:.2f}s"
        return ""

    def observe_o1(self, event: AgentEvent) -> str:
        self.events = max(self.events, int(event.sequence or 0))
        payload = event.payload or {}
        if event.kind in {"token_usage", "model_response"}:
            tokens = int(payload.get("total_tokens") or payload.get("tokens") or 0)
            self.model_tokens += max(0, tokens)
        if event.kind in {"terminal_result", "setup_done"}:
            self.terminal_ms += max(0, int(event.duration_ms or payload.get("duration_ms") or 0))
        if self.limits.max_model_tokens and self.model_tokens > self.limits.max_model_tokens:
            return f"max model tokens exceeded: {self.model_tokens}/{self.limits.max_model_tokens}"
        if self.limits.max_terminal_seconds and self.terminal_ms > int(self.limits.max_terminal_seconds * 1000):
            return f"max terminal time exceeded: {self.terminal_ms}ms"
        return ""

    def freeze(self, reason: str) -> None:
        self.frozen = True
        self.reason = reason

    def snapshot(self) -> dict[str, Any]:
        return {
            "events": self.events,
            "model_tokens": self.model_tokens,
            "terminal_ms": self.terminal_ms,
            "frozen": self.frozen,
            "reason": self.reason,
            "limits": self.limits.__dict__.copy(),
        }


__all__ = ["GovernorLimits", "GovernorState"]

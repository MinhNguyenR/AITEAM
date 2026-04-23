from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeConfig:
    """Extensible runtime layer for orchestration hooks, events, and persistence."""

    orchestration_tags: dict[str, str] = field(default_factory=dict)
    event_sink: Any | None = None
    persistence_uri: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

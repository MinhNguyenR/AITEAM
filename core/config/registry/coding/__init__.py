from __future__ import annotations

from typing import Any, Dict

from .chat import REGISTRY as _CHAT
from .devops import REGISTRY as _DEVOPS
from .fixers import REGISTRY as _FIXERS
from .leaders import REGISTRY as _LEADERS
from .researchers import REGISTRY as _RESEARCHERS
from .reviewers import REGISTRY as _REVIEWERS
from .support import REGISTRY as _SUPPORT
from .system import REGISTRY as _SYSTEM
from .testers import REGISTRY as _TESTERS
from .workers import REGISTRY as _WORKERS

REGISTRY: Dict[str, Dict[str, Any]] = {
    **_SYSTEM,
    **_CHAT,
    **_LEADERS,
    **_RESEARCHERS,
    **_SUPPORT,
    **_WORKERS,
    **_TESTERS,
    **_REVIEWERS,
    **_FIXERS,
    **_DEVOPS,
}

__all__ = ["REGISTRY"]

"""Compatibility facade for the runtime engine.

New code should import from :mod:`aiteamruntime.core`.
"""

from .core.context import AgentContext, RunHandle
from .core.runtime import AgentRuntime
from .core.state import AgentSpec, WorkItem

__all__ = ["AgentContext", "AgentRuntime", "AgentSpec", "RunHandle", "WorkItem"]

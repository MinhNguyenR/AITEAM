"""AgentProtocol — structural interface for all agents in the AI Team system.

This module defines the ``AgentProtocol`` runtime-checkable Protocol so that
``core`` modules can type-check against agents without importing concrete
classes from ``agents.*``, keeping the dependency arrow one-way
(``agents → core``, never ``core → agents`` at module load time).

Usage in ``core``::

    from core.domain.agent_protocol import AgentProtocol

    def run_agent(agent: AgentProtocol, prompt: str) -> str:
        return agent.generate_context(prompt)
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class AgentProtocol(Protocol):
    """Minimal interface every agent must satisfy."""

    agent_name: str
    model_name: str

    def generate_context(
        self,
        state_path: str,
        *,
        stream_to_monitor: bool = False,
    ) -> str:
        """Generate context.md from state_path; return the output file path."""
        ...

    def read_project_file(self, file_name: str) -> Optional[str]:
        """Read a project file safely; return None if unavailable."""
        ...


@runtime_checkable
class ClassifierProtocol(Protocol):
    """Interface for classification agents (e.g. Ambassador)."""

    def parse(self, user_input: str) -> object:
        """Parse user input and return a DeltaBrief-like object."""
        ...


__all__ = ["AgentProtocol", "ClassifierProtocol"]

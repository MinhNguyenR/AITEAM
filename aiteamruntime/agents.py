"""Production trackaiteam workflow exports for the local aiteamruntime viewer.

The core package stays generic; this module exposes the bundled real-model
trackaiteam integration used by the web viewer and explicit demos.
"""

from aiteamruntime.integrations.trackaiteam.workflow import (
    DEFAULT_AGENT_LANES,
    WORKER_REGISTRY,
    ambassador_agent,
    build_trackaiteam_pipeline,
    explainer_agent,
    finalizer_agent,
    leader_agent,
    model_name,
    model_readiness,
    register_default_agents,
    registry_model_summary,
    secretary_agent,
    tool_curator_agent,
    worker_agent,
)

__all__ = [
    "DEFAULT_AGENT_LANES",
    "WORKER_REGISTRY",
    "ambassador_agent",
    "build_trackaiteam_pipeline",
    "explainer_agent",
    "finalizer_agent",
    "leader_agent",
    "model_name",
    "model_readiness",
    "register_default_agents",
    "registry_model_summary",
    "secretary_agent",
    "tool_curator_agent",
    "worker_agent",
]

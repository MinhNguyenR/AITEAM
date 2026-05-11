"""Pure library surface for the standalone AI Team runtime.

The package exports runtime primitives and pipeline-building helpers only.
Concrete demo/test workflows live under :mod:`aiteamruntime.test`.
"""

from .core import (
    AgentContext,
    AgentContract,
    AgentEvent,
    AgentRuntime,
    AgentSpec,
    EVENT_KINDS,
    EventBus,
    GovernorLimits,
    GovernorState,
    ReferenceStore,
    OverseerPolicy,
    OverseerState,
    RunHandle,
    SchemaValidator,
    ValidationResult,
    WorkItem,
    dual_payload,
)
from .resources import ResourceManager
from .tracing import SQLiteTraceStore, TraceStore

from .pipeline import (
    NodeBuilder,
    NodeDefinition,
    PipelineBuilder,
    PipelineDefinition,
    RoleDefinition,
    after_done,
    after_node,
    assigned_to,
    node_agent_id,
    node_done_stage,
    node_role_stage,
    node_start_stage,
    on_event,
    on_runtime_start,
)

__all__ = [
    "AgentContext",
    "AgentContract",
    "AgentEvent",
    "AgentRuntime",
    "AgentSpec",
    "EVENT_KINDS",
    "EventBus",
    "GovernorLimits",
    "GovernorState",
    "NodeBuilder",
    "NodeDefinition",
    "PipelineBuilder",
    "PipelineDefinition",
    "ResourceManager",
    "RoleDefinition",
    "RunHandle",
    "ReferenceStore",
    "OverseerPolicy",
    "OverseerState",
    "SchemaValidator",
    "SQLiteTraceStore",
    "TraceStore",
    "ValidationResult",
    "WorkItem",
    "after_done",
    "after_node",
    "assigned_to",
    "node_agent_id",
    "node_done_stage",
    "node_role_stage",
    "node_start_stage",
    "on_event",
    "on_runtime_start",
    "dual_payload",
]

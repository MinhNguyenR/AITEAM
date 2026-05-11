from __future__ import annotations

from aiteamruntime.core.runtime import AgentRuntime
from aiteamruntime.pipeline import (
    PipelineBuilder,
    PipelineDefinition,
    _tag_kinds,
    after_done,
    any_of,
    assigned_to,
    on_event,
    on_runtime_start,
)

from .config import DEFAULT_AGENT_LANES, WORKER_REGISTRY
from .model import model_name, model_readiness, registry_model_summary
from .roles.finalization import explainer_agent, finalizer_agent
from .roles.intake import ambassador_agent, leader_agent
from .roles.secretary import secretary_agent
from .roles.tooling import tool_curator_agent
from .roles.worker import worker_agent


def build_trackaiteam_pipeline(*, include_explainer: bool = True) -> PipelineDefinition:
    builder = PipelineBuilder()
    builder.role("Ambassador", ambassador_agent, on_runtime_start("classify"), lane="Ambassador")
    builder.role(
        "Leader",
        leader_agent,
        any_of(after_done("Ambassador", "classify"), on_event("answered")),
        lane="Leader",
    )
    builder.role(
        "Tool Curator",
        tool_curator_agent,
        any_of(after_done("Leader", "plan"), on_event("setup_done")),
        lane="Tool Curator",
    )
    for worker_id in WORKER_REGISTRY:
        builder.role(worker_id, worker_agent, assigned_to(worker_id), lane=worker_id)
    builder.role(
        "Secretary",
        secretary_agent,
        _tag_kinds(
            lambda event: event.kind in {"setup_requested", "terminal_requested", "secretary_command"},
            {"setup_requested", "terminal_requested", "secretary_command"},
        ),
        lane="Secretary",
    )
    builder.role("Runtime Finalizer", finalizer_agent, on_event("validated"), lane="runtime")
    if include_explainer:
        builder.role(
            "Explainer",
            explainer_agent,
            _tag_kinds(
                lambda event: event.kind == "question" and str(event.payload.get("command") or "") == "explainer",
                {"question"},
            ),
            lane="Explainer",
        )
    return builder.build()


def register_default_agents(runtime: AgentRuntime, *, include_explainer: bool = True) -> AgentRuntime:
    return build_trackaiteam_pipeline(include_explainer=include_explainer).register(runtime)

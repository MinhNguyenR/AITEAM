from __future__ import annotations

import json
from typing import Any

from aiteamruntime.core.events import AgentEvent
from aiteamruntime.core.runtime import AgentContext

from ..model import chat_completion, model_meta, real_model_enabled
from ..utils import model_error


def finalizer_agent(ctx: AgentContext, event: AgentEvent) -> None:
    events = ctx.runtime.store.read_events(ctx.run_id)
    if any(item.get("agent_id") == "Runtime Finalizer" and item.get("kind") == "finalized" for item in events):
        return
    assigned_ids = {
        str(item.get("work_item_id") or ((item.get("assignment") or {}).get("id")) or "")
        for item in events
        if item.get("kind") in {"assigned", "reassigned"}
    }
    done_ids = {
        str(item.get("work_item_id") or "")
        for item in events
        if item.get("kind") == "done" and str(item.get("work_item_id") or "")
    }
    assigned_ids.discard("")
    if assigned_ids and not assigned_ids.issubset(done_ids):
        ctx.emit(
            "progress",
            {"assigned": sorted(assigned_ids), "done": sorted(done_ids), "trigger": event.kind},
            status="waiting",
            stage="finalize",
            role_state="waiting",
        )
        return
    if not real_model_enabled():
        ctx.emit(
            "error",
            {"stage": "finalize", "type": "ModelNotReady", "message": "OPENROUTER_API_KEY is required for Runtime Finalizer"},
            status="error",
            stage="finalize",
            role_state="error",
        )
        ctx.runtime.request_abort(ctx.run_id, "finalizer model provider is not configured")
        return
    role_key = "COMMANDER"
    try:
        result = chat_completion(
            role_key=role_key,
            system=(
                "You are Runtime Finalizer. Summarize the completed validation event in 3 concise bullets. "
                "Mention that this was a real OpenRouter-backed role run."
            ),
            user=json.dumps(event.to_dict(), ensure_ascii=False, indent=2),
            max_tokens=450,
        )
    except Exception as exc:
        model_error(ctx, stage="finalize", exc=exc)
        ctx.runtime.request_abort(ctx.run_id, "finalizer model failed")
        return
    payload: dict[str, Any] = {"stage": "finalize", "result": result, **model_meta(role_key)}
    ctx.emit("finalized", payload, stage="finalize", role_state="done")
    ctx.emit("done", {"stage": "finalize"}, stage="finalize", role_state="done")


def explainer_agent(ctx: AgentContext, event: AgentEvent) -> None:
    ctx.emit("reading", {"target": event.payload.get("target") or "@codebase"}, stage="explain")
    if not real_model_enabled():
        ctx.emit(
            "error",
            {"stage": "explain", "type": "ModelNotReady", "message": "OPENROUTER_API_KEY is required for Explainer"},
            status="error",
            stage="explain",
            role_state="error",
        )
        return
    role_key = "EXPLAINER"
    try:
        content = chat_completion(
            role_key=role_key,
            system="You are Explainer. Explain the selected runtime event and next action in plain language.",
            user=json.dumps(event.to_dict(), ensure_ascii=False, indent=2),
            max_tokens=450,
        )
        payload = {"content": content, **model_meta(role_key)}
    except Exception as exc:
        model_error(ctx, stage="explain", exc=exc)
        return
    ctx.emit("reasoning", payload, stage="explain")
    ctx.emit("done", {"stage": "explainer"}, stage="explain")

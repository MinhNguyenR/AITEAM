from __future__ import annotations

import json
import time

from aiteamruntime.core.events import AgentEvent
from aiteamruntime.core.runtime import AgentContext

from ..config import WORKER_REGISTRY
from ..dag import dag_from_plan, validate_dag
from ..model import (
    chat_json,
    leader_role_key,
    model_max_retries,
    model_meta,
    model_name,
    model_timeout,
    normalize_tier,
    real_model_enabled,
)
from ..planning import normalize_model_plan
from ..utils import model_error, prompt, write_run_artifact


def ambassador_agent(ctx: AgentContext, event: AgentEvent) -> None:
    task_prompt = prompt(event)
    words = [word for word in task_prompt.strip().split() if word]
    if not real_model_enabled():
        ctx.emit(
            "error",
            {"stage": "classify", "type": "ModelNotReady", "message": "OPENROUTER_API_KEY is required for trackaiteam production workflow"},
            status="error",
            stage="classify",
            role_state="error",
        )
        ctx.runtime.request_abort(ctx.run_id, "model provider is not configured")
        return
    if len(words) < 2:
        selected_leader_role_key = "LEADER_MEDIUM"
        brief = {
            "task": task_prompt,
            "summary": task_prompt[:180],
            "tier": "MEDIUM",
            "selected_leader": "Leader",
            "selected_leader_role_key": selected_leader_role_key,
            "selected_leader_model": model_name(selected_leader_role_key),
        }
        ctx.emit(
            "question",
            {
                "question": "Please clarify the target behavior, expected files, and success criteria.",
                **brief,
                "reason": "task is too short",
            },
            status="waiting",
            stage="classify",
            role_state="waiting",
        )
        ctx.emit("done", {**brief, "stage": "classify_waiting"}, stage="classify_waiting", role_state="waiting")
        return
    role_key = "AMBASSADOR"
    meta = model_meta(role_key)
    ctx.emit("reading", {"target": "task prompt", **meta}, stage="classify", role_state="running")
    started = time.monotonic()
    ctx.emit(
        "model_requested",
        {"operation": "classify_task", "timeout_s": model_timeout(), "max_retries": model_max_retries(), **meta},
        stage="classify",
        role_state="running",
    )
    try:
        model_brief = chat_json(
            role_key=role_key,
            system=(
                "You are Ambassador in a production-style event-driven AI team runtime. "
                "Classify the user's task and decide whether the Leader needs clarification. "
                "Return JSON only with keys: task, summary, tier, selected_leader, "
                "requires_clarification, question. selected_leader must be Leader. "
                "tier must be LOW, MEDIUM, HARD, or UNKNOWN."
            ),
            user=f"Task:\n{task_prompt}",
            max_tokens=500,
        )
    except Exception as exc:
        model_error(ctx, stage="classify", exc=exc)
        ctx.runtime.request_abort(ctx.run_id, "ambassador model failed")
        return
    ctx.emit(
        "model_response",
        {"operation": "classify_task", "keys": sorted(str(key) for key in model_brief), **meta},
        stage="classify",
        duration_ms=int((time.monotonic() - started) * 1000),
        role_state="done",
    )
    raw_tier = str(model_brief.get("tier") or "UNKNOWN").upper()
    tier = normalize_tier(raw_tier)
    selected_leader_role_key = leader_role_key(tier)
    brief = {
        "task": str(model_brief.get("task") or task_prompt),
        "summary": str(model_brief.get("summary") or task_prompt[:180]),
        "tier": tier,
        "raw_tier": raw_tier,
        "selected_leader": "Leader",
        "selected_leader_role_key": selected_leader_role_key,
        "selected_leader_model": model_name(selected_leader_role_key),
        "requires_clarification": bool(model_brief.get("requires_clarification")),
        "question": str(model_brief.get("question") or "").strip(),
        **meta,
    }
    if brief["requires_clarification"] and brief["question"]:
        ctx.emit("question", brief, status="waiting", stage="classify", role_state="waiting")
        ctx.emit("done", {**brief, "stage": "classify_waiting"}, stage="classify_waiting", role_state="waiting")
        return
    ctx.emit(
        "routing",
        {
            "from": "Ambassador",
            "to": brief["selected_leader"],
            "leader_role_key": brief["selected_leader_role_key"],
            "leader_model": brief["selected_leader_model"],
            "tier": brief["tier"],
            "reason": brief["summary"],
        },
        stage="classify",
        role_state="done",
    )
    ctx.emit("classifying", brief, stage="classify", role_state="running")
    ctx.emit("done", {**brief, "stage": "classify"}, stage="classify", role_state="done")


def leader_agent(ctx: AgentContext, event: AgentEvent) -> None:
    trigger_payload = dict(event.payload or {})
    embedded_brief = trigger_payload.get("brief") if isinstance(trigger_payload.get("brief"), dict) else {}
    brief = dict(embedded_brief or trigger_payload)
    tier = normalize_tier(str(brief.get("tier") or trigger_payload.get("tier") or "MEDIUM"))
    role_key = leader_role_key(tier)
    source_agent_id = str(trigger_payload.get("question_agent_id") or event.agent_id)
    base_task = str(brief.get("task") or trigger_payload.get("task") or trigger_payload.get("summary") or "")
    task = base_task
    if event.kind == "answered":
        answer = str(trigger_payload.get("answer") or "").strip()
        question = str(trigger_payload.get("question") or "").strip()
        task = f"Original task:\n{base_task}\n\nClarification question:\n{question}\n\nClarification answer:\n{answer}".strip()
        brief = {
            **brief,
            "task": base_task,
            "summary": str(brief.get("summary") or base_task[:180]),
            "clarification_question": question,
            "clarification_answer": answer,
            "answered_event_id": event.event_id,
            "question_event_id": str(trigger_payload.get("question_event_id") or ""),
        }
    if "clarify" in task.lower() and event.kind != "answered":
        ctx.emit(
            "question",
            {
                "question": "Leader needs an implementation target and validation command before planning.",
                "task": task,
                "reason": "leader clarification requested by task text",
            },
            status="waiting",
            stage="plan",
            role_state="waiting",
        )
        ctx.emit("done", {"stage": "plan_waiting", "task": task}, stage="plan_waiting", role_state="waiting")
        return
    leader_meta = model_meta(role_key)
    ctx.emit(
        "reading",
        {
            "file": "task brief",
            "purpose": "create gated runtime plan",
            "task": base_task,
            "summary": str(brief.get("summary") or base_task[:180]),
            "brief": brief,
            "trigger_kind": event.kind,
            "source_agent_id": source_agent_id,
            "source_event_id": event.event_id,
            "tier": tier,
            **leader_meta,
        },
        stage="plan",
        role_state="running",
    )
    started = time.monotonic()
    ctx.emit(
        "model_requested",
        {
            "operation": "generate_plan",
            "tier": tier,
            "selected_by": source_agent_id,
            "source_event_id": event.event_id,
            "task_summary": str(brief.get("summary") or base_task[:180]),
            "timeout_s": model_timeout(),
            "max_retries": model_max_retries(),
            **leader_meta,
        },
        stage="plan",
        role_state="running",
    )
    try:
        model_plan = chat_json(
            role_key=role_key,
            system=(
                "You are Leader in an event-driven multi-agent runtime. "
                "Reason about the task and return JSON only with keys: reasoning, "
                "work_items, validation_commands, dependencies. "
                "work_items must be an array of objects with title, files, depends_on, timeout. "
                "Create five useful work_items so Worker A through Worker E can all prove they ran. "
                "Do not emit terminal setup commands; Tool Curator prepares Secretary-only project setup. "
                "Use only relative files under .aiteamruntime/<task-slug>/."
            ),
            user=(
                f"Task brief:\n{task}\n\n"
                f"Structured brief:\n{json.dumps(brief, ensure_ascii=False, indent=2)}\n\n"
                f"Available worker registry:\n{json.dumps(WORKER_REGISTRY, ensure_ascii=False, indent=2)}"
            ),
            max_tokens=1200,
        )
    except Exception as exc:
        model_error(ctx, stage="plan", exc=exc)
        ctx.runtime.request_abort(ctx.run_id, "leader model failed")
        return
    ctx.emit(
        "model_response",
        {"operation": "generate_plan", "keys": sorted(str(key) for key in model_plan), **leader_meta},
        stage="plan",
        duration_ms=int((time.monotonic() - started) * 1000),
        role_state="done",
    )
    plan = normalize_model_plan(task, model_plan, role_key=role_key)
    dag = dag_from_plan(plan)
    dropped_deps = [
        {"id": str(item.get("id") or ""), "dropped_depends_on": list(item.get("dropped_depends_on") or [])}
        for item in dag.get("work_items") or []
        if isinstance(item, dict) and item.get("dropped_depends_on")
    ]
    if dropped_deps:
        ctx.emit(
            "progress",
            {"state": "normalized_non_id_dependencies", "items": dropped_deps},
            status="ok",
            stage="plan",
            role_state="running",
        )
    dag_errors = validate_dag(dag)
    if dag_errors:
        ctx.emit("blocked", {"reason": "leader produced invalid dag.json", "errors": dag_errors}, status="blocked", stage="plan", role_state="blocked")
        ctx.runtime.request_abort(ctx.run_id, "leader dag invalid")
        return
    plan["dag"] = dag
    plan["work_items"] = dag["work_items"]
    plan["files"] = sorted({path for item in dag["work_items"] for path in item.get("allowed_paths") or []})
    try:
        dag_path, dag_full_path, dag_ref = write_run_artifact(ctx, "dag.json", json.dumps(dag, ensure_ascii=False, indent=2), project_dir=str(dag.get("project_root") or ""))
        plan["dag_path"] = dag_path
        plan["dag_ref"] = dag_ref
        ctx.emit("artifact_written", {"path": dag_path, "absolute_path": str(dag_full_path), "ref_id": dag_ref, "storage": "runtime_cache"}, stage="plan")
        ctx.emit("dag_ready", {"dag": dag, "dag_path": dag_path, "dag_ref": dag_ref}, stage="plan", role_state="done")
    except Exception as exc:
        ctx.emit("error", {"type": type(exc).__name__, "message": str(exc), "path": "dag.json"}, status="error", stage="plan", role_state="error")
        ctx.runtime.request_abort(ctx.run_id, "leader dag write failed")
        return
    ctx.emit(
        "reasoning",
        {"content": str(model_plan.get("reasoning") or "Leader produced a real model plan."), **leader_meta},
        stage="plan",
    )
    ctx.emit("writing", {"file": "runtime plan", "plan": plan, **leader_meta}, stage="plan")
    ctx.emit("done", {"stage": "plan", "plan": plan, "task": task, **leader_meta}, stage="plan", role_state="done")

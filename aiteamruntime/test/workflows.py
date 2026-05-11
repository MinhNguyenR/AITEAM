from __future__ import annotations

import json
import importlib.util
import os
import re
import time
import sys
from concurrent.futures import TimeoutError as FutureTimeoutError
from functools import lru_cache
from pathlib import Path
from typing import Any

from aiteamruntime.events import AgentEvent
from aiteamruntime.runtime import AgentContext, AgentRuntime, WorkItem

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

DEFAULT_AGENT_LANES = (
    "Ambassador",
    "Leader",
    "Tool Curator",
    "Secretary",
    "Worker A",
    "Worker B",
    "Worker C",
    "Worker D",
    "Worker E",
    "Explainer",
)

WORKER_REGISTRY = {
    "Worker A": {"role": "implementation", "reason": "general code changes and narrow feature work"},
    "Worker B": {"role": "tests", "reason": "focused tests, regression checks, and fixtures"},
    "Worker C": {"role": "frontend", "reason": "viewer, assets, and user workflow polish"},
    "Worker D": {"role": "runtime", "reason": "orchestration, scheduling, and resource coordination"},
    "Worker E": {"role": "docs", "reason": "summaries, handoff notes, and final packaging"},
}

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"
_MODEL_UNAVAILABLE_UNTIL = 0.0
ROLE_REGISTRY_KEYS = {
    "Ambassador": "AMBASSADOR",
    "Tool Curator": "TOOL_CURATOR",
    "Runtime Finalizer": "COMMANDER",
    "Explainer": "EXPLAINER",
    "Worker A": "WORKER_A",
    "Worker B": "WORKER_B",
    "Worker C": "WORKER_C",
    "Worker D": "WORKER_D",
    "Worker E": "WORKER_E",
}


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _prompt(event: AgentEvent) -> str:
    return str(event.payload.get("prompt") or event.payload.get("task") or "")


def _openrouter_key() -> str:
    return str(os.environ.get("OPENROUTER_API_KEY") or os.environ.get("AITEAMRUNTIME_REAL_MODEL_API_KEY") or "").strip()


def _real_model_enabled() -> bool:
    if time.monotonic() < _MODEL_UNAVAILABLE_UNTIL:
        return False
    disabled = str(os.environ.get("AITEAMRUNTIME_DISABLE_REAL_MODEL") or "").strip().lower()
    forced = str(os.environ.get("AITEAMRUNTIME_REAL_MODEL") or "").strip().lower() in {"1", "true", "yes", "on"}
    if os.environ.get("PYTEST_CURRENT_TEST") and not forced:
        return False
    return bool(_openrouter_key()) and disabled not in {"1", "true", "yes", "on"}


def _mark_model_unavailable(seconds: float = 30.0) -> None:
    global _MODEL_UNAVAILABLE_UNTIL
    _MODEL_UNAVAILABLE_UNTIL = max(_MODEL_UNAVAILABLE_UNTIL, time.monotonic() + max(0.0, seconds))


@lru_cache(maxsize=1)
def _registry() -> dict[str, dict[str, Any]]:
    root = Path(__file__).resolve().parents[2]
    registry_dir = root / "core" / "config" / "registry" / "coding"
    files = ("system.py", "chat.py", "leaders.py", "researchers.py", "support.py", "workers.py", "testers.py", "reviewers.py", "fixers.py", "devops.py")
    merged: dict[str, dict[str, Any]] = {}
    for name in files:
        path = registry_dir / name
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"_aiteamruntime_registry_{path.stem}", path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            data = getattr(module, "REGISTRY", {})
        except Exception:
            continue
        if isinstance(data, dict):
            merged.update({str(key).upper(): dict(value) for key, value in data.items() if isinstance(value, dict)})
    return merged


def _role_config(role_key: str) -> dict[str, Any]:
    key = role_key.upper()
    cfg = dict(_registry().get(key) or {})
    if not cfg:
        cfg = {"model": DEFAULT_OPENROUTER_MODEL, "max_tokens": 900, "temperature": 0.2, "top_p": 1.0}
    overrides = _load_model_overrides()
    if key in overrides:
        cfg["model"] = str(overrides[key])
        cfg["is_overridden"] = True
    else:
        cfg["is_overridden"] = False
    forced = str(os.environ.get("AITEAMRUNTIME_FORCE_MODEL") or "").strip()
    if forced:
        cfg["model"] = forced
        cfg["is_forced"] = True
    return cfg


def _load_model_overrides() -> dict[str, str]:
    path = Path.home() / ".ai-team" / "model_overrides.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    raw = data.get("model_overrides") if isinstance(data, dict) else {}
    if not isinstance(raw, dict):
        return {}
    return {str(key).upper(): str(value) for key, value in raw.items() if str(value).strip()}


def _model_name(role_key: str = "AMBASSADOR") -> str:
    cfg = _role_config(role_key)
    return str(cfg.get("model") or os.environ.get("OPENROUTER_MODEL") or DEFAULT_OPENROUTER_MODEL).strip()


def _model_timeout() -> float:
    return float(os.environ.get("AITEAMRUNTIME_MODEL_TIMEOUT") or 45)


def _model_max_retries() -> int:
    return int(os.environ.get("AITEAMRUNTIME_MODEL_MAX_RETRIES") or 0)


def _leader_role_key(tier: str = "MEDIUM") -> str:
    normalized = _normalize_tier(tier)
    if normalized in {"LOW", "EASY"}:
        return "LEADER_LOW"
    if normalized in {"HARD", "HIGH"}:
        return "LEADER_HIGH"
    return "LEADER_MEDIUM"


def _normalize_tier(tier: str = "MEDIUM") -> str:
    normalized = str(tier or "MEDIUM").strip().upper()
    if normalized in {"LOW", "EASY"}:
        return "LOW"
    if normalized in {"HARD", "HIGH"}:
        return "HARD"
    if normalized in {"MEDIUM", "NORMAL"}:
        return "MEDIUM"
    return "MEDIUM"


def _role_key(agent_id: str, *, tier: str = "") -> str:
    if agent_id == "Leader":
        return _leader_role_key(tier)
    return ROLE_REGISTRY_KEYS.get(agent_id, agent_id.replace(" ", "_").upper())


def _model_meta(role_key: str = "AMBASSADOR") -> dict[str, Any]:
    cfg = _role_config(role_key)
    return {
        "provider": "openrouter",
        "model": _model_name(role_key),
        "mode": "real",
        "registry_key": role_key.upper(),
        "registry_role": str(cfg.get("role") or ""),
        "is_overridden": bool(cfg.get("is_overridden")),
        "is_forced": bool(cfg.get("is_forced")),
    }


def registry_model_summary() -> dict[str, dict[str, Any]]:
    keys = ["AMBASSADOR", "LEADER_LOW", "LEADER_MEDIUM", "LEADER_HIGH", "TOOL_CURATOR", "COMMANDER", "EXPLAINER", *[f"WORKER_{letter}" for letter in "ABCDE"]]
    summary = {}
    for key in keys:
        cfg = _role_config(key)
        summary[key] = {
            "model": _model_name(key),
            "role": str(cfg.get("role") or ""),
            "is_overridden": bool(cfg.get("is_overridden")),
            "is_forced": bool(cfg.get("is_forced")),
        }
    return summary


def _chat_completion(*, role_key: str, system: str, user: str, max_tokens: int = 900) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency exists in project metadata
        raise RuntimeError("openai package is required for OpenRouter model mode") from exc
    cfg = _role_config(role_key)
    configured_max = int(cfg.get("max_tokens") or max_tokens)
    client = OpenAI(
        api_key=_openrouter_key(),
        base_url=OPENROUTER_BASE_URL,
        timeout=_model_timeout(),
        max_retries=_model_max_retries(),
        default_headers={
            "HTTP-Referer": "http://127.0.0.1:8765",
            "X-Title": "aiteamruntime trackaiteam",
        },
    )
    response = client.chat.completions.create(
        model=_model_name(role_key),
        temperature=float(os.environ.get("AITEAMRUNTIME_MODEL_TEMPERATURE") or cfg.get("temperature") or 0.2),
        top_p=float(cfg.get("top_p") or 1.0),
        max_tokens=min(max_tokens, configured_max),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def _chat_json(*, role_key: str, system: str, user: str, max_tokens: int = 900) -> dict[str, Any]:
    text = _chat_completion(role_key=role_key, system=system, user=user, max_tokens=max_tokens)
    try:
        return _parse_json_object(text)
    except (json.JSONDecodeError, ValueError) as exc:
        repair = _chat_completion(
            role_key=role_key,
            system=(
                "You repair malformed JSON for an automated runtime. "
                "Return one valid JSON object only. No markdown. No commentary."
            ),
            user=f"Original instruction:\n{system}\n\nMalformed response:\n{text}\n\nParse error:\n{exc}",
            max_tokens=max_tokens,
        )
        return _parse_json_object(repair)


def _parse_json_object(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
        raw = re.sub(r"```$", "", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start : end + 1]
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("model returned JSON that is not an object")
    return data


def _slug(value: str, fallback: str = "task") -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value[:56]).strip("-")
    return "-".join(part for part in slug.split("-") if part) or fallback


def _safe_rel_path(path: str, fallback: str) -> str:
    raw = str(path or "").replace("\\", "/").strip()
    raw = raw.lstrip("/")
    invalid_windows_chars = set('<>:"|?*')
    if (
        not raw
        or raw.startswith("../")
        or "/../" in raw
        or raw == ".."
        or any(ch in invalid_windows_chars for ch in raw)
    ):
        return fallback
    if raw.startswith(".aiteamruntime/"):
        return raw
    return fallback


def _model_error(ctx: AgentContext, *, stage: str, exc: Exception, work_item_id: str = "") -> None:
    _mark_model_unavailable()
    role_key = _role_key(ctx.agent_id)
    ctx.emit(
        "error",
        {"stage": stage, "type": type(exc).__name__, "message": str(exc), **_model_meta(role_key)},
        status="error",
        stage=stage,
        work_item_id=work_item_id,
        role_state="error",
    )


def _normalize_model_plan(task: str, model_plan: dict[str, Any], *, role_key: str) -> dict[str, Any]:
    """Keep model-authored planning while enforcing runtime safety boundaries."""
    slug = _slug(task)
    raw_items = model_plan.get("work_items") if isinstance(model_plan.get("work_items"), list) else []
    work_items: list[dict[str, Any]] = []
    worker_count = len(WORKER_REGISTRY)
    for index in range(worker_count):
        raw = raw_items[index] if index < len(raw_items) and isinstance(raw_items[index], dict) else {}
        worker_label = list(WORKER_REGISTRY)[index]
        role_slug = _slug(WORKER_REGISTRY[worker_label]["role"], f"worker-{index + 1}")
        fallback = f".aiteamruntime/{slug}/{role_slug}.md"
        raw_files = raw.get("files") if isinstance(raw.get("files"), list) else []
        file_path = _safe_rel_path(str(raw_files[0]) if raw_files else "", fallback)
        raw_depends_on = raw.get("depends_on") if isinstance(raw.get("depends_on"), list) else []
        work_items.append(
            {
                "id": str(raw.get("id") or f"wi-{role_slug}"),
                "title": str(raw.get("title") or f"{worker_label}: {WORKER_REGISTRY[worker_label]['reason']}"),
                "files": [file_path],
                "depends_on": [str(dep) for dep in raw_depends_on],
                "timeout": float(raw.get("timeout") or 60),
            }
        )
    raw_dependencies = model_plan.get("dependencies") if isinstance(model_plan.get("dependencies"), list) else []
    return {
        "task": task,
        "work_items": work_items,
        "setup_commands": [],
        "validation_commands": [{"argv": [sys.executable, "-c", "print('aiteamruntime openrouter validation ok')"], "label": "python validation check"}],
        "files": sorted({path for item in work_items for path in item["files"]}),
        "dependencies": [str(dep) for dep in raw_dependencies],
        "model_plan": {
            "reasoning": str(model_plan.get("reasoning") or ""),
            **_model_meta(role_key),
        },
    }


def ambassador_agent(ctx: AgentContext, event: AgentEvent) -> None:
    prompt = _prompt(event)
    words = [word for word in prompt.strip().split() if word]
    if len(words) < 2:
        selected_leader_role_key = "LEADER_MEDIUM"
        brief = {
            "task": prompt,
            "summary": prompt[:180],
            "tier": "MEDIUM",
            "selected_leader": "Leader",
            "selected_leader_role_key": selected_leader_role_key,
            "selected_leader_model": _model_name(selected_leader_role_key),
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
    if _real_model_enabled():
        role_key = "AMBASSADOR"
        meta = _model_meta(role_key)
        ctx.emit("reading", {"target": "task prompt", **meta}, stage="classify", role_state="running")
        started = time.monotonic()
        ctx.emit(
            "model_requested",
            {"operation": "classify_task", "timeout_s": _model_timeout(), "max_retries": _model_max_retries(), **meta},
            stage="classify",
            role_state="running",
        )
        try:
            model_brief = _chat_json(
                role_key=role_key,
                system=(
                    "You are Ambassador in a production-style event-driven AI team runtime. "
                    "Classify the user's task and decide whether the Leader needs clarification. "
                    "Return JSON only with keys: task, summary, tier, selected_leader, "
                    "requires_clarification, question. selected_leader must be Leader. "
                    "tier must be LOW, MEDIUM, HARD, or UNKNOWN."
                ),
                user=f"Task:\n{prompt}",
                max_tokens=500,
            )
        except Exception as exc:
            _model_error(ctx, stage="classify", exc=exc)
            selected_leader_role_key = "LEADER_MEDIUM"
            brief = {
                "task": prompt,
                "summary": prompt[:180],
                "tier": "MEDIUM",
                "raw_tier": "MODEL_ERROR_FALLBACK",
                "selected_leader": "Leader",
                "selected_leader_role_key": selected_leader_role_key,
                "selected_leader_model": _model_name(selected_leader_role_key),
                "requires_clarification": False,
                "question": "",
                **meta,
            }
            ctx.emit(
                "routing",
                {
                    "from": "Ambassador",
                    "to": brief["selected_leader"],
                    "leader_role_key": selected_leader_role_key,
                    "leader_model": brief["selected_leader_model"],
                    "tier": brief["tier"],
                    "reason": "model error fallback",
                },
                stage="classify",
                role_state="done",
            )
            ctx.emit("classifying", brief, stage="classify", role_state="running")
            ctx.emit("done", {**brief, "stage": "classify"}, stage="classify", role_state="done")
            return
        ctx.emit(
            "model_response",
            {"operation": "classify_task", "keys": sorted(str(key) for key in model_brief), **meta},
            stage="classify",
            duration_ms=int((time.monotonic() - started) * 1000),
            role_state="done",
        )
        raw_tier = str(model_brief.get("tier") or "UNKNOWN").upper()
        tier = _normalize_tier(raw_tier)
        selected_leader_role_key = _leader_role_key(tier)
        brief = {
            "task": str(model_brief.get("task") or prompt),
            "summary": str(model_brief.get("summary") or prompt[:180]),
            "tier": tier,
            "raw_tier": raw_tier,
            "selected_leader": "Leader",
            "selected_leader_role_key": selected_leader_role_key,
            "selected_leader_model": _model_name(selected_leader_role_key),
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
                "leader_role_key": selected_leader_role_key,
                "leader_model": brief["selected_leader_model"],
                "tier": brief["tier"],
                "reason": brief["summary"],
            },
            stage="classify",
            role_state="done",
        )
        ctx.emit("classifying", brief, stage="classify", role_state="running")
        ctx.emit("done", {**brief, "stage": "classify"}, stage="classify", role_state="done")
        return
    selected_leader_role_key = "LEADER_MEDIUM"
    brief = {
        "task": prompt,
        "summary": prompt[:180],
        "tier": "MEDIUM",
        "selected_leader": "Leader",
        "selected_leader_role_key": selected_leader_role_key,
        "selected_leader_model": _model_name(selected_leader_role_key),
    }
    ctx.emit(
        "routing",
        {
            "from": "Ambassador",
            "to": "Leader",
            "leader_role_key": selected_leader_role_key,
            "leader_model": _model_name(selected_leader_role_key),
            "tier": "MEDIUM",
            "reason": "fallback classifier",
        },
        stage="classify",
        role_state="done",
    )
    ctx.emit("classifying", brief, stage="classify", role_state="running")
    _sleep(0.02)
    ctx.emit("done", {**brief, "stage": "classify"}, stage="classify", role_state="done")


def leader_agent(ctx: AgentContext, event: AgentEvent) -> None:
    trigger_payload = dict(event.payload or {})
    embedded_brief = trigger_payload.get("brief") if isinstance(trigger_payload.get("brief"), dict) else {}
    brief = dict(embedded_brief or trigger_payload)
    tier = _normalize_tier(str(brief.get("tier") or trigger_payload.get("tier") or "MEDIUM"))
    role_key = _leader_role_key(tier)
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
    leader_meta = _model_meta(role_key)
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
    if _real_model_enabled():
        started = time.monotonic()
        ctx.emit(
            "model_requested",
            {
                "operation": "generate_plan",
                "tier": tier,
                "selected_by": source_agent_id,
                "source_event_id": event.event_id,
                "task_summary": str(brief.get("summary") or base_task[:180]),
                "timeout_s": _model_timeout(),
                "max_retries": _model_max_retries(),
                **leader_meta,
            },
            stage="plan",
            role_state="running",
        )
        try:
            model_plan = _chat_json(
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
            _model_error(ctx, stage="plan", exc=exc)
            slug = _slug(task)
            work_items = [
                {
                    "id": "wi-implementation",
                    "title": f"Implement workspace artifact for {slug}",
                    "files": [f".aiteamruntime/{slug}/implementation.txt"],
                    "depends_on": [],
                    "timeout": 30,
                },
                {
                    "id": "wi-viewer",
                    "title": f"Create validation notes for {slug}",
                    "files": [f".aiteamruntime/{slug}/validation.txt"],
                    "depends_on": [],
                    "timeout": 30,
                },
            ]
            plan = {
                "task": task,
                "work_items": work_items,
                "setup_commands": [],
                "validation_commands": [
                    {"argv": [sys.executable, "-c", "print('aiteamruntime validation ok')"], "label": "python validation check"}
                ],
                "files": sorted({path for item in work_items for path in item["files"]}),
                "dependencies": [],
                "model_error_fallback": True,
            }
            ctx.emit(
                "reasoning",
                {"content": "Leader generated a local recovery plan because the configured model failed.", **leader_meta},
                stage="plan",
            )
            ctx.emit("writing", {"file": "runtime plan", "plan": plan, **leader_meta}, stage="plan")
            ctx.emit("done", {"stage": "plan", "plan": plan, "task": task, **leader_meta}, stage="plan", role_state="done")
            return
        ctx.emit(
            "model_response",
            {"operation": "generate_plan", "keys": sorted(str(key) for key in model_plan), **leader_meta},
            stage="plan",
            duration_ms=int((time.monotonic() - started) * 1000),
            role_state="done",
        )
        plan = _normalize_model_plan(task, model_plan, role_key=role_key)
        ctx.emit(
            "reasoning",
            {"content": str(model_plan.get("reasoning") or "Leader produced a real model plan."), **leader_meta},
            stage="plan",
        )
        ctx.emit("writing", {"file": "runtime plan", "plan": plan, **leader_meta}, stage="plan")
        ctx.emit("done", {"stage": "plan", "plan": plan, "task": task, **leader_meta}, stage="plan", role_state="done")
        return
    _sleep(0.02)
    slug = _slug(task)
    work_items = [
        {
            "id": "wi-implementation",
            "title": f"Implement workspace artifact for {slug}",
            "files": [f".aiteamruntime/{slug}/implementation.txt"],
            "depends_on": [],
            "timeout": 30,
        },
        {
            "id": "wi-viewer",
            "title": f"Create validation notes for {slug}",
            "files": [f".aiteamruntime/{slug}/validation.txt"],
            "depends_on": [],
            "timeout": 30,
        },
    ]
    plan = {
        "task": task,
        "work_items": work_items,
        "setup_commands": [],
        "validation_commands": [{"argv": [sys.executable, "-c", "print('aiteamruntime validation ok')"], "label": "python validation check"}],
        "files": sorted({path for item in work_items for path in item["files"]}),
        "dependencies": [],
    }
    ctx.emit("reasoning", {"content": "Standalone test workflow: plan is data, runtime stays generic."}, stage="plan")
    ctx.emit("writing", {"file": "runtime plan", "plan": plan}, stage="plan")
    ctx.emit("done", {"stage": "plan", "plan": plan, "task": task}, stage="plan", role_state="done")


def tool_curator_agent(ctx: AgentContext, event: AgentEvent) -> None:
    if event.kind == "setup_done":
        _release_assignments_after_setup(ctx, event)
        return
    plan = dict(event.payload.get("plan") or {})
    work_items = [WorkItem.from_payload(item) for item in plan.get("work_items") or []]
    ctx.emit("reading", {"file": "runtime plan", "purpose": "select tools and compatible workers"}, stage="tooling")
    _sleep(0.01)
    tool_notes: dict[str, Any] = {
        "tools": ["stdlib http.server", "ThreadPoolExecutor", "pytest"],
        "worker_registry": WORKER_REGISTRY,
        "assignment_notes": "Assigned by local worker registry.",
        "project_setup_commands": [],
    }
    if _real_model_enabled():
        role_key = "TOOL_CURATOR"
        try:
            model_tools = _chat_json(
                role_key=role_key,
                system=(
                    "You are Tool Curator. Return JSON only with keys: tools, assignment_notes, project_setup_commands. "
                    "project_setup_commands are Secretary-only commands needed before workers start. "
                    "Only include setup/scaffold commands when the workspace does not already contain the required project scaffold. "
                    "Do not put validation commands or worker commands in project_setup_commands."
                ),
                user=json.dumps(
                    {
                        "plan": plan,
                        "worker_registry": WORKER_REGISTRY,
                        "workspace_snapshot": _workspace_snapshot(ctx),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                max_tokens=1200,
            )
        except Exception as exc:
            _model_error(ctx, stage="tooling", exc=exc)
            tool_notes["project_setup_commands"] = _safe_setup_commands(ctx, plan, [])
            tool_notes["model_error_fallback"] = True
        else:
            tools = model_tools.get("tools") if isinstance(model_tools.get("tools"), list) else tool_notes["tools"]
            tool_notes = {
                "tools": [str(tool) for tool in tools],
                "worker_registry": WORKER_REGISTRY,
                "assignment_notes": str(model_tools.get("assignment_notes") or ""),
                "project_setup_commands": _safe_setup_commands(ctx, plan, model_tools.get("project_setup_commands")),
                **_model_meta(role_key),
            }
    else:
        tool_notes["project_setup_commands"] = _safe_setup_commands(ctx, plan, [])
    ctx.emit("writing", {"file": "tool choices", **tool_notes}, stage="tooling")
    tool_path = _tool_file_path(plan)
    tool_content = (
        "Tools selected by Tool Curator\n"
        "\nSecretary-only setup\n"
        + _format_setup_commands(tool_notes.get("project_setup_commands") or [])
        + "\nWorker-facing tools\n"
        + "".join(f"- {tool}\n" for tool in tool_notes["tools"])
        + f"\nAssignment notes:\n{tool_notes.get('assignment_notes') or 'Assigned by worker registry.'}\n"
    )
    try:
        tool_full_path = _write_workspace_text(ctx, tool_path, tool_content)
        ctx.emit("file_create", {"path": tool_path, "absolute_path": str(tool_full_path), "added_lines": len(tool_content.splitlines())}, stage="tooling")
    except Exception as exc:
        ctx.emit("worker_failed", {"reason": str(exc), "target": tool_path}, status="error", stage="tooling")
        return
    assignments = _build_assignments(ctx, work_items)
    setup_commands = [command for command in tool_notes.get("project_setup_commands") or [] if isinstance(command, dict)]
    if setup_commands:
        gate_id = f"setup-{event.event_id[:12]}"
        ctx.emit(
            "progress",
            {
                "stage": "setup",
                "gate_id": gate_id,
                "state": "waiting_for_secretary",
                "assignments": assignments,
                "setup_commands": setup_commands,
            },
            status="waiting",
            stage="setup",
            role_state="waiting",
        )
        _request_setup_command(ctx, gate_id, setup_commands, 0)
    else:
        _emit_assignments(ctx, assignments)
    ctx.emit("done", {"stage": "tooling", "assignments": assignments, "plan": plan, "setup_commands": setup_commands}, stage="tooling")


def _workspace_snapshot(ctx: AgentContext) -> dict[str, Any]:
    workspace = ctx.runtime.resources.workspace_for(ctx.run_id)
    root = Path(workspace) if workspace else Path.cwd()
    names = []
    for name in ("package.json", "vite.config.js", "vite.config.ts", "src", "app", "pages", "pyproject.toml"):
        try:
            if (root / name).exists():
                names.append(name)
        except OSError:
            pass
    return {"workspace": str(root), "exists": root.exists(), "entries": names}


def _safe_setup_commands(ctx: AgentContext, plan: dict[str, Any], raw_commands: Any) -> list[dict[str, Any]]:
    workspace = ctx.runtime.resources.workspace_for(ctx.run_id)
    root = Path(workspace) if workspace else Path.cwd()
    task_blob = json.dumps(plan, ensure_ascii=False).lower()
    has_package = (root / "package.json").exists()
    needs_react = any(token in task_blob for token in ("react", "vite", "frontend", "ui", "web app", "next.js", "nextjs"))
    if has_package:
        return _filter_safe_setup_commands(raw_commands)
    if needs_react:
        return [_python_vite_react_project_command()]
    return _filter_safe_setup_commands(raw_commands)


def _filter_safe_setup_commands(raw_commands: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_commands, list):
        return []
    allowed: list[dict[str, Any]] = []
    for command in raw_commands[:3]:
        if not isinstance(command, dict):
            continue
        argv = [str(part) for part in command.get("argv") or []]
        if not argv:
            continue
        executable = Path(argv[0]).name.lower()
        if executable not in {"python", "python.exe", Path(sys.executable).name.lower()}:
            continue
        allowed.append(
            {
                "label": str(command.get("label") or "Secretary setup command"),
                "argv": argv,
                "timeout": float(command.get("timeout") or 60),
            }
        )
    return allowed


def _python_vite_react_project_command() -> dict[str, Any]:
    script = (
        "import json\n"
        "import time\n"
        "from pathlib import Path\n"
        "root=Path.cwd()\n"
        "root.mkdir(parents=True, exist_ok=True)\n"
        "src=root/'src'\n"
        "src.mkdir(exist_ok=True)\n"
        "pkg={\n"
        "  'name':'aiteamruntime-vite-react-app',\n"
        "  'private':True,\n"
        "  'version':'0.1.0',\n"
        "  'type':'module',\n"
        "  'scripts':{'dev':'vite --host 127.0.0.1','build':'vite build','preview':'vite preview --host 127.0.0.1'},\n"
        "  'dependencies':{'@vitejs/plugin-react':'latest','vite':'latest','react':'latest','react-dom':'latest'},\n"
        "  'devDependencies':{}\n"
        "}\n"
        "(root/'package.json').write_text(json.dumps(pkg, ensure_ascii=False, indent=2)+'\\n', encoding='utf-8')\n"
        "(root/'index.html').write_text(\"<!doctype html>\\n<html><head><meta charset='UTF-8'/><meta name='viewport' content='width=device-width, initial-scale=1.0'/><title>AI Team Runtime App</title></head><body><div id='root'></div><script type='module' src='/src/main.jsx'></script></body></html>\\n\", encoding='utf-8')\n"
        "(src/'main.jsx').write_text(\"import React from 'react';\\nimport { createRoot } from 'react-dom/client';\\nimport App from './App.jsx';\\nimport './style.css';\\n\\ncreateRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>);\\n\", encoding='utf-8')\n"
        "(src/'App.jsx').write_text(\"export default function App() {\\n  return (\\n    <main className='app-shell'>\\n      <section className='workspace-panel'>\\n        <p className='eyebrow'>AI Team Runtime</p>\\n        <h1>React project scaffold is ready</h1>\\n        <p>Secretary created this Vite-compatible project before workers received assignments.</p>\\n      </section>\\n    </main>\\n  );\\n}\\n\", encoding='utf-8')\n"
        "(src/'style.css').write_text(\":root{font-family:Inter,system-ui,Segoe UI,Arial,sans-serif;color:#20242a;background:#f7f8fb}body{margin:0}.app-shell{min-height:100vh;display:grid;place-items:center;padding:32px}.workspace-panel{max-width:720px;border:1px solid #d9dee7;background:white;border-radius:8px;padding:28px}.eyebrow{font-size:12px;text-transform:uppercase;color:#5c6b7d;letter-spacing:.04em}h1{margin:0 0 12px;font-size:32px}\\n\", encoding='utf-8')\n"
        "manifest={'tool':'Secretary','project':'vite-react','created_at':time.time(),'files':['package.json','index.html','src/main.jsx','src/App.jsx','src/style.css']}\n"
        "(root/'.aiteamruntime_setup.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\\n', encoding='utf-8')\n"
        "print('Secretary created Vite React project scaffold')\n"
        "print(json.dumps(manifest, ensure_ascii=False))\n"
    )
    return {
        "label": "Secretary create Vite React project scaffold",
        "argv": [sys.executable, "-c", script],
        "timeout": 60,
        "creates": ["package.json", "index.html", "src/main.jsx", "src/App.jsx", "src/style.css", ".aiteamruntime_setup.json"],
    }


def _format_setup_commands(commands: list[dict[str, Any]]) -> str:
    if not commands:
        return "- No setup required before workers.\n"
    lines = []
    for command in commands:
        label = str(command.get("label") or "setup")
        argv = " ".join(str(part) for part in command.get("argv") or [])
        lines.append(f"- {label}: `{argv}`")
    return "\n".join(lines) + "\n"


def _build_assignments(ctx: AgentContext, work_items: list[WorkItem]) -> list[dict[str, Any]]:
    assignments: list[dict[str, Any]] = []
    claimed_files: dict[str, str] = {}
    worker_order = list(WORKER_REGISTRY)
    for index, item in enumerate(work_items):
        worker = worker_order[index % len(worker_order)]
        conflict = next((path for path in item.allowed_paths if path in claimed_files), "")
        if conflict:
            ctx.emit(
                "blocked",
                {
                    "resource_type": "file",
                    "resource_key": conflict,
                    "owner_agent_id": claimed_files[conflict],
                    "reason": "file already assigned; queued for serialization",
                    "work_item_id": item.id,
                },
                status="blocked",
                stage="tooling",
                work_item_id=item.id,
                resource_key=conflict,
            )
            worker = claimed_files[conflict]
        for path in item.allowed_paths:
            claimed_files.setdefault(path, worker)
        item.assigned_worker = worker
        assignment = item.to_dict()
        assignment["reason"] = WORKER_REGISTRY[worker]["reason"]
        assignments.append(assignment)
    return assignments


def _emit_assignments(ctx: AgentContext, assignments: list[dict[str, Any]], *, gate_id: str = "") -> None:
    for assignment in assignments:
        payload = {
            "stage": "work",
            "work_item": assignment,
            "assigned_worker": assignment.get("assigned_worker"),
            "allowed_paths": assignment.get("allowed_paths") or [],
        }
        if gate_id:
            payload["setup_gate_id"] = gate_id
        ctx.emit(
            "assigned",
            payload,
            stage="work",
            work_item_id=str(assignment.get("id") or ""),
            assignment=assignment,
            role_state="waiting",
        )


def _request_setup_command(ctx: AgentContext, gate_id: str, commands: list[dict[str, Any]], index: int) -> None:
    if index < 0 or index >= len(commands):
        return
    payload = _command_payload(commands[index], "setup")
    payload["gate_id"] = gate_id
    payload["setup_index"] = index
    payload["setup_total"] = len(commands)
    payload["creates"] = list(commands[index].get("creates") or [])
    ctx.emit("setup_requested", payload, stage="setup", role_state="waiting")


def _release_assignments_after_setup(ctx: AgentContext, event: AgentEvent) -> None:
    gate_id = str(event.payload.get("gate_id") or "")
    if not gate_id:
        return
    events = ctx.runtime.store.read_events(ctx.run_id)
    if any((item.get("payload") or {}).get("setup_gate_id") == gate_id and item.get("kind") == "assigned" for item in events):
        return
    gate = next(
        (
            item
            for item in reversed(events)
            if item.get("kind") == "progress"
            and item.get("agent_id") == "Tool Curator"
            and (item.get("payload") or {}).get("gate_id") == gate_id
        ),
        None,
    )
    if gate is None:
        return
    payload = gate.get("payload") or {}
    commands = payload.get("setup_commands") if isinstance(payload.get("setup_commands"), list) else []
    assignments = payload.get("assignments") if isinstance(payload.get("assignments"), list) else []
    results = [
        item
        for item in events
        if item.get("kind") == "setup_done" and (item.get("payload") or {}).get("gate_id") == gate_id
    ]
    if any(str(item.get("status") or "") in {"error", "timeout"} for item in results):
        ctx.emit("blocked", {"gate_id": gate_id, "reason": "setup failed; workers not released"}, status="blocked", stage="setup", role_state="blocked")
        return
    if len(results) < len(commands):
        requested_indexes = {
            int((item.get("payload") or {}).get("setup_index") or 0)
            for item in events
            if item.get("kind") == "setup_requested" and (item.get("payload") or {}).get("gate_id") == gate_id
        }
        next_index = len(results)
        if next_index not in requested_indexes:
            _request_setup_command(ctx, gate_id, commands, next_index)
        ctx.emit(
            "progress",
            {"gate_id": gate_id, "state": "waiting_for_setup", "done": len(results), "total": len(commands)},
            status="waiting",
            stage="setup",
            role_state="waiting",
        )
        return
    ctx.emit("progress", {"gate_id": gate_id, "state": "setup_complete_releasing_workers"}, stage="setup", role_state="done")
    _emit_assignments(ctx, [dict(item) for item in assignments if isinstance(item, dict)], gate_id=gate_id)


def secretary_agent(ctx: AgentContext, event: AgentEvent) -> None:
    """Route every command through the shared Secretary subprocess.

    Workers, validation steps, and setup-time hooks all emit the same kinds
    here; the Secretary is the *only* role allowed to actually run a child
    command, and it does so via the long-running ``SecretaryProcess`` so we
    never spawn a fresh ``python.exe`` per validation.
    """
    command = str(event.payload.get("command") or "")
    requested_cwd = str(event.payload.get("cwd") or ".")
    workspace = ctx.runtime.resources.workspace_for(ctx.run_id)
    cwd = workspace if requested_cwd in {"", "."} and workspace else requested_cwd
    argv = event.payload.get("argv")
    timeout = float(event.payload.get("timeout") or 20.0)
    stage = "setup" if event.kind == "setup_requested" else str(event.stage or event.payload.get("stage") or "validate")
    if event.kind == "setup_requested":
        result_kind = "setup_done"
    elif event.kind == "secretary_command":
        result_kind = "secretary_result"
    else:
        result_kind = "terminal_result"

    if not isinstance(argv, list) or not argv:
        ctx.emit(
            result_kind,
            {"command": command, "cwd": cwd, "status": "failed", "exit_code": 2,
             "output": "argv required", "stdout": "", "stderr": "argv required"},
            status="error",
            stage=stage,
            role_state="done",
        )
        ctx.emit("done", {"stage": stage, "command": command}, stage=stage)
        return

    started = time.monotonic()
    ctx.emit(
        "terminal_running",
        {"command": command, "cwd": cwd, "status": "running"},
        status="running",
        stage=stage,
        role_state="running",
    )
    try:
        result = _run_secretary_command_with_retry(ctx, [str(part) for part in argv], cwd=cwd or ".", timeout=timeout)
    except Exception as exc:
        message = f"secretary error ({type(exc).__name__}): {exc or 'no result returned before wait deadline'}"
        result = {
            "exit_code": 1,
            "stdout": "",
            "stderr": message,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "timed_out": isinstance(exc, FutureTimeoutError),
        }

    exit_code = int(result.get("exit_code") or 0)
    output = "\n".join(p for p in (result.get("stdout") or "", result.get("stderr") or "") if p).strip()
    status = "passed" if exit_code == 0 else ("timeout" if result.get("timed_out") else "failed")
    ctx.emit(
        result_kind,
        {
            "command": command,
            "cwd": cwd,
            "status": status,
            "exit_code": exit_code,
            "output": output,
            "stdout": result.get("stdout") or "",
            "stderr": result.get("stderr") or "",
            "timed_out": bool(result.get("timed_out")),
            "gate_id": event.payload.get("gate_id") or "",
            "setup_index": event.payload.get("setup_index"),
            "setup_total": event.payload.get("setup_total"),
            "creates": list(event.payload.get("creates") or []),
            "work_item_id": event.work_item_id or event.payload.get("work_item_id") or "",
        },
        status="ok" if exit_code == 0 else ("timeout" if result.get("timed_out") else "error"),
        stage=stage,
        work_item_id=event.work_item_id or str(event.payload.get("work_item_id") or ""),
        duration_ms=int(result.get("duration_ms") or (time.monotonic() - started) * 1000),
        role_state="done",
    )
    if stage == "validate" and exit_code == 0:
        ctx.emit(
            "validated",
            {"stage": "validate", "command": command, "result": "passed", "work_item_id": event.work_item_id or event.payload.get("work_item_id") or ""},
            stage="validate",
            work_item_id=event.work_item_id or str(event.payload.get("work_item_id") or ""),
            role_state="done",
        )
    ctx.emit(
        "done",
        {"stage": stage, "command": command, "work_item_id": event.work_item_id or event.payload.get("work_item_id") or ""},
        stage=stage,
        work_item_id=event.work_item_id or str(event.payload.get("work_item_id") or ""),
    )


def _run_secretary_command_with_retry(ctx: AgentContext, argv: list[str], *, cwd: str, timeout: float) -> dict[str, Any]:
    secretary = ctx.runtime.secretary()
    future = secretary.submit(argv, cwd=cwd, timeout=timeout)
    try:
        return future.result(timeout=timeout + 5.0)
    except FutureTimeoutError:
        try:
            secretary.terminate(timeout=1.0)
        except Exception:
            pass
        ctx.runtime._secretary = None
        retry = ctx.runtime.secretary().submit(argv, cwd=cwd, timeout=timeout)
        return retry.result(timeout=timeout + 5.0)


def worker_agent(ctx: AgentContext, event: AgentEvent) -> None:
    item = WorkItem.from_payload(dict(event.assignment or event.payload.get("work_item") or event.payload))
    allowed = set(item.allowed_paths)
    started = time.monotonic()
    ctx.emit("reading", {"files": sorted(allowed), "work_item_id": item.id}, stage="work", work_item_id=item.id, role_state="running")
    _sleep(0.02)
    target = sorted(allowed)[0] if allowed else f"virtual/{item.id}.txt"
    if _real_model_enabled():
        role_key = _role_key(ctx.agent_id)
        try:
            content = _chat_completion(
                role_key=role_key,
                system=(
                    "You are a worker agent in a real event-driven runtime test. "
                    "Do exactly the assigned work item. Produce a concrete markdown/text artifact. "
                    "Include lines starting with Agent:, Work item:, and RESULT:. "
                    "Do not claim to modify files other than the assigned allowed path."
                ),
                user=json.dumps(
                    {
                        "agent": ctx.agent_id,
                        "worker_role": WORKER_REGISTRY.get(ctx.agent_id, {}),
                        "work_item": item.to_dict(),
                        "target_file": target,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                max_tokens=900,
            )
        except Exception as exc:
            _model_error(ctx, stage="work", exc=exc, work_item_id=item.id)
            content = (
                f"Work item: {item.id}\n"
                f"Title: {item.title}\n"
                f"Agent: {ctx.agent_id}\n"
                "RESULT: local recovery artifact written after model provider error.\n"
            )
    else:
        content = f"Work item: {item.id}\nTitle: {item.title}\nAgent: {ctx.agent_id}\n"
    ctx.emit("writing", {"file": target, "content": content, "work_item_id": item.id}, stage="work", work_item_id=item.id)
    try:
        full_path = ctx.runtime.resources.resolve_workspace_path(ctx.run_id, target)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        before = full_path.read_text(encoding="utf-8").splitlines() if full_path.exists() else []
        full_path.write_text(content, encoding="utf-8")
        after = full_path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        ctx.emit("worker_failed", {"reason": str(exc), "work_item_id": item.id, "target": target}, status="error", stage="work", work_item_id=item.id)
        return
    ctx.emit("file_update", {"path": target, "absolute_path": str(full_path), "added_lines": max(0, len(after) - len(before)), "removed_lines": 0, "work_item_id": item.id}, stage="work", work_item_id=item.id)
    code = f"from pathlib import Path; p=Path({str(full_path)!r}); print('validated {item.id}:', p.exists(), p.stat().st_size)"
    ctx.emit(
        "terminal_requested",
        {
            "command": f"python validate workspace artifact {item.id}",
            "argv": [sys.executable, "-c", code],
            "cwd": ".",
            "work_item_id": item.id,
            "stage": "validate",
        },
        stage="validate",
        work_item_id=item.id,
    )
    ctx.emit("done", {"stage": "work", "work_item_id": item.id, "files_changed": [target]}, stage="work", work_item_id=item.id, duration_ms=int((time.monotonic() - started) * 1000), role_state="done")


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
    payload: dict[str, Any] = {"stage": "finalize", "result": "standalone runtime run complete"}
    if _real_model_enabled():
        role_key = "COMMANDER"
        try:
            result = _chat_completion(
                role_key=role_key,
                system=(
                    "You are Runtime Finalizer. Summarize the completed validation event in 3 concise bullets. "
                    "Mention that this was a real OpenRouter-backed role run."
                ),
                user=json.dumps(event.to_dict(), ensure_ascii=False, indent=2),
                max_tokens=450,
            )
        except Exception as exc:
            _model_error(ctx, stage="finalize", exc=exc)
            return
        payload = {"stage": "finalize", "result": result, **_model_meta(role_key)}
    ctx.emit("finalized", payload, stage="finalize", role_state="done")
    ctx.emit("done", {"stage": "finalize"}, stage="finalize", role_state="done")


def explainer_agent(ctx: AgentContext, event: AgentEvent) -> None:
    ctx.emit("reading", {"target": event.payload.get("target") or "@codebase"}, stage="explain")
    if _real_model_enabled():
        role_key = "EXPLAINER"
        try:
            content = _chat_completion(
                role_key=role_key,
                system="You are Explainer. Explain the selected runtime event and next action in plain language.",
                user=json.dumps(event.to_dict(), ensure_ascii=False, indent=2),
                max_tokens=450,
            )
            payload = {"content": content, **_model_meta(role_key)}
        except Exception as exc:
            _model_error(ctx, stage="explain", exc=exc)
            return
    else:
        payload = {"content": "Explain only when explicitly requested from workflow monitor."}
    ctx.emit("reasoning", payload, stage="explain")
    ctx.emit("done", {"stage": "explainer"}, stage="explain")


def build_demo_pipeline(*, include_explainer: bool = True) -> PipelineDefinition:
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
    return build_demo_pipeline(include_explainer=include_explainer).register(runtime)


def _command_payload(command: Any, stage: str) -> dict[str, Any]:
    if isinstance(command, dict):
        argv = [str(part) for part in command.get("argv") or []]
        label = str(command.get("label") or " ".join(argv))
        timeout = float(command.get("timeout") or 30)
    else:
        argv = []
        label = str(command)
        timeout = 30.0
    return {"command": label, "argv": argv, "cwd": ".", "stage": stage, "timeout": timeout}


def _tool_file_path(plan: dict[str, Any]) -> str:
    files = [str(path) for path in plan.get("files") or [] if str(path)]
    if files:
        parent = Path(files[0]).parent.as_posix()
        if parent and parent != ".":
            return f"{parent}/tools.txt"
    return ".aiteamruntime/tools.txt"


def _write_workspace_text(ctx: AgentContext, path: str, content: str) -> Path:
    full_path = ctx.runtime.resources.resolve_workspace_path(ctx.run_id, path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return full_path


# NOTE: ``_run_allowed_command`` was removed in the Secretary subprocess refactor.
# All command execution now flows through ``ctx.runtime.secretary().submit(...)``
# which keeps a single long-running ``python.exe`` per runtime instead of
# spawning one child per validation step.

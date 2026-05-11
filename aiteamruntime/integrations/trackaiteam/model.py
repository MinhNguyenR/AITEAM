from __future__ import annotations

import importlib.util
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"
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
REQUIRED_REGISTRY_KEYS = [
    "AMBASSADOR",
    "LEADER_LOW",
    "LEADER_MEDIUM",
    "LEADER_HIGH",
    "TOOL_CURATOR",
    "COMMANDER",
    *[f"WORKER_{letter}" for letter in "ABCDE"],
]


def openrouter_key() -> str:
    return str(os.environ.get("OPENROUTER_API_KEY") or os.environ.get("AITEAMRUNTIME_REAL_MODEL_API_KEY") or "").strip()


def real_model_enabled() -> bool:
    disabled = str(os.environ.get("AITEAMRUNTIME_DISABLE_REAL_MODEL") or "").strip().lower()
    return bool(openrouter_key()) and disabled not in {"1", "true", "yes", "on"} and not missing_registry_models()


def missing_registry_models() -> list[str]:
    if str(os.environ.get("AITEAMRUNTIME_FORCE_MODEL") or "").strip():
        return []
    overrides = load_model_overrides()
    raw_registry = registry()
    missing: list[str] = []
    for key in REQUIRED_REGISTRY_KEYS:
        if overrides.get(key):
            continue
        if not (raw_registry.get(key) or {}).get("model"):
            missing.append(f"registry:{key}")
    return missing


def model_readiness() -> dict[str, Any]:
    missing: list[str] = []
    if not openrouter_key():
        missing.append("OPENROUTER_API_KEY")
    registry_data = registry_model_summary()
    missing.extend(missing_registry_models())
    disabled = str(os.environ.get("AITEAMRUNTIME_DISABLE_REAL_MODEL") or "").strip().lower() in {"1", "true", "yes", "on"}
    return {
        "ok": not missing and not disabled,
        "provider": "openrouter",
        "enabled": real_model_enabled(),
        "missing": missing,
        "disabled": disabled,
        "source": "core.config.registry",
        "registry": registry_data,
    }


@lru_cache(maxsize=1)
def registry() -> dict[str, dict[str, Any]]:
    root = Path(__file__).resolve().parents[3]
    registry_dir = root / "core" / "config" / "registry" / "coding"
    files = (
        "system.py",
        "chat.py",
        "leaders.py",
        "researchers.py",
        "support.py",
        "workers.py",
        "testers.py",
        "reviewers.py",
        "fixers.py",
        "devops.py",
    )
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


def role_config(role_key: str) -> dict[str, Any]:
    key = role_key.upper()
    cfg = dict(registry().get(key) or {})
    if not cfg:
        cfg = {"model": DEFAULT_OPENROUTER_MODEL, "max_tokens": 900, "temperature": 0.2, "top_p": 1.0}
    overrides = load_model_overrides()
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


def load_model_overrides() -> dict[str, str]:
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


def model_name(role_key: str = "AMBASSADOR") -> str:
    cfg = role_config(role_key)
    return str(cfg.get("model") or os.environ.get("OPENROUTER_MODEL") or DEFAULT_OPENROUTER_MODEL).strip()


def model_timeout() -> float:
    return float(os.environ.get("AITEAMRUNTIME_MODEL_TIMEOUT") or 45)


def model_max_retries() -> int:
    return int(os.environ.get("AITEAMRUNTIME_MODEL_MAX_RETRIES") or 0)


def leader_role_key(tier: str = "MEDIUM") -> str:
    normalized = normalize_tier(tier)
    if normalized in {"LOW", "EASY"}:
        return "LEADER_LOW"
    if normalized in {"HARD", "HIGH"}:
        return "LEADER_HIGH"
    return "LEADER_MEDIUM"


def normalize_tier(tier: str = "MEDIUM") -> str:
    normalized = str(tier or "MEDIUM").strip().upper()
    if normalized in {"LOW", "EASY"}:
        return "LOW"
    if normalized in {"HARD", "HIGH"}:
        return "HARD"
    if normalized in {"MEDIUM", "NORMAL"}:
        return "MEDIUM"
    return "MEDIUM"


def role_key(agent_id: str, *, tier: str = "") -> str:
    if agent_id == "Leader":
        return leader_role_key(tier)
    return ROLE_REGISTRY_KEYS.get(agent_id, agent_id.replace(" ", "_").upper())


def model_meta(role_key: str = "AMBASSADOR") -> dict[str, Any]:
    cfg = role_config(role_key)
    return {
        "provider": "openrouter",
        "model": model_name(role_key),
        "mode": "real",
        "registry_key": role_key.upper(),
        "registry_role": str(cfg.get("role") or ""),
        "is_overridden": bool(cfg.get("is_overridden")),
        "is_forced": bool(cfg.get("is_forced")),
    }


def registry_model_summary() -> dict[str, dict[str, Any]]:
    keys = [
        "AMBASSADOR",
        "LEADER_LOW",
        "LEADER_MEDIUM",
        "LEADER_HIGH",
        "TOOL_CURATOR",
        "COMMANDER",
        "EXPLAINER",
        *[f"WORKER_{letter}" for letter in "ABCDE"],
    ]
    summary = {}
    for key in keys:
        cfg = role_config(key)
        summary[key] = {
            "model": model_name(key),
            "role": str(cfg.get("role") or ""),
            "is_overridden": bool(cfg.get("is_overridden")),
            "is_forced": bool(cfg.get("is_forced")),
        }
    return summary


def chat_completion(*, role_key: str, system: str, user: str, max_tokens: int = 900) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency exists in project metadata
        raise RuntimeError("openai package is required for OpenRouter model mode") from exc
    cfg = role_config(role_key)
    configured_max = int(cfg.get("max_tokens") or max_tokens)
    client = OpenAI(
        api_key=openrouter_key(),
        base_url=OPENROUTER_BASE_URL,
        timeout=model_timeout(),
        max_retries=model_max_retries(),
        default_headers={
            "HTTP-Referer": "http://127.0.0.1:8765",
            "X-Title": "aiteamruntime trackaiteam",
        },
    )
    response = client.chat.completions.create(
        model=model_name(role_key),
        temperature=float(os.environ.get("AITEAMRUNTIME_MODEL_TEMPERATURE") or cfg.get("temperature") or 0.2),
        top_p=float(cfg.get("top_p") or 1.0),
        max_tokens=min(max_tokens, configured_max),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def chat_json(*, role_key: str, system: str, user: str, max_tokens: int = 900) -> dict[str, Any]:
    text = chat_completion(role_key=role_key, system=system, user=user, max_tokens=max_tokens)
    try:
        return parse_json_object(text)
    except (json.JSONDecodeError, ValueError) as exc:
        repair = chat_completion(
            role_key=role_key,
            system=(
                "You repair malformed JSON for an automated runtime. "
                "Return one valid JSON object only. No markdown. No commentary."
            ),
            user=f"Original instruction:\n{system}\n\nMalformed response:\n{text}\n\nParse error:\n{exc}",
            max_tokens=max_tokens,
        )
        return parse_json_object(repair)


def parse_json_object(text: str) -> dict[str, Any]:
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

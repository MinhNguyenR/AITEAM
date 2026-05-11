from __future__ import annotations

import os
import importlib.util
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class MemoryApiDecision:
    allowed: bool
    reason: str = ""
    operation: str = ""
    role_key: str = ""
    model: str = ""
    input_tokens: int = 0
    estimated_cost_usd: float = 0.0


class MemoryCostGuard:
    """Fail-closed budget guard for paid memory API calls.

    This guard is intentionally process-local. It prevents accidental bursts in
    one CLI/runtime process while persistent usage rows remain the source of
    truth for dashboards.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._session_spend = 0.0
        self._daily_spend = 0.0
        self._daily_day = time.strftime("%Y-%m-%d")
        self._call_times: deque[float] = deque()

    def check(
        self,
        operation: str,
        *,
        role_key: str,
        model: str,
        input_tokens: int = 0,
        estimated_cost_usd: float | None = None,
        manual: bool = False,
    ) -> MemoryApiDecision:
        op = str(operation or "memory_api")
        role = str(role_key or "")
        cfg = get_memory_worker_config(role) or {}
        mdl = str(model or cfg.get("model") or "")
        tokens = max(0, int(input_tokens or 0))
        cost = float(estimated_cost_usd if estimated_cost_usd is not None else estimate_memory_cost_usd(role, mdl, tokens, op))
        mode = _env_choice("AI_TEAM_MEMORY_API_MODE", "auto", {"auto", "off", "manual", "always"})
        if mode == "off":
            return MemoryApiDecision(False, "memory api mode is off", op, role, mdl, tokens, cost)
        if mode == "manual" and not manual:
            return MemoryApiDecision(False, "memory api mode requires manual calls", op, role, mdl, tokens, cost)
        if not memory_openrouter_api_key():
            return MemoryApiDecision(False, "OPENROUTER_API_KEY is missing", op, role, mdl, tokens, cost)
        max_tokens = _env_int("AI_TEAM_MEMORY_MAX_INPUT_TOKENS_PER_CALL", 32_000, minimum=256)
        if tokens > max_tokens:
            return MemoryApiDecision(False, f"input tokens exceed memory max per call ({max_tokens})", op, role, mdl, tokens, cost)
        with self._lock:
            self._roll_daily_if_needed()
            now = time.time()
            while self._call_times and now - self._call_times[0] > 60:
                self._call_times.popleft()
            max_calls = _env_int("AI_TEAM_MEMORY_MAX_CALLS_PER_MINUTE", 20, minimum=1)
            if len(self._call_times) >= max_calls:
                return MemoryApiDecision(False, "memory api calls per minute exceeded", op, role, mdl, tokens, cost)
            daily_limit = _env_float("AI_TEAM_MEMORY_DAILY_USD_LIMIT", 0.25, minimum=0.0)
            session_limit = _env_float("AI_TEAM_MEMORY_SESSION_USD_LIMIT", 0.10, minimum=0.0)
            if daily_limit and self._daily_spend + cost > daily_limit:
                return MemoryApiDecision(False, "memory daily budget exceeded", op, role, mdl, tokens, cost)
            if session_limit and self._session_spend + cost > session_limit:
                return MemoryApiDecision(False, "memory session budget exceeded", op, role, mdl, tokens, cost)
            return MemoryApiDecision(True, "allowed", op, role, mdl, tokens, cost)

    def record(self, decision: MemoryApiDecision, *, status: str = "ok", cached: bool = False, metadata: dict[str, Any] | None = None) -> None:
        if decision.allowed and not cached and status == "ok":
            with self._lock:
                self._roll_daily_if_needed()
                self._session_spend += max(0.0, decision.estimated_cost_usd)
                self._daily_spend += max(0.0, decision.estimated_cost_usd)
                self._call_times.append(time.time())
        _append_memory_usage(decision, status=status, cached=cached, metadata=metadata or {})

    def _roll_daily_if_needed(self) -> None:
        today = time.strftime("%Y-%m-%d")
        if today != self._daily_day:
            self._daily_day = today
            self._daily_spend = 0.0


def get_memory_cost_guard() -> MemoryCostGuard:
    global _GUARD
    try:
        return _GUARD
    except NameError:
        _GUARD = MemoryCostGuard()
        return _GUARD


def estimate_tokens_local(text: str) -> int:
    raw = str(text or "")
    if not raw:
        return 0
    try:
        from core.storage._token_window import estimate_tokens

        return estimate_tokens(raw)
    except Exception:
        return max(1, len(raw) // 4)


def estimate_memory_cost_usd(role_key: str, model: str, input_tokens: int, operation: str = "") -> float:
    cfg = get_memory_worker_config(role_key) or {}
    pricing = cfg.get("pricing") or {}
    if "per_query" in pricing:
        return max(0.0, float(pricing.get("per_query") or 0.0))
    input_m = pricing.get("input")
    if input_m is not None:
        return max(0.0, int(input_tokens or 0) * float(input_m or 0.0) / 1_000_000)
    op = str(operation or "").lower()
    if "rerank" in op:
        return _env_float("AI_TEAM_RERANK_ESTIMATED_COST_USD", 0.002, minimum=0.0)
    if "embed" in op:
        return int(input_tokens or 0) * _env_float("AI_TEAM_EMBED_ESTIMATED_INPUT_PER_MILLION_USD", 0.10, minimum=0.0) / 1_000_000
    if "compact" in op or "settle" in op:
        return int(input_tokens or 0) * _env_float("AI_TEAM_COMPACT_ESTIMATED_INPUT_PER_MILLION_USD", 1.00, minimum=0.0) / 1_000_000
    return _env_float("AI_TEAM_MEMORY_ESTIMATED_CALL_USD", 0.001, minimum=0.0)


def _append_memory_usage(decision: MemoryApiDecision, *, status: str, cached: bool, metadata: dict[str, Any]) -> None:
    try:
        from utils.tracker import append_usage_log

        append_usage_log(
            {
                "agent": "Memory",
                "role_key": decision.role_key,
                "model": decision.model,
                "prompt_tokens": decision.input_tokens,
                "completion_tokens": 0,
                "total_tokens": decision.input_tokens,
                "cost_usd": decision.estimated_cost_usd if decision.allowed and not cached and status == "ok" else 0.0,
                "status": status,
                "action": decision.operation,
                "cached": cached,
                "reason": decision.reason,
                **{k: v for k, v in metadata.items() if k not in {"body", "documents", "prompt", "api_key"}},
            }
        )
    except Exception:
        return


def memory_openrouter_api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY", "")


def memory_openrouter_base_url() -> str:
    url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"openrouter.ai", "api.openrouter.ai"}:
        raise RuntimeError("OPENROUTER_BASE_URL is not allowed for memory API calls")
    return url


def memory_home() -> Path:
    return Path.home() / ".ai-team"


def get_memory_worker_config(role_key: str) -> dict[str, Any] | None:
    key = str(role_key or "").upper()
    root = Path(__file__).resolve().parents[2]
    registry_dir = root / "core" / "config" / "registry" / "coding"
    for filename in ("memory.py", "system.py"):
        path = registry_dir / filename
        try:
            spec = importlib.util.spec_from_file_location(f"_memory_guard_registry_{path.stem}", path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            registry = getattr(module, "REGISTRY", {})
            if isinstance(registry, dict) and isinstance(registry.get(key), dict):
                return dict(registry[key])
        except Exception:
            continue
    return None


def _env_choice(name: str, default: str, allowed: set[str]) -> str:
    value = os.getenv(name, "").strip().lower() or default
    return value if value in allowed else default


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return max(minimum, value)


def _env_float(name: str, default: float, *, minimum: float) -> float:
    raw = os.getenv(name, "").strip()
    try:
        value = float(raw) if raw else default
    except ValueError:
        value = default
    return max(minimum, value)


__all__ = [
    "MemoryApiDecision",
    "MemoryCostGuard",
    "estimate_memory_cost_usd",
    "estimate_tokens_local",
    "get_memory_worker_config",
    "get_memory_cost_guard",
    "memory_home",
    "memory_openrouter_api_key",
    "memory_openrouter_base_url",
]

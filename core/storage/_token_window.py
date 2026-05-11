from __future__ import annotations

import os
from typing import Any


SMALL_TEXT_FALLBACK_CHARS = 512


def estimate_tokens(text: str, *, model: str = "") -> int:
    raw = str(text or "")
    if not raw:
        return 0
    if len(raw) <= SMALL_TEXT_FALLBACK_CHARS:
        return max(1, len(raw) // 4)
    try:
        import tiktoken

        try:
            enc = tiktoken.encoding_for_model(model) if model else tiktoken.get_encoding("cl100k_base")
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(raw))
    except Exception:
        return max(1, len(raw) // 4)


def memory_budget_tokens(default: int = 600_000) -> int:
    raw = os.getenv("AI_TEAM_MEMORY_BUDGET_TOKENS", "").strip()
    try:
        return max(4096, int(raw)) if raw else default
    except ValueError:
        return default


def raw_compact_chunk_tokens(default: int = 50_000) -> int:
    raw = os.getenv("AI_TEAM_RAW_COMPACT_CHUNK_TOKENS", "").strip()
    try:
        return max(1000, int(raw)) if raw else default
    except ValueError:
        return default


def summary_budget_ratio(default: float = 0.20) -> float:
    raw = os.getenv("AI_TEAM_SUMMARY_BUDGET_RATIO", "").strip()
    try:
        value = float(raw) if raw else default
        return min(0.8, max(0.05, value))
    except ValueError:
        return default


def build_token_aware_window(
    messages: list[dict[str, Any]],
    summaries: list[dict[str, Any]] | None = None,
    *,
    budget: int | None = None,
    system_prompt_tokens: int = 0,
    model: str = "",
) -> list[dict[str, str]]:
    """Build oldest-to-newest context under budget using summaries + raw tail."""
    remaining = max(0, int(budget or memory_budget_tokens()) - int(system_prompt_tokens or 0))
    out_reversed: list[dict[str, str]] = []

    # Raw tail has priority.
    for msg in reversed(messages or []):
        role = str(msg.get("role") or "")
        if role not in {"user", "assistant", "system"}:
            continue
        content = str(msg.get("content") or "")
        cost = int(msg.get("token_count") or 0) or estimate_tokens(content, model=model)
        if cost > remaining and out_reversed:
            break
        if cost > remaining:
            content = content[-max(256, remaining * 4) :]
            cost = estimate_tokens(content, model=model)
        out_reversed.append({"role": role, "content": content})
        remaining -= cost
        if remaining <= 0:
            break

    summary_cap = int((budget or memory_budget_tokens()) * summary_budget_ratio())
    used_summary_tokens = 0
    summary_messages: list[dict[str, str]] = []
    for summary in summaries or []:
        body = str(summary.get("body") or "")
        if not body:
            continue
        cost = estimate_tokens(body, model=model)
        if used_summary_tokens + cost > summary_cap or cost > remaining:
            continue
        summary_messages.append({"role": "system", "content": f"[memory summary]\n{body}"})
        used_summary_tokens += cost
        remaining -= cost
        if remaining <= 0:
            break

    return summary_messages + list(reversed(out_reversed))


def total_message_tokens(messages: list[dict[str, Any]], *, model: str = "") -> int:
    return sum(int(m.get("token_count") or 0) or estimate_tokens(str(m.get("content") or ""), model=model) for m in messages)

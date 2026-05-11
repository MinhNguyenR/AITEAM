"""Rollups: by role/model, period usage, session summaries."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Dict, List

from .tracker_cache import cache_get, cache_set
from .tracker_helpers import parse_day, safe_float, safe_int
from .tracker_usage import read_usage_log


def aggregate_rows_by_role_model(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    m: Dict[tuple, Dict[str, Any]] = {}
    for r in rows:
        role = str(r.get("role_key") or r.get("agent") or "unknown")
        mod = str(r.get("model") or "")
        key = (role, mod)
        if key not in m:
            m[key] = {"role": role, "model": mod, "requests": 0, "tokens": 0, "cost": 0.0}
        b = m[key]
        b["requests"] += 1
        b["tokens"] += safe_int(r.get("total_tokens"))
        b["cost"] += safe_float(r.get("cost_usd"))
    return sorted(m.values(), key=lambda x: -x["tokens"])


def search_model_substring(rows: List[Dict[str, Any]], needle: str) -> List[Dict[str, Any]]:
    n = (needle or "").lower()
    if not n:
        return []
    agg: Dict[tuple, Dict[str, Any]] = {}
    for r in rows:
        mod = str(r.get("model") or "")
        if n not in mod.lower():
            continue
        role = str(r.get("role_key") or r.get("agent") or "unknown")
        k = (role, mod)
        if k not in agg:
            agg[k] = {"role": role, "model": mod, "requests": 0, "tokens": 0, "cost": 0.0}
        agg[k]["requests"] += 1
        agg[k]["tokens"] += safe_int(r.get("total_tokens"))
        agg[k]["cost"] += safe_float(r.get("cost_usd"))
    return sorted(agg.values(), key=lambda x: -x["tokens"])


def aggregate_role_detail(rows: List[Dict[str, Any]], role_name: str) -> List[Dict[str, Any]]:
    """Return per-model token breakdown for *role_name* (case-insensitive)."""
    needle = role_name.strip().lower()
    m: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        role = str(r.get("role_key") or r.get("agent") or "unknown")
        if role.lower() != needle:
            continue
        mod = str(r.get("model") or "")
        if mod not in m:
            m[mod] = {
                "model": mod,
                "requests": 0,
                "input_tokens": 0,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
            }
        b = m[mod]
        b["requests"] += 1
        b["input_tokens"] += safe_int(r.get("prompt_tokens"))
        b["cache_read_tokens"] += safe_int(r.get("cache_read_tokens"))
        b["cache_write_tokens"] += safe_int(r.get("cache_write_tokens"))
        b["output_tokens"] += safe_int(r.get("completion_tokens"))
        b["cost"] += safe_float(r.get("cost_usd"))
    return sorted(m.values(), key=lambda x: -x["requests"])


def rows_for_summary_period(period: str) -> List[Dict[str, Any]]:
    cache_key = f"summary_period:{period or 'session'}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    rows = read_usage_log(last_n=8000)
    if not rows:
        return []
    p = (period or "session").lower()
    if p == "today":
        today = date.today()
        result = [r for r in rows if parse_day(str(r.get("timestamp", ""))) == today]
        return cache_set(cache_key, result)
    return cache_set(cache_key, rows)


def aggregate_usage_by_role(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_role: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        rk = str(r.get("role_key") or r.get("agent") or "unknown").strip() or "unknown"
        mid = str(r.get("model") or "")
        if rk not in by_role:
            by_role[rk] = {
                "requests": 0,
                "tokens": 0,
                "cost_usd": 0.0,
                "context_tokens_est": 0,
                "by_model": defaultdict(lambda: {"requests": 0, "tokens": 0, "cost_usd": 0.0}),
            }
        br = by_role[rk]
        toks = safe_int(r.get("total_tokens"))
        cost = safe_float(r.get("cost_usd"))
        br["requests"] += 1
        br["tokens"] += toks
        br["cost_usd"] += cost
        br["context_tokens_est"] += toks
        bm = br["by_model"][mid]
        bm["requests"] += 1
        bm["tokens"] += toks
        bm["cost_usd"] += cost
    for br in by_role.values():
        br["by_model"] = dict(br["by_model"])
    return by_role


def build_usage_summary(period: str = "session") -> Dict[str, Any]:
    cache_key = f"build_summary:{period or 'session'}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    rows = rows_for_summary_period(period)
    total_requests = len(rows)
    total_tokens = sum(safe_int(r.get("total_tokens")) for r in rows)
    total_cost = sum(safe_float(r.get("cost_usd")) for r in rows)
    by_role = aggregate_usage_by_role(rows)
    return cache_set(
        cache_key,
        {
            "period": period,
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "by_role": by_role,
        },
    )


def get_local_stats(for_today: bool = False) -> Dict[str, Any]:
    rows = read_usage_log(last_n=5000)
    if not rows:
        return {"total_requests": 0, "total_tokens": 0, "total_cost": 0.0, "by_agent": {}}

    today = date.today()
    selected = []
    for row in rows:
        if not for_today:
            selected.append(row)
            continue
        d = parse_day(str(row.get("timestamp", "")))
        if d == today:
            selected.append(row)

    total_requests = len(selected)
    total_tokens = sum(safe_int(r.get("total_tokens")) for r in selected)
    total_cost = sum(safe_float(r.get("cost_usd")) for r in selected)
    by_agent: Dict[str, Dict[str, Any]] = {}
    for r in selected:
        agent = str(r.get("role_key") or r.get("agent") or "unknown")
        if agent not in by_agent:
            by_agent[agent] = {"requests": 0, "tokens": 0, "cost": 0.0, "model": r.get("model", "")}
        by_agent[agent]["requests"] += 1
        by_agent[agent]["tokens"] += safe_int(r.get("total_tokens"))
        by_agent[agent]["cost"] += safe_float(r.get("cost_usd"))
    return {
        "total_requests": total_requests,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "by_agent": by_agent,
    }


def get_period_usage() -> Dict[str, Dict[str, float]]:
    rows = read_usage_log(last_n=5000)
    today = date.today()
    month_key = (today.year, today.month)
    year_key = today.year
    out = {
        "daily": {"requests": 0, "tokens": 0, "spend": 0.0},
        "monthly": {"requests": 0, "tokens": 0, "spend": 0.0},
        "yearly": {"requests": 0, "tokens": 0, "spend": 0.0},
    }
    for r in rows:
        d = parse_day(str(r.get("timestamp", "")))
        if d is None:
            continue
        if d == today:
            out["daily"]["requests"] += 1
            out["daily"]["tokens"] += safe_int(r.get("total_tokens"))
            out["daily"]["spend"] += safe_float(r.get("cost_usd"))
        if (d.year, d.month) == month_key:
            out["monthly"]["requests"] += 1
            out["monthly"]["tokens"] += safe_int(r.get("total_tokens"))
            out["monthly"]["spend"] += safe_float(r.get("cost_usd"))
        if d.year == year_key:
            out["yearly"]["requests"] += 1
            out["yearly"]["tokens"] += safe_int(r.get("total_tokens"))
            out["yearly"]["spend"] += safe_float(r.get("cost_usd"))
    return out

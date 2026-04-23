"""Single source of truth for usage export (TXT/PDF/XLSX)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from utils import tracker

from ..tui.utils import default_range, safe_float, safe_int
from .state import DashboardRangeState


@dataclass
class RoleAgg:
    role: str
    requests: int
    tokens: int
    cost_usd: float


@dataclass
class RoleModelAgg:
    role: str
    model: str
    requests: int
    tokens: int
    cost_usd: float


@dataclass
class UsageReport:
    label: str
    since: datetime | None
    until: datetime | None
    generated_at: datetime
    total_requests: int
    total_tokens: int
    total_spend: float
    prompt_tokens: int
    completion_tokens: int
    cli_turns: int
    by_role: list[RoleAgg]
    by_role_model: list[RoleModelAgg]
    batches: list[dict[str, Any]]
    raw_rows: list[dict[str, Any]]
    period_summary: dict[str, dict[str, Any]]
    batch_display_limit: int = 40
    raw_display_note: str = ""


def build_usage_report(
    range_state: DashboardRangeState,
    *,
    batch_limit: int = 40,
    fill_rows_if_empty: bool = True,
) -> UsageReport:
    since = range_state.since
    until = range_state.until
    if since is None or until is None:
        since, until = default_range()
    label = str(range_state.label or "")
    batches = tracker.summarize_tokens_by_cli_batches(since, until)
    rows_all: list[dict[str, Any]] = list(range_state.rows or [])
    if fill_rows_if_empty and not rows_all:
        rows_all = tracker.read_usage_rows_timerange(since, until)

    tot_r = len(rows_all)
    tot_t = sum(safe_int(r.get("total_tokens")) for r in rows_all)
    tot_c = sum(safe_float(r.get("cost_usd")) for r in rows_all)
    io_all = tracker.token_io_totals(rows_all)

    role_map: dict[str, dict[str, float | int]] = {}
    for r in rows_all:
        role = str(r.get("role_key") or r.get("agent") or "unknown")
        if role not in role_map:
            role_map[role] = {"requests": 0, "tokens": 0, "cost": 0.0}
        role_map[role]["requests"] = int(role_map[role]["requests"]) + 1
        role_map[role]["tokens"] = int(role_map[role]["tokens"]) + safe_int(r.get("total_tokens"))
        role_map[role]["cost"] = float(role_map[role]["cost"]) + safe_float(r.get("cost_usd"))

    by_role = [
        RoleAgg(role=k, requests=int(v["requests"]), tokens=int(v["tokens"]), cost_usd=float(v["cost"]))
        for k, v in sorted(role_map.items(), key=lambda x: (-int(x[1]["tokens"]), str(x[0])))
    ]

    agg_rm: dict[tuple[str, str], dict[str, float | int]] = {}
    for r in rows_all:
        role = str(r.get("role_key") or r.get("agent") or "unknown")
        model = str(r.get("model") or "(unknown)")
        key = (role, model)
        if key not in agg_rm:
            agg_rm[key] = {"requests": 0, "tokens": 0, "cost_usd": 0.0}
        agg_rm[key]["requests"] = int(agg_rm[key]["requests"]) + 1
        agg_rm[key]["tokens"] = int(agg_rm[key]["tokens"]) + int(r.get("total_tokens", 0) or 0)
        agg_rm[key]["cost_usd"] = float(agg_rm[key]["cost_usd"]) + float(r.get("cost_usd", 0.0) or 0.0)

    by_role_model = [
        RoleModelAgg(
            role=k[0],
            model=k[1],
            requests=int(v["requests"]),
            tokens=int(v["tokens"]),
            cost_usd=float(v["cost_usd"]),
        )
        for k, v in sorted(agg_rm.items(), key=lambda x: (-int(x[1]["tokens"]), str(x[0][0]), str(x[0][1])))
    ]

    raw_note = ""
    if len(rows_all) > 5000:
        raw_note = f"(export lists up to 5000 raw rows in XLSX; total in range: {len(rows_all)})"

    return UsageReport(
        label=label,
        since=since,
        until=until,
        generated_at=datetime.now(),
        total_requests=tot_r,
        total_tokens=tot_t,
        total_spend=tot_c,
        prompt_tokens=int(io_all.get("prompt_tokens", 0)),
        completion_tokens=int(io_all.get("completion_tokens", 0)),
        cli_turns=len(batches),
        by_role=by_role,
        by_role_model=by_role_model,
        batches=batches[:batch_limit],
        raw_rows=rows_all[:5000],
        period_summary=tracker.get_period_usage(),
        batch_display_limit=batch_limit,
        raw_display_note=raw_note,
    )

"""Helpers for workflow Textual monitor: pipeline state, checkpoints, notifications."""
from __future__ import annotations

import re
from typing import Any

from core.bootstrap import REPO_ROOT
from core.config import config  # re-exported for callers that patch via helpers.config
from core.orchestration import get_graph

from ...runtime.persist.activity_log import format_activity_lines, list_recent_activity
from ...runtime.persist.checkpointer import get_checkpointer
from ...runtime import session as ws

from ._pipeline_meta import (
    PIPELINE_LEADER, PIPELINE_HARD,
    _steps_for_tier, _registry_key_for_step,
    _display_name, _role_subtitle, _model_for_step,
    _pipeline_info_lines, _STEP_LABEL, _SPINNER_CHARS,
    _node_status_icon, _first_graph_step_id,
    _compute_visual_states, _build_pipeline_markup,
)

TOKEN_WARN_THRESHOLD = 262_000


def _project_root_default() -> str:
    r = ws.get_workflow_project_root()
    return r if r else str(REPO_ROOT)


def _activity_min_ts_kw() -> float | None:
    mt = ws.get_workflow_activity_min_ts()
    return mt if mt > 0 else None


def _event_sequence_warning() -> str:
    recs = list_recent_activity(limit=120, min_ts=_activity_min_ts_kw())
    has_state = any(str(r.get("action", "")) == "state_json_written" for r in recs)
    has_enter = any(
        str(r.get("node", "")) == "leader_generate"
        and str(r.get("action", "")) in {"enter", "leader_generate_failed", "context_written"}
        for r in recs
    )
    if has_state and not has_enter:
        return "warning: state.json written but leader_generate event missing"
    return ""


_FILE_ACTIONS = frozenset({"context_written", "state_json_written", "artifact_written"})


def _parse_token_counts() -> tuple[int, int]:
    """Return (prompt_tokens, completion_tokens) from the latest usage event (any node)."""
    mt = _activity_min_ts_kw()
    records = list_recent_activity(limit=100, min_ts=mt if mt and mt > 0 else None)
    for r in reversed(records):
        if str(r.get("action")) == "usage":
            detail = str(r.get("detail", ""))
            pt_m = re.search(r"prompt_tokens=(\d+)", detail)
            ct_m = re.search(r"completion_tokens=(\d+)", detail)
            if pt_m or ct_m:
                return (int(pt_m.group(1)) if pt_m else 0,
                        int(ct_m.group(1)) if ct_m else 0)
    return (0, 0)


def _parse_token_counts_for_node(node: str) -> tuple[int, int]:
    """Return (prompt_tokens, completion_tokens) for a specific node."""
    mt = _activity_min_ts_kw()
    records = list_recent_activity(limit=200, min_ts=mt if mt and mt > 0 else None)
    for r in reversed(records):
        if str(r.get("node", "")) == node and str(r.get("action")) == "usage":
            detail = str(r.get("detail", ""))
            pt_m = re.search(r"prompt_tokens=(\d+)", detail)
            ct_m = re.search(r"completion_tokens=(\d+)", detail)
            if pt_m or ct_m:
                return (int(pt_m.group(1)) if pt_m else 0,
                        int(ct_m.group(1)) if ct_m else 0)
    return (0, 0)


def _parse_file_events() -> list[tuple[str, str, str]]:
    """Return (node, action, detail) for file-write events."""
    mt = _activity_min_ts_kw()
    records = list_recent_activity(limit=100, min_ts=mt if mt and mt > 0 else None)
    return [
        (str(r.get("node", "")), str(r.get("action", "")), str(r.get("detail", ""))[:100])
        for r in records
        if str(r.get("action", "")) in _FILE_ACTIONS
    ]


def _info_list_lines(
    snap: dict, spin_idx: int,
    completed_nodes: set | None = None,
) -> list[str]:
    """Vertical list of pipeline nodes for LIST mode /info."""
    tier = snap.get("brief_tier")
    active = str(snap.get("active_step") or "idle")
    lines: list[str] = ["[dim]-- pipeline nodes ----------------------------------[/dim]"]

    timeline = ws.get_workflow_list_timeline()
    seen: list[str] = []
    for evt in timeline:
        n = str(evt.get("node") or "")
        if n and n not in seen:
            seen.append(n)
    if completed_nodes:
        for cn in ("ambassador", "leader_generate", "human_context_gate", "tool_curator",
                   "worker", "restore_worker", "secretary", "finalize_phase1"):
            if cn in completed_nodes and cn not in seen:
                seen.append(cn)
    all_steps = _steps_for_tier(tier) if tier else ["ambassador"]
    for s in all_steps:
        if s not in seen:
            seen.append(s)

    for node in seen:
        icon   = _node_status_icon(node, snap, spin_idx, completed_nodes)
        label  = _STEP_LABEL.get(node, node)
        pt, ct = _parse_token_counts_for_node(node)
        if pt or ct:
            tok = f"  [dim]in:{pt:,} out:{ct:,}[/dim]"
        elif node == active:
            tok = "  [dim]streaming...[/dim]"
        else:
            tok = ""
        role = _display_name(node, tier)
        lines.append(f"  {icon} [bold]{role:<16}[/bold] {label}{tok}")
    return lines


def _info_chain_lines(
    snap: dict, spin_idx: int,
    completed_nodes: set | None = None,
) -> list[str]:
    """Horizontal chain visualization for CHAIN mode /info."""
    tier = snap.get("brief_tier")
    lines: list[str] = ["[dim]-- pipeline nodes ----------------------------------[/dim]"]

    timeline = ws.get_workflow_list_timeline()
    seen: list[str] = []
    for evt in timeline:
        n = str(evt.get("node") or "")
        if n and n not in seen:
            seen.append(n)
    if completed_nodes:
        for cn in ("ambassador", "leader_generate", "human_context_gate", "tool_curator",
                   "worker", "restore_worker", "secretary", "finalize_phase1"):
            if cn in completed_nodes and cn not in seen:
                seen.append(cn)
    all_steps = _steps_for_tier(tier) if tier else ["ambassador"]
    for s in all_steps:
        if s not in seen:
            seen.append(s)

    parts = []
    for node in seen:
        icon  = _node_status_icon(node, snap, spin_idx, completed_nodes)
        label = _display_name(node, tier)
        parts.append(f"[{icon} {label}]")
    chain_line = " [dim]---[/dim] ".join(parts)
    lines.append(f"  {chain_line}")
    lines.append("")

    active = str(snap.get("active_step") or "idle")
    for node in seen:
        icon  = _node_status_icon(node, snap, spin_idx, completed_nodes)
        label = _STEP_LABEL.get(node, node)
        pt, ct = _parse_token_counts_for_node(node)
        if pt or ct:
            tok = f"  [dim]in:{pt:,}  out:{ct:,}[/dim]"
        elif node == active:
            tok = "  [dim]streaming...[/dim]"
        else:
            tok = ""
        lines.append(f"  {icon} {label}{tok}")
    return lines


def _checkpoint_blocks(needle: str) -> list[str]:
    tid = ws.get_thread_id()
    needle_l = needle.lower().strip()
    blocks: list[str] = []
    act_lines = format_activity_lines(list_recent_activity(limit=400, min_ts=_activity_min_ts_kw()), needle)
    if act_lines:
        blocks.append("[bold]-- Activity log --[/bold]\n" + "\n".join(act_lines[-80:]))
    if not tid:
        blocks.append("No thread_id -- run agent first.")
        return blocks
    try:
        ib = ws.get_interrupt_before()
        graph = get_graph(get_checkpointer(), interrupt_before=ib if ib else ())
        cfg = {"configurable": {"thread_id": tid}}
        hist = list(graph.get_state_history(cfg))
    except (OSError, RuntimeError, ValueError, TypeError) as e:
        blocks.append(f"Checkpoint error: {e}")
        return blocks
    ck_lines = 0
    for idx, h in enumerate(hist):
        next_n = getattr(h, "next", None)
        vals   = getattr(h, "values", None) or {}
        meta   = getattr(h, "metadata", None)
        keys   = ",".join(sorted(str(k) for k in vals.keys()))
        brief  = vals.get("brief_dict") if isinstance(vals, dict) else {}
        task_id = str(brief.get("task_uuid") or "") if isinstance(brief, dict) else ""
        ctx_path = str(vals.get("context_path") or "") if isinstance(vals, dict) else ""
        body = f"task_id={task_id or '-'} context_path={ctx_path or '-'} keys=[{keys}]"
        if needle_l:
            hay = f"{next_n} {body}".lower()
            if needle_l not in hay:
                continue
        ck_lines += 1
        extra = f" meta={meta}" if meta else ""
        blocks.append(f"[bold]#{idx}[/bold] next={next_n}{extra}\n{body}\n[dim]---[/dim]")
    if needle_l and ck_lines == 0:
        blocks.append("No matching checkpoint.")
    return blocks if blocks else ["No data."]


def _match_notification_id(prefix: str) -> str | None:
    prefix = prefix.strip().lower()
    if not prefix:
        return None
    for n in ws.list_active_notifications():
        nid = str(n.get("id", ""))
        if nid.lower() == prefix or nid.lower().startswith(prefix):
            return nid
    return None

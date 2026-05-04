"""Helpers for workflow Textual monitor: pipeline state, checkpoints, notifications."""

from __future__ import annotations

import re
from typing import Any

from agents.team_map._team_map import get_graph
from core.bootstrap import REPO_ROOT
from core.config import config
from core.domain.routing_map import pipeline_nodes_for_tier, pipeline_registry_key_for_tier

from ...runtime.persist.activity_log import format_activity_lines, list_recent_activity
from ...runtime.persist.checkpointer import get_checkpointer
from ...runtime.present.pipeline_markdown import build_pipeline_markup as _build_pipeline_markup_core
from ...runtime import session as ws

PIPELINE_LEADER = pipeline_nodes_for_tier("MEDIUM")
PIPELINE_HARD   = pipeline_nodes_for_tier("HARD")

TOKEN_WARN_THRESHOLD = 262_000


def _project_root_default() -> str:
    r = ws.get_workflow_project_root()
    return r if r else str(REPO_ROOT)


def _activity_min_ts_kw() -> float | None:
    mt = ws.get_workflow_activity_min_ts()
    return mt if mt > 0 else None


def _steps_for_tier(tier: str | None) -> list[str]:
    return pipeline_nodes_for_tier(tier)


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


def _display_name(step_id: str, tier: str | None = None) -> str:
    if step_id in ("leader_generate", "tool_curator"):
        key = _registry_key_for_step(step_id, tier)
        if key:
            role = str((config.get_worker(key) or {}).get("role", "") or "")
            if role:
                return role
    return {
        "ambassador":         "Ambassador",
        "leader_generate":    "Leader",
        "human_context_gate": "Review",
        "tool_curator":       "Tool Curator",
        "finalize_phase1":    "Finalize",
    }.get(step_id, step_id)


def _registry_key_for_step(step_id: str, tier: str | None) -> str | None:
    if step_id == "ambassador":
        return "AMBASSADOR"
    if step_id == "leader_generate":
        return pipeline_registry_key_for_tier(tier or "MEDIUM")
    if step_id == "tool_curator":
        return "TOOL_CURATOR"
    return None


def _role_subtitle(step_id: str, tier: str | None, selected_leader: str) -> str:
    key = _registry_key_for_step(step_id, tier)
    if key:
        cfg = config.get_worker(key) or {}
        return str(cfg.get("role", key))
    if step_id == "human_context_gate":
        return "Human review context.md"
    if step_id == "tool_curator":
        return "Tool selection + tools.md"
    if step_id == "finalize_phase1":
        return "Cleanup + state"
    return ""


def _model_for_step(step_id: str, tier: str | None) -> str:
    """Return short model name for a pipeline step (for display)."""
    key = _registry_key_for_step(step_id, tier)
    if not key:
        return ""
    cfg = config.get_worker(key) or {}
    model = str(cfg.get("model", "") or "")
    if not model:
        return ""
    # Short name: last segment after / (e.g. claude-3-5-sonnet-20241022)
    short = model.rsplit("/", 1)[-1] if "/" in model else model
    # Further shorten: remove date suffix if long
    parts = short.rsplit("-", 1)
    if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 8:
        short = parts[0]
    return short


def _pipeline_info_lines(tier: str | None, steps: list[str]) -> list[str]:
    """Build info lines: role  registry-key  model  reason  for all steps."""
    lines: list[str] = [
        f"[dim]── Pipeline Info  Tier {tier or '—'} ──[/dim]"
    ]
    for sid in steps:
        key   = _registry_key_for_step(sid, tier)
        role  = _display_name(sid, tier)
        model = _model_for_step(sid, tier)
        reason = ""
        if key:
            cfg    = config.get_worker(key) or {}
            reason = str(cfg.get("reason", "") or "")
        if key and model:
            lines.append(
                f"  [bold]{role:<14}[/bold]"
                f"  [dim]{key:<16}[/dim]"
                f"  [cyan]{model}[/cyan]"
            )
        elif key:
            lines.append(f"  [bold]{role:<14}[/bold]  [dim]{key}[/dim]")
        else:
            lines.append(f"  [bold]{role:<14}[/bold]  [dim](no model)[/dim]")
        if reason:
            lines.append(f"  [dim]  └─ {reason}[/dim]")
    return lines


_STEP_LABEL: dict[str, str] = {
    "ambassador":         "Generate state.json",
    "leader_generate":    "Generate context.md",
    "human_context_gate": "Review context.md",
    "tool_curator":       "Generate tools.md",
    "finalize_phase1":    "Finalize pipeline",
}

_SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def _node_status_icon(
    node: str, snap: dict, spin_idx: int,
    completed_nodes: set | None = None,
) -> str:
    """Return one-char status icon for a node from snapshot."""
    sc = _SPINNER_CHARS[spin_idx % len(_SPINNER_CHARS)]
    amb = str(snap.get("ambassador_status") or "idle")
    active = str(snap.get("active_step") or "idle")
    failed = bool(snap.get("graph_failed"))
    finished = bool(snap.get("run_finished"))
    paused = bool(snap.get("paused_at_gate"))

    if node == "ambassador":
        if amb == "running": return f"[#888888]{sc}[/#888888]"
        if amb == "done":    return "[bold green]●[/bold green]"
        if amb == "error":   return "[bold red]✗[/bold red]"
        if completed_nodes and "ambassador" in completed_nodes:
            return "[bold green]●[/bold green]"
        return "[dim]○[/dim]"

    tier = snap.get("brief_tier")
    if amb != "done" or not tier:
        if completed_nodes and node in completed_nodes:
            return "[bold green]●[/bold green]"
        return "[dim]○[/dim]"

    if node == active:
        if failed: return "[bold red]✗[/bold red]"
        return f"[#888888]{sc}[/#888888]"
    if node == "human_context_gate" and paused:
        return f"[#888888]{sc}[/#888888]"
    # Check if node appears BEFORE current active in the standard sequence
    order = ["ambassador", "leader_generate", "human_context_gate", "tool_curator", "finalize_phase1"]
    if node in order and active in order:
        ni, ai = order.index(node), order.index(active)
        if ni < ai:
            return "[bold green]●[/bold green]"
        if ni == ai and finished:
            return "[bold green]●[/bold green]"
    if finished and not failed:
        return "[bold green]●[/bold green]"
    # Fallback: TUI-injected completed_nodes (survives reset_pipeline_visual)
    if completed_nodes and node in completed_nodes:
        return "[bold green]●[/bold green]"
    # Also check workflow_list_nodes_state in snapshot
    for ns in (snap.get("workflow_list_nodes_state") or []):
        if isinstance(ns, dict) and str(ns.get("node")) == node:
            st = str(ns.get("status") or "")
            if st == "done":   return "[bold green]●[/bold green]"
            if st in ("error", "failed"): return "[bold red]✗[/bold red]"
            break
    return "[dim]○[/dim]"


def _info_list_lines(
    snap: dict, spin_idx: int,
    completed_nodes: set | None = None,
) -> list[str]:
    """Vertical list of pipeline nodes for LIST mode /info."""
    tier = snap.get("brief_tier")
    active = str(snap.get("active_step") or "idle")
    lines: list[str] = ["[dim]── pipeline nodes ──────────────────────────────────[/dim]"]

    # Determine which nodes have appeared so far
    timeline = ws.get_workflow_list_timeline()
    seen: list[str] = []
    for evt in timeline:
        n = str(evt.get("node") or "")
        if n and n not in seen:
            seen.append(n)
    # Include completed nodes even if timeline was reset
    if completed_nodes:
        for cn in ("ambassador", "leader_generate", "human_context_gate", "tool_curator", "finalize_phase1"):
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
            tok = "  [dim]streaming…[/dim]"
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
    lines: list[str] = ["[dim]── pipeline nodes ──────────────────────────────────[/dim]"]

    timeline = ws.get_workflow_list_timeline()
    seen: list[str] = []
    for evt in timeline:
        n = str(evt.get("node") or "")
        if n and n not in seen:
            seen.append(n)
    if completed_nodes:
        for cn in ("ambassador", "leader_generate", "human_context_gate", "tool_curator", "finalize_phase1"):
            if cn in completed_nodes and cn not in seen:
                seen.append(cn)
    all_steps = _steps_for_tier(tier) if tier else ["ambassador"]
    for s in all_steps:
        if s not in seen:
            seen.append(s)

    # Build horizontal chain: [icon Role] ─── [icon Role] ─── ...
    parts = []
    for node in seen:
        icon  = _node_status_icon(node, snap, spin_idx, completed_nodes)
        label = _display_name(node, tier)
        parts.append(f"[{icon} {label}]")
    chain_line = " [dim]───[/dim] ".join(parts)
    lines.append(f"  {chain_line}")
    lines.append("")

    # Detail per node
    active = str(snap.get("active_step") or "idle")
    for node in seen:
        icon  = _node_status_icon(node, snap, spin_idx, completed_nodes)
        label = _STEP_LABEL.get(node, node)
        pt, ct = _parse_token_counts_for_node(node)
        if pt or ct:
            tok = f"  [dim]in:{pt:,}  out:{ct:,}[/dim]"
        elif node == active:
            tok = "  [dim]streaming…[/dim]"
        else:
            tok = ""
        lines.append(f"  {icon} {label}{tok}")
    return lines


def _first_graph_step_id(tier: str | None) -> str:
    return "leader_generate"


def _compute_visual_states(
    steps: list[str],
    snap: dict[str, Any],
    last_node: str | None,
    now: float,
) -> dict[str, str]:
    amb           = snap["ambassador_status"]
    tier          = snap["brief_tier"]
    active        = snap["active_step"]
    paused        = snap["paused_at_gate"]
    finished      = snap["run_finished"]
    failed        = snap["graph_failed"]
    accept_status = str(snap.get("context_accept_status") or "none")
    busy_ts       = float(snap.get("busy_ts") or 0.0)

    out: dict[str, str] = {}
    for i, sid in enumerate(steps):
        if sid == "ambassador":
            if   amb == "running": out[sid] = "spin"
            elif amb == "error":   out[sid] = "error"
            elif amb == "done" or tier: out[sid] = "done"
            else: out[sid] = "pending"
            continue

        if amb != "done" or not tier:
            out[sid] = "pending"
            continue

        if finished and not failed and accept_status in {"accepted", "none"}:
            out[sid] = "done"; continue
        if finished and not failed and accept_status == "deferred":
            out[sid] = "wait" if sid == "human_context_gate" else ("pending" if sid == "finalize_phase1" else "done")
            continue
        if failed:
            ln = last_node or _first_graph_step_id(tier)
            if ln == "end_failed":
                ln = _first_graph_step_id(tier)
            fail_idx = steps.index(ln) if ln in steps else -1
            if fail_idx < 0:
                fail_idx = steps.index(_first_graph_step_id(tier)) if _first_graph_step_id(tier) in steps else 1
            if i < fail_idx:   out[sid] = "done"
            elif i == fail_idx: out[sid] = "error"
            else:               out[sid] = "pending"
            continue
        if paused and "human_context_gate" in steps:
            gi = steps.index("human_context_gate")
            if i < gi:   out[sid] = "done"
            elif i == gi: out[sid] = "wait"
            else:         out[sid] = "pending"
            continue
        if active in steps:
            j = steps.index(active)
            if i < j:    out[sid] = "done"
            elif i == j: out[sid] = "spin"
            else:        out[sid] = "pending"
        else:
            if active == "idle" and amb == "done" and tier and not finished and not failed and len(steps) > 1:
                fg = steps[1]
                try:
                    clarif_wait = ws.is_clarification_pending()
                except Exception:
                    clarif_wait = False
                if clarif_wait:
                    out[sid] = "wait" if sid == fg else "pending"
                elif (now - busy_ts) < 30.0:
                    out[sid] = "spin" if sid == fg else "pending"
                else:
                    out[sid] = "pending"
            else:
                out[sid] = "pending"
    return out


_FILE_ACTIONS = frozenset({"context_written", "state_json_written", "artifact_written"})


def _parse_token_counts() -> tuple[int, int]:
    """Return (prompt_tokens, completion_tokens) from the LATEST usage event (any node)."""
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
    """Return (prompt_tokens, completion_tokens) for a specific node (per-role tracking)."""
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
    """Return (node, action, detail) for file-write events — detail is raw path (callers must not display it)."""
    mt = _activity_min_ts_kw()
    records = list_recent_activity(limit=100, min_ts=mt if mt and mt > 0 else None)
    return [
        (str(r.get("node", "")), str(r.get("action", "")), str(r.get("detail", ""))[:100])
        for r in records
        if str(r.get("action", "")) in _FILE_ACTIONS
    ]


def _build_pipeline_markup(
    steps: list[str],
    states: dict[str, str],
    tier: str | None,
    selected_leader: str,
    spin_idx: int,
    active_detail: str | None = None,
) -> str:
    return _build_pipeline_markup_core(
        steps, states, tier, selected_leader, spin_idx,
        _display_name, _role_subtitle,
        active_detail=active_detail,
    )


def _checkpoint_blocks(needle: str) -> list[str]:
    tid = ws.get_thread_id()
    needle_l = needle.lower().strip()
    blocks: list[str] = []
    act_lines = format_activity_lines(list_recent_activity(limit=400, min_ts=_activity_min_ts_kw()), needle)
    if act_lines:
        blocks.append("[bold]-- Activity log --[/bold]\n" + "\n".join(act_lines[-80:]))
    if not tid:
        blocks.append("No thread_id — run agent first.")
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

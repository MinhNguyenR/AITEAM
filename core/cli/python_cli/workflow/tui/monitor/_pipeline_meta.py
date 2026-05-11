"""Pipeline structure and visual state: step labels, icons, node ordering, visual states."""
from __future__ import annotations

from typing import Any

from core.config import config
from core.domain.routing_map import pipeline_nodes_for_tier, pipeline_registry_key_for_tier
from ...runtime.present.pipeline_markdown import build_pipeline_markup as _build_pipeline_markup_core
from ...runtime import session as ws


PIPELINE_LEADER = pipeline_nodes_for_tier("MEDIUM")
PIPELINE_HARD   = pipeline_nodes_for_tier("HARD")


def _steps_for_tier(tier: str | None) -> list[str]:
    return pipeline_nodes_for_tier(tier)


def _registry_key_for_step(step_id: str, tier: str | None) -> str | None:
    if step_id == "ambassador":
        return "AMBASSADOR"
    if step_id == "leader_generate":
        return pipeline_registry_key_for_tier(tier or "MEDIUM")
    if step_id == "tool_curator":
        return "TOOL_CURATOR"
    if step_id in ("worker", "restore_worker"):
        return "WORKER_A"
    if step_id == "secretary":
        return "SECRETARY"
    return None


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
        "worker":             "Worker",
        "restore_worker":     "Worker Restore",
        "secretary":          "Secretary",
        "finalize_phase1":    "Finalize",
    }.get(step_id, step_id)


def _role_subtitle(step_id: str, tier: str | None, selected_leader: str) -> str:
    key = _registry_key_for_step(step_id, tier)
    if key:
        cfg = config.get_worker(key) or {}
        return str(cfg.get("role", key))
    if step_id == "human_context_gate":
        return "Human review context.md"
    if step_id == "tool_curator":
        return "Tool selection + tools.md"
    if step_id == "worker":
        return "Code implementation"
    if step_id == "restore_worker":
        return "Restore from backup"
    if step_id == "secretary":
        return "Validation commands"
    if step_id == "finalize_phase1":
        return "Cleanup + state"
    return ""


def _model_for_step(step_id: str, tier: str | None) -> str:
    key = _registry_key_for_step(step_id, tier)
    if not key:
        return ""
    cfg = config.get_worker(key) or {}
    model = str(cfg.get("model", "") or "")
    if not model:
        return ""
    short = model.rsplit("/", 1)[-1] if "/" in model else model
    parts = short.rsplit("-", 1)
    if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 8:
        short = parts[0]
    return short


def _pipeline_info_lines(tier: str | None, steps: list[str]) -> list[str]:
    lines: list[str] = [f"[dim]-- Pipeline Info  Tier {tier or '--'} --[/dim]"]
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
            lines.append(f"  [dim]  └- {reason}[/dim]")
    return lines


_STEP_LABEL: dict[str, str] = {
    "ambassador":         "Generate state.json",
    "leader_generate":    "Generate context.md",
    "human_context_gate": "Review context.md",
    "tool_curator":       "Generate tools.md",
    "worker":             "Implement code changes",
    "restore_worker":     "Restore code backup",
    "secretary":          "Run validation commands",
    "finalize_phase1":    "Finalize pipeline",
}

_SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

_NODE_ORDER = ["ambassador", "leader_generate", "human_context_gate", "tool_curator",
               "worker", "restore_worker", "secretary", "finalize_phase1"]


def _node_status_icon(
    node: str, snap: dict, spin_idx: int,
    completed_nodes: set | None = None,
) -> str:
    sc = _SPINNER_CHARS[spin_idx % len(_SPINNER_CHARS)]
    amb = str(snap.get("ambassador_status") or "idle")
    active = str(snap.get("active_step") or "idle")
    failed = bool(snap.get("graph_failed"))
    finished = bool(snap.get("run_finished"))
    paused = bool(snap.get("paused_at_gate"))

    if node == "ambassador":
        if amb == "running": return f"[#888888]{sc}[/#888888]"
        if amb == "done":    return "[bold green]✔[/bold green]"
        if amb == "error":   return "[bold red]✘[/bold red]"
        if completed_nodes and "ambassador" in completed_nodes:
            return "[bold green]✔[/bold green]"
        return "[dim]○[/dim]"

    tier = snap.get("brief_tier")
    if amb != "done" or not tier:
        if completed_nodes and node in completed_nodes:
            return "[bold green]✔[/bold green]"
        return "[dim]○[/dim]"

    if node == active:
        if failed: return "[bold red]✘[/bold red]"
        return f"[#888888]{sc}[/#888888]"
    if node == "human_context_gate" and paused:
        return f"[#888888]{sc}[/#888888]"
    if node in _NODE_ORDER and active in _NODE_ORDER:
        ni, ai = _NODE_ORDER.index(node), _NODE_ORDER.index(active)
        if ni < ai:
            return "[bold green]✔[/bold green]"
        if ni == ai and finished:
            return "[bold green]✔[/bold green]"
    if finished and not failed:
        return "[bold green]✔[/bold green]"
    if completed_nodes and node in completed_nodes:
        return "[bold green]✔[/bold green]"
    for ns in (snap.get("workflow_list_nodes_state") or []):
        if isinstance(ns, dict) and str(ns.get("node")) == node:
            st = str(ns.get("status") or "")
            if st == "done":   return "[bold green]✔[/bold green]"
            if st in ("error", "failed"): return "[bold red]✘[/bold red]"
            break
    return "[dim]○[/dim]"


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


__all__ = [
    "PIPELINE_LEADER", "PIPELINE_HARD",
    "_steps_for_tier", "_registry_key_for_step",
    "_display_name", "_role_subtitle", "_model_for_step",
    "_pipeline_info_lines", "_STEP_LABEL", "_SPINNER_CHARS", "_NODE_ORDER",
    "_node_status_icon", "_first_graph_step_id",
    "_compute_visual_states", "_build_pipeline_markup",
]

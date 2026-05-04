"""Shared utility helpers for the monitor TUI."""
from __future__ import annotations

from io import StringIO
from core.cli.python_cli.i18n import t


def _r2a(markup: str, width: int = 160) -> str:
    """Rich markup → ANSI escape codes."""
    if markup == "":
        return ""
    from rich.console import Console as RichConsole
    sio = StringIO()
    con = RichConsole(file=sio, highlight=False, markup=True,
                      width=width, force_terminal=True, no_color=False)
    con.print(markup, end="")
    return sio.getvalue()


def _get_role_display(step_id: str) -> str:
    """Get configured role name for a pipeline step (falls back to generic label)."""
    from ....runtime import session as ws
    snap = ws.get_pipeline_snapshot()
    tier = snap.get("brief_tier")
    try:
        from ..helpers import _registry_key_for_step
        from core.config import config as _cfg
        key = _registry_key_for_step(step_id, tier)
        if key:
            cfg = _cfg.get_worker(key) or {}
            role = str(cfg.get("role", "") or "")
            if role:
                if step_id == "leader_generate" and tier:
                    return f"{role} {tier.upper()}"
                return role
    except Exception:
        pass
    _ROLE: dict[str, str] = {
        "ambassador":         t("pipeline.ambassador"),
        "leader_generate":    t("pipeline.leader"),
        "human_context_gate": t("gate.human_gate"),
        "tool_curator":       t("pipeline.tool_curator"),
        "finalize_phase1":    t("pipeline.finalize"),
    }
    return _ROLE.get(step_id, step_id)

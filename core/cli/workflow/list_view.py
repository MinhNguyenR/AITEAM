from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from rich.box import ROUNDED
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from core.cli.workflow import session as ws
from core.cli.workflow.activity_log import list_recent_activity
from core.cli.ui import PASTEL_BLUE, PASTEL_CYAN, clear_screen, console, print_divider, print_header

_MODEL_NODES = {
    "ambassador",
    "cli",
    "leader_generate",
    "expert_solo",
    "expert_coplan",
    "human_context_gate",
    "finalize_phase1",
    "end_failed",
    "runner",
}
_PATH_RE = re.compile(r"([A-Za-z]:\\[^\s]+|/[\w./-]+)")


def _model_logs(limit: int = 200) -> list[dict]:
    mt = ws.get_workflow_activity_min_ts()
    min_ts = mt if mt > 0 else None
    out = []
    for r in list_recent_activity(limit=limit * 3, min_ts=min_ts):
        if str(r.get("node", "")).lower() in _MODEL_NODES:
            out.append(r)
    return out


def _extract_paths(text: str) -> list[str]:
    res = []
    for m in _PATH_RE.findall(text or ""):
        p = m.strip()
        if p:
            res.append(p)
    return res


def _open_in_editor(path: str) -> None:
    p = Path(path)
    if not p.exists():
        console.print(f"[yellow]File không tồn tại:[/yellow] {path}")
        return
    editor = os.environ.get("EDITOR", "notepad" if os.name == "nt" else "nano")
    subprocess.run([editor, str(p)], check=False)


def _status_panel() -> None:
    snap = ws.get_pipeline_snapshot()
    notif = snap.get("notifications") or []
    notif_lines = []
    for i, n in enumerate(notif[-5:], 1):
        nid = str(n.get("id", ""))[:8]
        notif_lines.append(f"{i}. {nid} {n.get('title','')}  dismiss {nid} | view {nid}")
    if not notif_lines:
        notif_lines = ["Không có thông báo."]
    msg = (
        f"Step {snap.get('active_step')}  Tier {snap.get('brief_tier') or '—'}  Pause "
        f"{'yes' if snap.get('paused_at_gate') else 'no'}\n"
        + "\n".join(notif_lines)
    )
    console.print(Panel(msg, title="Workflow status", border_style=PASTEL_BLUE, box=ROUNDED))


def _nodes_panel() -> None:
    nodes = ws.get_workflow_list_nodes_state()
    tbl = Table(box=ROUNDED, border_style=PASTEL_BLUE, show_header=True, header_style="bold cyan")
    tbl.add_column("#", width=3)
    tbl.add_column("Node", width=22)
    tbl.add_column("Status", width=10)
    tbl.add_column("Detail")
    for i, n in enumerate(nodes, 1):
        st = str(n.get("status", "pending")).upper()
        color = {"RUNNING": "yellow", "COMPLETE": "green", "ERROR": "red"}.get(st, "white")
        tbl.add_row(str(i), str(n.get("node", "")), f"[{color}]{st}[/{color}]", str(n.get("detail", "")))
    console.print(tbl)


def _log_panel() -> None:
    rows = _model_logs(25)
    lines = []
    for r in rows[-20:]:
        node = str(r.get("node", ""))
        act = str(r.get("action", ""))
        det = str(r.get("detail", ""))
        lines.append(f"[bold]{node}[/bold] {act} {det}")
    console.print(Panel("\n".join(lines) if lines else "Chưa có log model.", title="Model activity", border_style=PASTEL_BLUE, box=ROUNDED))


def _render() -> None:
    clear_screen()
    print_header("START TASK", "Workflow list view (Rich)")
    _status_panel()
    print_divider("Pipeline")
    _nodes_panel()
    print_divider("Model log")
    _log_panel()
    console.print(
        "[dim]rewind gate|cp|node | regenerate <task> | search <t> | log | check | back | exit[/dim]"
    )


def _search(term: str) -> None:
    term_l = term.lower().strip()
    logs = _model_logs(300)
    matches = []
    for r in logs:
        line = f"{r.get('node','')} {r.get('action','')} {r.get('detail','')}"
        if term_l and term_l not in line.lower():
            continue
        matches.append(line)
    clear_screen()
    print_header("SEARCH")
    if not matches:
        console.print("[yellow]Không có kết quả.[/yellow]")
        input("Enter để quay lại...")
        return
    for i, line in enumerate(matches[:50], 1):
        console.print(f"{i}. {line}")
    paths = []
    for m in matches:
        paths.extend(_extract_paths(m))
    uniq = []
    for p in paths:
        if p not in uniq:
            uniq.append(p)
    if uniq:
        console.print()
        console.print("[bold]File paths:[/bold]")
        for i, p in enumerate(uniq[:20], 1):
            console.print(f"{i}. {p}")
        pick = Prompt.ask("Mở file số (Enter bỏ qua)", default="").strip()
        if pick.isdigit():
            idx = int(pick) - 1
            if 0 <= idx < len(uniq[:20]):
                _open_in_editor(uniq[idx])
    input("Enter để quay lại...")


def run_workflow_list_view(project_root: str) -> None:
    ws.set_workflow_project_root(project_root)
    ws.apply_stale_workflow_ui_if_needed(project_root)
    while True:
        _render()
        cmdline = Prompt.ask(f"[{PASTEL_CYAN}]workflow(list)[/{PASTEL_CYAN}]").strip()
        if not cmdline:
            continue
        parts = cmdline.split(None, 1)
        cmd = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""
        if cmd == "exit":
            return
        if cmd == "back":
            return
        if cmd == "rewind":
            if rest == "gate":
                ws.enqueue_monitor_command("rewind_gate", {})
                continue
            if rest.lower().startswith("cp "):
                idx = rest[3:].strip()
                if idx.isdigit():
                    ws.enqueue_monitor_command("rewind_checkpoint", {"target": int(idx)})
                continue
            if rest.lower().startswith("node "):
                node = rest[5:].strip()
                if node:
                    ws.enqueue_monitor_command("rewind_checkpoint", {"target": node})
                continue
            continue
        if cmd == "regenerate":
            if not rest:
                continue
            ws.enqueue_monitor_command("regenerate", {"prompt": rest})
            continue
        if cmd == "check":
            ws.enqueue_monitor_command("context_accept", {"project_root": project_root})
            continue
        if cmd == "log":
            _search("")
            continue
        if cmd == "search":
            _search(rest)
            continue

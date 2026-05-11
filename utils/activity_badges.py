from __future__ import annotations

ACTION_BADGES: dict[str, str] = {
    "state_json_written": "[bold magenta][STATE+][/bold magenta]",
    "state_json_deleted_on_accept": "[bold green][STATE-][/bold green]",
    "context_written": "[bold green][CTX+][/bold green]",
    "paused_review": "[bold yellow][PAUSE][/bold yellow]",
    "outcome_completed": "[bold green][DONE][/bold green]",
    "outcome_failed": "[bold red][FAIL][/bold red]",
    "graph_start": "[bold blue][START][/bold blue]",
    "graph_error": "[bold red][ERR][/bold red]",
    "node_complete": "[dim][OK][/dim]",
    "enter": "[bold cyan][->][/bold cyan]",
    "done": "[bold green][OK][/bold green]",
    "failed": "[bold red][X][/bold red]",
    "artifact_deleted_on_rewind": "[bold yellow][REWIND][/bold yellow]",
    "regenerate_started": "[bold cyan][REGEN][/bold cyan]",
}

# Human-readable text for (node, action) pairs
_ACTION_HUMAN: dict[tuple[str, str], str] = {
    ("ambassador", "enter"): "Ambassador bắt đầu phân tích task",
    ("ambassador", "done"): "Ambassador hoàn thành -> tier={detail}",
    ("ambassador", "node_complete"): "Ambassador xử lý xong",
    ("runner", "graph_start"): "Pipeline khởi động",
    ("runner", "graph_error"): "Pipeline gặp lỗi",
    ("leader_generate", "enter"): "Leader bắt đầu tạo context.md",
    ("leader_generate", "state_json_written"): "Leader đã ghi state.json",
    ("leader_generate", "context_written"): "Leader đã tạo xong context.md",
    ("leader_generate", "node_complete"): "Leader hoàn thành bước",
    ("leader_generate", "failed"): "Leader thất bại",
    ("expert_solo", "enter"): "Expert bắt đầu xử lý task độc lập",
    ("expert_solo", "state_json_written"): "Expert đã ghi state.json",
    ("expert_solo", "node_complete"): "Expert hoàn thành bước",
    ("human_context_gate", "paused_review"): "⏸ Đợi review context.md",
    ("human_context_gate", "node_complete"): "Gate kiểm tra context",
    ("finalize_phase1", "node_complete"): "Finalize hoàn tất Phase 1",
    ("finalize_phase1", "outcome_completed"): "✅ Pipeline Phase 1 hoàn tất",
    ("cli", "regenerate_started"): "Bắt đầu tạo lại context",
}


def badge_for_action(action: str) -> str:
    return ACTION_BADGES.get(action, "")


def human_text_for(node: str, action: str, detail: str = "") -> str:
    key = (node.lower(), action.lower())
    template = _ACTION_HUMAN.get(key)
    if template:
        text = template.format(detail=detail, node=node, action=action)
        return text
    return ""


def format_action_with_badge(action: str) -> str:
    badge = badge_for_action(action)
    if not badge:
        return f"[cyan]{action}[/cyan]"
    return f"{badge} [cyan]{action}[/cyan]"


__all__ = [
    "ACTION_BADGES",
    "badge_for_action",
    "format_action_with_badge",
    "human_text_for",
]

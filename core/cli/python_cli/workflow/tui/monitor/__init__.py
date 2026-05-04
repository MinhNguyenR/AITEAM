"""Workflow monitor TUI — public API."""
from .app import WorkflowListApp


def run_workflow_list_view(project_root: str) -> None:
    """Open the list-view TUI (blocks until TUI exits)."""
    from ...runtime import session as ws
    ws.set_workflow_project_root(project_root)
    WorkflowListApp().run()


__all__ = ["WorkflowListApp", "run_workflow_list_view"]

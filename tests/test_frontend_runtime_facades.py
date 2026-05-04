from __future__ import annotations


def test_cli_frontend_facades_resolve():
    from core.frontends.cli import confirm_context, main_loop, show_context_viewer, show_settings, start_pipeline_from_tui

    assert callable(main_loop)
    assert callable(show_settings)
    assert callable(show_context_viewer)
    assert callable(confirm_context)
    assert callable(start_pipeline_from_tui)


def test_tui_frontend_facades_resolve():
    from core.frontends.tui import WorkflowListApp, run_workflow_list_view

    assert WorkflowListApp is not None
    assert callable(run_workflow_list_view)


def test_runtime_session_facade_matches_legacy():
    from core.runtime import session as runtime_session
    from core.cli.python_cli.workflow.runtime import session as legacy_session

    assert runtime_session.get_pipeline_snapshot is legacy_session.get_pipeline_snapshot
    assert runtime_session.enqueue_monitor_command is legacy_session.enqueue_monitor_command

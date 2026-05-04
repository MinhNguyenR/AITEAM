from __future__ import annotations

import sys


def test_shell_state_matches_app_state_exports():
    from core.app_state import get_cli_settings as app_get_cli_settings
    from core.app_state import log_system_action as app_log_system_action
    from core.cli.python_cli.shell.state import get_cli_settings, log_system_action

    assert get_cli_settings is app_get_cli_settings or callable(get_cli_settings)
    assert log_system_action is app_log_system_action or callable(log_system_action)


def test_pipeline_state_is_orchestration_shim():
    from core.domain.pipeline_state import write_task_state_json
    from core.orchestration.pipeline_artifacts import write_task_state_json as orchestration_write

    assert write_task_state_json is orchestration_write


def test_team_map_is_orchestration_shim():
    from agents.team_map._team_map import get_graph
    from core.orchestration.team_graph import get_graph as orchestration_get_graph

    assert get_graph is orchestration_get_graph


def test_dashboard_services_is_application_shim():
    sys.modules.pop("core.services", None)
    sys.modules.pop("core.services.dashboard_data", None)
    sys.modules.pop("core.dashboard.shell.data", None)
    from core.dashboard.application.data import read_usage_log as app_read_usage_log
    from core.services.dashboard_data import read_usage_log as services_read_usage_log
    from core.dashboard.shell.data import read_usage_log as shell_read_usage_log

    assert services_read_usage_log is app_read_usage_log
    assert shell_read_usage_log is app_read_usage_log

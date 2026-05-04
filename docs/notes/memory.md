# Codebase Memory

**Last Updated:** 2026-05-04
**Total Files:** 342
**Total Lines of Code:** 37,215


## Structure
```text
ai-team/
+-- .env (1 lines)
+-- .env.example (7 lines)
+-- .gitignore (20 lines)
+-- .pre-commit-config.yaml (20 lines)
+-- CHANGELOG.md (75 lines)
+-- LICENSE (201 lines)
+-- MANIFEST.in (5 lines)
+-- README.md (472 lines)
+-- agents/
|   +-- __init__.py (1 lines)
|   +-- _api_client.py (497 lines)
|   +-- _budget_manager.py (34 lines)
|   +-- _knowledge_manager.py (34 lines)
|   +-- ambassador.py (409 lines)
|   +-- base_agent.py (347 lines)
|   +-- browser.py (0 lines)
|   +-- chat_agent.py (49 lines)
|   +-- commander.py (0 lines)
|   +-- compact_worker.py (99 lines)
|   +-- expert.py (338 lines)
|   +-- final_reviewer.py (0 lines)
|   +-- fix_worker.py (0 lines)
|   +-- leader.py (292 lines)
|   +-- llm_usage.py (12 lines)
|   +-- researcher.py (0 lines)
|   +-- reviewer.py (0 lines)
|   +-- secretary.py (0 lines)
|   +-- team_map/
|   |   +-- __init__.py (5 lines)
|   |   \-- _team_map.py (171 lines)
|   +-- test_agent.py (0 lines)
|   +-- tool_curator.py (0 lines)
|   \-- worker.py (0 lines)
+-- core/
|   +-- __init__.py (1 lines)
|   +-- api/
|   |   \-- __init__.py (1 lines)
|   +-- bootstrap.py (18 lines)
|   +-- cli/
|   |   +-- __init__.py (8 lines)
|   |   +-- chrome/
|   |   +-- python_cli/
|   |   +-- python_cli/
|   |   |   +-- __init__.py (5 lines)
|   |   |   +-- entrypoints/
|   |   |   |   +-- __init__.py (0 lines)
|   |   |   |   \-- app.py (119 lines)
|   |   |   +-- features/
|   |   |   |   +-- __init__.py (1 lines)
|   |   |   |   +-- ask/
|   |   |   |   |   +-- __init__.py (0 lines)
|   |   |   |   |   +-- chat_manager.py (166 lines)
|   |   |   |   |   +-- flow.py (187 lines)
|   |   |   |   |   +-- history_renderer.py (92 lines)
|   |   |   |   |   \-- model_selector.py (64 lines)
|   |   |   |   +-- change/
|   |   |   |   |   +-- __init__.py (17 lines)
|   |   |   |   |   +-- detail.py (274 lines)
|   |   |   |   |   +-- flow.py (14 lines)
|   |   |   |   |   +-- helpers.py (58 lines)
|   |   |   |   |   \-- list.py (83 lines)
|   |   |   |   +-- context/
|   |   |   |   |   +-- __init__.py (22 lines)
|   |   |   |   |   +-- common.py (104 lines)
|   |   |   |   |   +-- confirm.py (88 lines)
|   |   |   |   |   +-- flow.py (29 lines)
|   |   |   |   |   +-- monitor_actions.py (71 lines)
|   |   |   |   |   \-- viewer.py (163 lines)
|   |   |   |   +-- dashboard/
|   |   |   |   |   +-- __init__.py (0 lines)
|   |   |   |   |   \-- flow.py (3 lines)
|   |   |   |   +-- settings/
|   |   |   |   |   +-- __init__.py (0 lines)
|   |   |   |   |   \-- flow.py (121 lines)
|   |   |   |   \-- start/
|   |   |   |       +-- __init__.py (3 lines)
|   |   |   |       +-- clarification_helpers.py (54 lines)
|   |   |   |       +-- flow.py (260 lines)
|   |   |   |       \-- pipeline_runner.py (178 lines)
|   |   |   +-- shell/
|   |   |   |   +-- __init__.py (0 lines)
|   |   |   |   +-- choice_lists.py (16 lines)
|   |   |   |   +-- command_registry.py (157 lines)
|   |   |   |   +-- menu.py (306 lines)
|   |   |   |   +-- monitor_payload.py (49 lines)
|   |   |   |   +-- monitor_queue_drain.py (129 lines)
|   |   |   |   +-- nav.py (28 lines)
|   |   |   |   +-- prompt.py (131 lines)
|   |   |   |   +-- safe_editor.py (40 lines)
|   |   |   |   \-- state.py (303 lines)
|   |   |   +-- ui/
|   |   |   |   +-- __init__.py (0 lines)
|   |   |   |   +-- help_terminal.py (95 lines)
|   |   |   |   +-- helpbox.py (14 lines)
|   |   |   |   +-- palette.py (63 lines)
|   |   |   |   \-- ui.py (129 lines)
|   |   |   \-- workflow/
|   |   |       +-- __init__.py (1 lines)
|   |   |       +-- runtime/
|   |   |       |   +-- __init__.py (4 lines)
|   |   |       |   +-- graph/
|   |   |       |   |   +-- __init__.py (1 lines)
|   |   |       |   |   +-- runner.py (245 lines)
|   |   |       |   |   +-- runner_resume.py (45 lines)
|   |   |       |   |   +-- runner_rewind.py (230 lines)
|   |   |       |   |   \-- runner_ui.py (67 lines)
|   |   |       |   +-- persist/
|   |   |       |   |   +-- __init__.py (1 lines)
|   |   |       |   |   +-- activity_log.py (191 lines)
|   |   |       |   |   \-- checkpointer.py (23 lines)
|   |   |       |   +-- present/
|   |   |       |   |   +-- __init__.py (1 lines)
|   |   |       |   |   \-- pipeline_markdown.py (99 lines)
|   |   |       |   \-- session/
|   |   |       |       +-- __init__.py (105 lines)
|   |   |       |       +-- _session_core.py (50 lines)
|   |   |       |       +-- session_monitor_manager.py (30 lines)
|   |   |       |       +-- session_notification.py (174 lines)
|   |   |       |       +-- session_pause_manager.py (89 lines)
|   |   |       |       +-- session_pipeline_state.py (689 lines)
|   |   |       |       \-- session_store.py (45 lines)
|   |   |       \-- tui/
|   |   |           +-- __init__.py (1 lines)
|   |   |           +-- __main__.py (6 lines)
|   |   |           +-- app/
|   |   |           |   +-- __init__.py (0 lines)
|   |   |           |   +-- list_view.py (4 lines)
|   |   |           |   +-- monitor_app.py (4 lines)
|   |   |           |   +-- monitor_helpers.py (470 lines)
|   |   |           |   \-- monitor_screens.py (310 lines)
|   |   |           +-- entry/
|   |   |           |   +-- __init__.py (1 lines)
|   |   |           |   +-- __main__.py (7 lines)
|   |   |           |   +-- list_view.py (4 lines)
|   |   |           |   \-- monitor_app.py (4 lines)
|   |   |           +-- monitor/
|   |   |           |   +-- __init__.py (12 lines)
|   |   |           |   +-- app.py (251 lines)
|   |   |           |   +-- commands/
|   |   |           |   |   +-- __init__.py (13 lines)
|   |   |           |   |   +-- ask.py (73 lines)
|   |   |           |   |   +-- btw.py (108 lines)
|   |   |           |   |   +-- check.py (64 lines)
|   |   |           |   |   \-- mixin.py (329 lines)
|   |   |           |   +-- core/
|   |   |           |   |   +-- __init__.py (19 lines)
|   |   |           |   |   +-- _constants.py (59 lines)
|   |   |           |   |   +-- _content_mixin.py (81 lines)
|   |   |           |   |   +-- _controls.py (130 lines)
|   |   |           |   |   +-- _layout_mixin.py (243 lines)
|   |   |           |   |   +-- _render_mixin.py (324 lines)
|   |   |           |   |   +-- _tasks_mixin.py (106 lines)
|   |   |           |   |   +-- _utils.py (40 lines)
|   |   |           |   |   \-- _views_mixin.py (78 lines)
|   |   |           |   \-- state/
|   |   |           |       +-- __init__.py (38 lines)
|   |   |           |       +-- _ambassador.py (32 lines)
|   |   |           |       +-- _clarify.py (16 lines)
|   |   |           |       +-- _gate.py (40 lines)
|   |   |           |       +-- _leader.py (61 lines)
|   |   |           |       \-- _pipeline.py (26 lines)
|   |   |           \-- shared/
|   |   |               +-- __init__.py (1 lines)
|   |   |               +-- agent_cards.py (129 lines)
|   |   |               +-- btw_inline.py (87 lines)
|   |   |               \-- display_policy.py (19 lines)
|   |   \-- workflow/
|   |       +-- runtime/
|   |       \-- tui/
|   +-- config/
|   |   +-- __init__.py (26 lines)
|   |   +-- constants.py (35 lines)
|   |   +-- hardware.py (107 lines)
|   |   +-- pricing.py (172 lines)
|   |   +-- registry/
|   |   |   +-- __init__.py (34 lines)
|   |   |   \-- coding/
|   |   |       +-- __init__.py (29 lines)
|   |   |       +-- chat.py (26 lines)
|   |   |       +-- devops.py (16 lines)
|   |   |       +-- fixers.py (56 lines)
|   |   |       +-- leaders.py (36 lines)
|   |   |       +-- researchers.py (36 lines)
|   |   |       +-- reviewers.py (44 lines)
|   |   |       +-- support.py (46 lines)
|   |   |       +-- system.py (36 lines)
|   |   |       +-- testers.py (26 lines)
|   |   |       \-- workers.py (56 lines)
|   |   +-- runtime_config.py (14 lines)
|   |   +-- service.py (252 lines)
|   |   \-- settings.py (98 lines)
|   +-- dashboard/
|   |   +-- __init__.py (5 lines)
|   |   +-- output/
|   |   |   +-- __init__.py (1 lines)
|   |   |   +-- exporters.py (230 lines)
|   |   |   \-- pdf_export.py (172 lines)
|   |   +-- reporting/
|   |   |   +-- __init__.py (1 lines)
|   |   |   +-- report_model.py (131 lines)
|   |   |   +-- report_txt_format.py (116 lines)
|   |   |   +-- state.py (83 lines)
|   |   |   \-- text_export.py (35 lines)
|   |   +-- shell/
|   |   |   +-- __init__.py (1 lines)
|   |   |   +-- app.py (177 lines)
|   |   |   +-- budget.py (54 lines)
|   |   |   +-- data.py (18 lines)
|   |   |   +-- history.py (205 lines)
|   |   |   \-- total.py (59 lines)
|   |   \-- tui/
|   |       +-- __init__.py (1 lines)
|   |       +-- log_console.py (6 lines)
|   |       +-- panels.py (12 lines)
|   |       +-- render.py (179 lines)
|   |       \-- utils.py (60 lines)
|   +-- domain/
|   |   +-- __init__.py (0 lines)
|   |   +-- agent_protocol.py (51 lines)
|   |   +-- delta_brief.py (86 lines)
|   |   +-- pipeline_state.py (109 lines)
|   |   +-- prompts/
|   |   |   +-- __init__.py (35 lines)
|   |   |   +-- ambassador.py (61 lines)
|   |   |   +-- ask_mode.py (35 lines)
|   |   |   +-- btw_coordinator.py (56 lines)
|   |   |   +-- clarification.py (29 lines)
|   |   |   +-- expert.py (74 lines)
|   |   |   \-- leader.py (120 lines)
|   |   +-- routing_map.py (51 lines)
|   |   \-- skills/
|   |       +-- __init__.py (22 lines)
|   |       +-- _registry.py (35 lines)
|   |       +-- examples/
|   |       |   +-- __init__.py (5 lines)
|   |       |   \-- echo.py (15 lines)
|   |       \-- hooks.py (12 lines)
|   +-- paths.py (12 lines)
|   +-- resources/
|   |   +-- README.md (3 lines)
|   |   \-- fonts/
|   |       +-- Inter_18pt-Regular.ttf (0 lines)
|   |       \-- Inter_24pt-Bold.ttf (0 lines)
|   +-- runtime_config.py (4 lines)
|   +-- services/
|   |   +-- __init__.py (1 lines)
|   |   \-- dashboard_data.py (12 lines)
|   \-- storage/
|       +-- __init__.py (30 lines)
|       +-- ask_chat_store.py (278 lines)
|       +-- ask_history.py (102 lines)
|       +-- graphrag_store.py (253 lines)
|       +-- knowledge/
|       |   +-- __init__.py (10 lines)
|       |   +-- repository.py (28 lines)
|       |   +-- sqlite_repository.py (422 lines)
|       |   \-- vault_key.py (73 lines)
|       +-- knowledge_store.py (65 lines)
|       +-- knowledge_text.py (95 lines)
|       \-- prompt_store_protocol.py (27 lines)
+-- docs/
|   +-- REPO_LAYOUT.md (19 lines)
|   +-- design/
|   |   \-- README.md (3 lines)
|   +-- notes/
|   |   +-- README.md (3 lines)
|   |   \-- memory.md (317 lines)
|   +-- security.md (6 lines)
|   +-- skills_admin/
|   |   +-- AgentAudit/
|   |   |   +-- AGENT_AUDIT.md (47 lines)
|   |   |   +-- PROJECT_SUMMARY.md (24 lines)
|   |   |   \-- README.md (17 lines)
|   |   +-- GraphRag/
|   |   |   +-- PROJECT_MAP.md (231 lines)
|   |   |   +-- PROJECT_SUMMARY.md (285 lines)
|   |   |   \-- README.md (27 lines)
|   |   \-- README.md (8 lines)
|   \-- workflow_overhaul_prompt.md (147 lines)
+-- pyproject.toml (82 lines)
+-- scripts/
|   +-- README.md (3 lines)
|   +-- analyze_codebase.py (114 lines)
|   \-- run_aiteam.py (6 lines)
+-- tests/
|   +-- cli/
|   |   +-- test_cli_prompt_ux.py (89 lines)
|   |   \-- test_ui_clear.py (21 lines)
|   +-- conftest.py (8 lines)
|   +-- test_activity_badges.py (56 lines)
|   +-- test_activity_log.py (156 lines)
|   +-- test_ambassador_methods.py (204 lines)
|   +-- test_ambassador_tier_classification.py (110 lines)
|   +-- test_api_client_stream.py (218 lines)
|   +-- test_api_client_unit.py (218 lines)
|   +-- test_ask_chat_manager.py (114 lines)
|   +-- test_ask_chat_store.py (258 lines)
|   +-- test_ask_history.py (162 lines)
|   +-- test_base_agent_extra.py (220 lines)
|   +-- test_budget_guard.py (54 lines)
|   +-- test_budget_manager.py (65 lines)
|   +-- test_cli_security_helpers.py (61 lines)
|   +-- test_cli_state.py (163 lines)
|   +-- test_cli_state_overrides.py (150 lines)
|   +-- test_config_hardware.py (116 lines)
|   +-- test_config_pricing.py (261 lines)
|   +-- test_config_registry.py (76 lines)
|   +-- test_config_service.py (239 lines)
|   +-- test_config_settings.py (102 lines)
|   +-- test_dashboard_batches_browser.py (31 lines)
|   +-- test_dashboard_helpers.py (50 lines)
|   +-- test_dashboard_history_browser.py (25 lines)
|   +-- test_dashboard_history_pure.py (61 lines)
|   +-- test_dashboard_pdf.py (82 lines)
|   +-- test_dashboard_pdf_font_fallback.py (56 lines)
|   +-- test_dashboard_range_picker.py (17 lines)
|   +-- test_dashboard_range_state.py (102 lines)
|   +-- test_dashboard_render.py (41 lines)
|   +-- test_dashboard_tui_utils.py (73 lines)
|   +-- test_dashboard_turn_views.py (77 lines)
|   +-- test_delta_brief.py (133 lines)
|   +-- test_domain_prompts.py (118 lines)
|   +-- test_env_guard.py (140 lines)
|   +-- test_expert_agent.py (297 lines)
|   +-- test_expert_coplan.py (175 lines)
|   +-- test_export_txt_format.py (21 lines)
|   +-- test_file_manager.py (189 lines)
|   +-- test_graphrag_store.py (157 lines)
|   +-- test_graphrag_utils.py (73 lines)
|   +-- test_import_smoke_python_cli.py (22 lines)
|   +-- test_input_validator.py (49 lines)
|   +-- test_json_utils.py (58 lines)
|   +-- test_knowledge_manager.py (127 lines)
|   +-- test_knowledge_repository.py (59 lines)
|   +-- test_knowledge_store_module.py (101 lines)
|   +-- test_knowledge_text.py (156 lines)
|   +-- test_leader_flow.py (143 lines)
|   +-- test_leader_generate.py (216 lines)
|   +-- test_leader_pure.py (124 lines)
|   +-- test_llm_usage.py (59 lines)
|   +-- test_logger_utils.py (69 lines)
|   +-- test_monitor_commands_regenerate.py (67 lines)
|   +-- test_monitor_helpers_tier_display.py (16 lines)
|   +-- test_monitor_payload.py (88 lines)
|   +-- test_pure_cli_modules.py (201 lines)
|   +-- test_report_txt_format.py (145 lines)
|   +-- test_runner_inline_progress.py (76 lines)
|   +-- test_runner_rewind_logic.py (268 lines)
|   +-- test_runner_rewind_pure.py (95 lines)
|   +-- test_runtime_config.py (34 lines)
|   +-- test_security_and_config.py (145 lines)
|   +-- test_session_monitor_manager.py (62 lines)
|   +-- test_session_notification.py (132 lines)
|   +-- test_session_notification_extra.py (181 lines)
|   +-- test_session_pause_manager.py (128 lines)
|   +-- test_session_pipeline_state.py (230 lines)
|   +-- test_session_pipeline_state_extra.py (191 lines)
|   +-- test_session_pipeline_state_uncovered.py (166 lines)
|   +-- test_session_store.py (72 lines)
|   +-- test_skills_registry.py (40 lines)
|   +-- test_sqlite_repository_extra.py (195 lines)
|   +-- test_team_map_routing.py (66 lines)
|   +-- test_tracker_aggregate.py (83 lines)
|   +-- test_tracker_aggregate_extra.py (136 lines)
|   +-- test_tracker_batches.py (118 lines)
|   +-- test_tracker_batches_summarize.py (143 lines)
|   +-- test_tracker_budget.py (103 lines)
|   +-- test_tracker_cache.py (81 lines)
|   +-- test_tracker_dashboard_summary.py (28 lines)
|   +-- test_tracker_helpers.py (133 lines)
|   +-- test_tracker_usage.py (74 lines)
|   +-- test_vault_key.py (67 lines)
|   +-- test_workflow_activity_format.py (14 lines)
|   \-- test_workflow_toast_queue.py (49 lines)
\-- utils/
    +-- __init__.py (1 lines)
    +-- activity_badges.py (68 lines)
    +-- ask_history.py (36 lines)
    +-- budget_guard.py (27 lines)
    +-- delta_brief.py (20 lines)
    +-- env_guard.py (92 lines)
    +-- file_manager.py (127 lines)
    +-- free_model_finder.py (130 lines)
    +-- graphrag_utils.py (47 lines)
    +-- input_validator.py (36 lines)
    +-- json_utils.py (57 lines)
    +-- logger.py (43 lines)
    \-- tracker/
        +-- __init__.py (86 lines)
        +-- tracker_aggregate.py (175 lines)
        +-- tracker_batches.py (126 lines)
        +-- tracker_budget.py (75 lines)
        +-- tracker_cache.py (45 lines)
        +-- tracker_helpers.py (118 lines)
        +-- tracker_openrouter.py (37 lines)
        \-- tracker_usage.py (117 lines)
```

## Connections (Internal Imports)
- **agents/_api_client.py**
  - imports `core.config.constants`
  - imports `utils.budget_guard`
  - imports `utils.env_guard`

- **agents/ambassador.py**
  - imports `agents.base_agent`
  - imports `core.bootstrap`
  - imports `core.config`
  - imports `core.domain.delta_brief`
  - imports `core.domain.prompts`
  - imports `core.domain.routing_map`
  - imports `utils.input_validator`
  - imports `utils.json_utils`
  - imports `utils.tracker`

- **agents/base_agent.py**
  - imports `agents._api_client`
  - imports `agents._budget_manager`
  - imports `agents._knowledge_manager`
  - imports `core.bootstrap`
  - imports `core.config`
  - imports `core.config.constants`

- **agents/chat_agent.py**
  - imports `core.config`
  - imports `core.config.settings`
  - imports `core.domain.prompts`

- **agents/compact_worker.py**
  - imports `agents.base_agent`
  - imports `core.config`

- **agents/expert.py**
  - imports `agents.base_agent`
  - imports `core.config`
  - imports `core.domain.prompts`
  - imports `utils.file_manager`

- **agents/leader.py**
  - imports `agents.base_agent`
  - imports `core.config`
  - imports `core.config.constants`
  - imports `core.domain.delta_brief`
  - imports `core.domain.prompts`
  - imports `utils.file_manager`

- **agents/tool_curator.py**
  - imports `agents.base_agent`
  - imports `core.config`
  - imports `core.domain.pipeline_state`
  - imports `utils.file_manager`
  - imports `utils.graphrag_utils`

- **agents/llm_usage.py**
  - imports `agents._api_client`

- **agents/team_map/_team_map.py**
  - imports `agents.leader`
  - imports `core.bootstrap`
  - imports `core.cli.python_cli.workflow.runtime`
  - imports `core.domain.delta_brief`
  - imports `core.domain.pipeline_state`
  - imports `utils.file_manager`
  - imports `utils.logger`

- **core/cli/python_cli/__init__.py**
  - imports `core.cli.python_cli.shell`

- **core/cli/python_cli/entrypoints/app.py**
  - imports `core.bootstrap`
  - imports `core.cli.python_cli.shell.menu`
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.ui.ui`

- **core/cli/python_cli/features/ask/chat_manager.py**
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.ui.ui`
  - imports `core.storage`

- **core/cli/python_cli/features/ask/flow.py**
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.ui.ui`
  - imports `core.domain.prompts`
  - imports `core.storage`
  - imports `utils.input_validator`

- **core/cli/python_cli/features/ask/history_renderer.py**
  - imports `core.cli.python_cli.ui.ui`

- **core/cli/python_cli/features/ask/model_selector.py**
  - imports `agents._api_client`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.config`
  - imports `core.config.settings`
  - imports `utils.budget_guard`

- **core/cli/python_cli/features/change/detail.py**
  - imports `core.cli.python_cli.features.change.helpers`
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.prompt`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.ui.ui`
  - imports `core.config`
  - imports `core.config.pricing`

- **core/cli/python_cli/features/change/flow.py**
  - imports `core.cli.python_cli.features.change`

- **core/cli/python_cli/features/change/helpers.py**
  - imports `core.cli.python_cli.ui.ui`
  - imports `core.config`

- **core/cli/python_cli/features/change/list.py**
  - imports `core.cli.python_cli.features.change.helpers`
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.ui.ui`

- **core/cli/python_cli/features/context/common.py**
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.workflow.runtime`
  - imports `core.cli.python_cli.workflow.runtime.persist.activity_log`
  - imports `core.config`
  - imports `core.domain.delta_brief`
  - imports `utils.file_manager`
  - imports `utils.logger`

- **core/cli/python_cli/features/context/confirm.py**
  - imports `core.cli.python_cli.features.context.common`
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.prompt`
  - imports `core.cli.python_cli.shell.safe_editor`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.ui.ui`

- **core/cli/python_cli/features/context/flow.py**
  - imports `core.cli.python_cli.features.context`

- **core/cli/python_cli/features/context/monitor_actions.py**
  - imports `core.cli.python_cli.features.context.common`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.workflow.runtime`
  - imports `core.cli.python_cli.workflow.runtime.graph.runner`
  - imports `core.cli.python_cli.workflow.runtime.persist.activity_log`
  - imports `core.domain.delta_brief`

- **core/cli/python_cli/features/context/viewer.py**
  - imports `core.cli.python_cli.features.context.common`
  - imports `core.cli.python_cli.shell.choice_lists`
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.prompt`
  - imports `core.cli.python_cli.shell.safe_editor`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.ui.ui`
  - imports `core.cli.python_cli.workflow.runtime`
  - imports `core.cli.python_cli.workflow.runtime.graph.runner`
  - imports `core.domain.delta_brief`

- **core/cli/python_cli/features/dashboard/flow.py**
  - imports `core.dashboard`

- **core/cli/python_cli/features/settings/flow.py**
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.prompt`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.ui.ui`

- **core/cli/python_cli/features/start/flow.py**
  - imports `core.cli.python_cli.features.ask.flow`
  - imports `core.cli.python_cli.features.context.flow`
  - imports `core.cli.python_cli.shell.choice_lists`
  - imports `core.cli.python_cli.shell.command_registry`
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.prompt`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.ui.ui`
  - imports `core.cli.python_cli.workflow.runtime`
  - imports `core.cli.python_cli.workflow.runtime.persist.activity_log`
  - imports `core.domain.pipeline_state`
  - imports `core.cli.python_cli.features.start.clarification_helpers`
  - imports `core.cli.python_cli.features.start.pipeline_runner`
  - imports `utils.file_manager`
  - imports `utils.logger`

- **core/cli/python_cli/features/start/pipeline_runner.py**
  - imports `core.cli.python_cli.workflow.runtime`
  - imports `core.domain.pipeline_state`
  - imports `core.cli.python_cli.workflow.runtime.graph.runner`
  - imports `utils.logger`
  - imports `core.cli.python_cli.features.start.clarification_helpers`
  - imports `core.cli.python_cli.shell.state`

- **core/cli/python_cli/features/start/clarification_helpers.py**
  - imports `utils.file_manager`
  - imports `agents._api_client`
  - imports `core.config`
  - imports `core.domain.prompts`

- **core/cli/python_cli/shell/choice_lists.py**
  - imports `core.cli.python_cli.shell.command_registry`

- **core/cli/python_cli/shell/menu.py**
  - imports `core.cli.python_cli.features.ask.flow`
  - imports `core.cli.python_cli.features.change.flow`
  - imports `core.cli.python_cli.features.context.flow`
  - imports `core.cli.python_cli.features.dashboard.flow`
  - imports `core.cli.python_cli.features.settings.flow`
  - imports `core.cli.python_cli.features.start.flow`
  - imports `core.cli.python_cli.shell.command_registry`
  - imports `core.cli.python_cli.shell.monitor_queue_drain`
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.prompt`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.ui.help_terminal`
  - imports `core.cli.python_cli.ui.palette`
  - imports `core.cli.python_cli.ui.ui`
  - imports `core.config`
  - imports `utils.env_guard`

- **core/cli/python_cli/shell/monitor_queue_drain.py**
  - imports `core.cli.python_cli.features.context.flow`
  - imports `core.cli.python_cli.shell.monitor_payload`
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.ui.ui`
  - imports `core.cli.python_cli.workflow.runtime`
  - imports `core.cli.python_cli.workflow.runtime.graph.runner`
  - imports `core.config`

- **core/cli/python_cli/shell/state.py**
  - imports `core.config.constants`
  - imports `core.storage`
  - imports `utils.env_guard`

- **core/cli/python_cli/ui/help_terminal.py**
  - imports `core.cli.python_cli.shell.prompt`

- **core/cli/python_cli/ui/helpbox.py**
  - imports `core.cli.python_cli.ui.ui`

- **core/cli/python_cli/ui/palette.py**
  - imports `core.cli.python_cli.shell.choice_lists`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.ui.ui`

- **core/cli/python_cli/workflow/runtime/graph/runner.py**
  - imports `agents.team_map._team_map`
  - imports `core.bootstrap`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.ui.ui`
  - imports `core.domain.routing_map`
  - imports `utils.logger`

- **core/cli/python_cli/workflow/runtime/graph/runner_resume.py**
  - imports `agents.team_map._team_map`

- **core/cli/python_cli/workflow/runtime/graph/runner_rewind.py**
  - imports `agents.team_map._team_map`
  - imports `utils.file_manager`
  - imports `utils.logger`

- **core/cli/python_cli/workflow/runtime/persist/activity_log.py**
  - imports `utils.activity_badges`
  - imports `utils.env_guard`
  - imports `utils.file_manager`

- **core/cli/python_cli/workflow/runtime/session/_session_core.py**
  - imports `utils.file_manager`

- **core/cli/python_cli/workflow/runtime/session/session_store.py**
  - imports `utils.file_manager`

- **core/cli/python_cli/workflow/tui/app/monitor_helpers.py**
  - imports `agents.team_map._team_map`
  - imports `core.bootstrap`
  - imports `core.config`
  - imports `core.domain.routing_map`

- **core/cli/python_cli/workflow/tui/app/monitor_screens.py**
  - imports `core.cli.python_cli.features.context.flow`
  - imports `core.cli.python_cli.shell.safe_editor`
  - imports `core.cli.python_cli.shell.state`

- **core/cli/python_cli/workflow/tui/shared/agent_cards.py**
  - imports `core.config`

- **core/config/__init__.py**
  - imports `core.config.service`

- **core/config/pricing.py**
  - imports `core.config.constants`

- **core/config/service.py**
  - imports `core.config.hardware`
  - imports `core.config.pricing`
  - imports `core.config.registry`
  - imports `core.config.settings`

- **core/dashboard/output/exporters.py**
  - imports `core.config.constants`
  - imports `core.paths`

- **core/dashboard/output/pdf_export.py**
  - imports `core.paths`

- **core/dashboard/reporting/report_model.py**
  - imports `utils`

- **core/dashboard/reporting/state.py**
  - imports `utils.tracker`

- **core/dashboard/shell/app.py**
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.prompt`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.ui.ui`
  - imports `utils`

- **core/dashboard/shell/budget.py**
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.prompt`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.cli.python_cli.ui.ui`

- **core/dashboard/shell/data.py**
  - imports `utils`

- **core/dashboard/shell/history.py**
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.prompt`
  - imports `core.cli.python_cli.ui.ui`
  - imports `core.dashboard.shell`

- **core/dashboard/shell/total.py**
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.prompt`
  - imports `core.cli.python_cli.ui.ui`
  - imports `core.dashboard.shell`

- **core/dashboard/tui/render.py**
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.shell.prompt`
  - imports `core.config`
  - imports `utils`

- **core/dashboard/tui/utils.py**
  - imports `core.cli.python_cli.ui.ui`
  - imports `utils`

- **core/domain/pipeline_state.py**
  - imports `core.config`
  - imports `core.domain.delta_brief`
  - imports `core.domain.routing_map`
  - imports `utils.file_manager`
  - imports `utils.logger`

- **core/paths.py**
  - imports `core.bootstrap`

- **core/runtime_config.py**
  - imports `core.config.runtime_config`

- **core/services/dashboard_data.py**
  - imports `core.dashboard.shell.data`

- **core/storage/__init__.py**
  - imports `core.storage.ask_chat_store`
  - imports `core.storage.graphrag_store`
  - imports `core.storage.knowledge_store`

- **core/storage/ask_chat_store.py**
  - imports `utils.file_manager`

- **core/storage/ask_history.py**
  - imports `core.config.constants`
  - imports `core.storage.ask_chat_store`
  - imports `utils.file_manager`

- **core/storage/graphrag_store.py**
  - imports `core.config.constants`

- **core/storage/knowledge/__init__.py**
  - imports `core.storage.knowledge.repository`
  - imports `core.storage.knowledge.sqlite_repository`
  - imports `core.storage.knowledge.vault_key`

- **core/storage/knowledge/sqlite_repository.py**
  - imports `core.config.constants`
  - imports `core.storage.knowledge.vault_key`
  - imports `core.storage.knowledge_text`

- **core/storage/knowledge_store.py**
  - imports `core.config.constants`
  - imports `core.storage.knowledge.repository`
  - imports `core.storage.knowledge.sqlite_repository`
  - imports `core.storage.knowledge_text`

- **scripts/run_aiteam.py**
  - imports `core.cli.python_cli.entrypoints.app`

- **tests/cli/test_cli_prompt_ux.py**
  - imports `core.cli.python_cli`

- **tests/cli/test_ui_clear.py**
  - imports `core.cli.python_cli.ui`

- **tests/conftest.py**
  - imports `core.bootstrap`

- **tests/test_activity_badges.py**
  - imports `utils.activity_badges`

- **tests/test_activity_log.py**
  - imports `core.cli.python_cli.workflow.runtime.persist.activity_log`

- **tests/test_ambassador_tier_classification.py**
  - imports `agents.ambassador`

- **tests/test_api_client_stream.py**
  - imports `agents._api_client`
  - imports `agents._budget_manager`
  - imports `agents.base_agent`

- **tests/test_api_client_unit.py**
  - imports `agents._api_client`
  - imports `agents._budget_manager`
  - imports `agents.base_agent`

- **tests/test_ask_chat_manager.py**
  - imports `core.cli.python_cli.features.ask.chat_manager`

- **tests/test_ask_chat_store.py**
  - imports `core.storage.ask_chat_store`

- **tests/test_base_agent_extra.py**
  - imports `agents._budget_manager`
  - imports `agents.base_agent`

- **tests/test_budget_guard.py**
  - imports `utils.budget_guard`

- **tests/test_budget_manager.py**
  - imports `agents._budget_manager`
  - imports `agents.base_agent`

- **tests/test_cli_security_helpers.py**
  - imports `core.cli.python_cli.shell.monitor_payload`
  - imports `core.cli.python_cli.shell.safe_editor`

- **tests/test_cli_state.py**
  - imports `core.cli.python_cli.shell.state`

- **tests/test_cli_state_overrides.py**
  - imports `core.cli.python_cli.shell.state`

- **tests/test_config_hardware.py**
  - imports `core.config.hardware`

- **tests/test_config_pricing.py**
  - imports `core.config.pricing`

- **tests/test_config_registry.py**
  - imports `core.config.registry`

- **tests/test_config_settings.py**
  - imports `core.config.settings`

- **tests/test_dashboard_batches_browser.py**
  - imports `core.dashboard.reporting.state`
  - imports `core.dashboard.shell`

- **tests/test_dashboard_helpers.py**
  - imports `core.dashboard.reporting.state`
  - imports `core.dashboard.tui.utils`

- **tests/test_dashboard_history_browser.py**
  - imports `core.dashboard.reporting.state`
  - imports `core.dashboard.shell`

- **tests/test_dashboard_history_pure.py**
  - imports `core.dashboard.shell.history`

- **tests/test_dashboard_pdf.py**
  - imports `core.dashboard.output.pdf_export`
  - imports `core.dashboard.reporting.state`

- **tests/test_dashboard_pdf_font_fallback.py**
  - imports `core.dashboard.output.pdf_export`
  - imports `core.dashboard.reporting.state`

- **tests/test_dashboard_range_picker.py**
  - imports `core.dashboard.tui.render`

- **tests/test_dashboard_range_state.py**
  - imports `core.dashboard.reporting.state`

- **tests/test_dashboard_render.py**
  - imports `core.dashboard.tui.render`

- **tests/test_dashboard_tui_utils.py**
  - imports `core.dashboard.tui.utils`

- **tests/test_dashboard_turn_views.py**
  - imports `core.dashboard.reporting.state`
  - imports `core.dashboard.shell`

- **tests/test_delta_brief.py**
  - imports `utils.delta_brief`

- **tests/test_domain_prompts.py**
  - imports `core.domain.prompts`

- **tests/test_env_guard.py**
  - imports `utils.env_guard`

- **tests/test_expert_coplan.py**
  - imports `agents.expert`

- **tests/test_export_txt_format.py**
  - imports `core.dashboard.reporting.report_model`
  - imports `core.dashboard.reporting.report_txt_format`
  - imports `core.dashboard.reporting.state`

- **tests/test_graphrag_store.py**
  - imports `core.storage.graphrag_store`

- **tests/test_graphrag_utils.py**
  - imports `utils.graphrag_utils`

- **tests/test_import_smoke_python_cli.py**
  - imports `core.cli.python_cli`

- **tests/test_input_validator.py**
  - imports `utils.input_validator`

- **tests/test_json_utils.py**
  - imports `utils.json_utils`

- **tests/test_knowledge_manager.py**
  - imports `agents._knowledge_manager`

- **tests/test_knowledge_repository.py**
  - imports `core.storage.knowledge`

- **tests/test_knowledge_text.py**
  - imports `core.storage.knowledge_text`

- **tests/test_leader_flow.py**
  - imports `core.bootstrap`

- **tests/test_leader_pure.py**
  - imports `agents.leader`
  - imports `core.config.constants`

- **tests/test_llm_usage.py**
  - imports `agents.llm_usage`

- **tests/test_logger_utils.py**
  - imports `utils.logger`

- **tests/test_monitor_commands_regenerate.py**
  - imports `core.cli.python_cli.workflow.tui.monitor.commands.mixin`
  - imports `core.cli.python_cli.workflow.tui.monitor.core._constants`

- **tests/test_monitor_helpers_tier_display.py**
  - imports `core.cli.python_cli.workflow.tui.app`

- **tests/test_monitor_payload.py**
  - imports `core.cli.python_cli.shell.monitor_payload`

- **tests/test_pure_cli_modules.py**
  - imports `core.cli.python_cli.shell.command_registry`
  - imports `core.cli.python_cli.shell.nav`
  - imports `core.cli.python_cli.workflow.runtime.present.pipeline_markdown`
  - imports `core.cli.python_cli.workflow.tui.shared.display_policy`
  - imports `core.domain.routing_map`

- **tests/test_report_txt_format.py**
  - imports `core.dashboard.reporting.report_model`
  - imports `core.dashboard.reporting.report_txt_format`

- **tests/test_runner_inline_progress.py**
  - imports `core.cli.python_cli.workflow.runtime.graph`

- **tests/test_runner_rewind_logic.py**
  - imports `core.cli.python_cli.workflow.runtime.graph.runner_rewind`

- **tests/test_runner_rewind_pure.py**
  - imports `core.cli.python_cli.workflow.runtime.graph.runner_rewind`

- **tests/test_runtime_config.py**
  - imports `core.config.runtime_config`

- **tests/test_security_and_config.py**
  - imports `agents.base_agent`
  - imports `core.cli.python_cli.shell.state`
  - imports `core.config.settings`
  - imports `core.storage.knowledge_store`
  - imports `utils.env_guard`
  - imports `utils.input_validator`

- **tests/test_session_monitor_manager.py**
  - imports `core.cli.python_cli.workflow.runtime.session.session_monitor_manager`

- **tests/test_session_notification.py**
  - imports `core.cli.python_cli.workflow.runtime.session.session_notification`

- **tests/test_session_notification_extra.py**
  - imports `core.cli.python_cli.workflow.runtime.session.session_notification`

- **tests/test_session_pause_manager.py**
  - imports `core.cli.python_cli.workflow.runtime.session.session_pause_manager`

- **tests/test_session_pipeline_state.py**
  - imports `core.cli.python_cli.workflow.runtime.session.session_pipeline_state`

- **tests/test_session_pipeline_state_extra.py**
  - imports `core.cli.python_cli.workflow.runtime.session.session_pipeline_state`

- **tests/test_session_pipeline_state_uncovered.py**
  - imports `core.cli.python_cli.workflow.runtime.session.session_pipeline_state`

- **tests/test_session_store.py**
  - imports `core.cli.python_cli.workflow.runtime.session.session_store`

- **tests/test_skills_registry.py**
  - imports `core.domain.skills`

- **tests/test_sqlite_repository_extra.py**
  - imports `core.storage.knowledge.sqlite_repository`

- **tests/test_team_map_routing.py**
  - imports `agents.team_map._team_map`

- **tests/test_tracker_aggregate.py**
  - imports `utils.tracker.tracker_aggregate`

- **tests/test_tracker_aggregate_extra.py**
  - imports `utils.tracker.tracker_aggregate`
  - imports `utils.tracker.tracker_cache`

- **tests/test_tracker_batches_summarize.py**
  - imports `utils.tracker.tracker_batches`

- **tests/test_tracker_budget.py**
  - imports `utils.tracker.tracker_budget`

- **tests/test_tracker_cache.py**
  - imports `utils.tracker.tracker_cache`

- **tests/test_tracker_dashboard_summary.py**
  - imports `utils`

- **tests/test_tracker_helpers.py**
  - imports `utils.tracker.tracker_helpers`

- **tests/test_tracker_usage.py**
  - imports `utils.tracker.tracker_usage`

- **tests/test_vault_key.py**
  - imports `core.storage.knowledge.vault_key`

- **tests/test_workflow_activity_format.py**
  - imports `core.cli.python_cli.workflow.runtime.persist.activity_log`

- **tests/test_workflow_toast_queue.py**
  - imports `core.cli.python_cli.workflow.runtime`

- **utils/ask_history.py**
  - imports `core.storage.ask_history`

- **utils/budget_guard.py**
  - imports `core.cli.python_cli.shell.state`
  - imports `utils`

- **utils/delta_brief.py**
  - imports `core.domain.delta_brief`

- **utils/env_guard.py**
  - imports `core.config.constants`
  - imports `utils.file_manager`

- **utils/file_manager.py**
  - imports `core.config`

- **utils/tracker/tracker_helpers.py**
  - imports `core.config.constants`


## Session Summary: Tool Curator & TUI Refactoring
**Date:** 2026-05-04
**Objective:** Architect and implement the `ToolCurator` agent and refactor the TUI to eliminate redundant shims.

### 1. Tool Curator Integration
- Introduced `ToolCurator` to run after `Human Gate` and before `Finalize`.
- Substates: `reading`, `thinking`, `looking_for`, `writing`.
- Communication: File-based (`tools.md`), GraphRAG FTS5 ingestion, and `CompressedBrain` knowledge.
- Model: `deepseek/deepseek-v4-flash` (Support tier).

### 2. TUI Architecture Refactor
- Eliminated redundant shim chain: `tui/entry/` and `tui/app/` (shims only).
- Consolidated core logic: Moved `monitor_helpers.py` and `monitor_screens.py` into `tui/monitor/`.
- Simplified public API: `core.cli.python_cli.workflow.tui` now exports directly from `monitor`.
- Fixed circular/deep import chains involving 6+ files.

### 3. Pipeline Expansion
- Pipeline Node Order: `ambassador` → `leader_generate` → `human_context_gate` → `tool_curator` → `finalize_phase1`.
- Enhanced `TeamState` to track `tools_path` and `curator_failed` status.


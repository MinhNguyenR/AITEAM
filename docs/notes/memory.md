# Codebase Memory

**Last Updated:** 2026-05-04
**Total Files:** 401
**Total Lines of Code:** 34010


## Structure
`	ext
|-- agents/
|   |-- team_map/
|   |   |-- __init__.py (5 lines)
|   |   \-- _team_map.py (5 lines)
|   |-- __init__.py (1 lines)
|   |-- _api_client.py (580 lines)
|   |-- _budget_manager.py (34 lines)
|   |-- _knowledge_manager.py (38 lines)
|   |-- ambassador.py (413 lines)
|   |-- base_agent.py (351 lines)
|   |-- browser.py (0 lines)
|   |-- chat_agent.py (49 lines)
|   |-- commander.py (0 lines)
|   |-- compact_worker.py (99 lines)
|   |-- expert.py (338 lines)
|   |-- final_reviewer.py (0 lines)
|   |-- fix_worker.py (0 lines)
|   |-- leader.py (296 lines)
|   |-- llm_usage.py (12 lines)
|   |-- researcher.py (0 lines)
|   |-- reviewer.py (0 lines)
|   |-- secretary.py (0 lines)
|   |-- test_agent.py (0 lines)
|   |-- tool_curator.py (218 lines)
|   \-- worker.py (0 lines)
|-- aiteam.egg-info/
|   |-- dependency_links.txt (1 lines)
|   |-- entry_points.txt (2 lines)
|   |-- PKG-INFO (29 lines)
|   |-- requires.txt (22 lines)
|   |-- SOURCES.txt (339 lines)
|   \-- top_level.txt (3 lines)
|-- core/
|   |-- api/
|   |   \-- __init__.py (1 lines)
|   |-- app_state/
|   |   |-- __init__.py (41 lines)
|   |   |-- _io.py (17 lines)
|   |   |-- actions.py (38 lines)
|   |   |-- context_state.py (68 lines)
|   |   |-- overrides.py (163 lines)
|   |   \-- settings.py (83 lines)
|   |-- cli/
|   |   |-- chrome/
|   |   |-- python_cli/
|   |   |   |-- entrypoints/
|   |   |   |   |-- __init__.py (0 lines)
|   |   |   |   \-- app.py (119 lines)
|   |   |   |-- features/
|   |   |   |   |-- ask/
|   |   |   |   |   |-- __init__.py (0 lines)
|   |   |   |   |   |-- chat_manager.py (168 lines)
|   |   |   |   |   |-- flow.py (186 lines)
|   |   |   |   |   |-- history_renderer.py (85 lines)
|   |   |   |   |   \-- model_selector.py (64 lines)
|   |   |   |   |-- change/
|   |   |   |   |   |-- __init__.py (17 lines)
|   |   |   |   |   |-- detail.py (295 lines)
|   |   |   |   |   |-- flow.py (14 lines)
|   |   |   |   |   |-- helpers.py (54 lines)
|   |   |   |   |   \-- list.py (81 lines)
|   |   |   |   |-- context/
|   |   |   |   |   |-- __init__.py (22 lines)
|   |   |   |   |   |-- common.py (104 lines)
|   |   |   |   |   |-- confirm.py (83 lines)
|   |   |   |   |   |-- flow.py (29 lines)
|   |   |   |   |   |-- monitor_actions.py (71 lines)
|   |   |   |   |   \-- viewer.py (157 lines)
|   |   |   |   |-- dashboard/
|   |   |   |   |   |-- __init__.py (0 lines)
|   |   |   |   |   \-- flow.py (3 lines)
|   |   |   |   |-- settings/
|   |   |   |   |   |-- __init__.py (0 lines)
|   |   |   |   |   \-- flow.py (137 lines)
|   |   |   |   |-- start/
|   |   |   |   |   |-- __init__.py (3 lines)
|   |   |   |   |   |-- clarification_helpers.py (61 lines)
|   |   |   |   |   |-- flow.py (258 lines)
|   |   |   |   |   \-- pipeline_runner.py (177 lines)
|   |   |   |   \-- __init__.py (1 lines)
|   |   |   |-- shell/
|   |   |   |   |-- __init__.py (0 lines)
|   |   |   |   |-- choice_lists.py (16 lines)
|   |   |   |   |-- command_registry.py (162 lines)
|   |   |   |   |-- menu.py (309 lines)
|   |   |   |   |-- monitor_payload.py (49 lines)
|   |   |   |   |-- monitor_queue_drain.py (128 lines)
|   |   |   |   |-- nav.py (28 lines)
|   |   |   |   |-- prompt.py (162 lines)
|   |   |   |   |-- safe_editor.py (40 lines)
|   |   |   |   \-- state.py (278 lines)
|   |   |   |-- ui/
|   |   |   |   |-- palette/
|   |   |   |   |   |-- __init__.py (45 lines)
|   |   |   |   |   |-- app.py (161 lines)
|   |   |   |   |   |-- footer.py (39 lines)
|   |   |   |   |   |-- items.py (170 lines)
|   |   |   |   |   |-- lexer.py (31 lines)
|   |   |   |   |   |-- popup.py (74 lines)
|   |   |   |   |   |-- shared.py (132 lines)
|   |   |   |   |   \-- styles.py (11 lines)
|   |   |   |   |-- .translations.json (215 lines)
|   |   |   |   |-- __init__.py (0 lines)
|   |   |   |   |-- autocomplete.py (183 lines)
|   |   |   |   |-- help_terminal.py (95 lines)
|   |   |   |   |-- helpbox.py (14 lines)
|   |   |   |   |-- palette_app.py (6 lines)
|   |   |   |   |-- palette_shared.py (24 lines)
|   |   |   |   |-- rich_command_palette.py (130 lines)
|   |   |   |   \-- ui.py (129 lines)
|   |   |   |-- workflow/
|   |   |   |   |-- runtime/
|   |   |   |   |   |-- graph/
|   |   |   |   |   |   |-- __init__.py (1 lines)
|   |   |   |   |   |   |-- runner.py (246 lines)
|   |   |   |   |   |   |-- runner_resume.py (45 lines)
|   |   |   |   |   |   |-- runner_rewind.py (230 lines)
|   |   |   |   |   |   \-- runner_ui.py (67 lines)
|   |   |   |   |   |-- persist/
|   |   |   |   |   |   |-- __init__.py (1 lines)
|   |   |   |   |   |   |-- activity_log.py (191 lines)
|   |   |   |   |   |   \-- checkpointer.py (23 lines)
|   |   |   |   |   |-- present/
|   |   |   |   |   |   |-- __init__.py (1 lines)
|   |   |   |   |   |   \-- pipeline_markdown.py (99 lines)
|   |   |   |   |   |-- session/
|   |   |   |   |   |   |-- __init__.py (109 lines)
|   |   |   |   |   |   |-- _session_core.py (50 lines)
|   |   |   |   |   |   |-- session_monitor_manager.py (30 lines)
|   |   |   |   |   |   |-- session_notification.py (174 lines)
|   |   |   |   |   |   |-- session_pause_manager.py (89 lines)
|   |   |   |   |   |   |-- session_pipeline_state.py (758 lines)
|   |   |   |   |   |   \-- session_store.py (45 lines)
|   |   |   |   |   \-- __init__.py (4 lines)
|   |   |   |   |-- tui/
|   |   |   |   |   |-- monitor/
|   |   |   |   |   |   |-- commands/
|   |   |   |   |   |   |   |-- __init__.py (13 lines)
|   |   |   |   |   |   |   |-- ask.py (74 lines)
|   |   |   |   |   |   |   |-- btw.py (118 lines)
|   |   |   |   |   |   |   |-- check.py (65 lines)
|   |   |   |   |   |   |   \-- mixin.py (362 lines)
|   |   |   |   |   |   |-- core/
|   |   |   |   |   |   |   |-- __init__.py (19 lines)
|   |   |   |   |   |   |   |-- _constants.py (62 lines)
|   |   |   |   |   |   |   |-- _content_mixin.py (86 lines)
|   |   |   |   |   |   |   |-- _controls.py (130 lines)
|   |   |   |   |   |   |   |-- _layout_mixin.py (334 lines)
|   |   |   |   |   |   |   |-- _render_mixin.py (398 lines)
|   |   |   |   |   |   |   |-- _tasks_mixin.py (109 lines)
|   |   |   |   |   |   |   |-- _utils.py (45 lines)
|   |   |   |   |   |   |   \-- _views_mixin.py (78 lines)
|   |   |   |   |   |   |-- state/
|   |   |   |   |   |   |   |-- __init__.py (35 lines)
|   |   |   |   |   |   |   |-- _ambassador.py (51 lines)
|   |   |   |   |   |   |   |-- _clarify.py (24 lines)
|   |   |   |   |   |   |   |-- _gate.py (44 lines)
|   |   |   |   |   |   |   |-- _leader.py (102 lines)
|   |   |   |   |   |   |   |-- _pipeline.py (28 lines)
|   |   |   |   |   |   |   \-- _tool_curator.py (87 lines)
|   |   |   |   |   |   |-- __init__.py (12 lines)
|   |   |   |   |   |   |-- app.py (309 lines)
|   |   |   |   |   |   |-- helpers.py (476 lines)
|   |   |   |   |   |   \-- screens.py (309 lines)
|   |   |   |   |   |-- shared/
|   |   |   |   |   |   |-- __init__.py (1 lines)
|   |   |   |   |   |   |-- agent_cards.py (129 lines)
|   |   |   |   |   |   |-- btw_inline.py (84 lines)
|   |   |   |   |   |   \-- display_policy.py (19 lines)
|   |   |   |   |   |-- __init__.py (1 lines)
|   |   |   |   |   \-- __main__.py (6 lines)
|   |   |   |   \-- __init__.py (1 lines)
|   |   |   |-- __init__.py (5 lines)
|   |   |   \-- i18n.py (990 lines)
|   |   |-- workflow/
|   |   |   |-- runtime/
|   |   |   \-- tui/
|   |   \-- __init__.py (8 lines)
|   |-- config/
|   |   |-- registry/
|   |   |   |-- coding/
|   |   |   |   |-- __init__.py (29 lines)
|   |   |   |   |-- chat.py (28 lines)
|   |   |   |   |-- devops.py (17 lines)
|   |   |   |   |-- fixers.py (61 lines)
|   |   |   |   |-- leaders.py (39 lines)
|   |   |   |   |-- researchers.py (39 lines)
|   |   |   |   |-- reviewers.py (47 lines)
|   |   |   |   |-- support.py (50 lines)
|   |   |   |   |-- system.py (39 lines)
|   |   |   |   |-- testers.py (28 lines)
|   |   |   |   \-- workers.py (61 lines)
|   |   |   \-- __init__.py (34 lines)
|   |   |-- __init__.py (26 lines)
|   |   |-- constants.py (35 lines)
|   |   |-- hardware.py (107 lines)
|   |   |-- pricing.py (172 lines)
|   |   |-- runtime_config.py (14 lines)
|   |   |-- service.py (253 lines)
|   |   \-- settings.py (98 lines)
|   |-- dashboard/
|   |   |-- application/
|   |   |   |-- __init__.py (13 lines)
|   |   |   \-- data.py (26 lines)
|   |   |-- export/
|   |   |   \-- __init__.py (5 lines)
|   |   |-- output/
|   |   |   |-- __init__.py (1 lines)
|   |   |   |-- exporters.py (230 lines)
|   |   |   \-- pdf_export.py (172 lines)
|   |   |-- presentation/
|   |   |   |-- shell/
|   |   |   |   \-- __init__.py (5 lines)
|   |   |   |-- tui/
|   |   |   |   \-- __init__.py (3 lines)
|   |   |   \-- __init__.py (2 lines)
|   |   |-- reporting/
|   |   |   |-- __init__.py (13 lines)
|   |   |   |-- report_model.py (131 lines)
|   |   |   |-- report_txt_format.py (116 lines)
|   |   |   |-- state.py (83 lines)
|   |   |   \-- text_export.py (35 lines)
|   |   |-- shell/
|   |   |   |-- __init__.py (1 lines)
|   |   |   |-- app.py (168 lines)
|   |   |   |-- budget.py (55 lines)
|   |   |   |-- data.py (11 lines)
|   |   |   |-- history.py (191 lines)
|   |   |   \-- total.py (68 lines)
|   |   |-- tui/
|   |   |   |-- __init__.py (1 lines)
|   |   |   |-- log_console.py (6 lines)
|   |   |   |-- panels.py (12 lines)
|   |   |   |-- render.py (189 lines)
|   |   |   \-- utils.py (60 lines)
|   |   \-- __init__.py (5 lines)
|   |-- domain/
|   |   |-- prompts/
|   |   |   |-- __init__.py (39 lines)
|   |   |   |-- ambassador.py (60 lines)
|   |   |   |-- ask_mode.py (43 lines)
|   |   |   |-- btw_coordinator.py (56 lines)
|   |   |   |-- clarification.py (40 lines)
|   |   |   |-- expert.py (61 lines)
|   |   |   \-- leader.py (117 lines)
|   |   |-- skills/
|   |   |   |-- examples/
|   |   |   |   |-- __init__.py (5 lines)
|   |   |   |   \-- echo.py (15 lines)
|   |   |   |-- __init__.py (22 lines)
|   |   |   |-- _registry.py (35 lines)
|   |   |   \-- hooks.py (12 lines)
|   |   |-- __init__.py (0 lines)
|   |   |-- agent_protocol.py (51 lines)
|   |   |-- delta_brief.py (87 lines)
|   |   |-- pipeline_state.py (16 lines)
|   |   \-- routing_map.py (52 lines)
|   |-- frontends/
|   |   |-- cli/
|   |   |   |-- __init__.py (13 lines)
|   |   |   |-- app.py (6 lines)
|   |   |   |-- context.py (7 lines)
|   |   |   |-- settings.py (6 lines)
|   |   |   \-- start.py (6 lines)
|   |   |-- dashboard/
|   |   |   \-- __init__.py (9 lines)
|   |   |-- tui/
|   |   |   |-- __init__.py (4 lines)
|   |   |   |-- __main__.py (9 lines)
|   |   |   \-- monitor.py (6 lines)
|   |   \-- __init__.py (2 lines)
|   |-- orchestration/
|   |   |-- __init__.py (13 lines)
|   |   |-- pipeline_artifacts.py (101 lines)
|   |   |-- team_graph.py (66 lines)
|   |   |-- team_nodes.py (130 lines)
|   |   |-- team_routing.py (18 lines)
|   |   \-- team_state.py (20 lines)
|   |-- resources/
|   |   |-- fonts/
|   |   |   |-- Inter_18pt-Regular.ttf (7235 lines)
|   |   |   \-- Inter_24pt-Bold.ttf (7394 lines)
|   |   \-- README.md (3 lines)
|   |-- runtime/
|   |   |-- __init__.py (4 lines)
|   |   \-- session.py (4 lines)
|   |-- services/
|   |   |-- __init__.py (1 lines)
|   |   \-- dashboard_data.py (12 lines)
|   |-- storage/
|   |   |-- knowledge/
|   |   |   |-- __init__.py (10 lines)
|   |   |   |-- repository.py (28 lines)
|   |   |   |-- sqlite_repository.py (418 lines)
|   |   |   \-- vault_key.py (61 lines)
|   |   |-- __init__.py (30 lines)
|   |   |-- ask_chat_store.py (278 lines)
|   |   |-- ask_history.py (102 lines)
|   |   |-- graphrag_store.py (253 lines)
|   |   |-- knowledge_store.py (65 lines)
|   |   |-- knowledge_text.py (95 lines)
|   |   \-- prompt_store_protocol.py (27 lines)
|   |-- __init__.py (1 lines)
|   |-- bootstrap.py (18 lines)
|   |-- paths.py (12 lines)
|   \-- runtime_config.py (4 lines)
|-- docs/
|   |-- design/
|   |   \-- README.md (3 lines)
|   |-- notes/
|   |   |-- memory.md (1304 lines)
|   |   \-- README.md (3 lines)
|   |-- skills_admin/
|   |   |-- AgentAudit/
|   |   |   |-- AGENT_AUDIT.md (47 lines)
|   |   |   |-- PROJECT_SUMMARY.md (24 lines)
|   |   |   \-- README.md (17 lines)
|   |   |-- GraphRag/
|   |   |   |-- PROJECT_MAP.md (231 lines)
|   |   |   |-- PROJECT_SUMMARY.md (285 lines)
|   |   |   \-- README.md (27 lines)
|   |   \-- README.md (8 lines)
|   |-- REPO_LAYOUT.md (19 lines)
|   \-- security.md (6 lines)
|-- scripts/
|   |-- README.md (3 lines)
|   \-- run_aiteam.py (6 lines)
|-- tests/
|   |-- cli/
|   |   |-- test_cli_prompt_ux.py (89 lines)
|   |   \-- test_ui_clear.py (21 lines)
|   |-- conftest.py (8 lines)
|   |-- test_activity_badges.py (56 lines)
|   |-- test_activity_log.py (156 lines)
|   |-- test_ambassador_methods.py (204 lines)
|   |-- test_ambassador_tier_classification.py (110 lines)
|   |-- test_api_client_stream.py (218 lines)
|   |-- test_api_client_unit.py (218 lines)
|   |-- test_ask_chat_manager.py (117 lines)
|   |-- test_ask_chat_store.py (258 lines)
|   |-- test_ask_history.py (162 lines)
|   |-- test_base_agent_extra.py (220 lines)
|   |-- test_budget_guard.py (54 lines)
|   |-- test_budget_manager.py (65 lines)
|   |-- test_cli_security_helpers.py (61 lines)
|   |-- test_cli_state.py (165 lines)
|   |-- test_cli_state_overrides.py (152 lines)
|   |-- test_config_hardware.py (116 lines)
|   |-- test_config_pricing.py (261 lines)
|   |-- test_config_registry.py (76 lines)
|   |-- test_config_service.py (239 lines)
|   |-- test_config_settings.py (102 lines)
|   |-- test_dashboard_batches_browser.py (34 lines)
|   |-- test_dashboard_helpers.py (50 lines)
|   |-- test_dashboard_history_browser.py (27 lines)
|   |-- test_dashboard_history_pure.py (66 lines)
|   |-- test_dashboard_pdf.py (82 lines)
|   |-- test_dashboard_pdf_font_fallback.py (56 lines)
|   |-- test_dashboard_range_picker.py (17 lines)
|   |-- test_dashboard_range_state.py (102 lines)
|   |-- test_dashboard_render.py (41 lines)
|   |-- test_dashboard_tui_utils.py (76 lines)
|   |-- test_dashboard_turn_views.py (77 lines)
|   |-- test_delta_brief.py (133 lines)
|   |-- test_domain_prompts.py (118 lines)
|   |-- test_env_guard.py (140 lines)
|   |-- test_expert_agent.py (297 lines)
|   |-- test_expert_coplan.py (175 lines)
|   |-- test_export_txt_format.py (21 lines)
|   |-- test_file_manager.py (189 lines)
|   |-- test_frontend_runtime_facades.py (26 lines)
|   |-- test_graphrag_store.py (157 lines)
|   |-- test_graphrag_utils.py (73 lines)
|   |-- test_import_smoke_python_cli.py (22 lines)
|   |-- test_input_validator.py (49 lines)
|   |-- test_json_utils.py (58 lines)
|   |-- test_knowledge_manager.py (127 lines)
|   |-- test_knowledge_repository.py (59 lines)
|   |-- test_knowledge_store_module.py (101 lines)
|   |-- test_knowledge_text.py (156 lines)
|   |-- test_leader_flow.py (143 lines)
|   |-- test_leader_generate.py (216 lines)
|   |-- test_leader_pure.py (124 lines)
|   |-- test_llm_usage.py (59 lines)
|   |-- test_logger_utils.py (69 lines)
|   |-- test_monitor_commands_regenerate.py (67 lines)
|   |-- test_monitor_helpers_tier_display.py (16 lines)
|   |-- test_monitor_payload.py (88 lines)
|   |-- test_orchestration_split.py (12 lines)
|   |-- test_palette_package.py (120 lines)
|   |-- test_pure_cli_modules.py (201 lines)
|   |-- test_refactor_facades.py (38 lines)
|   |-- test_report_txt_format.py (145 lines)
|   |-- test_runner_inline_progress.py (76 lines)
|   |-- test_runner_rewind_logic.py (268 lines)
|   |-- test_runner_rewind_pure.py (95 lines)
|   |-- test_runtime_config.py (34 lines)
|   |-- test_security_and_config.py (145 lines)
|   |-- test_session_monitor_manager.py (62 lines)
|   |-- test_session_notification.py (132 lines)
|   |-- test_session_notification_extra.py (181 lines)
|   |-- test_session_pause_manager.py (128 lines)
|   |-- test_session_pipeline_state.py (230 lines)
|   |-- test_session_pipeline_state_extra.py (191 lines)
|   |-- test_session_pipeline_state_uncovered.py (166 lines)
|   |-- test_session_store.py (72 lines)
|   |-- test_skills_registry.py (40 lines)
|   |-- test_sqlite_repository_extra.py (195 lines)
|   |-- test_team_map_routing.py (66 lines)
|   |-- test_tracker_aggregate.py (83 lines)
|   |-- test_tracker_aggregate_extra.py (136 lines)
|   |-- test_tracker_batches.py (118 lines)
|   |-- test_tracker_batches_summarize.py (143 lines)
|   |-- test_tracker_budget.py (103 lines)
|   |-- test_tracker_cache.py (81 lines)
|   |-- test_tracker_dashboard_summary.py (28 lines)
|   |-- test_tracker_helpers.py (133 lines)
|   |-- test_tracker_usage.py (74 lines)
|   |-- test_vault_key.py (67 lines)
|   |-- test_workflow_activity_format.py (14 lines)
|   \-- test_workflow_toast_queue.py (49 lines)
|-- utils/
|   |-- tracker/
|   |   |-- __init__.py (86 lines)
|   |   |-- tracker_aggregate.py (175 lines)
|   |   |-- tracker_batches.py (126 lines)
|   |   |-- tracker_budget.py (75 lines)
|   |   |-- tracker_cache.py (45 lines)
|   |   |-- tracker_helpers.py (118 lines)
|   |   |-- tracker_openrouter.py (37 lines)
|   |   \-- tracker_usage.py (117 lines)
|   |-- __init__.py (1 lines)
|   |-- activity_badges.py (68 lines)
|   |-- ask_history.py (36 lines)
|   |-- budget_guard.py (27 lines)
|   |-- delta_brief.py (20 lines)
|   |-- env_guard.py (92 lines)
|   |-- file_manager.py (127 lines)
|   |-- free_model_finder.py (132 lines)
|   |-- graphrag_utils.py (47 lines)
|   |-- input_validator.py (36 lines)
|   |-- json_utils.py (57 lines)
|   \-- logger.py (43 lines)
|-- .env (1 lines)
|-- .env.example (7 lines)
|-- .gitignore (20 lines)
|-- CHANGELOG.md (75 lines)
|-- CLAUDE.md (65 lines)
|-- LICENSE (201 lines)
|-- MANIFEST.in (5 lines)
|-- package-lock.json (6 lines)
|-- pyproject.toml (82 lines)
\-- README.md (472 lines)
`

## Connections (Dependency Map)

### Agents
- **agents/_api_client.py**
  - from core.config import config
  - from core.config.constants import API_BASE_BACKOFF_SEC, API_MAX_RETRIES
  - from core.config.registry import get_worker_config
  - from core.runtime import session as _ws_mod
  - from utils.budget_guard import DashboardBudgetExceeded, ensure_dashboard_budget_available
  - from utils.env_guard import redact_for_display
  - from utils.logger import workflow_event as _wfe
  - from utils.tracker import append_usage_log
  - from utils.tracker import compute_cost_usd
- **agents/_budget_manager.py**
  - from agents.base_agent import BudgetExceeded
- **agents/_knowledge_manager.py**
  - from core.storage import CompressedBrain
- **agents/ambassador.py**
  - from agents.base_agent import BaseAgent
  - from core.bootstrap import ensure_project_root
  - from core.config import config
  - from core.domain.delta_brief import DeltaBrief
  - from core.domain.prompts import AMBASSADOR_SYSTEM_PROMPT
  - from core.domain.routing_map import selected_leader_for_tier
  - from core.runtime import session as _ws
  - from utils.graphrag_utils import try_ingest_prompt_doc
  - from utils.input_validator import validate_user_prompt
  - from utils.json_utils import parse_json_resilient, strip_markdown_fences
  - from utils.logger import workflow_event as _wfe
  - from utils.tracker import append_usage_log, compute_cost_usd
- **agents/base_agent.py**
  - from agents._api_client import APIClient
  - from agents._budget_manager import BudgetManager
  - from agents._knowledge_manager import KnowledgeManager
  - from core.app_state import get_prompt_overrides
  - from core.bootstrap import ensure_project_root
  - from core.config import config
  - from core.config.constants import API_BASE_BACKOFF_SEC, API_MAX_RETRIES
  - from core.config.settings import openrouter_base_url as _base_url
- **agents/chat_agent.py**
  - from core.config import config as _config
  - from core.config.settings import openrouter_base_url
  - from core.domain.prompts import ASK_MODE_SYSTEM_PROMPT
- **agents/compact_worker.py**
  - from agents.base_agent import BaseAgent
  - from core.config import config
- **agents/expert.py**
  - from agents.base_agent import BaseAgent
  - from core.config import config
  - from core.domain.prompts import (
  - from utils.file_manager import atomic_write_text
  - from utils.graphrag_utils import try_ingest_context
- **agents/leader.py**
  - from agents.base_agent import BaseAgent
  - from core.config import config
  - from core.config.constants import STATE_CHAR_LIMIT_DEFAULT, STATE_CHAR_LIMIT_LOW
  - from core.domain.delta_brief import is_no_context
  - from core.domain.prompts import (
  - from core.runtime import session as _ws
  - from utils.file_manager import atomic_write_text
  - from utils.graphrag_utils import try_ingest_context, try_ingest_prompt_doc
- **agents/llm_usage.py**
  - from agents._api_client import (
- **agents/team_map/_team_map.py**
  - from core.orchestration.team_graph import TeamState, get_graph, route_after_leader, route_entry
- **agents/tool_curator.py**
  - from agents.base_agent import BaseAgent
  - from core.config import config
  - from core.runtime import session as ws
  - from utils.file_manager import atomic_write_text
  - from utils.graphrag_utils import try_ingest_context, try_ingest_prompt_doc

### Core
- **core/app_state/actions.py**
  - from core.config.constants import ACTIONS_LOG_FILE
  - from utils.env_guard import redact_for_display
- **core/app_state/context_state.py**
  - from core.storage import ask_history
- **core/app_state/overrides.py**
  - from core.config import Config
  - from core.config.constants import MODEL_OVERRIDES_FILE
  - from core.storage.knowledge.vault_key import load_or_create_vault_key
- **core/app_state/settings.py**
  - from core.config.constants import LEGACY_SETTINGS_FILE, SETTINGS_FILE
- **core/cli/python_cli/__init__.py**
  - from core.cli.python_cli.shell import prompt as cli_prompt
- **core/cli/python_cli/entrypoints/app.py**
  - from core.app_state import get_cli_settings
  - from core.bootstrap import ensure_project_root
  - from core.cli.python_cli.shell.menu import (
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.ui.ui import PASTEL_BLUE, console
- **core/cli/python_cli/features/ask/chat_manager.py**
  - from core.app_state import log_system_action
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.shell.prompt import wait_enter as _we
  - from core.cli.python_cli.ui.palette_app import ask_with_palette
  - from core.cli.python_cli.ui.ui import PASTEL_BLUE, clear_screen, console
  - from core.storage import ask_history
- **core/cli/python_cli/features/ask/flow.py**
  - from core.app_state import get_prompt_overrides, log_system_action
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.ui.ui import console, clear_screen
  - from core.domain.prompts import ASK_MODE_SYSTEM_PROMPT
  - from core.storage import ask_history
  - from utils.input_validator import PromptInvalid, PromptTooLong, validate_user_prompt
- **core/cli/python_cli/features/ask/history_renderer.py**
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.ui.palette import ask_with_palette
  - from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, SOFT_WHITE, console
- **core/cli/python_cli/features/ask/model_selector.py**
  - from agents._api_client import make_openai_client
  - from core.app_state import get_sampling_overrides
  - from core.app_state import log_system_action
  - from core.config import config
  - from core.config.settings import openrouter_base_url
  - from utils.budget_guard import ensure_dashboard_budget_available
  - from utils.tracker import append_usage_log, compute_cost_usd
- **core/cli/python_cli/features/change/detail.py**
  - from core.cli.python_cli.features.change.helpers import indexed_workers, prompt_panel_content, score_bar
  - from core.cli.python_cli.i18n import t as _t
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice, wait_enter
  - from core.cli.python_cli.shell.state import (
  - from core.cli.python_cli.ui.palette_app import ask_with_palette
  - from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, clear_screen, console
  - from core.config import config
  - from core.config.pricing import fetch_model_detail
  - from utils.free_model_finder import show_free_model_picker
- **core/cli/python_cli/features/change/flow.py**
  - from core.cli.python_cli.features.change import (
- **core/cli/python_cli/features/change/helpers.py**
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.ui.ui import console
  - from core.config import config
- **core/cli/python_cli/features/change/list.py**
  - from core.cli.python_cli.features.change.helpers import indexed_workers, price_str
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.ui.palette_app import ask_with_palette
  - from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, SOFT_WHITE, clear_screen, console, print_header
- **core/cli/python_cli/features/context/common.py**
  - from core.app_state import load_context_state, log_system_action, update_context_state
  - from core.cli.python_cli.workflow.runtime.persist.activity_log import clear_workflow_activity_log
  - from core.config import config
  - from core.domain.delta_brief import STATE_FILENAME
  - from core.runtime import session as ws
  - from core.storage.graphrag_store import delete_by_context_path
  - from utils.file_manager import latest_context_path, paths_for_task
  - from utils.logger import log_state_json_deleted_on_accept
- **core/cli/python_cli/features/context/confirm.py**
  - from core.app_state import log_system_action, update_context_state
  - from core.cli.python_cli.features.context.common import full_context_cleanup, graphrag_drop
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.shell.prompt import ask_choice
  - from core.cli.python_cli.shell.safe_editor import run_editor_on_file
  - from core.cli.python_cli.ui.ui import BRIGHT_BLUE, PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, clear_screen, console, print_divider, print_header
- **core/cli/python_cli/features/context/flow.py**
  - from core.cli.python_cli.features.context import (
- **core/cli/python_cli/features/context/monitor_actions.py**
  - from core.app_state import log_system_action, update_context_state
  - from core.cli.python_cli.features.context.common import (
  - from core.cli.python_cli.workflow.runtime.graph.runner import resume_workflow
  - from core.cli.python_cli.workflow.runtime.persist.activity_log import clear_workflow_activity_log
  - from core.domain.delta_brief import is_no_context
  - from core.runtime import session as ws
- **core/cli/python_cli/features/context/viewer.py**
  - from core.app_state import load_context_state, log_system_action, update_context_state
  - from core.cli.python_cli.features.context.common import (
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.choice_lists import context_viewer_choices
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.shell.prompt import ask_choice, wait_enter
  - from core.cli.python_cli.shell.safe_editor import run_editor_on_file
  - from core.cli.python_cli.ui.palette import ask_with_palette
  - from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, clear_screen, console, print_header
  - from core.cli.python_cli.workflow.runtime.graph.runner import resume_workflow
  - from core.domain.delta_brief import is_no_context
  - from core.runtime import session as ws
- **core/cli/python_cli/features/dashboard/flow.py**
  - from core.frontends.dashboard import show_dashboard
- **core/cli/python_cli/features/settings/flow.py**
  - from core.app_state import get_cli_settings, save_cli_settings
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.shell.prompt import ask_choice
  - from core.cli.python_cli.ui.ui import (
- **core/cli/python_cli/features/start/clarification_helpers.py**
  - from agents._api_client import make_openai_client
  - from core.config import config as _cfg
  - from core.config.settings import openrouter_base_url
  - from core.domain.prompts import build_clarification_qa_prompt
  - from utils.file_manager import paths_for_task
- **core/cli/python_cli/features/start/flow.py**
  - from core.app_state import get_cli_settings, log_system_action
  - from core.cli.python_cli.features.ask.flow import _pick_chat_on_ask_entry, looks_like_code_intent
  - from core.cli.python_cli.features.context.flow import (
  - from core.cli.python_cli.features.start.clarification_helpers import is_ambiguous_task, generate_clarification_qa
  - from core.cli.python_cli.features.start.pipeline_runner import start_pipeline_from_tui
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.choice_lists import start_mode_choices
  - from core.cli.python_cli.shell.command_registry import START_MODE_BY_NUMBER
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.shell.prompt import ask_choice, wait_enter
  - from core.cli.python_cli.ui.palette_app import ask_with_palette
  - from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, console
  - from core.cli.python_cli.workflow.runtime.graph.runner import run_agent_graph
  - from core.cli.python_cli.workflow.runtime.persist.activity_log import list_recent_activity
  - from core.frontends.tui import run_workflow_list_view
  - from core.orchestration.pipeline_artifacts import write_task_state_json
  - from core.runtime import session as ws_session
  - from utils import tracker as _tr
  - from utils.file_manager import paths_for_task
  - from utils.logger import workflow_event
- **core/cli/python_cli/features/start/pipeline_runner.py**
  - from agents.ambassador import Ambassador
  - from core.app_state.settings import get_cli_settings
  - from core.cli.python_cli.features.start.clarification_helpers import is_ambiguous_task, generate_clarification_qa
  - from core.cli.python_cli.workflow.runtime.graph.runner import run_agent_graph
  - from core.domain.delta_brief import DeltaBrief
  - from core.orchestration.pipeline_artifacts import write_task_state_json
  - from core.runtime import session as ws_session
  - from utils import tracker as _tr
  - from utils.logger import workflow_event
- **core/cli/python_cli/i18n.py**
  - from core.app_state import get_cli_settings
- **core/cli/python_cli/shell/choice_lists.py**
  - from core.cli.python_cli.shell.command_registry import menu_commands
- **core/cli/python_cli/shell/command_registry.py**
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/shell/menu.py**
  - from core.app_state import (
  - from core.cli.python_cli.features.ask.flow import run_ask_mode
  - from core.cli.python_cli.features.change.flow import pick_role_key_from_indexed_workers, show_role_detail
  - from core.cli.python_cli.features.context.flow import find_context_md, is_no_context, show_context as _show_context_flow
  - from core.cli.python_cli.features.settings.flow import show_settings
  - from core.cli.python_cli.features.start.flow import run_start as _run_start_flow
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.command_registry import help_screen_markdown, MAIN_MENU_VALID_CHOICES, MAIN_PROMPT_LABEL
  - from core.cli.python_cli.shell.monitor_queue_drain import drain_monitor_command_queue
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice
  - from core.cli.python_cli.ui.help_terminal import spawn_help_in_new_terminal
  - from core.cli.python_cli.ui.rich_command_palette import capture_menu_ansi, render_command_palette
  - from core.cli.python_cli.ui.ui import (
  - from core.config import config
  - from core.frontends.dashboard import show_dashboard
  - from core.frontends.tui import run_workflow_list_view
  - from core.runtime import session as _ws
  - from core.runtime import session as ws
  - from utils.env_guard import find_active_env_path, run_startup_checks
  - from utils.file_manager import ensure_ask_data_dir, ensure_workflow_dir
- **core/cli/python_cli/shell/monitor_queue_drain.py**
  - from core.app_state import log_system_action
  - from core.cli.python_cli.features.context.flow import (
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.monitor_payload import resolve_trusted_project_root, sanitize_monitor_prompt
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.ui.ui import console
  - from core.cli.python_cli.workflow.runtime.graph.runner import rewind_to_checkpoint, rewind_to_last_gate
  - from core.cli.python_cli.workflow.runtime.persist.activity_log import clear_workflow_activity_log
  - from core.config import config
  - from core.runtime import session as ws
- **core/cli/python_cli/shell/prompt.py**
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.ui.autocomplete import ChoiceCompleter
  - from core.cli.python_cli.ui.palette_app import ask_with_palette
- **core/cli/python_cli/shell/state.py**
  - from core.app_state import actions as _actions
  - from core.app_state import context_state as _context
  - from core.app_state import overrides as _overrides
  - from core.app_state import settings as _settings
  - from core.config.constants import (
- **core/cli/python_cli/ui/autocomplete.py**
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/ui/help_terminal.py**
  - from core.cli.python_cli.shell.command_registry import HELP_SCREEN_MARKDOWN
  - from core.cli.python_cli.shell.prompt import wait_enter
- **core/cli/python_cli/ui/helpbox.py**
  - from core.cli.python_cli.ui.ui import console
- **core/cli/python_cli/ui/palette/footer.py**
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.ui.autocomplete import COMMAND_REGISTRY
- **core/cli/python_cli/ui/palette/items.py**
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.ui.autocomplete import COMMAND_REGISTRY, get_popup_sections
- **core/cli/python_cli/ui/palette/popup.py**
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/ui/palette/styles.py**
  - from core.cli.python_cli.ui.ui import PASTEL_CYAN, SOFT_WHITE
- **core/cli/python_cli/ui/palette_app.py**
  - from core.cli.python_cli.ui.palette import ask_with_palette
- **core/cli/python_cli/ui/palette_shared.py**
  - from core.cli.python_cli.ui.palette import (
- **core/cli/python_cli/ui/rich_command_palette.py**
  - from core.app_state import get_cli_settings, is_context_active
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.choice_lists import menu_commands
  - from core.cli.python_cli.ui.ui import (
- **core/cli/python_cli/workflow/runtime/graph/runner.py**
  - from core.app_state.actions import log_system_action
  - from core.app_state.context_state import update_context_state
  - from core.bootstrap import REPO_ROOT
  - from core.cli.python_cli.ui.ui import console
  - from core.domain.routing_map import pipeline_nodes_for_tier
  - from core.orchestration import get_graph
  - from utils.logger import artifact_detail, workflow_event
- **core/cli/python_cli/workflow/runtime/graph/runner_resume.py**
  - from core.orchestration import get_graph
- **core/cli/python_cli/workflow/runtime/graph/runner_rewind.py**
  - from core.orchestration import get_graph
  - from utils.file_manager import paths_for_task
  - from utils.logger import artifact_detail, workflow_event
- **core/cli/python_cli/workflow/runtime/persist/activity_log.py**
  - from utils.activity_badges import format_action_with_badge, human_text_for
  - from utils.env_guard import redact_for_display
  - from utils.file_manager import ensure_workflow_dir
- **core/cli/python_cli/workflow/runtime/session/_session_core.py**
  - from utils.file_manager import ensure_db_dir, ensure_workflow_dir
- **core/cli/python_cli/workflow/runtime/session/session_pipeline_state.py**
  - from core.cli.python_cli.features.context.flow import find_context_md, is_no_context
- **core/cli/python_cli/workflow/runtime/session/session_store.py**
  - from utils.file_manager import ensure_workflow_dir
- **core/cli/python_cli/workflow/tui/monitor/app.py**
  - from core.cli.python_cli.features.context import find_context_md
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/workflow/tui/monitor/commands/ask.py**
  - from core.cli.python_cli.features.ask.model_selector import _ask_model
  - from core.cli.python_cli.i18n import t
  - from core.domain.prompts import ASK_MODE_SYSTEM_PROMPT
- **core/cli/python_cli/workflow/tui/monitor/commands/btw.py**
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/workflow/tui/monitor/commands/check.py**
  - from core.cli.python_cli.features.context import find_context_md
  - from core.cli.python_cli.features.context.monitor_actions import apply_context_accept_from_monitor
  - from core.cli.python_cli.features.context.monitor_actions import apply_context_delete_from_monitor
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.safe_editor import build_editor_argv
- **core/cli/python_cli/workflow/tui/monitor/commands/mixin.py**
  - from core.app_state import log_system_action
  - from core.cli.python_cli.features.context.monitor_actions import apply_context_accept_from_monitor
  - from core.cli.python_cli.features.context.monitor_actions import apply_context_delete_from_monitor
  - from core.cli.python_cli.features.start.flow import start_pipeline_from_tui
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/workflow/tui/monitor/core/_constants.py**
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/workflow/tui/monitor/core/_content_mixin.py**
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/workflow/tui/monitor/core/_layout_mixin.py**
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.ui.palette import (
- **core/cli/python_cli/workflow/tui/monitor/core/_render_mixin.py**
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/workflow/tui/monitor/core/_tasks_mixin.py**
  - from core.cli.python_cli.features.context.monitor_actions import apply_context_delete_from_monitor
  - from core.cli.python_cli.features.start.flow import start_pipeline_from_tui
- **core/cli/python_cli/workflow/tui/monitor/core/_utils.py**
  - from core.cli.python_cli.i18n import t
  - from core.config import config as _cfg
- **core/cli/python_cli/workflow/tui/monitor/core/_views_mixin.py**
  - from core.cli.python_cli.features.context.flow import find_context_md, is_no_context
- **core/cli/python_cli/workflow/tui/monitor/helpers.py**
  - from core.bootstrap import REPO_ROOT
  - from core.config import config
  - from core.domain.routing_map import pipeline_nodes_for_tier, pipeline_registry_key_for_tier
  - from core.orchestration import get_graph
- **core/cli/python_cli/workflow/tui/monitor/screens.py**
  - from core.app_state import log_system_action
  - from core.cli.python_cli.features.context.flow import find_context_md, is_no_context
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.safe_editor import run_editor_on_file
- **core/cli/python_cli/workflow/tui/monitor/state/_ambassador.py**
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/workflow/tui/monitor/state/_clarify.py**
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/workflow/tui/monitor/state/_gate.py**
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/workflow/tui/monitor/state/_leader.py**
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/workflow/tui/monitor/state/_pipeline.py**
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/workflow/tui/monitor/state/_tool_curator.py**
  - from core.cli.python_cli.i18n import t
- **core/cli/python_cli/workflow/tui/shared/agent_cards.py**
  - from core.config import config
- **core/cli/python_cli/workflow/tui/shared/btw_inline.py**
  - from agents._api_client import make_openai_client
  - from core.config import config as _cfg
  - from core.config.settings import openrouter_base_url
  - from core.domain.prompts import build_btw_inline_prompt
- **core/config/__init__.py**
  - from core.config.service import Config, ConfigError
- **core/config/pricing.py**
  - from core.config.constants import HTTP_JSON_MAX_BYTES
- **core/config/service.py**
  - from core.app_state import get_model_overrides
  - from core.app_state import get_model_overrides, get_prompt_overrides
  - from core.config.hardware import build_hardware_string, detect_gpu_info, detect_total_ram_gb
  - from core.config.pricing import fetch_openrouter_pricing, sync_live_pricing
  - from core.config.registry import (
  - from core.config.settings import mask_api_key, openrouter_api_key, openrouter_base_url, require_openrouter_api_key, load_environment
- **core/dashboard/application/__init__.py**
  - from core.dashboard.reporting.state import DashboardRangeState
- **core/dashboard/application/data.py**
  - from utils import tracker
- **core/dashboard/export/__init__.py**
  - from core.dashboard.output.exporters import export_excel
  - from core.dashboard.output.pdf_export import export_pdf
  - from core.dashboard.reporting.text_export import export_txt
- **core/dashboard/output/exporters.py**
  - from core.config.constants import HTTP_DOWNLOAD_MAX_BYTES, HTTP_READ_TIMEOUT_SEC
  - from core.paths import FONTS_DIR, LEGACY_ASSETS_FONTS, REPO_ROOT
- **core/dashboard/output/pdf_export.py**
  - from core.paths import FONTS_DIR, LEGACY_ASSETS_FONTS, REPO_ROOT
- **core/dashboard/presentation/shell/__init__.py**
  - from core.dashboard.shell.app import show_dashboard
  - from core.dashboard.shell.history import show_history_browser
  - from core.dashboard.shell.total import show_total_browser
- **core/dashboard/presentation/tui/__init__.py**
  - from core.dashboard.tui.render import header, render_wallet_usage
- **core/dashboard/reporting/report_model.py**
  - from utils import tracker
- **core/dashboard/reporting/state.py**
  - from utils.tracker import parse_usage_timestamp
- **core/dashboard/shell/app.py**
  - from core.app_state.context_state import load_context_state, save_context_state
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice, normalize_global_command
  - from core.cli.python_cli.ui.palette_app import ask_with_palette
  - from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, SOFT_WHITE, BRIGHT_BLUE, clear_screen
  - from core.cli.python_cli.ui.ui import console
  - from utils import tracker
- **core/dashboard/shell/budget.py**
  - from core.app_state.settings import save_cli_settings
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice
  - from core.cli.python_cli.ui.ui import clear_screen
  - from core.cli.python_cli.ui.ui import console
- **core/dashboard/shell/data.py**
  - from core.dashboard.application.data import (
- **core/dashboard/shell/history.py**
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice, normalize_global_command, wait_enter
  - from core.cli.python_cli.ui.palette_app import ask_with_palette
  - from core.cli.python_cli.ui.ui import PASTEL_CYAN, clear_screen
  - from core.cli.python_cli.ui.ui import console
  - from core.dashboard.application import data as dashboard_data
- **core/dashboard/shell/total.py**
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.shell.prompt import GLOBAL_BACK, GLOBAL_EXIT, ask_choice
  - from core.cli.python_cli.ui.ui import clear_screen
  - from core.dashboard.application import data as dashboard_data
- **core/dashboard/tui/panels.py**
  - from core.cli.python_cli.ui.ui import console
- **core/dashboard/tui/render.py**
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.shell.nav import NavToMain
  - from core.cli.python_cli.shell.prompt import ask_choice
  - from core.cli.python_cli.ui.palette_app import ask_with_palette
  - from core.config import config
  - from utils import tracker
  - from utils.tracker import get_usage_summary
- **core/dashboard/tui/utils.py**
  - from core.cli.python_cli.ui.ui import clear_screen
  - from utils import tracker
- **core/domain/agent_protocol.py**
  - from core.domain.agent_protocol import AgentProtocol
- **core/domain/pipeline_state.py**
  - from core.orchestration.pipeline_artifacts import (
- **core/domain/prompts/expert.py**
  - from core.domain.prompts.leader import _PROJECT_MODE_NOTE
- **core/frontends/cli/app.py**
  - from core.cli.python_cli.entrypoints.app import main_loop
- **core/frontends/cli/context.py**
  - from core.cli.python_cli.features.context.confirm import confirm_context
  - from core.cli.python_cli.features.context.viewer import show_context as show_context_viewer
- **core/frontends/cli/settings.py**
  - from core.cli.python_cli.features.settings.flow import show_settings
- **core/frontends/cli/start.py**
  - from core.cli.python_cli.features.start.pipeline_runner import start_pipeline_from_tui
- **core/frontends/dashboard/__init__.py**
  - from core.dashboard.presentation.shell import (
- **core/frontends/tui/__main__.py**
  - from core.frontends.tui.monitor import run_workflow_list_view
- **core/frontends/tui/monitor.py**
  - from core.cli.python_cli.workflow.tui.monitor import WorkflowListApp, run_workflow_list_view
- **core/orchestration/pipeline_artifacts.py**
  - from agents.ambassador import DeltaBrief
  - from agents.leader import BaseLeader, LeaderHigh, LeaderLow, LeaderMed
  - from agents.tool_curator import ToolCurator
  - from core.config import config
  - from core.domain.delta_brief import build_state_payload
  - from core.domain.routing_map import pipeline_registry_key_for_tier
  - from core.runtime import session as ws
  - from utils.file_manager import atomic_write_text, paths_for_task
  - from utils.logger import log_state_json_written, workflow_event
- **core/orchestration/team_graph.py**
  - from core.bootstrap import ensure_project_root
- **core/orchestration/team_nodes.py**
  - from core.app_state.context_state import update_context_state
  - from core.domain.delta_brief import DeltaBrief
  - from core.runtime import session as ws
  - from utils.file_manager import paths_for_task
  - from utils.logger import artifact_detail, workflow_event
- **core/paths.py**
  - from core.bootstrap import REPO_ROOT
- **core/runtime/session.py**
  - from core.cli.python_cli.workflow.runtime.session import *  # noqa: F401,F403
- **core/runtime_config.py**
  - from core.config.runtime_config import RuntimeConfig
- **core/services/dashboard_data.py**
  - from core.dashboard.application.data import (
- **core/storage/__init__.py**
  - from core.storage.ask_chat_store import AskChatSQLiteAPI, get_ask_chat_store
  - from core.storage.graphrag_store import (  # cspell:ignore graphrag
  - from core.storage.knowledge_store import CompressedBrain, extract_keywords, get_brain, smart_search, store_knowledge
- **core/storage/ask_chat_store.py**
  - from utils.file_manager import ensure_ask_data_dir
- **core/storage/ask_history.py**
  - from core.config.constants import AI_TEAM_HOME
  - from core.storage.ask_chat_store import get_ask_chat_store
  - from utils.file_manager import ensure_ask_data_dir
- **core/storage/graphrag_store.py**
  - from core.config.constants import AI_TEAM_HOME
- **core/storage/knowledge/__init__.py**
  - from core.storage.knowledge.repository import KnowledgeRepository
  - from core.storage.knowledge.sqlite_repository import SqliteKnowledgeRepository, VaultMissingKeyError
  - from core.storage.knowledge.vault_key import load_or_create_vault_key
- **core/storage/knowledge/sqlite_repository.py**
  - from core.config import Config
  - from core.config.constants import VAULT_DECOMPRESS_MAX_BYTES
  - from core.storage.knowledge.vault_key import load_or_create_vault_key
  - from core.storage.knowledge_text import (
- **core/storage/knowledge_store.py**
  - from core.config import Config
  - from core.config.constants import AI_TEAM_HOME
  - from core.storage.knowledge.repository import KnowledgeRepository
  - from core.storage.knowledge.sqlite_repository import (
  - from core.storage.knowledge_text import extract_keywords

### Scripts
- **scripts/run_aiteam.py**
  - from core.cli.python_cli.entrypoints.app import main_loop

### Tests
- **tests/cli/test_cli_prompt_ux.py**
  - from core.cli.python_cli import cli_prompt
- **tests/cli/test_ui_clear.py**
  - from core.cli.python_cli.ui import ui
- **tests/conftest.py**
  - from core.bootstrap import ensure_project_root
- **tests/test_activity_badges.py**
  - from utils.activity_badges import (
- **tests/test_activity_log.py**
  - import core.cli.python_cli.workflow.runtime.persist.activity_log as al
- **tests/test_ambassador_methods.py**
  - from agents.ambassador import Ambassador
- **tests/test_ambassador_tier_classification.py**
  - from agents.ambassador import Ambassador
- **tests/test_api_client_stream.py**
  - from agents._api_client import APIClient
  - from agents._budget_manager import BudgetManager
  - from agents.base_agent import BudgetExceeded
  - from utils.budget_guard import DashboardBudgetExceeded
- **tests/test_api_client_unit.py**
  - from agents._api_client import APIClient
  - from agents._budget_manager import BudgetManager
  - from agents.base_agent import BudgetExceeded
  - from core.config.constants import API_MAX_RETRIES
- **tests/test_ask_chat_manager.py**
  - from core.cli.python_cli.features.ask.chat_manager import (
- **tests/test_ask_chat_store.py**
  - from core.storage.ask_chat_store import AskChatSQLiteAPI
  - from core.storage.ask_chat_store import get_ask_chat_store, clear_ask_chat_store_cache
- **tests/test_ask_history.py**
  - import utils.ask_history as ah
- **tests/test_base_agent_extra.py**
  - from agents._budget_manager import BudgetManager
  - from agents.base_agent import BaseAgent, BudgetExceeded
- **tests/test_budget_guard.py**
  - from utils.budget_guard import DashboardBudgetExceeded, ensure_dashboard_budget_available
- **tests/test_budget_manager.py**
  - from agents._budget_manager import BudgetManager
  - from agents.base_agent import BudgetExceeded
- **tests/test_cli_security_helpers.py**
  - from core.cli.python_cli.shell.monitor_payload import (
  - from core.cli.python_cli.shell.safe_editor import build_editor_argv
- **tests/test_cli_state.py**
  - import core.cli.python_cli.shell.state as state_mod
- **tests/test_cli_state_overrides.py**
  - import core.cli.python_cli.shell.state as state_mod
- **tests/test_config_hardware.py**
  - from core.config.hardware import build_hardware_string, detect_gpu_info, detect_total_ram_gb
- **tests/test_config_pricing.py**
  - from core.config.pricing import (
  - from core.config.pricing import fetch_model_detail
- **tests/test_config_registry.py**
  - from core.config.registry import (
- **tests/test_config_service.py**
  - from core.config.service import Config
- **tests/test_config_settings.py**
  - from core.config.settings import (
- **tests/test_dashboard_batches_browser.py**
  - from core.dashboard.reporting.state import DashboardRangeState
  - from core.dashboard.shell import total as total_mod
- **tests/test_dashboard_helpers.py**
  - from core.dashboard.reporting.state import DashboardRangeState
  - from core.dashboard.tui.utils import default_range, paginate, safe_float, safe_int, sort_rows_chronological
- **tests/test_dashboard_history_browser.py**
  - from core.dashboard.reporting.state import DashboardRangeState
  - from core.dashboard.shell import history as history_mod
- **tests/test_dashboard_history_pure.py**
  - from core.dashboard.shell.history import _parse_positive_int
- **tests/test_dashboard_pdf.py**
  - from core.dashboard.output.pdf_export import export_pdf
  - from core.dashboard.reporting.state import DashboardRangeState
- **tests/test_dashboard_pdf_font_fallback.py**
  - from core.dashboard.output.pdf_export import export_pdf
  - from core.dashboard.reporting.state import DashboardRangeState
- **tests/test_dashboard_range_picker.py**
  - import core.dashboard.tui.render as dashboard_render
- **tests/test_dashboard_range_state.py**
  - from core.dashboard.reporting.state import DashboardRangeState, DashboardPalette
- **tests/test_dashboard_render.py**
  - from core.dashboard.tui.render import fmt_budget_line, render_session_usage_panel, render_wallet_usage
- **tests/test_dashboard_tui_utils.py**
  - from core.dashboard.tui.utils import default_range, paginate, safe_float, safe_int
- **tests/test_dashboard_turn_views.py**
  - from core.dashboard.reporting.state import DashboardRangeState
  - from core.dashboard.shell import history as history_mod
  - from core.dashboard.shell import total as total_mod
- **tests/test_delta_brief.py**
  - from utils.delta_brief import (
- **tests/test_domain_prompts.py**
  - from core.domain.prompts import (
- **tests/test_env_guard.py**
  - from utils.env_guard import (
- **tests/test_expert_agent.py**
  - from agents.expert import Expert
- **tests/test_expert_coplan.py**
  - from agents.expert import Expert
- **tests/test_export_txt_format.py**
  - from core.dashboard.reporting.report_model import build_usage_report
  - from core.dashboard.reporting.report_txt_format import format_usage_report_txt
  - from core.dashboard.reporting.state import DashboardRangeState
- **tests/test_file_manager.py**
  - from utils.file_manager import _safe_join
  - from utils.file_manager import atomic_write_text
  - from utils.file_manager import ensure_ask_data_dir
  - from utils.file_manager import ensure_db_dir
  - from utils.file_manager import ensure_run_dir
  - from utils.file_manager import ensure_workflow_dir
  - from utils.file_manager import get_cache_root
  - from utils.file_manager import latest_context_path
  - from utils.file_manager import paths_for_task
- **tests/test_frontend_runtime_facades.py**
  - from core.cli.python_cli.workflow.runtime import session as legacy_session
  - from core.frontends.cli import confirm_context, main_loop, show_context_viewer, show_settings, start_pipeline_from_tui
  - from core.frontends.tui import WorkflowListApp, run_workflow_list_view
  - from core.runtime import session as runtime_session
- **tests/test_graphrag_store.py**
  - import core.storage.graphrag_store as gs
- **tests/test_graphrag_utils.py**
  - from utils.graphrag_utils import try_ingest_context
  - import utils.graphrag_utils as gu
- **tests/test_import_smoke_python_cli.py**
  - import core.cli.python_cli as _root
- **tests/test_input_validator.py**
  - from utils.input_validator import (
- **tests/test_json_utils.py**
  - from utils.json_utils import parse_json_resilient, strip_markdown_fences
- **tests/test_knowledge_manager.py**
  - from agents._knowledge_manager import KnowledgeManager
- **tests/test_knowledge_repository.py**
  - from core.storage.knowledge import SqliteKnowledgeRepository
- **tests/test_knowledge_store_module.py**
  - from core.storage.knowledge_store import _vault_unwrap
  - from core.storage.knowledge_store import _vault_wrap
  - import core.storage.knowledge_store as ks
- **tests/test_knowledge_text.py**
  - from core.storage.knowledge_text import (
- **tests/test_leader_flow.py**
  - from agents.ambassador import Ambassador
  - from agents.leader import LeaderHigh, LeaderLow, LeaderMed
  - from core.bootstrap import ensure_project_root
  - from core.config import config
- **tests/test_leader_generate.py**
  - from agents.leader import BaseLeader
  - from agents.leader import LeaderHigh
  - from agents.leader import LeaderLow
  - from agents.leader import LeaderMed
- **tests/test_leader_pure.py**
  - from agents.leader import LeaderMed
  - from agents.leader import _truncate_state, BaseLeader
  - from core.config.constants import STATE_CHAR_LIMIT_DEFAULT
- **tests/test_llm_usage.py**
  - from agents.llm_usage import chat_completions_create, chat_completions_create_stream, log_usage_event
- **tests/test_logger_utils.py**
  - from utils.logger import artifact_detail, log_state_json_deleted_on_accept, log_state_json_written, workflow_event
- **tests/test_monitor_commands_regenerate.py**
  - from core.cli.python_cli.workflow.tui.monitor.commands.mixin import _CommandsMixin
  - from core.cli.python_cli.workflow.tui.monitor.core._constants import _GATE_REGEN, _GATE_WAITING
- **tests/test_monitor_helpers_tier_display.py**
  - from core.cli.python_cli.workflow.tui.monitor import helpers as mh
- **tests/test_monitor_payload.py**
  - from core.cli.python_cli.shell.monitor_payload import (
- **tests/test_orchestration_split.py**
  - from core.orchestration.team_graph import TeamState, route_after_leader, route_entry
  - from core.orchestration.team_routing import route_after_leader as split_route_after_leader
  - from core.orchestration.team_routing import route_entry as split_route_entry
  - from core.orchestration.team_state import TeamState as split_team_state
- **tests/test_palette_package.py**
  - from core.cli.python_cli.ui.palette import (
  - from core.cli.python_cli.ui.palette.items import _split_registry_into_sections
- **tests/test_pure_cli_modules.py**
  - from core.cli.python_cli.shell.command_registry import (
  - from core.cli.python_cli.shell.nav import NavBack, NavToMain, is_nav_back, is_nav_exit, raise_if_global_nav
  - from core.cli.python_cli.workflow.runtime.present.pipeline_markdown import SPINNER, build_pipeline_markup
  - from core.cli.python_cli.workflow.runtime.present.pipeline_markdown import _glyph
  - from core.cli.python_cli.workflow.tui.shared.display_policy import WorkflowDisplayPolicy, resolve_display_policy
  - from core.domain.routing_map import pipeline_registry_key_for_tier, selected_leader_for_tier
- **tests/test_refactor_facades.py**
  - from agents.team_map._team_map import get_graph
  - from core.app_state import get_cli_settings as app_get_cli_settings
  - from core.app_state import log_system_action as app_log_system_action
  - from core.cli.python_cli.shell.state import get_cli_settings, log_system_action
  - from core.dashboard.application.data import read_usage_log as app_read_usage_log
  - from core.dashboard.shell.data import read_usage_log as shell_read_usage_log
  - from core.domain.pipeline_state import write_task_state_json
  - from core.orchestration.pipeline_artifacts import write_task_state_json as orchestration_write
  - from core.orchestration.team_graph import get_graph as orchestration_get_graph
  - from core.services.dashboard_data import read_usage_log as services_read_usage_log
- **tests/test_report_txt_format.py**
  - from core.dashboard.reporting.report_model import RoleAgg, RoleModelAgg, UsageReport
  - from core.dashboard.reporting.report_txt_format import _ascii_table, _hline, format_usage_report_txt
- **tests/test_runner_inline_progress.py**
  - from core.cli.python_cli.workflow.runtime.graph import runner
- **tests/test_runner_rewind_logic.py**
  - from core.cli.python_cli.workflow.runtime.graph.runner_rewind import (
- **tests/test_runner_rewind_pure.py**
  - from core.cli.python_cli.workflow.runtime.graph.runner_rewind import (
- **tests/test_runtime_config.py**
  - from core.config.runtime_config import RuntimeConfig
- **tests/test_security_and_config.py**
  - from agents.base_agent import BaseAgent
  - from core.cli.python_cli.shell.state import log_system_action
  - from core.config import Config
  - from core.config.settings import mask_api_key
  - from core.storage.knowledge.sqlite_repository import _vault_unwrap as _unwrap
  - from core.storage.knowledge_store import _vault_wrap
  - from utils.env_guard import redact_for_display
  - from utils.input_validator import (
  - from utils.tracker.tracker_openrouter import fetch_wallet
- **tests/test_session_monitor_manager.py**
  - import core.cli.python_cli.workflow.runtime.session.session_monitor_manager as smm
- **tests/test_session_notification.py**
  - import core.cli.python_cli.workflow.runtime.session.session_notification as sn
- **tests/test_session_notification_extra.py**
  - import core.cli.python_cli.workflow.runtime.session.session_notification as sn
- **tests/test_session_pause_manager.py**
  - import core.cli.python_cli.workflow.runtime.session.session_pause_manager as spm
- **tests/test_session_pipeline_state.py**
  - import core.cli.python_cli.workflow.runtime.session.session_pipeline_state as sps
- **tests/test_session_pipeline_state_extra.py**
  - import core.cli.python_cli.workflow.runtime.session.session_pipeline_state as sps
- **tests/test_session_pipeline_state_uncovered.py**
  - import core.cli.python_cli.workflow.runtime.session.session_pipeline_state as sps
- **tests/test_session_store.py**
  - from core.cli.python_cli.workflow.runtime.session.session_store import load_session_data, save_session_data
- **tests/test_skills_registry.py**
  - from core.domain.skills import (
- **tests/test_sqlite_repository_extra.py**
  - from core.storage.knowledge.sqlite_repository import (
- **tests/test_team_map_routing.py**
  - from agents.team_map._team_map import route_entry, route_after_leader
- **tests/test_tracker_aggregate.py**
  - from utils.tracker.tracker_aggregate import (
- **tests/test_tracker_aggregate_extra.py**
  - from utils.tracker.tracker_aggregate import (
  - from utils.tracker.tracker_cache import _CACHE_LAST
- **tests/test_tracker_batches.py**
  - from utils.tracker.tracker_batches import append_cli_batch
  - from utils.tracker.tracker_batches import read_cli_batches_tail
- **tests/test_tracker_batches_summarize.py**
  - from utils.tracker.tracker_batches import summarize_tokens_by_cli_batches
- **tests/test_tracker_budget.py**
  - from utils.tracker.tracker_budget import (
- **tests/test_tracker_cache.py**
  - from utils.tracker.tracker_cache import (
- **tests/test_tracker_dashboard_summary.py**
  - from utils import tracker
- **tests/test_tracker_helpers.py**
  - from utils.tracker.tracker_helpers import (
- **tests/test_tracker_usage.py**
  - from utils.tracker.tracker_usage import compute_cost_usd, append_usage_log
- **tests/test_vault_key.py**
  - from core.storage.knowledge.vault_key import _normalize_key, _secure_chmod, load_or_create_vault_key
- **tests/test_workflow_activity_format.py**
  - from core.cli.python_cli.workflow.runtime.persist.activity_log import format_activity_lines
- **tests/test_workflow_toast_queue.py**
  - from core.cli.python_cli.workflow.runtime import session as ws
  - from core.cli.python_cli.workflow.runtime.session import _session_core, session_store

### Utils
- **utils/ask_history.py**
  - from core.storage.ask_history import (
- **utils/budget_guard.py**
  - from core.app_state.settings import get_cli_settings
  - from utils import tracker
- **utils/delta_brief.py**
  - from core.domain.delta_brief import (
- **utils/env_guard.py**
  - from core.config.constants import AI_TEAM_HOME
  - from utils.file_manager import get_cache_root
- **utils/file_manager.py**
  - from core.config import config
  - from core.domain.delta_brief import CONTEXT_FILENAME, STATE_FILENAME, VALIDATION_REPORT_FILENAME
- **utils/free_model_finder.py**
  - from core.app_state import get_model_overrides, set_model_override
  - from core.cli.python_cli.i18n import t
  - from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, SOFT_WHITE, console
  - from core.config import config
  - from utils.free_model_finder import find_free_models, show_free_model_picker
- **utils/graphrag_utils.py**
  - from core.storage.graphrag_store import ingest_prompt_doc
  - from core.storage.graphrag_store import try_ingest_context_md
- **utils/logger.py**
  - from core.app_state import log_system_action
  - from core.cli.python_cli.workflow.runtime.persist.activity_log import append_workflow_activity
- **utils/tracker/tracker_helpers.py**
  - from core.config.constants import AI_TEAM_HOME
- **utils/tracker/tracker_usage.py**
  - from core.config import config

## Session Summaries

### 1. Tool Curator Integration (Completed)
- Fully integrated into LangGraph pipeline: Human Gate -> Tool Curator -> Finalize.
- Purpose: Reads context.md, analyzes venv via sys.executable, generates tools.md.

### 2. TUI Refactoring (Completed)
- Removed redundant entry/ and app/ shims.
- Consolidated logic into monitor/.

### 3. Bounded Module Refactoring (In Progress)
- Goal: Decouple CLI/TUI from core logic.
- New Modules: core/app_state/, core/orchestration/, core/frontends/, core/runtime/.

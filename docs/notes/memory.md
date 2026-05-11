# Codebase Memory

**Last Updated:** 2026-05-07
**Total Files:** 393
**Total Lines of Code:** 37922

## Structure
```text
|-- .pre-commit-config.yaml (20 lines)
|-- CHANGELOG.md (75 lines)
|-- CLAUDE.md (65 lines)
|-- README.md (472 lines)
|-- pyproject.toml (82 lines)
|-- .github/
|   |-- workflows/
|   |   \-- ci.yml (48 lines)
|-- agents/
|   |-- __init__.py (1 lines)
|   |-- _api_client.py (620 lines)
|   |-- _budget_manager.py (34 lines)
|   |-- _knowledge_manager.py (38 lines)
|   |-- ambassador.py (430 lines)
|   |-- base_agent.py (351 lines)
|   |-- browser.py (binary/0 lines)
|   |-- chat_agent.py (49 lines)
|   |-- commander.py (binary/0 lines)
|   |-- compact_worker.py (99 lines)
|   |-- expert.py (338 lines)
|   |-- explainer.py (182 lines)
|   |-- final_reviewer.py (binary/0 lines)
|   |-- fix_worker.py (binary/0 lines)
|   |-- leader.py (345 lines)
|   |-- llm_usage.py (12 lines)
|   |-- researcher.py (binary/0 lines)
|   |-- reviewer.py (binary/0 lines)
|   |-- secretary.py (286 lines)
|   |-- test_agent.py (binary/0 lines)
|   |-- tool_curator.py (218 lines)
|   \-- worker.py (335 lines)
|   |-- team_map/
|   |   |-- __init__.py (5 lines)
|   |   \-- _team_map.py (5 lines)
|-- core/
|   |-- __init__.py (1 lines)
|   |-- bootstrap.py (18 lines)
|   |-- paths.py (12 lines)
|   \-- runtime_config.py (4 lines)
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
|   |   |-- __init__.py (8 lines)
|   |   \-- package.json (15 lines)
|   |   |-- chrome/
|   |   |-- python_cli/
|   |   |   |-- __init__.py (5 lines)
|   |   |   \-- i18n.py (1062 lines)
|   |   |   |-- entrypoints/
|   |   |   |   |-- __init__.py (binary/0 lines)
|   |   |   |   \-- app.py (119 lines)
|   |   |   |-- features/
|   |   |   |   \-- __init__.py (1 lines)
|   |   |   |   |-- ask/
|   |   |   |   |   |-- __init__.py (binary/0 lines)
|   |   |   |   |   |-- chat_manager.py (201 lines)
|   |   |   |   |   |-- flow.py (237 lines)
|   |   |   |   |   |-- history_renderer.py (88 lines)
|   |   |   |   |   \-- model_selector.py (64 lines)
|   |   |   |   |-- change/
|   |   |   |   |   |-- __init__.py (17 lines)
|   |   |   |   |   |-- detail.py (388 lines)
|   |   |   |   |   |-- flow.py (14 lines)
|   |   |   |   |   |-- helpers.py (54 lines)
|   |   |   |   |   \-- list.py (81 lines)
|   |   |   |   |-- context/
|   |   |   |   |   |-- __init__.py (22 lines)
|   |   |   |   |   |-- common.py (104 lines)
|   |   |   |   |   |-- confirm.py (84 lines)
|   |   |   |   |   |-- flow.py (29 lines)
|   |   |   |   |   |-- monitor_actions.py (80 lines)
|   |   |   |   |   \-- viewer.py (158 lines)
|   |   |   |   |-- dashboard/
|   |   |   |   |   |-- __init__.py (binary/0 lines)
|   |   |   |   |   \-- flow.py (3 lines)
|   |   |   |   |-- explain/
|   |   |   |   |   |-- __init__.py (binary/0 lines)
|   |   |   |   |   \-- flow.py (55 lines)
|   |   |   |   |-- settings/
|   |   |   |   |   |-- __init__.py (binary/0 lines)
|   |   |   |   |   \-- flow.py (127 lines)
|   |   |   |   |-- start/
|   |   |   |   |   |-- __init__.py (3 lines)
|   |   |   |   |   |-- clarification_helpers.py (111 lines)
|   |   |   |   |   |-- flow.py (281 lines)
|   |   |   |   |   \-- pipeline_runner.py (213 lines)
|   |   |   |-- shell/
|   |   |   |   |-- __init__.py (binary/0 lines)
|   |   |   |   |-- choice_lists.py (16 lines)
|   |   |   |   |-- command_parser.py (39 lines)
|   |   |   |   |-- command_registry.py (159 lines)
|   |   |   |   |-- menu.py (722 lines)
|   |   |   |   |-- monitor_payload.py (49 lines)
|   |   |   |   |-- monitor_queue_drain.py (128 lines)
|   |   |   |   |-- nav.py (28 lines)
|   |   |   |   |-- prompt.py (164 lines)
|   |   |   |   |-- safe_editor.py (40 lines)
|   |   |   |   |-- safe_read.py (12 lines)
|   |   |   |   \-- state.py (278 lines)
|   |   |   |-- ui/
|   |   |   |   |-- .translations.json (333 lines)
|   |   |   |   |-- __init__.py (binary/0 lines)
|   |   |   |   |-- autocomplete.py (202 lines)
|   |   |   |   |-- help_terminal.py (95 lines)
|   |   |   |   |-- helpbox.py (14 lines)
|   |   |   |   |-- palette_app.py (6 lines)
|   |   |   |   |-- palette_shared.py (24 lines)
|   |   |   |   |-- rich_command_palette.py (106 lines)
|   |   |   |   \-- ui.py (130 lines)
|   |   |   |   |-- palette/
|   |   |   |   |   |-- __init__.py (47 lines)
|   |   |   |   |   |-- app.py (235 lines)
|   |   |   |   |   |-- footer.py (39 lines)
|   |   |   |   |   |-- items.py (176 lines)
|   |   |   |   |   |-- lexer.py (75 lines)
|   |   |   |   |   |-- popup.py (80 lines)
|   |   |   |   |   |-- shared.py (229 lines)
|   |   |   |   |   \-- styles.py (11 lines)
|   |   |   |-- workflow/
|   |   |   |   \-- __init__.py (1 lines)
|   |   |   |   |-- runtime/
|   |   |   |   |   \-- __init__.py (4 lines)
|   |   |   |   |   |-- graph/
|   |   |   |   |   |   |-- __init__.py (1 lines)
|   |   |   |   |   |   |-- runner.py (248 lines)
|   |   |   |   |   |   |-- runner_resume.py (44 lines)
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
|   |   |   |   |   |   |-- __init__.py (135 lines)
|   |   |   |   |   |   |-- _session_core.py (50 lines)
|   |   |   |   |   |   |-- session_monitor_manager.py (30 lines)
|   |   |   |   |   |   |-- session_notification.py (174 lines)
|   |   |   |   |   |   |-- session_pause_manager.py (89 lines)
|   |   |   |   |   |   |-- session_pipeline_state.py (1030 lines)
|   |   |   |   |   |   \-- session_store.py (45 lines)
|   |   |   |   |-- tui/
|   |   |   |   |   |-- __init__.py (1 lines)
|   |   |   |   |   \-- __main__.py (6 lines)
|   |   |   |   |   |-- monitor/
|   |   |   |   |   |   |-- __init__.py (12 lines)
|   |   |   |   |   |   |-- app.py (335 lines)
|   |   |   |   |   |   |-- helpers.py (492 lines)
|   |   |   |   |   |   \-- screens.py (310 lines)
|   |   |   |   |   |   |-- commands/
|   |   |   |   |   |   |   |-- __init__.py (13 lines)
|   |   |   |   |   |   |   |-- ask.py (74 lines)
|   |   |   |   |   |   |   |-- btw.py (118 lines)
|   |   |   |   |   |   |   |-- check.py (65 lines)
|   |   |   |   |   |   |   \-- mixin.py (381 lines)
|   |   |   |   |   |   |-- core/
|   |   |   |   |   |   |   |-- __init__.py (19 lines)
|   |   |   |   |   |   |   |-- _constants.py (77 lines)
|   |   |   |   |   |   |   |-- _content_mixin.py (102 lines)
|   |   |   |   |   |   |   |-- _controls.py (146 lines)
|   |   |   |   |   |   |   |-- _layout_mixin.py (410 lines)
|   |   |   |   |   |   |   |-- _render_mixin.py (576 lines)
|   |   |   |   |   |   |   |-- _tasks_mixin.py (131 lines)
|   |   |   |   |   |   |   |-- _utils.py (44 lines)
|   |   |   |   |   |   |   \-- _views_mixin.py (160 lines)
|   |   |   |   |   |   |-- state/
|   |   |   |   |   |   |   |-- __init__.py (41 lines)
|   |   |   |   |   |   |   |-- _ambassador.py (99 lines)
|   |   |   |   |   |   |   |-- _clarify.py (26 lines)
|   |   |   |   |   |   |   |-- _explainer.py (75 lines)
|   |   |   |   |   |   |   |-- _gate.py (44 lines)
|   |   |   |   |   |   |   |-- _leader.py (156 lines)
|   |   |   |   |   |   |   |-- _pipeline.py (28 lines)
|   |   |   |   |   |   |   |-- _secretary.py (83 lines)
|   |   |   |   |   |   |   |-- _tool_curator.py (113 lines)
|   |   |   |   |   |   |   |-- _update_state.py (75 lines)
|   |   |   |   |   |   |   \-- _worker.py (115 lines)
|   |   |   |   |   |-- shared/
|   |   |   |   |   |   |-- __init__.py (1 lines)
|   |   |   |   |   |   |-- agent_cards.py (129 lines)
|   |   |   |   |   |   |-- btw_inline.py (84 lines)
|   |   |   |   |   |   \-- display_policy.py (19 lines)
|   |   |-- workflow/
|   |   |   |-- runtime/
|   |   |   |-- tui/
|   |-- config/
|   |   |-- __init__.py (26 lines)
|   |   |-- constants.py (35 lines)
|   |   |-- hardware.py (107 lines)
|   |   |-- pricing.py (172 lines)
|   |   |-- runtime_config.py (14 lines)
|   |   |-- service.py (253 lines)
|   |   \-- settings.py (98 lines)
|   |   |-- registry/
|   |   |   \-- __init__.py (34 lines)
|   |   |   |-- coding/
|   |   |   |   |-- __init__.py (29 lines)
|   |   |   |   |-- chat.py (28 lines)
|   |   |   |   |-- devops.py (17 lines)
|   |   |   |   |-- fixers.py (72 lines)
|   |   |   |   |-- leaders.py (39 lines)
|   |   |   |   |-- researchers.py (39 lines)
|   |   |   |   |-- reviewers.py (69 lines)
|   |   |   |   |-- support.py (50 lines)
|   |   |   |   |-- system.py (39 lines)
|   |   |   |   |-- testers.py (28 lines)
|   |   |   |   \-- workers.py (61 lines)
|   |-- dashboard/
|   |   \-- __init__.py (5 lines)
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
|   |   |   \-- __init__.py (2 lines)
|   |   |   |-- shell/
|   |   |   |   \-- __init__.py (5 lines)
|   |   |   |-- tui/
|   |   |   |   \-- __init__.py (3 lines)
|   |   |-- reporting/
|   |   |   |-- __init__.py (13 lines)
|   |   |   |-- report_model.py (131 lines)
|   |   |   |-- report_txt_format.py (116 lines)
|   |   |   |-- state.py (83 lines)
|   |   |   \-- text_export.py (35 lines)
|   |   |-- shell/
|   |   |   |-- __init__.py (1 lines)
|   |   |   |-- app.py (179 lines)
|   |   |   |-- budget.py (204 lines)
|   |   |   |-- data.py (11 lines)
|   |   |   |-- history.py (326 lines)
|   |   |   \-- total.py (87 lines)
|   |   |-- tui/
|   |   |   |-- __init__.py (1 lines)
|   |   |   |-- log_console.py (6 lines)
|   |   |   |-- panels.py (13 lines)
|   |   |   |-- render.py (191 lines)
|   |   |   \-- utils.py (60 lines)
|   |-- domain/
|   |   |-- __init__.py (binary/0 lines)
|   |   |-- agent_protocol.py (51 lines)
|   |   |-- delta_brief.py (87 lines)
|   |   |-- pipeline_state.py (16 lines)
|   |   \-- routing_map.py (54 lines)
|   |   |-- prompts/
|   |   |   |-- __init__.py (39 lines)
|   |   |   |-- ambassador.py (60 lines)
|   |   |   |-- ask_mode.py (43 lines)
|   |   |   |-- btw_coordinator.py (56 lines)
|   |   |   |-- clarification.py (40 lines)
|   |   |   |-- expert.py (61 lines)
|   |   |   \-- leader.py (158 lines)
|   |   |-- skills/
|   |   |   |-- __init__.py (32 lines)
|   |   |   |-- _categories.py (16 lines)
|   |   |   |-- _loader.py (29 lines)
|   |   |   |-- _registry.py (79 lines)
|   |   |   |-- backup_tool.py (12 lines)
|   |   |   \-- hooks.py (12 lines)
|   |   |   |-- builtin/
|   |   |   |   |-- __init__.py (4 lines)
|   |   |   |   |-- backup_restore.py (40 lines)
|   |   |   |   |-- file_operations.py (42 lines)
|   |   |   |   \-- terminal.py (35 lines)
|   |   |   |-- custom/
|   |   |   |   \-- __init__.py (4 lines)
|   |   |   |-- examples/
|   |   |   |   |-- __init__.py (5 lines)
|   |   |   |   \-- echo.py (15 lines)
|   |-- frontends/
|   |   \-- __init__.py (2 lines)
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
|   |-- orchestration/
|   |   |-- __init__.py (13 lines)
|   |   |-- pipeline_artifacts.py (125 lines)
|   |   |-- team_graph.py (75 lines)
|   |   |-- team_nodes.py (207 lines)
|   |   |-- team_routing.py (20 lines)
|   |   \-- team_state.py (24 lines)
|   |-- resources/
|   |   \-- README.md (3 lines)
|   |   |-- fonts/
|   |   |   |-- Inter_18pt-Regular.ttf (binary/0 lines)
|   |   |   \-- Inter_24pt-Bold.ttf (binary/0 lines)
|   |-- runtime/
|   |   |-- __init__.py (4 lines)
|   |   \-- session.py (4 lines)
|   |-- sandbox/
|   |   |-- __init__.py (8 lines)
|   |   |-- executor.py (90 lines)
|   |   |-- policy.py (37 lines)
|   |   \-- venv_manager.py (12 lines)
|   |-- services/
|   |   |-- __init__.py (1 lines)
|   |   \-- dashboard_data.py (12 lines)
|   |-- storage/
|   |   |-- __init__.py (41 lines)
|   |   |-- ask_chat_store.py (278 lines)
|   |   |-- ask_history.py (102 lines)
|   |   |-- code_backup.py (160 lines)
|   |   |-- graphrag_store.py (253 lines)
|   |   |-- knowledge_store.py (65 lines)
|   |   |-- knowledge_text.py (95 lines)
|   |   \-- prompt_store_protocol.py (27 lines)
|   |   |-- knowledge/
|   |   |   |-- __init__.py (10 lines)
|   |   |   |-- repository.py (28 lines)
|   |   |   |-- sqlite_repository.py (418 lines)
|   |   |   \-- vault_key.py (61 lines)
|-- docs/
|   |-- REPO_LAYOUT.md (19 lines)
|   \-- security.md (6 lines)
|   |-- design/
|   |   \-- README.md (3 lines)
|   |-- notes/
|   |   |-- README.md (3 lines)
|   |   \-- memory.md (555 lines)
|   |-- skills_admin/
|   |   \-- README.md (8 lines)
|   |   |-- AgentAudit/
|   |   |   |-- AGENT_AUDIT.md (47 lines)
|   |   |   |-- PROJECT_SUMMARY.md (24 lines)
|   |   |   \-- README.md (17 lines)
|   |   |-- GraphRag/
|   |   |   |-- PROJECT_MAP.md (231 lines)
|   |   |   |-- PROJECT_SUMMARY.md (285 lines)
|   |   |   \-- README.md (27 lines)
|-- scripts/
|   |-- README.md (3 lines)
|   |-- run_aiteam.py (6 lines)
|   \-- update_memory.py (158 lines)
|-- tests/
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
|   |-- cli/
|   |   |-- test_cli_prompt_ux.py (89 lines)
|   |   \-- test_ui_clear.py (21 lines)
|-- utils/
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
|   |-- tracker/
|   |   |-- __init__.py (86 lines)
|   |   |-- tracker_aggregate.py (175 lines)
|   |   |-- tracker_batches.py (126 lines)
|   |   |-- tracker_budget.py (75 lines)
|   |   |-- tracker_cache.py (45 lines)
|   |   |-- tracker_helpers.py (118 lines)
|   |   |-- tracker_openrouter.py (37 lines)
|   |   \-- tracker_usage.py (117 lines)
```

## Connections (Dependency Map)

- **agents\_api_client.py**
  - imports core
  - imports utils
- **agents\ambassador.py**
  - imports agents
  - imports core
  - imports utils
- **agents\base_agent.py**
  - imports agents
  - imports core
- **agents\chat_agent.py**
  - imports core
- **agents\compact_worker.py**
  - imports agents
  - imports core
- **agents\expert.py**
  - imports agents
  - imports core
  - imports utils
- **agents\explainer.py**
  - imports agents
  - imports core
- **agents\leader.py**
  - imports agents
  - imports core
  - imports utils
- **agents\llm_usage.py**
  - imports agents
- **agents\secretary.py**
  - imports agents
  - imports core
- **agents\team_map\_team_map.py**
  - imports core
- **agents\tool_curator.py**
  - imports agents
  - imports core
  - imports utils
- **agents\worker.py**
  - imports agents
  - imports core

## Session Summaries

### 4. Industrial AI Agentic Refactoring (Completed)
- **UI**: Detailed diffs with context windows (+green/-red) in `_update_state.py`.
- **Architecture**: Standardized slash-commands (`/back`, `/exit`, `/accept`, etc.) via `command_parser.py`.
- **Security**: `core/sandbox/` executor with allowlist policy for Worker/Secretary.
- **Efficiency**: Lazy-loading `core.storage` exports via `__getattr__` to minimize import side-effects.
- **Robustness**: UTF-8 `errors="replace"` in `safe_read.py" for all TUI file viewing.
- **Roster**: Automated Worker roster in Leader prompts; `restore_worker` node for backup recovery.

### 1. Multi-Agent Support Framework (Completed)
- **New Roles**:
  - **Worker**: Executes code tasks (Reading -> Thinking -> [Asking] -> Writing -> [Using]). Interleaves `Update` diffs after each file.
  - **Secretary**: CLI/Terminal executor with fallback logic (Reading -> Using -> [Fallback]).
  - **Explainer**: Codebase analysis (Using -> Thinking -> Writing).
- **TUI Streaming**:
  - **Reading**: Collapsible branch tree for file scanning.
  - **Thinking**: Tail-focused reasoning stream (last 6 lines).
  - **Writing**: Tail-focused code stream (last 12 lines).
  - **Using**: Per-command branches with individual status dots (â—/âœ—) and collapsible output.
  - **Update**: Independent system state showing colored diffs (+green/-red) immediately after each file write.

### 2. Architecture Clarification
- **core/app_state**: The project's runtime configuration hub. Manages model overrides, context state, and CLI settings.
- **core/cli/app**: Unrelated boilerplate remnants (Django models/views). Not part of the `ai-team` logic.
- **Explainer @codebase**: Token-optimized scanning using tools (`tree`, `grep`, `wc`) instead of LLM-per-file reading.

### 3. Tool Curator Integration (Completed)
- Fully integrated into LangGraph pipeline: Human Gate -> Tool Curator -> Worker -> Secretary -> Finalize.
- Purpose: Reads context.md, analyzes venv via sys.executable, generates tools.md.

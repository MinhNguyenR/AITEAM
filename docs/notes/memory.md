# Codebase Memory

**Last Updated:** 2026-05-12
**Total Files:** 480
**Total Lines of Code:** 55264

## Structure
```text
|-- .pre-commit-config.yaml (20 lines)
|-- CLAUDE.md (65 lines)
|-- README.md (472 lines)
|-- pyproject.toml (89 lines)
|-- .ai-team/
|-- .aiteamruntime/
|   |-- create-a-react-app-proof-project-in-this-empty-workspace/
|   |   |-- implementation.txt (4 lines)
|   |   \-- validation.txt (4 lines)
|   |-- demo-ai-team-event-driven-trace/
|   |   |-- implementation.txt (3 lines)
|   |   |-- tools.txt (12 lines)
|   |   \-- validation.txt (3 lines)
|   |-- implement-a-small-change/
|   |   |-- implementation.txt (3 lines)
|   |   |-- tools.txt (12 lines)
|   |   \-- validation.txt (3 lines)
|   |-- trace-web/
|   |   |-- implementation.txt (3 lines)
|   |   |-- tools.txt (12 lines)
|   |   \-- validation.txt (3 lines)
|-- .github/
|   |-- workflows/
|   |   \-- ci.yml (48 lines)
|-- agents/
|   |-- __init__.py (1 lines)
|   |-- ambassador.py (388 lines)
|   |-- base_agent.py (351 lines)
|   |-- browser.py (binary/0 lines)
|   |-- chat_agent.py (49 lines)
|   |-- commander.py (binary/0 lines)
|   |-- compact_worker.py (150 lines)
|   |-- expert.py (338 lines)
|   |-- explainer.py (369 lines)
|   |-- final_reviewer.py (binary/0 lines)
|   |-- fix_worker.py (binary/0 lines)
|   |-- leader.py (349 lines)
|   |-- llm_usage.py (12 lines)
|   |-- researcher.py (binary/0 lines)
|   |-- reviewer.py (binary/0 lines)
|   |-- secretary.py (379 lines)
|   |-- test_agent.py (binary/0 lines)
|   |-- tool_curator.py (269 lines)
|   \-- worker.py (505 lines)
|   |-- support/
|   |   |-- __init__.py (2 lines)
|   |   |-- _ambassador_classify.py (109 lines)
|   |   |-- _api_client.py (444 lines)
|   |   |-- _api_transport.py (110 lines)
|   |   |-- _budget_manager.py (34 lines)
|   |   |-- _knowledge_manager.py (38 lines)
|   |   |-- _leader_format.py (29 lines)
|   |   |-- _stream_aggregator.py (190 lines)
|   |   \-- _usage_logging.py (27 lines)
|   |-- team_map/
|   |   |-- __init__.py (5 lines)
|   |   \-- _team_map.py (5 lines)
|-- aiteamruntime/
|   |-- __init__.py (69 lines)
|   |-- agents.py (39 lines)
|   |-- artifacts.py (29 lines)
|   |-- bus.py (98 lines)
|   |-- contracts.py (88 lines)
|   |-- demo.py (20 lines)
|   |-- demo_cli.py (295 lines)
|   |-- events.py (152 lines)
|   |-- governor.py (67 lines)
|   |-- lock_manager.py (401 lines)
|   |-- overseer.py (31 lines)
|   |-- pipeline.py (520 lines)
|   |-- references.py (103 lines)
|   |-- resources.py (165 lines)
|   |-- runtime.py (1322 lines)
|   |-- scheduler.py (90 lines)
|   |-- secretary_proc.py (467 lines)
|   \-- traces.py (464 lines)
|   |-- integrations/
|   |   \-- __init__.py (2 lines)
|   |   |-- trackaiteam/
|   |   |   |-- __init__.py (21 lines)
|   |   |   \-- workflow.py (1241 lines)
|   |-- test/
|   |   |-- __init__.py (9 lines)
|   |   |-- test_contracts_governor.py (142 lines)
|   |   |-- test_pipeline.py (378 lines)
|   |   |-- test_production_boundaries.py (81 lines)
|   |   |-- test_real_model.py (258 lines)
|   |   \-- workflows.py (1293 lines)
|   |-- web/
|   |   |-- __init__.py (1 lines)
|   |   |-- cli.py (54 lines)
|   |   \-- server.py (913 lines)
|   |   |-- assets/
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
|   |   \-- __init__.py (8 lines)
|   |   |-- chrome/
|   |   |-- python_cli/
|   |   |   |-- __init__.py (5 lines)
|   |   |   \-- i18n.py (27 lines)
|   |   |   |-- entrypoints/
|   |   |   |   |-- __init__.py (binary/0 lines)
|   |   |   |   \-- app.py (119 lines)
|   |   |   |-- features/
|   |   |   |   \-- __init__.py (1 lines)
|   |   |   |   |-- ask/
|   |   |   |   |   |-- __init__.py (binary/0 lines)
|   |   |   |   |   |-- chat_manager.py (220 lines)
|   |   |   |   |   |-- flow.py (259 lines)
|   |   |   |   |   |-- history_renderer.py (90 lines)
|   |   |   |   |   \-- model_selector.py (64 lines)
|   |   |   |   |-- change/
|   |   |   |   |   |-- __init__.py (17 lines)
|   |   |   |   |   |-- _role_actions.py (197 lines)
|   |   |   |   |   |-- detail.py (213 lines)
|   |   |   |   |   |-- flow.py (14 lines)
|   |   |   |   |   |-- helpers.py (54 lines)
|   |   |   |   |   \-- list.py (83 lines)
|   |   |   |   |-- context/
|   |   |   |   |   |-- __init__.py (22 lines)
|   |   |   |   |   |-- common.py (104 lines)
|   |   |   |   |   |-- confirm.py (84 lines)
|   |   |   |   |   |-- flow.py (29 lines)
|   |   |   |   |   |-- monitor_actions.py (80 lines)
|   |   |   |   |   \-- viewer.py (159 lines)
|   |   |   |   |-- dashboard/
|   |   |   |   |   |-- __init__.py (binary/0 lines)
|   |   |   |   |   \-- flow.py (3 lines)
|   |   |   |   |-- explain/
|   |   |   |   |   |-- __init__.py (binary/0 lines)
|   |   |   |   |   \-- flow.py (91 lines)
|   |   |   |   |-- settings/
|   |   |   |   |   |-- __init__.py (binary/0 lines)
|   |   |   |   |   \-- flow.py (127 lines)
|   |   |   |   |-- start/
|   |   |   |   |   |-- __init__.py (3 lines)
|   |   |   |   |   |-- clarification_helpers.py (111 lines)
|   |   |   |   |   |-- flow.py (342 lines)
|   |   |   |   |   \-- pipeline_runner.py (228 lines)
|   |   |   |-- shell/
|   |   |   |   |-- __init__.py (binary/0 lines)
|   |   |   |   |-- _info_screen.py (125 lines)
|   |   |   |   |-- _status_screen.py (219 lines)
|   |   |   |   |-- choice_lists.py (16 lines)
|   |   |   |   |-- command_parser.py (39 lines)
|   |   |   |   |-- command_registry.py (160 lines)
|   |   |   |   |-- menu.py (176 lines)
|   |   |   |   |-- monitor_payload.py (49 lines)
|   |   |   |   |-- monitor_queue_drain.py (128 lines)
|   |   |   |   |-- nav.py (28 lines)
|   |   |   |   |-- prompt.py (172 lines)
|   |   |   |   |-- safe_editor.py (40 lines)
|   |   |   |   |-- safe_read.py (12 lines)
|   |   |   |   \-- state.py (278 lines)
|   |   |   |   |-- screens/
|   |   |   |   |   |-- __init__.py (2 lines)
|   |   |   |   |   \-- change.py (106 lines)
|   |   |   |-- ui/
|   |   |   |   |-- .translations.json (1895 lines)
|   |   |   |   |-- __init__.py (binary/0 lines)
|   |   |   |   |-- autocomplete.py (204 lines)
|   |   |   |   |-- help_terminal.py (95 lines)
|   |   |   |   |-- helpbox.py (14 lines)
|   |   |   |   |-- palette_app.py (6 lines)
|   |   |   |   |-- palette_shared.py (24 lines)
|   |   |   |   |-- rich_command_palette.py (106 lines)
|   |   |   |   \-- ui.py (130 lines)
|   |   |   |   |-- palette/
|   |   |   |   |   |-- __init__.py (49 lines)
|   |   |   |   |   |-- app.py (290 lines)
|   |   |   |   |   |-- footer.py (39 lines)
|   |   |   |   |   |-- items.py (196 lines)
|   |   |   |   |   |-- lexer.py (79 lines)
|   |   |   |   |   |-- popup.py (79 lines)
|   |   |   |   |   |-- shared.py (292 lines)
|   |   |   |   |   \-- styles.py (11 lines)
|   |   |   |-- workflow/
|   |   |   |   \-- __init__.py (1 lines)
|   |   |   |   |-- runtime/
|   |   |   |   |   \-- __init__.py (4 lines)
|   |   |   |   |   |-- graph/
|   |   |   |   |   |   |-- __init__.py (1 lines)
|   |   |   |   |   |   |-- runner.py (322 lines)
|   |   |   |   |   |   |-- runner_resume.py (52 lines)
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
|   |   |   |   |   |   |-- __init__.py (139 lines)
|   |   |   |   |   |   |-- _session_core.py (50 lines)
|   |   |   |   |   |   |-- session_monitor_manager.py (30 lines)
|   |   |   |   |   |   |-- session_notification.py (174 lines)
|   |   |   |   |   |   |-- session_pause_manager.py (89 lines)
|   |   |   |   |   |   |-- session_pipeline_state.py (551 lines)
|   |   |   |   |   |   \-- session_store.py (45 lines)
|   |   |   |   |   |   |-- state/
|   |   |   |   |   |   |   |-- __init__.py (2 lines)
|   |   |   |   |   |   |   |-- _clarification.py (52 lines)
|   |   |   |   |   |   |   |-- _diff_state.py (55 lines)
|   |   |   |   |   |   |   |-- _role_substates.py (289 lines)
|   |   |   |   |   |   |   |-- _stream_history.py (82 lines)
|   |   |   |   |   |   |   \-- _stream_state.py (170 lines)
|   |   |   |   |-- tui/
|   |   |   |   |   |-- __init__.py (1 lines)
|   |   |   |   |   \-- __main__.py (6 lines)
|   |   |   |   |   |-- monitor/
|   |   |   |   |   |   |-- __init__.py (12 lines)
|   |   |   |   |   |   |-- _pipeline_meta.py (278 lines)
|   |   |   |   |   |   |-- _task_pool.py (71 lines)
|   |   |   |   |   |   |-- app.py (335 lines)
|   |   |   |   |   |   |-- helpers.py (230 lines)
|   |   |   |   |   |   \-- screens.py (310 lines)
|   |   |   |   |   |   |-- commands/
|   |   |   |   |   |   |   |-- __init__.py (13 lines)
|   |   |   |   |   |   |   |-- ask.py (73 lines)
|   |   |   |   |   |   |   |-- btw.py (118 lines)
|   |   |   |   |   |   |   |-- check.py (67 lines)
|   |   |   |   |   |   |   |-- explainer.py (48 lines)
|   |   |   |   |   |   |   |-- gate.py (81 lines)
|   |   |   |   |   |   |   \-- mixin.py (337 lines)
|   |   |   |   |   |   |-- core/
|   |   |   |   |   |   |   |-- __init__.py (19 lines)
|   |   |   |   |   |   |   |-- _constants.py (81 lines)
|   |   |   |   |   |   |   |-- _content_mixin.py (102 lines)
|   |   |   |   |   |   |   |-- _controls.py (146 lines)
|   |   |   |   |   |   |   |-- _keybindings.py (217 lines)
|   |   |   |   |   |   |   |-- _layout_mixin.py (242 lines)
|   |   |   |   |   |   |   |-- _refresh_state_mixin.py (223 lines)
|   |   |   |   |   |   |   |-- _render_mixin.py (240 lines)
|   |   |   |   |   |   |   |-- _role_card_mixin.py (166 lines)
|   |   |   |   |   |   |   |-- _tasks_mixin.py (131 lines)
|   |   |   |   |   |   |   |-- _transition_mixin.py (143 lines)
|   |   |   |   |   |   |   |-- _utils.py (53 lines)
|   |   |   |   |   |   |   \-- _views_mixin.py (160 lines)
|   |   |   |   |   |   |-- state/
|   |   |   |   |   |   |   |-- __init__.py (41 lines)
|   |   |   |   |   |   |   |-- _ambassador.py (99 lines)
|   |   |   |   |   |   |   |-- _clarify.py (24 lines)
|   |   |   |   |   |   |   |-- _explainer.py (75 lines)
|   |   |   |   |   |   |   |-- _gate.py (44 lines)
|   |   |   |   |   |   |   |-- _leader.py (101 lines)
|   |   |   |   |   |   |   |-- _pipeline.py (28 lines)
|   |   |   |   |   |   |   |-- _secretary.py (83 lines)
|   |   |   |   |   |   |   |-- _tool_curator.py (79 lines)
|   |   |   |   |   |   |   |-- _update_state.py (75 lines)
|   |   |   |   |   |   |   \-- _worker.py (158 lines)
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
|   |   |   |   |-- __init__.py (31 lines)
|   |   |   |   |-- chat.py (32 lines)
|   |   |   |   |-- devops.py (17 lines)
|   |   |   |   |-- fixers.py (72 lines)
|   |   |   |   |-- leaders.py (45 lines)
|   |   |   |   |-- memory.py (39 lines)
|   |   |   |   |-- researchers.py (94 lines)
|   |   |   |   |-- reviewers.py (71 lines)
|   |   |   |   |-- support.py (58 lines)
|   |   |   |   |-- system.py (45 lines)
|   |   |   |   |-- testers.py (28 lines)
|   |   |   |   \-- workers.py (84 lines)
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
|   |   |   |-- app.py (223 lines)
|   |   |   |-- budget.py (197 lines)
|   |   |   |-- data.py (11 lines)
|   |   |   |-- history.py (346 lines)
|   |   |   \-- total.py (159 lines)
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
|   |   \-- routing_map.py (61 lines)
|   |   |-- prompts/
|   |   |   |-- __init__.py (49 lines)
|   |   |   |-- ambassador.py (64 lines)
|   |   |   |-- ask_mode.py (43 lines)
|   |   |   |-- btw_coordinator.py (56 lines)
|   |   |   |-- clarification.py (40 lines)
|   |   |   |-- expert.py (61 lines)
|   |   |   |-- leader.py (167 lines)
|   |   |   \-- workers.py (70 lines)
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
|   |   |-- pipeline_artifacts.py (135 lines)
|   |   |-- team_graph.py (93 lines)
|   |   |-- team_nodes.py (404 lines)
|   |   |-- team_routing.py (18 lines)
|   |   \-- team_state.py (34 lines)
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
|   |   |-- _path_guard.py (49 lines)
|   |   |-- executor.py (114 lines)
|   |   |-- policy.py (46 lines)
|   |   \-- venv_manager.py (47 lines)
|   |-- services/
|   |   |-- __init__.py (1 lines)
|   |   \-- dashboard_data.py (12 lines)
|   |-- storage/
|   |   |-- __init__.py (44 lines)
|   |   |-- _token_window.py (102 lines)
|   |   |-- ask_chat_store.py (497 lines)
|   |   |-- ask_history.py (103 lines)
|   |   |-- code_backup.py (213 lines)
|   |   |-- conversation_archive.py (36 lines)
|   |   |-- embedding_client.py (185 lines)
|   |   |-- graphrag_store.py (571 lines)
|   |   |-- knowledge_store.py (65 lines)
|   |   |-- knowledge_text.py (95 lines)
|   |   |-- memory_coordinator.py (246 lines)
|   |   |-- memory_cost_guard.py (230 lines)
|   |   |-- memory_settler.py (66 lines)
|   |   |-- prompt_store_protocol.py (27 lines)
|   |   |-- rerank_client.py (218 lines)
|   |   \-- sqlite_utils.py (32 lines)
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
|   |   \-- memory.md (3296 lines)
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
|-- pytest-cache-files-ocr7cxt5/
|   \-- README.md (8 lines)
|-- scripts/
|   |-- README.md (3 lines)
|   |-- run_aiteam.py (6 lines)
|   \-- update_memory.py (173 lines)
|-- tests/
|   |-- conftest.py (8 lines)
|   |-- test_activity_badges.py (56 lines)
|   |-- test_activity_log.py (156 lines)
|   |-- test_agent_runtime.py (199 lines)
|   |-- test_aiteamruntime_lifecycle.py (214 lines)
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
|   |-- test_dashboard_pdf.py (81 lines)
|   |-- test_dashboard_pdf_font_fallback.py (56 lines)
|   |-- test_dashboard_range_picker.py (17 lines)
|   |-- test_dashboard_range_state.py (102 lines)
|   |-- test_dashboard_render.py (41 lines)
|   |-- test_dashboard_tui_utils.py (76 lines)
|   |-- test_dashboard_turn_views.py (77 lines)
|   |-- test_delta_brief.py (133 lines)
|   |-- test_domain_prompts.py (118 lines)
|   |-- test_embedding_client.py (37 lines)
|   |-- test_env_guard.py (140 lines)
|   |-- test_expert_agent.py (297 lines)
|   |-- test_expert_coplan.py (175 lines)
|   |-- test_export_txt_format.py (21 lines)
|   |-- test_file_manager.py (189 lines)
|   |-- test_frontend_runtime_facades.py (26 lines)
|   |-- test_graphrag_hybrid.py (91 lines)
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
|   |-- test_memory_cost_guard.py (86 lines)
|   |-- test_memory_tier1_window.py (48 lines)
|   |-- test_memory_tier3_settler.py (28 lines)
|   |-- test_monitor_commands_regenerate.py (67 lines)
|   |-- test_monitor_helpers_tier_display.py (16 lines)
|   |-- test_monitor_payload.py (88 lines)
|   |-- test_monitor_role_cards.py (49 lines)
|   |-- test_orchestration_split.py (12 lines)
|   |-- test_palette_package.py (165 lines)
|   |-- test_pure_cli_modules.py (201 lines)
|   |-- test_refactor_facades.py (38 lines)
|   |-- test_report_txt_format.py (145 lines)
|   |-- test_rerank_client.py (58 lines)
|   |-- test_runner_inline_progress.py (76 lines)
|   |-- test_runner_rewind_logic.py (268 lines)
|   |-- test_runner_rewind_pure.py (95 lines)
|   |-- test_runtime_config.py (34 lines)
|   |-- test_sandbox_security.py (139 lines)
|   |-- test_secretary_proc.py (99 lines)
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
|   |-- test_team_map_routing.py (80 lines)
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
|   |   |-- __init__.py (88 lines)
|   |   |-- tracker_aggregate.py (204 lines)
|   |   |-- tracker_batches.py (126 lines)
|   |   |-- tracker_budget.py (75 lines)
|   |   |-- tracker_cache.py (45 lines)
|   |   |-- tracker_helpers.py (118 lines)
|   |   |-- tracker_openrouter.py (37 lines)
|   |   \-- tracker_usage.py (121 lines)
```

## Connections (Dependency Map)

- **agents\ambassador.py**
  - imports agents.base_agent
  - imports core.bootstrap
  - imports core.config
  - imports core.domain.delta_brief
  - imports core.domain.prompts
  - imports core.domain.routing_map
  - imports core.runtime
  - imports json
  - imports logging
  - imports re
  - imports rich.console
  - imports rich.panel
  - imports support._ambassador_classify
  - imports typing
  - imports utils.graphrag_utils
  - imports utils.input_validator
  - imports utils.json_utils
  - imports utils.logger
  - imports utils.tracker
- **agents\base_agent.py**
  - imports abc
  - imports agents.support._api_client
  - imports agents.support._budget_manager
  - imports agents.support._knowledge_manager
  - imports core.app_state
  - imports core.bootstrap
  - imports core.config
  - imports core.config.constants
  - imports core.config.settings
  - imports datetime
  - imports logging
  - imports openai
  - imports pathlib
  - imports re
  - imports threading
  - imports typing
- **agents\chat_agent.py**
  - imports __future__
  - imports core.config
  - imports core.config.settings
  - imports core.domain.prompts
  - imports openai
  - imports typing
- **agents\compact_worker.py**
  - imports __future__
  - imports agents.base_agent
  - imports core.config
  - imports json
  - imports logging
  - imports re
  - imports typing
- **agents\expert.py**
  - imports agents.base_agent
  - imports core.config
  - imports core.domain.prompts
  - imports json
  - imports logging
  - imports pathlib
  - imports re
  - imports rich.console
  - imports rich.panel
  - imports tempfile
  - imports typing
  - imports utils.file_manager
  - imports utils.graphrag_utils
- **agents\explainer.py**
  - imports __future__
  - imports agents.base_agent
  - imports core.config
  - imports core.runtime
  - imports core.storage.code_backup
  - imports difflib
  - imports logging
  - imports pathlib
  - imports re
  - imports subprocess
  - imports typing
- **agents\leader.py**
  - imports agents.base_agent
  - imports agents.support._leader_format
  - imports core.config
  - imports core.config.constants
  - imports core.domain.delta_brief
  - imports core.domain.prompts
  - imports core.runtime
  - imports json
  - imports logging
  - imports pathlib
  - imports typing
  - imports utils.file_manager
  - imports utils.graphrag_utils
- **agents\llm_usage.py**
  - imports agents.support._api_client
- **agents\secretary.py**
  - imports __future__
  - imports agents.base_agent
  - imports agents.support._api_client
  - imports core.config
  - imports core.config.settings
  - imports core.runtime
  - imports core.sandbox.executor
  - imports core.sandbox.policy
  - imports json
  - imports logging
  - imports pathlib
  - imports re
  - imports typing
  - imports utils.graphrag_utils
- **agents\support\_ambassador_classify.py**
  - imports __future__
  - imports re
  - imports typing
- **agents\support\_api_client.py**
  - imports __future__
  - imports _api_transport
  - imports _stream_aggregator
  - imports _usage_logging
  - imports core.config
  - imports core.config.constants
  - imports core.config.registry
  - imports core.runtime
  - imports core.storage._token_window
  - imports logging
  - imports openai
  - imports time
  - imports typing
  - imports utils.budget_guard
  - imports utils.env_guard
  - imports utils.tracker
- **agents\support\_api_transport.py**
  - imports __future__
  - imports logging
  - imports openai
  - imports typing
  - imports utils.tracker
- **agents\support\_budget_manager.py**
  - imports __future__
  - imports agents.base_agent
  - imports logging
  - imports typing
- **agents\support\_knowledge_manager.py**
  - imports __future__
  - imports core.storage
  - imports logging
  - imports threading
  - imports typing
- **agents\support\_leader_format.py**
  - imports __future__
  - imports re
  - imports typing
- **agents\support\_stream_aggregator.py**
  - imports __future__
  - imports _api_transport
  - imports core.runtime
  - imports json
  - imports logging
  - imports re
  - imports time
  - imports typing
- **agents\support\_usage_logging.py**
  - imports __future__
  - imports utils.logger
- **agents\team_map\__init__.py**
  - imports _team_map
- **agents\team_map\_team_map.py**
  - imports core.orchestration.team_graph
- **agents\tool_curator.py**
  - imports __future__
  - imports agents.base_agent
  - imports core.config
  - imports core.runtime
  - imports logging
  - imports pathlib
  - imports re
  - imports subprocess
  - imports sys
  - imports typing
  - imports utils.file_manager
  - imports utils.graphrag_utils
- **agents\worker.py**
  - imports __future__
  - imports agents.base_agent
  - imports agents.support._api_client
  - imports core.config
  - imports core.config.settings
  - imports core.domain.prompts
  - imports core.runtime
  - imports core.sandbox._path_guard
  - imports core.storage.code_backup
  - imports difflib
  - imports json
  - imports logging
  - imports pathlib
  - imports re
  - imports typing
  - imports utils.logger
- **aiteamruntime\__init__.py**
  - imports bus
  - imports contracts
  - imports events
  - imports governor
  - imports overseer
  - imports pipeline
  - imports references
  - imports resources
  - imports runtime
  - imports traces
- **aiteamruntime\agents.py**
  - imports aiteamruntime.integrations.trackaiteam.workflow
- **aiteamruntime\artifacts.py**
  - imports __future__
  - imports pathlib
- **aiteamruntime\bus.py**
  - imports __future__
  - imports collections
  - imports events
  - imports queue
  - imports threading
  - imports typing
- **aiteamruntime\contracts.py**
  - imports __future__
  - imports dataclasses
  - imports typing
- **aiteamruntime\demo.py**
  - imports __future__
  - imports runtime
  - imports test.workflows
  - imports traces
- **aiteamruntime\demo_cli.py**
  - imports __future__
  - imports agents
  - imports argparse
  - imports dataclasses
  - imports events
  - imports rich.console
  - imports rich.live
  - imports rich.panel
  - imports rich.prompt
  - imports rich.table
  - imports rich.text
  - imports runtime
  - imports subprocess
  - imports sys
  - imports threading
  - imports time
  - imports typing
- **aiteamruntime\events.py**
  - imports __future__
  - imports dataclasses
  - imports time
  - imports typing
  - imports uuid
- **aiteamruntime\governor.py**
  - imports __future__
  - imports dataclasses
  - imports events
  - imports time
  - imports typing
- **aiteamruntime\integrations\trackaiteam\__init__.py**
  - imports workflow
- **aiteamruntime\integrations\trackaiteam\workflow.py**
  - imports __future__
  - imports aiteamruntime.events
  - imports aiteamruntime.pipeline
  - imports aiteamruntime.runtime
  - imports concurrent.futures
  - imports functools
  - imports importlib.util
  - imports json
  - imports openai
  - imports os
  - imports pathlib
  - imports re
  - imports sys
  - imports time
  - imports typing
- **aiteamruntime\lock_manager.py**
  - imports __future__
  - imports collections
  - imports dataclasses
  - imports logging
  - imports threading
  - imports time
  - imports typing
- **aiteamruntime\overseer.py**
  - imports __future__
  - imports dataclasses
  - imports events
- **aiteamruntime\pipeline.py**
  - imports __future__
  - imports contracts
  - imports dataclasses
  - imports events
  - imports lock_manager
  - imports runtime
  - imports threading
  - imports typing
- **aiteamruntime\references.py**
  - imports __future__
  - imports json
  - imports pathlib
  - imports sqlite3
  - imports time
  - imports typing
  - imports uuid
- **aiteamruntime\resources.py**
  - imports __future__
  - imports dataclasses
  - imports pathlib
  - imports threading
  - imports typing
- **aiteamruntime\runtime.py**
  - imports __future__
  - imports bus
  - imports collections
  - imports concurrent.futures
  - imports contracts
  - imports dataclasses
  - imports events
  - imports governor
  - imports lock_manager
  - imports logging
  - imports overseer
  - imports references
  - imports resources
  - imports scheduler
  - imports secretary_proc
  - imports threading
  - imports time
  - imports traces
  - imports typing
  - imports uuid
- **aiteamruntime\scheduler.py**
  - imports __future__
  - imports bus
  - imports concurrent.futures
  - imports threading
  - imports typing
- **aiteamruntime\secretary_proc.py**
  - imports __future__
  - imports concurrent.futures
  - imports json
  - imports logging
  - imports os
  - imports pathlib
  - imports subprocess
  - imports sys
  - imports threading
  - imports time
  - imports traces
  - imports typing
  - imports uuid
- **aiteamruntime\test\__init__.py**
  - imports workflows
- **aiteamruntime\test\test_contracts_governor.py**
  - imports __future__
  - imports aiteamruntime
  - imports aiteamruntime.events
  - imports aiteamruntime.runtime
  - imports aiteamruntime.traces
- **aiteamruntime\test\test_pipeline.py**
  - imports __future__
  - imports aiteamruntime
  - imports aiteamruntime.events
  - imports aiteamruntime.runtime
  - imports aiteamruntime.test.workflows
  - imports aiteamruntime.traces
  - imports aiteamruntime.web.server
  - imports json
  - imports pathlib
  - imports threading
  - imports time
  - imports urllib.error
  - imports urllib.request
- **aiteamruntime\test\test_production_boundaries.py**
  - imports __future__
  - imports aiteamruntime.agents
  - imports aiteamruntime.events
  - imports aiteamruntime.runtime
  - imports aiteamruntime.traces
  - imports aiteamruntime.web
  - imports inspect
  - imports json
  - imports pathlib
  - imports threading
  - imports urllib.error
  - imports urllib.request
- **aiteamruntime\test\test_real_model.py**
  - imports __future__
  - imports aiteamruntime
  - imports aiteamruntime.events
  - imports aiteamruntime.integrations.trackaiteam
  - imports aiteamruntime.runtime
  - imports aiteamruntime.traces
  - imports dotenv
  - imports json
  - imports openai
  - imports os
  - imports pathlib
  - imports pytest
  - imports time
  - imports typing
- **aiteamruntime\test\workflows.py**
  - imports __future__
  - imports aiteamruntime.events
  - imports aiteamruntime.pipeline
  - imports aiteamruntime.runtime
  - imports concurrent.futures
  - imports functools
  - imports importlib.util
  - imports json
  - imports openai
  - imports os
  - imports pathlib
  - imports re
  - imports sys
  - imports time
  - imports typing
- **aiteamruntime\traces.py**
  - imports __future__
  - imports events
  - imports json
  - imports logging
  - imports os
  - imports pathlib
  - imports re
  - imports sqlite3
  - imports tempfile
  - imports threading
  - imports time
  - imports typing
  - imports uuid
- **aiteamruntime\web\cli.py**
  - imports __future__
  - imports argparse
  - imports demo
  - imports dotenv
  - imports server
  - imports sys
  - imports traces
  - imports webbrowser
- **aiteamruntime\web\server.py**
  - imports __future__
  - imports aiteamruntime.integrations.trackaiteam
  - imports http
  - imports http.server
  - imports json
  - imports os
  - imports pathlib
  - imports runtime
  - imports socket
  - imports string
  - imports threading
  - imports time
  - imports tkinter
  - imports traces
  - imports urllib.parse
  - imports uuid
- **core\app_state\__init__.py**
  - imports actions
  - imports context_state
  - imports overrides
  - imports settings
- **core\app_state\_io.py**
  - imports __future__
  - imports os
  - imports pathlib
- **core\app_state\actions.py**
  - imports __future__
  - imports core.config.constants
  - imports datetime
  - imports json
  - imports os
  - imports pathlib
  - imports utils.env_guard
- **core\app_state\context_state.py**
  - imports __future__
  - imports _io
  - imports actions
  - imports core.storage
  - imports datetime
  - imports json
  - imports pathlib
  - imports typing
- **core\app_state\overrides.py**
  - imports __future__
  - imports _io
  - imports actions
  - imports core.config
  - imports core.config.constants
  - imports core.storage.knowledge.vault_key
  - imports cryptography.fernet
  - imports datetime
  - imports json
  - imports logging
  - imports pathlib
  - imports typing
- **core\app_state\settings.py**
  - imports __future__
  - imports _io
  - imports core.config.constants
  - imports json
  - imports pathlib
  - imports threading
  - imports typing
- **core\bootstrap.py**
  - imports __future__
  - imports pathlib
  - imports sys
- **core\cli\python_cli\__init__.py**
  - imports core.cli.python_cli.shell
- **core\cli\python_cli\entrypoints\app.py**
  - imports __future__
  - imports click
  - imports core.app_state
  - imports core.bootstrap
  - imports core.cli.python_cli.shell.menu
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.ui.ui
  - imports os
  - imports sys
  - imports typing
- **core\cli\python_cli\features\ask\chat_manager.py**
  - imports __future__
  - imports concurrent.futures
  - imports core.app_state
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.ui.palette_app
  - imports core.cli.python_cli.ui.ui
  - imports core.storage
  - imports core.storage.conversation_archive
  - imports datetime
  - imports history_renderer
  - imports io
  - imports model_selector
  - imports re
  - imports rich.box
  - imports rich.console
  - imports rich.prompt
  - imports rich.table
  - imports shutil
  - imports typing
- **core\cli\python_cli\features\ask\flow.py**
  - imports __future__
  - imports chat_manager
  - imports core.app_state
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.ui.palette_app
  - imports core.cli.python_cli.ui.ui
  - imports core.domain.prompts
  - imports core.storage
  - imports core.storage._token_window
  - imports core.storage.memory_coordinator
  - imports history_renderer
  - imports io
  - imports model_selector
  - imports rich.box
  - imports rich.console
  - imports rich.markdown
  - imports rich.panel
  - imports shutil
  - imports time
  - imports typing
  - imports utils.input_validator
- **core\cli\python_cli\features\ask\history_renderer.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.ui.palette
  - imports core.cli.python_cli.ui.ui
  - imports rich.box
  - imports rich.markdown
  - imports rich.panel
  - imports rich.rule
  - imports rich.style
  - imports rich.table
  - imports rich.text
  - imports typing
- **core\cli\python_cli\features\ask\model_selector.py**
  - imports __future__
  - imports agents.support._api_client
  - imports core.app_state
  - imports core.config
  - imports core.config.settings
  - imports utils.budget_guard
  - imports utils.tracker
- **core\cli\python_cli\features\change\__init__.py**
  - imports detail
  - imports list
- **core\cli\python_cli\features\change\_role_actions.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.shell.state
  - imports core.cli.python_cli.ui.ui
  - imports json
  - imports rich.box
  - imports rich.panel
  - imports rich.prompt
  - imports urllib.request
  - imports utils.free_model_finder
- **core\cli\python_cli\features\change\detail.py**
  - imports __future__
  - imports core.cli.python_cli.features.change._role_actions
  - imports core.cli.python_cli.features.change.helpers
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.shell.state
  - imports core.cli.python_cli.ui.ui
  - imports core.config
  - imports core.config.pricing
  - imports json
  - imports rich.box
  - imports rich.markdown
  - imports rich.panel
  - imports rich.style
  - imports rich.table
- **core\cli\python_cli\features\change\flow.py**
  - imports __future__
  - imports core.cli.python_cli.features.change
- **core\cli\python_cli\features\change\helpers.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.ui.ui
  - imports core.config
  - imports rich.console
  - imports rich.markup
  - imports rich.text
  - imports textwrap
- **core\cli\python_cli\features\change\list.py**
  - imports __future__
  - imports core.cli.python_cli.features.change.helpers
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.ui.palette_app
  - imports core.cli.python_cli.ui.ui
  - imports rich.box
  - imports rich.prompt
  - imports rich.style
  - imports rich.table
  - imports typing
- **core\cli\python_cli\features\context\__init__.py**
  - imports common
  - imports confirm
  - imports monitor_actions
  - imports viewer
- **core\cli\python_cli\features\context\common.py**
  - imports __future__
  - imports core.app_state
  - imports core.cli.python_cli.workflow.runtime.persist.activity_log
  - imports core.config
  - imports core.domain.delta_brief
  - imports core.runtime
  - imports core.storage.graphrag_store
  - imports pathlib
  - imports utils.file_manager
  - imports utils.logger
- **core\cli\python_cli\features\context\confirm.py**
  - imports __future__
  - imports core.app_state
  - imports core.cli.python_cli.features.context.common
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.shell.safe_editor
  - imports core.cli.python_cli.shell.safe_read
  - imports core.cli.python_cli.ui.ui
  - imports pathlib
  - imports rich.box
  - imports rich.markdown
  - imports rich.panel
  - imports time
  - imports typing
- **core\cli\python_cli\features\context\flow.py**
  - imports __future__
  - imports core.cli.python_cli.features.context
- **core\cli\python_cli\features\context\monitor_actions.py**
  - imports __future__
  - imports core.app_state
  - imports core.cli.python_cli.features.context.common
  - imports core.cli.python_cli.workflow.runtime.graph.runner
  - imports core.cli.python_cli.workflow.runtime.persist.activity_log
  - imports core.domain.delta_brief
  - imports core.runtime
- **core\cli\python_cli\features\context\viewer.py**
  - imports __future__
  - imports core.app_state
  - imports core.cli.python_cli.features.context.common
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.choice_lists
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.shell.safe_editor
  - imports core.cli.python_cli.shell.safe_read
  - imports core.cli.python_cli.ui.palette
  - imports core.cli.python_cli.ui.ui
  - imports core.cli.python_cli.workflow.runtime.graph.runner
  - imports core.domain.delta_brief
  - imports core.runtime
  - imports rich.box
  - imports rich.markdown
  - imports rich.panel
  - imports rich.prompt
  - imports typing
- **core\cli\python_cli\features\dashboard\flow.py**
  - imports core.frontends.dashboard
- **core\cli\python_cli\features\explain\flow.py**
  - imports __future__
  - imports agents.explainer
  - imports core.app_state
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.ui.ui
  - imports os
  - imports pathlib
  - imports rich.box
  - imports rich.console
  - imports rich.panel
- **core\cli\python_cli\features\settings\flow.py**
  - imports __future__
  - imports core.app_state
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.ui.ui
  - imports io
  - imports rich.box
  - imports rich.console
  - imports rich.panel
  - imports rich.style
  - imports rich.table
  - imports time
- **core\cli\python_cli\features\start\clarification_helpers.py**
  - imports agents.support._api_client
  - imports core.config
  - imports core.config.settings
  - imports core.domain.prompts
  - imports json
  - imports logging
  - imports re
  - imports utils.file_manager
- **core\cli\python_cli\features\start\flow.py**
  - imports __future__
  - imports core.app_state
  - imports core.cli.python_cli.features.ask.flow
  - imports core.cli.python_cli.features.context.flow
  - imports core.cli.python_cli.features.start.clarification_helpers
  - imports core.cli.python_cli.features.start.pipeline_runner
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.choice_lists
  - imports core.cli.python_cli.shell.command_registry
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.ui.palette_app
  - imports core.cli.python_cli.ui.rich_command_palette
  - imports core.cli.python_cli.ui.ui
  - imports core.cli.python_cli.workflow.runtime.graph.runner
  - imports core.cli.python_cli.workflow.runtime.persist.activity_log
  - imports core.frontends.tui
  - imports core.orchestration.pipeline_artifacts
  - imports core.runtime
  - imports io
  - imports logging
  - imports rich.box
  - imports rich.console
  - imports rich.panel
  - imports rich.prompt
  - imports shutil
  - imports sys
  - imports threading
  - imports typing
  - imports utils
  - imports utils.file_manager
  - imports utils.logger
- **core\cli\python_cli\features\start\pipeline_runner.py**
  - imports agents.ambassador
  - imports agents.secretary
  - imports core.app_state.settings
  - imports core.cli.python_cli.features.start.clarification_helpers
  - imports core.cli.python_cli.workflow.runtime.graph.runner
  - imports core.domain.delta_brief
  - imports core.orchestration.pipeline_artifacts
  - imports core.runtime
  - imports json
  - imports logging
  - imports os
  - imports re
  - imports threading
  - imports time
  - imports utils
  - imports utils.logger
- **core\cli\python_cli\i18n.py**
  - imports __future__
- **core\cli\python_cli\shell\_info_screen.py**
  - imports __future__
  - imports core.app_state
  - imports core.cli.python_cli.features.change.flow
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.command_registry
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.shell.screens.change
  - imports core.cli.python_cli.ui.help_terminal
  - imports core.cli.python_cli.ui.palette_app
  - imports core.cli.python_cli.ui.ui
  - imports core.config
  - imports io
  - imports rich.box
  - imports rich.console
  - imports rich.markdown
  - imports rich.panel
  - imports rich.style
  - imports rich.table
  - imports shutil
  - imports typing
- **core\cli\python_cli\shell\_status_screen.py**
  - imports __future__
  - imports core.app_state
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.ui.ui
  - imports core.config
  - imports core.runtime
  - imports io
  - imports os
  - imports pathlib
  - imports platform
  - imports prompt_toolkit
  - imports prompt_toolkit.completion
  - imports prompt_toolkit.shortcuts
  - imports prompt_toolkit.styles
  - imports psutil
  - imports rich.box
  - imports rich.console
  - imports rich.panel
  - imports rich.style
  - imports rich.table
  - imports shutil
  - imports subprocess
  - imports time
  - imports winreg
- **core\cli\python_cli\shell\choice_lists.py**
  - imports __future__
  - imports core.cli.python_cli.shell.command_registry
- **core\cli\python_cli\shell\command_parser.py**
  - imports __future__
- **core\cli\python_cli\shell\command_registry.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
- **core\cli\python_cli\shell\menu.py**
  - imports __future__
  - imports core.app_state
  - imports core.cli.python_cli.features.ask.flow
  - imports core.cli.python_cli.features.context.flow
  - imports core.cli.python_cli.features.explain.flow
  - imports core.cli.python_cli.features.settings.flow
  - imports core.cli.python_cli.features.start.flow
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.command_registry
  - imports core.cli.python_cli.shell.monitor_queue_drain
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.shell.screens.info
  - imports core.cli.python_cli.shell.screens.status
  - imports core.cli.python_cli.ui.rich_command_palette
  - imports core.cli.python_cli.ui.ui
  - imports core.frontends.dashboard
  - imports core.frontends.tui
  - imports core.runtime
  - imports os
  - imports signal
  - imports sys
  - imports threading
  - imports time
  - imports utils.env_guard
- **core\cli\python_cli\shell\monitor_payload.py**
  - imports __future__
  - imports pathlib
- **core\cli\python_cli\shell\monitor_queue_drain.py**
  - imports __future__
  - imports collections.abc
  - imports core.app_state
  - imports core.cli.python_cli.features.context.flow
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.monitor_payload
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.ui.ui
  - imports core.cli.python_cli.workflow.runtime.graph.runner
  - imports core.cli.python_cli.workflow.runtime.persist.activity_log
  - imports core.config
  - imports core.runtime
  - imports typing
- **core\cli\python_cli\shell\prompt.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.ui.autocomplete
  - imports core.cli.python_cli.ui.palette_app
  - imports prompt_toolkit
  - imports rich.console
  - imports rich.markup
  - imports rich.prompt
  - imports rich.text
  - imports sys
  - imports typing
- **core\cli\python_cli\shell\safe_editor.py**
  - imports __future__
  - imports os
  - imports pathlib
  - imports shlex
  - imports subprocess
- **core\cli\python_cli\shell\safe_read.py**
  - imports __future__
  - imports pathlib
- **core\cli\python_cli\shell\screens\change.py**
  - imports __future__
  - imports core.app_state
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.ui.ui
  - imports core.config
  - imports io
  - imports rich.box
  - imports rich.console
  - imports rich.panel
  - imports rich.style
  - imports rich.table
  - imports shutil
- **core\cli\python_cli\shell\state.py**
  - imports __future__
  - imports core.app_state
  - imports core.config.constants
  - imports json
  - imports logging
  - imports pathlib
  - imports threading
  - imports typing
- **core\cli\python_cli\ui\autocomplete.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
  - imports prompt_toolkit.completion
  - imports prompt_toolkit.document
  - imports typing
- **core\cli\python_cli\ui\help_terminal.py**
  - imports __future__
  - imports core.cli.python_cli.shell.command_registry
  - imports core.cli.python_cli.shell.prompt
  - imports os
  - imports pathlib
  - imports rich.console
  - imports rich.markdown
  - imports rich.panel
  - imports shlex
  - imports shutil
  - imports subprocess
  - imports sys
- **core\cli\python_cli\ui\helpbox.py**
  - imports __future__
  - imports core.cli.python_cli.ui.ui
  - imports rich.box
  - imports rich.panel
- **core\cli\python_cli\ui\palette\__init__.py**
  - imports __future__
  - imports app
  - imports footer
  - imports items
  - imports lexer
  - imports popup
  - imports shared
- **core\cli\python_cli\ui\palette\app.py**
  - imports __future__
  - imports footer
  - imports items
  - imports os
  - imports popup
  - imports prompt_toolkit
  - imports prompt_toolkit.buffer
  - imports prompt_toolkit.data_structures
  - imports prompt_toolkit.document
  - imports prompt_toolkit.formatted_text
  - imports prompt_toolkit.key_binding
  - imports prompt_toolkit.layout
  - imports prompt_toolkit.layout.containers
  - imports prompt_toolkit.layout.controls
  - imports prompt_toolkit.layout.dimension
  - imports prompt_toolkit.mouse_events
  - imports re
  - imports rich.text
  - imports shared
  - imports shutil
- **core\cli\python_cli\ui\palette\footer.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.ui.autocomplete
  - imports io
  - imports rich.console
- **core\cli\python_cli\ui\palette\items.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.ui.autocomplete
  - imports styles
  - imports typing
- **core\cli\python_cli\ui\palette\lexer.py**
  - imports __future__
  - imports core.cli.python_cli.ui.autocomplete
  - imports prompt_toolkit.lexers
  - imports re
  - imports styles
  - imports typing
- **core\cli\python_cli\ui\palette\popup.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
  - imports items
  - imports prompt_toolkit.layout.containers
  - imports prompt_toolkit.layout.controls
  - imports prompt_toolkit.layout.dimension
  - imports prompt_toolkit.layout.margins
  - imports prompt_toolkit.widgets
  - imports typing
- **core\cli\python_cli\ui\palette\shared.py**
  - imports __future__
  - imports core.cli.python_cli.ui.autocomplete
  - imports items
  - imports lexer
  - imports pathlib
  - imports popup
  - imports prompt_toolkit.buffer
  - imports prompt_toolkit.filters
  - imports prompt_toolkit.layout.containers
  - imports prompt_toolkit.layout.controls
  - imports prompt_toolkit.layout.dimension
  - imports prompt_toolkit.layout.processors
  - imports prompt_toolkit.output.color_depth
  - imports prompt_toolkit.styles
  - imports prompt_toolkit.styles.defaults
  - imports prompt_toolkit.widgets
  - imports shutil
  - imports sys
  - imports time
  - imports typing
- **core\cli\python_cli\ui\palette\styles.py**
  - imports __future__
  - imports core.cli.python_cli.ui.ui
- **core\cli\python_cli\ui\palette_app.py**
  - imports __future__
  - imports core.cli.python_cli.ui.palette
- **core\cli\python_cli\ui\palette_shared.py**
  - imports __future__
  - imports core.cli.python_cli.ui.palette
- **core\cli\python_cli\ui\rich_command_palette.py**
  - imports __future__
  - imports core.app_state
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.choice_lists
  - imports core.cli.python_cli.ui.ui
  - imports io
  - imports rich.box
  - imports rich.console
  - imports rich.panel
  - imports rich.style
  - imports rich.table
  - imports rich.text
  - imports shutil
- **core\cli\python_cli\ui\ui.py**
  - imports __future__
  - imports importlib
  - imports os
  - imports pathlib
  - imports platform
  - imports rich.box
  - imports rich.console
  - imports rich.panel
  - imports rich.rule
  - imports rich.style
  - imports rich.text
  - imports subprocess
  - imports sys
  - imports tomllib
- **core\cli\python_cli\workflow\runtime\graph\runner.py**
  - imports __future__
  - imports contextlib
  - imports core.app_state.actions
  - imports core.app_state.context_state
  - imports core.bootstrap
  - imports core.cli.python_cli.ui.ui
  - imports core.domain.routing_map
  - imports core.orchestration
  - imports core.storage.memory_coordinator
  - imports logging
  - imports pathlib
  - imports persist.activity_log
  - imports persist.checkpointer
  - imports rich.live
  - imports runner_resume
  - imports runner_rewind
  - imports runner_ui
  - imports subprocess
  - imports sys
  - imports typing
  - imports utils.logger
- **core\cli\python_cli\workflow\runtime\graph\runner_resume.py**
  - imports __future__
  - imports core.orchestration
  - imports core.storage.conversation_archive
  - imports core.storage.memory_coordinator
  - imports logging
  - imports persist.checkpointer
- **core\cli\python_cli\workflow\runtime\graph\runner_rewind.py**
  - imports __future__
  - imports core.orchestration
  - imports datetime
  - imports logging
  - imports pathlib
  - imports persist.activity_log
  - imports persist.checkpointer
  - imports runner_resume
  - imports time
  - imports utils.file_manager
  - imports utils.logger
- **core\cli\python_cli\workflow\runtime\graph\runner_ui.py**
  - imports __future__
  - imports rich.box
  - imports rich.panel
  - imports rich.table
  - imports rich.text
- **core\cli\python_cli\workflow\runtime\persist\activity_log.py**
  - imports __future__
  - imports json
  - imports pathlib
  - imports time
  - imports typing
  - imports utils.activity_badges
  - imports utils.env_guard
  - imports utils.file_manager
- **core\cli\python_cli\workflow\runtime\persist\checkpointer.py**
  - imports __future__
  - imports functools
  - imports langgraph.checkpoint.sqlite
  - imports session
  - imports sqlite3
- **core\cli\python_cli\workflow\runtime\present\pipeline_markdown.py**
  - imports __future__
  - imports typing
- **core\cli\python_cli\workflow\runtime\session\__init__.py**
  - imports _session_core
  - imports session_monitor_manager
  - imports session_notification
  - imports session_pause_manager
  - imports session_pipeline_state
  - imports time
- **core\cli\python_cli\workflow\runtime\session\_session_core.py**
  - imports __future__
  - imports pathlib
  - imports session_store
  - imports typing
  - imports utils.file_manager
  - imports uuid
- **core\cli\python_cli\workflow\runtime\session\session_monitor_manager.py**
  - imports __future__
  - imports _session_core
- **core\cli\python_cli\workflow\runtime\session\session_notification.py**
  - imports __future__
  - imports _session_core
  - imports pathlib
  - imports time
  - imports typing
  - imports uuid
- **core\cli\python_cli\workflow\runtime\session\session_pause_manager.py**
  - imports __future__
  - imports _session_core
  - imports typing
- **core\cli\python_cli\workflow\runtime\session\session_pipeline_state.py**
  - imports __future__
  - imports _session_core
  - imports core.cli.python_cli.features.context.flow
  - imports pathlib
  - imports session_notification
  - imports session_pause_manager
  - imports state
  - imports state._clarification
  - imports state._diff_state
  - imports state._role_substates
  - imports state._stream_history
  - imports state._stream_state
  - imports threading
  - imports time
  - imports typing
  - imports utils.file_manager
  - imports uuid
- **core\cli\python_cli\workflow\runtime\session\session_store.py**
  - imports __future__
  - imports json
  - imports os
  - imports pathlib
  - imports threading
  - imports time
  - imports typing
  - imports utils.file_manager
- **core\cli\python_cli\workflow\runtime\session\state\_clarification.py**
  - imports __future__
  - imports _session_core
- **core\cli\python_cli\workflow\runtime\session\state\_diff_state.py**
  - imports __future__
  - imports threading
  - imports time
- **core\cli\python_cli\workflow\runtime\session\state\_role_substates.py**
  - imports __future__
  - imports threading
  - imports time
  - imports typing
- **core\cli\python_cli\workflow\runtime\session\state\_stream_history.py**
  - imports __future__
  - imports _session_core
  - imports json
  - imports os
  - imports threading
- **core\cli\python_cli\workflow\runtime\session\state\_stream_state.py**
  - imports __future__
  - imports threading
  - imports time
- **core\cli\python_cli\workflow\tui\__main__.py**
  - imports monitor
  - imports sys
- **core\cli\python_cli\workflow\tui\monitor\__init__.py**
  - imports app
  - imports runtime
- **core\cli\python_cli\workflow\tui\monitor\_pipeline_meta.py**
  - imports __future__
  - imports core.config
  - imports core.domain.routing_map
  - imports runtime
  - imports runtime.present.pipeline_markdown
  - imports typing
- **core\cli\python_cli\workflow\tui\monitor\_task_pool.py**
  - imports __future__
  - imports atexit
  - imports concurrent.futures
  - imports logging
  - imports threading
  - imports typing
- **core\cli\python_cli\workflow\tui\monitor\app.py**
  - imports __future__
  - imports asyncio
  - imports commands.mixin
  - imports core._constants
  - imports core._content_mixin
  - imports core._layout_mixin
  - imports core._render_mixin
  - imports core._tasks_mixin
  - imports core._utils
  - imports core._views_mixin
  - imports core.cli.python_cli.features.context
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.safe_read
  - imports helpers
  - imports prompt_toolkit
  - imports prompt_toolkit.buffer
  - imports queue
  - imports runtime
  - imports sys
  - imports time
  - imports typing
- **core\cli\python_cli\workflow\tui\monitor\commands\__init__.py**
  - imports ask
  - imports btw
  - imports check
  - imports mixin
- **core\cli\python_cli\workflow\tui\monitor\commands\ask.py**
  - imports __future__
  - imports _task_pool
  - imports core._constants
  - imports core.cli.python_cli.features.ask.model_selector
  - imports core.cli.python_cli.i18n
  - imports core.domain.prompts
- **core\cli\python_cli\workflow\tui\monitor\commands\btw.py**
  - imports __future__
  - imports _task_pool
  - imports core._constants
  - imports core._utils
  - imports core.cli.python_cli.i18n
  - imports helpers
  - imports runtime
  - imports shared.btw_inline
  - imports time
- **core\cli\python_cli\workflow\tui\monitor\commands\check.py**
  - imports __future__
  - imports _task_pool
  - imports core._constants
  - imports core._utils
  - imports core.cli.python_cli.features.context
  - imports core.cli.python_cli.features.context.monitor_actions
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.safe_editor
  - imports helpers
  - imports subprocess
- **core\cli\python_cli\workflow\tui\monitor\commands\explainer.py**
  - imports __future__
  - imports _task_pool
  - imports agents.explainer
  - imports core.app_state
- **core\cli\python_cli\workflow\tui\monitor\commands\gate.py**
  - imports __future__
  - imports _task_pool
  - imports core._constants
  - imports core.cli.python_cli.features.context.monitor_actions
  - imports core.cli.python_cli.features.start.flow
  - imports core.cli.python_cli.i18n
- **core\cli\python_cli\workflow\tui\monitor\commands\mixin.py**
  - imports __future__
  - imports ask
  - imports btw
  - imports check
  - imports core._constants
  - imports core._utils
  - imports core.app_state
  - imports core.cli.python_cli.i18n
  - imports explainer
  - imports gate
  - imports helpers
  - imports runtime
  - imports runtime.persist.activity_log
- **core\cli\python_cli\workflow\tui\monitor\core\__init__.py**
  - imports _constants
  - imports _content_mixin
  - imports _controls
  - imports _layout_mixin
  - imports _render_mixin
  - imports _tasks_mixin
  - imports _utils
  - imports _views_mixin
- **core\cli\python_cli\workflow\tui\monitor\core\_constants.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
  - imports re
- **core\cli\python_cli\workflow\tui\monitor\core\_content_mixin.py**
  - imports __future__
  - imports _utils
  - imports core.cli.python_cli.i18n
  - imports re
  - imports runtime
  - imports subprocess
  - imports sys
- **core\cli\python_cli\workflow\tui\monitor\core\_controls.py**
  - imports __future__
  - imports prompt_toolkit.data_structures
  - imports prompt_toolkit.formatted_text
  - imports prompt_toolkit.layout.controls
  - imports prompt_toolkit.mouse_events
- **core\cli\python_cli\workflow\tui\monitor\core\_keybindings.py**
  - imports __future__
  - imports _constants
  - imports _utils
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.ui.palette
  - imports prompt_toolkit.document
  - imports prompt_toolkit.filters
  - imports prompt_toolkit.key_binding
  - imports re
  - imports rich.markup
  - imports runtime
  - imports time
- **core\cli\python_cli\workflow\tui\monitor\core\_layout_mixin.py**
  - imports __future__
  - imports _constants
  - imports _controls
  - imports _keybindings
  - imports _utils
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.ui.palette
  - imports helpers
  - imports prompt_toolkit
  - imports prompt_toolkit.buffer
  - imports prompt_toolkit.document
  - imports prompt_toolkit.filters
  - imports prompt_toolkit.formatted_text
  - imports prompt_toolkit.layout
  - imports prompt_toolkit.layout.containers
  - imports prompt_toolkit.layout.controls
  - imports prompt_toolkit.layout.processors
- **core\cli\python_cli\workflow\tui\monitor\core\_refresh_state_mixin.py**
  - imports __future__
  - imports _constants
  - imports _utils
  - imports core.cli.python_cli.i18n
  - imports state
  - imports state._update_state
  - imports time
- **core\cli\python_cli\workflow\tui\monitor\core\_render_mixin.py**
  - imports __future__
  - imports _constants
  - imports _refresh_state_mixin
  - imports _role_card_mixin
  - imports _transition_mixin
  - imports _utils
  - imports core.cli.python_cli.i18n
  - imports helpers
  - imports runtime
  - imports state
  - imports state._clarify
  - imports state._leader
  - imports state._secretary
  - imports state._tool_curator
  - imports state._worker
  - imports time
- **core\cli\python_cli\workflow\tui\monitor\core\_role_card_mixin.py**
  - imports __future__
  - imports _constants
  - imports _utils
  - imports helpers
  - imports state
  - imports state._leader
  - imports state._secretary
  - imports state._tool_curator
  - imports state._worker
  - imports sys
  - imports time
- **core\cli\python_cli\workflow\tui\monitor\core\_tasks_mixin.py**
  - imports __future__
  - imports _constants
  - imports _task_pool
  - imports core.cli.python_cli.features.context.monitor_actions
  - imports core.cli.python_cli.features.start.flow
  - imports helpers
  - imports runtime
  - imports time
- **core\cli\python_cli\workflow\tui\monitor\core\_transition_mixin.py**
  - imports __future__
  - imports _constants
  - imports _utils
  - imports core.cli.python_cli.i18n
  - imports helpers
  - imports runtime
  - imports state
  - imports state._leader
  - imports time
- **core\cli\python_cli\workflow\tui\monitor\core\_utils.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
  - imports core.config
  - imports helpers
  - imports io
  - imports rich.console
  - imports runtime
- **core\cli\python_cli\workflow\tui\monitor\core\_views_mixin.py**
  - imports __future__
  - imports _utils
  - imports core.cli.python_cli.features.context.flow
  - imports pathlib
  - imports re
  - imports runtime.persist.activity_log
- **core\cli\python_cli\workflow\tui\monitor\helpers.py**
  - imports __future__
  - imports _pipeline_meta
  - imports core.bootstrap
  - imports core.config
  - imports core.orchestration
  - imports re
  - imports runtime
  - imports runtime.persist.activity_log
  - imports runtime.persist.checkpointer
  - imports typing
- **core\cli\python_cli\workflow\tui\monitor\screens.py**
  - imports __future__
  - imports core.app_state
  - imports core.cli.python_cli.features.context.flow
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.safe_editor
  - imports core.cli.python_cli.shell.safe_read
  - imports helpers
  - imports pathlib
  - imports runtime
  - imports runtime.persist.activity_log
  - imports textual.app
  - imports textual.binding
  - imports textual.containers
  - imports textual.screen
  - imports textual.widgets
- **core\cli\python_cli\workflow\tui\monitor\state\__init__.py**
  - imports __future__
  - imports _ambassador
  - imports _clarify
  - imports _explainer
  - imports _gate
  - imports _leader
  - imports _pipeline
  - imports _secretary
  - imports _tool_curator
  - imports _worker
- **core\cli\python_cli\workflow\tui\monitor\state\_ambassador.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
- **core\cli\python_cli\workflow\tui\monitor\state\_clarify.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
- **core\cli\python_cli\workflow\tui\monitor\state\_explainer.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
- **core\cli\python_cli\workflow\tui\monitor\state\_gate.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
- **core\cli\python_cli\workflow\tui\monitor\state\_leader.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
- **core\cli\python_cli\workflow\tui\monitor\state\_pipeline.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
- **core\cli\python_cli\workflow\tui\monitor\state\_secretary.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
- **core\cli\python_cli\workflow\tui\monitor\state\_tool_curator.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
- **core\cli\python_cli\workflow\tui\monitor\state\_update_state.py**
  - imports __future__
- **core\cli\python_cli\workflow\tui\monitor\state\_worker.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
- **core\cli\python_cli\workflow\tui\shared\agent_cards.py**
  - imports __future__
  - imports core.config
  - imports dataclasses
  - imports monitor.helpers
  - imports typing
- **core\cli\python_cli\workflow\tui\shared\btw_inline.py**
  - imports __future__
  - imports agents.support._api_client
  - imports core.config
  - imports core.config.settings
  - imports core.domain.prompts
  - imports logging
  - imports monitor.helpers
  - imports typing
- **core\cli\python_cli\workflow\tui\shared\display_policy.py**
  - imports __future__
  - imports dataclasses
- **core\config\__init__.py**
  - imports __future__
  - imports core.config.service
  - imports typing
- **core\config\constants.py**
  - imports pathlib
- **core\config\hardware.py**
  - imports GPUtil
  - imports __future__
  - imports ctypes
  - imports os
  - imports platform
  - imports psutil
  - imports subprocess
  - imports torch
  - imports typing
- **core\config\pricing.py**
  - imports __future__
  - imports core.config.constants
  - imports json
  - imports typing
  - imports urllib.error
  - imports urllib.request
- **core\config\registry\__init__.py**
  - imports __future__
  - imports coding
  - imports typing
- **core\config\registry\coding\__init__.py**
  - imports __future__
  - imports chat
  - imports devops
  - imports fixers
  - imports leaders
  - imports memory
  - imports researchers
  - imports reviewers
  - imports support
  - imports system
  - imports testers
  - imports typing
  - imports workers
- **core\config\registry\coding\chat.py**
  - imports __future__
  - imports typing
- **core\config\registry\coding\devops.py**
  - imports __future__
  - imports typing
- **core\config\registry\coding\fixers.py**
  - imports __future__
  - imports typing
- **core\config\registry\coding\leaders.py**
  - imports __future__
  - imports typing
- **core\config\registry\coding\memory.py**
  - imports __future__
  - imports typing
- **core\config\registry\coding\researchers.py**
  - imports __future__
  - imports typing
- **core\config\registry\coding\reviewers.py**
  - imports __future__
  - imports typing
- **core\config\registry\coding\support.py**
  - imports __future__
  - imports typing
- **core\config\registry\coding\system.py**
  - imports __future__
  - imports typing
- **core\config\registry\coding\testers.py**
  - imports __future__
  - imports typing
- **core\config\registry\coding\workers.py**
  - imports __future__
  - imports typing
- **core\config\runtime_config.py**
  - imports __future__
  - imports dataclasses
  - imports typing
- **core\config\service.py**
  - imports __future__
  - imports core.app_state
  - imports core.config.hardware
  - imports core.config.pricing
  - imports core.config.registry
  - imports core.config.settings
  - imports os
  - imports pathlib
  - imports platform
  - imports rich.console
  - imports typing
- **core\config\settings.py**
  - imports __future__
  - imports dotenv
  - imports os
  - imports pathlib
  - imports prompt_toolkit
  - imports urllib.parse
- **core\dashboard\__init__.py**
  - imports __future__
  - imports presentation.shell
- **core\dashboard\application\__init__.py**
  - imports core.dashboard.reporting.state
  - imports data
- **core\dashboard\application\data.py**
  - imports __future__
  - imports datetime
  - imports typing
  - imports utils
- **core\dashboard\export\__init__.py**
  - imports core.dashboard.output.exporters
  - imports core.dashboard.output.pdf_export
  - imports core.dashboard.reporting.text_export
- **core\dashboard\output\exporters.py**
  - imports __future__
  - imports core.config.constants
  - imports core.paths
  - imports datetime
  - imports openpyxl
  - imports openpyxl.styles
  - imports os
  - imports pathlib
  - imports reporting.report_model
  - imports reporting.state
  - imports tui.log_console
  - imports typing
  - imports urllib.error
  - imports urllib.request
- **core\dashboard\output\pdf_export.py**
  - imports __future__
  - imports core.paths
  - imports datetime
  - imports fpdf
  - imports pathlib
  - imports reporting.report_model
  - imports reporting.state
  - imports reporting.text_export
  - imports tui.log_console
  - imports typing
- **core\dashboard\presentation\shell\__init__.py**
  - imports core.dashboard.shell.app
  - imports core.dashboard.shell.history
  - imports core.dashboard.shell.total
- **core\dashboard\presentation\tui\__init__.py**
  - imports core.dashboard.tui.render
- **core\dashboard\reporting\__init__.py**
  - imports report_model
  - imports report_txt_format
  - imports state
  - imports text_export
- **core\dashboard\reporting\report_model.py**
  - imports __future__
  - imports dataclasses
  - imports datetime
  - imports state
  - imports tui.utils
  - imports typing
  - imports utils
- **core\dashboard\reporting\report_txt_format.py**
  - imports __future__
  - imports report_model
- **core\dashboard\reporting\state.py**
  - imports __future__
  - imports dataclasses
  - imports datetime
  - imports pathlib
  - imports typing
  - imports utils.tracker
- **core\dashboard\reporting\text_export.py**
  - imports __future__
  - imports datetime
  - imports pathlib
  - imports report_model
  - imports report_txt_format
  - imports state
  - imports tui.log_console
- **core\dashboard\shell\app.py**
  - imports __future__
  - imports budget
  - imports core.app_state.context_state
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.ui.palette_app
  - imports core.cli.python_cli.ui.ui
  - imports datetime
  - imports history
  - imports io
  - imports pathlib
  - imports reporting.state
  - imports rich.box
  - imports rich.console
  - imports rich.panel
  - imports rich.prompt
  - imports rich.style
  - imports rich.table
  - imports shutil
  - imports total
  - imports tui.render
  - imports tui.utils
  - imports typing
  - imports utils
- **core\dashboard\shell\budget.py**
  - imports __future__
  - imports core.app_state.settings
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.ui.palette_app
  - imports core.cli.python_cli.ui.ui
  - imports io
  - imports rich.box
  - imports rich.console
  - imports rich.panel
  - imports rich.style
  - imports rich.table
  - imports rich.text
  - imports shutil
  - imports tui.render
  - imports typing
  - imports utils
- **core\dashboard\shell\data.py**
  - imports core.dashboard.application.data
- **core\dashboard\shell\history.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.ui.palette_app
  - imports core.cli.python_cli.ui.ui
  - imports core.dashboard.application
  - imports io
  - imports output.exporters
  - imports output.pdf_export
  - imports pathlib
  - imports reporting.state
  - imports reporting.text_export
  - imports rich.box
  - imports rich.console
  - imports rich.panel
  - imports rich.prompt
  - imports rich.style
  - imports rich.table
  - imports rich.text
  - imports shutil
  - imports tui.panels
  - imports tui.render
  - imports tui.utils
  - imports typing
- **core\dashboard\shell\total.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.ui.ui
  - imports core.dashboard.application
  - imports io
  - imports reporting.state
  - imports rich.box
  - imports rich.console
  - imports rich.table
  - imports shutil
  - imports tui.panels
  - imports tui.render
  - imports tui.utils
  - imports utils
- **core\dashboard\tui\log_console.py**
  - imports __future__
  - imports rich.console
- **core\dashboard\tui\panels.py**
  - imports __future__
  - imports core.cli.python_cli.ui.ui
  - imports rich.box
  - imports rich.panel
  - imports typing
- **core\dashboard\tui\render.py**
  - imports __future__
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.shell.prompt
  - imports core.cli.python_cli.ui.palette_app
  - imports core.config
  - imports datetime
  - imports log_console
  - imports rich.box
  - imports rich.panel
  - imports rich.prompt
  - imports rich.style
  - imports rich.table
  - imports rich.text
  - imports typing
  - imports utils
  - imports utils.tracker
- **core\dashboard\tui\utils.py**
  - imports __future__
  - imports core.cli.python_cli.ui.ui
  - imports datetime
  - imports typing
  - imports utils
- **core\domain\agent_protocol.py**
  - imports __future__
  - imports typing
- **core\domain\delta_brief.py**
  - imports __future__
  - imports datetime
  - imports pathlib
  - imports pydantic
  - imports typing
  - imports uuid
- **core\domain\pipeline_state.py**
  - imports core.orchestration.pipeline_artifacts
- **core\domain\prompts\__init__.py**
  - imports ambassador
  - imports ask_mode
  - imports btw_coordinator
  - imports clarification
  - imports expert
  - imports leader
  - imports workers
- **core\domain\prompts\expert.py**
  - imports core.domain.prompts.leader
  - imports json
  - imports typing
- **core\domain\prompts\leader.py**
  - imports core.config
- **core\domain\prompts\workers.py**
  - imports __future__
  - imports typing
- **core\domain\routing_map.py**
  - imports __future__
  - imports typing
- **core\domain\skills\__init__.py**
  - imports __future__
  - imports _loader
  - imports _registry
  - imports hooks
- **core\domain\skills\_categories.py**
  - imports __future__
- **core\domain\skills\_loader.py**
  - imports __future__
  - imports importlib
  - imports logging
  - imports pathlib
- **core\domain\skills\_registry.py**
  - imports __future__
  - imports dataclasses
  - imports typing
- **core\domain\skills\backup_tool.py**
  - imports __future__
  - imports core.domain.skills.builtin.backup_restore
- **core\domain\skills\builtin\__init__.py**
  - imports __future__
- **core\domain\skills\builtin\backup_restore.py**
  - imports __future__
  - imports _categories
  - imports _registry
  - imports core.storage.code_backup
- **core\domain\skills\builtin\file_operations.py**
  - imports __future__
  - imports _categories
  - imports _registry
  - imports pathlib
- **core\domain\skills\builtin\terminal.py**
  - imports __future__
  - imports _categories
  - imports _registry
  - imports core.sandbox.executor
- **core\domain\skills\custom\__init__.py**
  - imports __future__
- **core\domain\skills\examples\__init__.py**
  - imports __future__
- **core\domain\skills\examples\echo.py**
  - imports __future__
  - imports _registry
- **core\domain\skills\hooks.py**
  - imports __future__
  - imports _registry
- **core\frontends\cli\__init__.py**
  - imports app
  - imports context
  - imports settings
  - imports start
- **core\frontends\cli\app.py**
  - imports __future__
  - imports core.cli.python_cli.entrypoints.app
- **core\frontends\cli\context.py**
  - imports __future__
  - imports core.cli.python_cli.features.context.confirm
  - imports core.cli.python_cli.features.context.viewer
- **core\frontends\cli\settings.py**
  - imports __future__
  - imports core.cli.python_cli.features.settings.flow
- **core\frontends\cli\start.py**
  - imports __future__
  - imports core.cli.python_cli.features.start.pipeline_runner
- **core\frontends\dashboard\__init__.py**
  - imports __future__
  - imports core.dashboard.presentation.shell
- **core\frontends\tui\__init__.py**
  - imports monitor
- **core\frontends\tui\__main__.py**
  - imports __future__
  - imports core.frontends.tui.monitor
  - imports sys
- **core\frontends\tui\monitor.py**
  - imports __future__
  - imports core.cli.python_cli.workflow.tui.monitor
- **core\orchestration\__init__.py**
  - imports pipeline_artifacts
  - imports team_graph
- **core\orchestration\pipeline_artifacts.py**
  - imports __future__
  - imports agents.ambassador
  - imports agents.leader
  - imports agents.secretary
  - imports agents.tool_curator
  - imports agents.worker
  - imports core.config
  - imports core.domain.delta_brief
  - imports core.domain.routing_map
  - imports core.runtime
  - imports json
  - imports pathlib
  - imports typing
  - imports utils.file_manager
  - imports utils.logger
- **core\orchestration\team_graph.py**
  - imports __future__
  - imports core.bootstrap
  - imports langgraph.graph
  - imports team_nodes
  - imports team_routing
  - imports team_state
  - imports typing
- **core\orchestration\team_nodes.py**
  - imports __future__
  - imports collections
  - imports core.app_state.context_state
  - imports core.domain.delta_brief
  - imports core.runtime
  - imports core.storage.code_backup
  - imports logging
  - imports pathlib
  - imports pipeline_artifacts
  - imports re
  - imports team_state
  - imports utils.file_manager
  - imports utils.logger
- **core\orchestration\team_routing.py**
  - imports __future__
  - imports team_state
- **core\orchestration\team_state.py**
  - imports __future__
  - imports typing
- **core\paths.py**
  - imports __future__
  - imports core.bootstrap
- **core\runtime\__init__.py**
  - imports session
- **core\runtime\session.py**
  - imports __future__
  - imports core.cli.python_cli.workflow.runtime.session
- **core\runtime_config.py**
  - imports core.config.runtime_config
- **core\sandbox\__init__.py**
  - imports __future__
  - imports executor
  - imports policy
- **core\sandbox\_path_guard.py**
  - imports __future__
  - imports os
  - imports pathlib
- **core\sandbox\executor.py**
  - imports __future__
  - imports core.sandbox.venv_manager
  - imports dataclasses
  - imports os
  - imports pathlib
  - imports policy
  - imports shlex
  - imports subprocess
  - imports sys
  - imports typing
- **core\sandbox\policy.py**
  - imports __future__
  - imports re
- **core\sandbox\venv_manager.py**
  - imports __future__
  - imports os
  - imports pathlib
  - imports subprocess
  - imports sys
- **core\services\dashboard_data.py**
  - imports core.dashboard.application.data
- **core\storage\__init__.py**
  - imports __future__
  - imports importlib
  - imports typing
- **core\storage\_token_window.py**
  - imports __future__
  - imports os
  - imports tiktoken
  - imports typing
- **core\storage\ask_chat_store.py**
  - imports __future__
  - imports core.storage._token_window
  - imports core.storage.sqlite_utils
  - imports datetime
  - imports hashlib
  - imports json
  - imports logging
  - imports pathlib
  - imports sqlite3
  - imports threading
  - imports typing
- **core\storage\ask_history.py**
  - imports __future__
  - imports core.config.constants
  - imports core.storage.ask_chat_store
  - imports pathlib
  - imports shutil
  - imports typing
  - imports utils.file_manager
- **core\storage\code_backup.py**
  - imports __future__
  - imports core.bootstrap
  - imports core.sandbox._path_guard
  - imports os
  - imports pathlib
  - imports sqlite3
  - imports time
- **core\storage\conversation_archive.py**
  - imports __future__
  - imports core.storage.ask_chat_store
  - imports dataclasses
  - imports typing
- **core\storage\embedding_client.py**
  - imports __future__
  - imports array
  - imports core.storage.memory_cost_guard
  - imports core.storage.sqlite_utils
  - imports dataclasses
  - imports hashlib
  - imports logging
  - imports openai
  - imports os
  - imports pathlib
  - imports time
  - imports typing
- **core\storage\graphrag_store.py**
  - imports __future__
  - imports core.storage.embedding_client
  - imports core.storage.memory_cost_guard
  - imports core.storage.rerank_client
  - imports core.storage.sqlite_utils
  - imports datetime
  - imports hashlib
  - imports json
  - imports logging
  - imports math
  - imports os
  - imports pathlib
  - imports re
  - imports sqlite3
  - imports typing
- **core\storage\knowledge\__init__.py**
  - imports core.storage.knowledge.repository
  - imports core.storage.knowledge.sqlite_repository
  - imports core.storage.knowledge.vault_key
- **core\storage\knowledge\repository.py**
  - imports __future__
  - imports typing
- **core\storage\knowledge\sqlite_repository.py**
  - imports __future__
  - imports contextlib
  - imports core.config
  - imports core.config.constants
  - imports core.storage.knowledge.vault_key
  - imports core.storage.knowledge_text
  - imports cryptography.fernet
  - imports datetime
  - imports hashlib
  - imports logging
  - imports os
  - imports pathlib
  - imports re
  - imports sqlite3
  - imports typing
  - imports zlib
- **core\storage\knowledge\vault_key.py**
  - imports __future__
  - imports cryptography.fernet
  - imports logging
  - imports os
  - imports pathlib
  - imports typing
- **core\storage\knowledge_store.py**
  - imports __future__
  - imports core.config
  - imports core.config.constants
  - imports core.storage.knowledge.repository
  - imports core.storage.knowledge.sqlite_repository
  - imports core.storage.knowledge_text
  - imports pathlib
  - imports typing
- **core\storage\knowledge_text.py**
  - imports __future__
  - imports re
  - imports sqlite3
  - imports typing
- **core\storage\memory_coordinator.py**
  - imports __future__
  - imports agents.compact_worker
  - imports core.storage._token_window
  - imports core.storage.ask_chat_store
  - imports core.storage.graphrag_store
  - imports core.storage.memory_cost_guard
  - imports core.storage.memory_settler
  - imports datetime
  - imports json
  - imports logging
  - imports os
  - imports time
  - imports typing
- **core\storage\memory_cost_guard.py**
  - imports __future__
  - imports collections
  - imports core.storage._token_window
  - imports dataclasses
  - imports importlib.util
  - imports os
  - imports pathlib
  - imports threading
  - imports time
  - imports typing
  - imports urllib.parse
  - imports utils.tracker
- **core\storage\memory_settler.py**
  - imports __future__
  - imports atexit
  - imports collections
  - imports core.storage.memory_coordinator
  - imports os
  - imports threading
  - imports time
- **core\storage\prompt_store_protocol.py**
  - imports __future__
  - imports typing
- **core\storage\rerank_client.py**
  - imports __future__
  - imports core.storage.memory_cost_guard
  - imports core.storage.sqlite_utils
  - imports dataclasses
  - imports hashlib
  - imports json
  - imports logging
  - imports os
  - imports pathlib
  - imports time
  - imports typing
  - imports urllib.error
  - imports urllib.request
- **core\storage\sqlite_utils.py**
  - imports __future__
  - imports os
  - imports pathlib
  - imports sqlite3
- **scripts\run_aiteam.py**
  - imports core.cli.python_cli.entrypoints.app
- **scripts\update_memory.py**
  - imports ast
  - imports datetime
  - imports os
  - imports re
- **tests\cli\test_cli_prompt_ux.py**
  - imports __future__
  - imports core.cli.python_cli
  - imports unittest
- **tests\cli\test_ui_clear.py**
  - imports __future__
  - imports core.cli.python_cli.ui
  - imports unittest
- **tests\conftest.py**
  - imports __future__
  - imports core.bootstrap
  - imports pathlib
- **tests\test_activity_badges.py**
  - imports utils.activity_badges
- **tests\test_activity_log.py**
  - imports core.cli.python_cli.workflow.runtime.persist.activity_log
  - imports json
  - imports pathlib
  - imports pytest
  - imports time
  - imports unittest.mock
- **tests\test_agent_runtime.py**
  - imports __future__
  - imports aiteamruntime.demo
  - imports aiteamruntime.events
  - imports aiteamruntime.runtime
  - imports aiteamruntime.test.workflows
  - imports aiteamruntime.traces
  - imports aiteamruntime.web.server
  - imports collections
  - imports json
  - imports threading
  - imports time
  - imports urllib.request
- **tests\test_aiteamruntime_lifecycle.py**
  - imports __future__
  - imports aiteamruntime
  - imports aiteamruntime.lock_manager
  - imports aiteamruntime.test.workflows
  - imports aiteamruntime.traces
  - imports pathlib
  - imports pytest
  - imports threading
  - imports time
- **tests\test_ambassador_methods.py**
  - imports __future__
  - imports agents.ambassador
  - imports json
  - imports pytest
  - imports types
  - imports unittest.mock
- **tests\test_ambassador_tier_classification.py**
  - imports agents.ambassador
  - imports pytest
- **tests\test_api_client_stream.py**
  - imports __future__
  - imports agents.base_agent
  - imports agents.support._api_client
  - imports agents.support._budget_manager
  - imports pytest
  - imports sys
  - imports types
  - imports unittest.mock
  - imports utils.budget_guard
- **tests\test_api_client_unit.py**
  - imports __future__
  - imports agents.base_agent
  - imports agents.support._api_client
  - imports agents.support._budget_manager
  - imports core.config.constants
  - imports pytest
  - imports types
  - imports unittest.mock
- **tests\test_ask_chat_manager.py**
  - imports core.cli.python_cli.features.ask.chat_manager
  - imports pytest
  - imports re
  - imports sys
  - imports unittest.mock
- **tests\test_ask_chat_store.py**
  - imports core.storage.ask_chat_store
  - imports json
  - imports pathlib
  - imports pytest
  - imports time
- **tests\test_ask_history.py**
  - imports sys
  - imports unittest.mock
  - imports utils.ask_history
- **tests\test_base_agent_extra.py**
  - imports agents.base_agent
  - imports agents.support._budget_manager
  - imports pathlib
  - imports pytest
  - imports threading
  - imports unittest.mock
- **tests\test_budget_guard.py**
  - imports pytest
  - imports unittest.mock
  - imports utils.budget_guard
- **tests\test_budget_manager.py**
  - imports agents.base_agent
  - imports agents.support._budget_manager
  - imports pytest
- **tests\test_cli_security_helpers.py**
  - imports __future__
  - imports core.cli.python_cli.shell.monitor_payload
  - imports core.cli.python_cli.shell.safe_editor
  - imports pathlib
  - imports pytest
- **tests\test_cli_state.py**
  - imports core.cli.python_cli.shell.state
  - imports json
  - imports pathlib
  - imports pytest
  - imports sys
  - imports threading
  - imports unittest.mock
- **tests\test_cli_state_overrides.py**
  - imports core.cli.python_cli.shell.state
  - imports datetime
  - imports json
  - imports pathlib
  - imports pytest
  - imports sys
  - imports unittest.mock
- **tests\test_config_hardware.py**
  - imports __future__
  - imports core.config.hardware
  - imports subprocess
  - imports sys
  - imports unittest.mock
- **tests\test_config_pricing.py**
  - imports core.config.pricing
  - imports json
  - imports logging
  - imports pytest
  - imports unittest.mock
  - imports urllib.error
- **tests\test_config_registry.py**
  - imports core.config.registry
- **tests\test_config_service.py**
  - imports __future__
  - imports core.config.service
  - imports os
  - imports pytest
  - imports unittest.mock
- **tests\test_config_settings.py**
  - imports __future__
  - imports core.config.settings
  - imports os
  - imports pytest
  - imports unittest.mock
- **tests\test_dashboard_batches_browser.py**
  - imports __future__
  - imports core.dashboard.reporting.state
  - imports core.dashboard.shell
  - imports sys
- **tests\test_dashboard_helpers.py**
  - imports __future__
  - imports core.dashboard.reporting.state
  - imports core.dashboard.tui.utils
  - imports datetime
- **tests\test_dashboard_history_browser.py**
  - imports __future__
  - imports core.dashboard.reporting.state
  - imports core.dashboard.shell
  - imports datetime
  - imports sys
- **tests\test_dashboard_history_pure.py**
  - imports core.dashboard.shell.history
  - imports sys
  - imports unittest.mock
- **tests\test_dashboard_pdf.py**
  - imports __future__
  - imports core.dashboard.output.pdf_export
  - imports core.dashboard.reporting.state
  - imports pathlib
  - imports sys
- **tests\test_dashboard_pdf_font_fallback.py**
  - imports __future__
  - imports core.dashboard.output.pdf_export
  - imports core.dashboard.reporting.state
  - imports pathlib
- **tests\test_dashboard_range_picker.py**
  - imports __future__
  - imports core.dashboard.tui.render
  - imports datetime
- **tests\test_dashboard_range_state.py**
  - imports core.dashboard.reporting.state
  - imports datetime
  - imports pytest
- **tests\test_dashboard_render.py**
  - imports __future__
  - imports core.dashboard.tui.render
- **tests\test_dashboard_tui_utils.py**
  - imports core.dashboard.tui.utils
  - imports datetime
  - imports sys
  - imports unittest.mock
- **tests\test_dashboard_turn_views.py**
  - imports __future__
  - imports core.dashboard.reporting.state
  - imports core.dashboard.shell
  - imports datetime
- **tests\test_delta_brief.py**
  - imports pathlib
  - imports pydantic
  - imports pytest
  - imports utils.delta_brief
- **tests\test_domain_prompts.py**
  - imports core.domain.prompts
- **tests\test_embedding_client.py**
  - imports __future__
  - imports core.config.registry
  - imports core.storage.embedding_client
  - imports types
  - imports unittest.mock
- **tests\test_env_guard.py**
  - imports os
  - imports pathlib
  - imports pytest
  - imports stat
  - imports unittest.mock
  - imports utils.env_guard
- **tests\test_expert_agent.py**
  - imports __future__
  - imports agents.expert
  - imports json
  - imports pathlib
  - imports pytest
  - imports unittest.mock
- **tests\test_expert_coplan.py**
  - imports agents.expert
  - imports json
  - imports pathlib
  - imports pytest
  - imports tempfile
- **tests\test_export_txt_format.py**
  - imports __future__
  - imports core.dashboard.reporting.report_model
  - imports core.dashboard.reporting.report_txt_format
  - imports core.dashboard.reporting.state
  - imports datetime
- **tests\test_file_manager.py**
  - imports os
  - imports pathlib
  - imports pytest
  - imports time
  - imports unittest.mock
  - imports utils.file_manager
- **tests\test_frontend_runtime_facades.py**
  - imports __future__
  - imports core.cli.python_cli.workflow.runtime
  - imports core.frontends.cli
  - imports core.frontends.tui
  - imports core.runtime
- **tests\test_graphrag_hybrid.py**
  - imports __future__
  - imports core.storage.graphrag_store
  - imports core.storage.rerank_client
  - imports types
  - imports unittest.mock
- **tests\test_graphrag_store.py**
  - imports core.storage.graphrag_store
  - imports pathlib
  - imports pytest
  - imports sqlite3
  - imports unittest.mock
- **tests\test_graphrag_utils.py**
  - imports importlib
  - imports logging
  - imports pathlib
  - imports pytest
  - imports unittest.mock
  - imports utils.graphrag_utils
- **tests\test_import_smoke_python_cli.py**
  - imports __future__
  - imports core.cli.python_cli
  - imports importlib
  - imports pkgutil
  - imports pytest
- **tests\test_input_validator.py**
  - imports pytest
  - imports utils.input_validator
- **tests\test_json_utils.py**
  - imports json
  - imports pytest
  - imports utils.json_utils
- **tests\test_knowledge_manager.py**
  - imports __future__
  - imports agents.support._knowledge_manager
  - imports logging
  - imports pytest
  - imports threading
  - imports types
  - imports unittest.mock
- **tests\test_knowledge_repository.py**
  - imports __future__
  - imports core.storage.knowledge
  - imports pytest
  - imports sqlite3
- **tests\test_knowledge_store_module.py**
  - imports __future__
  - imports core.storage.knowledge_store
  - imports pathlib
  - imports pytest
  - imports sys
  - imports unittest.mock
- **tests\test_knowledge_text.py**
  - imports core.storage.knowledge_text
  - imports sqlite3
- **tests\test_leader_flow.py**
  - imports agents.ambassador
  - imports agents.leader
  - imports core.bootstrap
  - imports core.config
  - imports json
  - imports pathlib
  - imports rich.console
  - imports rich.markdown
  - imports rich.panel
  - imports sys
  - imports traceback
- **tests\test_leader_generate.py**
  - imports __future__
  - imports agents.leader
  - imports json
  - imports pathlib
  - imports pytest
  - imports unittest.mock
- **tests\test_leader_pure.py**
  - imports agents.leader
  - imports core.config.constants
  - imports json
  - imports pathlib
  - imports pytest
  - imports unittest.mock
- **tests\test_llm_usage.py**
  - imports agents.llm_usage
  - imports sys
  - imports unittest.mock
- **tests\test_logger_utils.py**
  - imports pathlib
  - imports sys
  - imports unittest.mock
  - imports utils.logger
- **tests\test_memory_cost_guard.py**
  - imports __future__
  - imports core.storage.embedding_client
  - imports core.storage.graphrag_store
  - imports core.storage.memory_cost_guard
  - imports core.storage.memory_settler
  - imports pytest
  - imports unittest.mock
- **tests\test_memory_tier1_window.py**
  - imports __future__
  - imports core.storage._token_window
  - imports core.storage.memory_coordinator
- **tests\test_memory_tier3_settler.py**
  - imports __future__
  - imports core.storage.ask_chat_store
  - imports core.storage.memory_coordinator
  - imports core.storage.memory_settler
- **tests\test_monitor_commands_regenerate.py**
  - imports __future__
  - imports core.cli.python_cli.workflow.tui.monitor.commands.mixin
  - imports core.cli.python_cli.workflow.tui.monitor.core._constants
  - imports sys
  - imports unittest.mock
- **tests\test_monitor_helpers_tier_display.py**
  - imports __future__
  - imports core.cli.python_cli.workflow.tui.monitor
  - imports unittest.mock
- **tests\test_monitor_payload.py**
  - imports core.cli.python_cli.shell.monitor_payload
  - imports pathlib
  - imports pytest
- **tests\test_monitor_role_cards.py**
  - imports __future__
  - imports core.cli.python_cli.workflow.tui.monitor.core._render_mixin
  - imports core.cli.python_cli.workflow.tui.monitor.helpers
  - imports time
- **tests\test_orchestration_split.py**
  - imports __future__
  - imports core.orchestration.team_graph
  - imports core.orchestration.team_routing
  - imports core.orchestration.team_state
- **tests\test_palette_package.py**
  - imports __future__
  - imports core.cli.python_cli.ui.palette
  - imports core.cli.python_cli.ui.palette.app
  - imports core.cli.python_cli.ui.palette.items
  - imports prompt_toolkit.document
- **tests\test_pure_cli_modules.py**
  - imports core.cli.python_cli.shell.command_registry
  - imports core.cli.python_cli.shell.nav
  - imports core.cli.python_cli.workflow.runtime.present.pipeline_markdown
  - imports core.cli.python_cli.workflow.tui.shared.display_policy
  - imports core.domain.routing_map
  - imports pytest
  - imports sys
- **tests\test_refactor_facades.py**
  - imports __future__
  - imports agents.team_map._team_map
  - imports core.app_state
  - imports core.cli.python_cli.shell.state
  - imports core.dashboard.application.data
  - imports core.dashboard.shell.data
  - imports core.domain.pipeline_state
  - imports core.orchestration.pipeline_artifacts
  - imports core.orchestration.team_graph
  - imports core.services.dashboard_data
  - imports sys
- **tests\test_report_txt_format.py**
  - imports core.dashboard.reporting.report_model
  - imports core.dashboard.reporting.report_txt_format
  - imports datetime
- **tests\test_rerank_client.py**
  - imports __future__
  - imports core.config
  - imports core.storage.rerank_client
  - imports json
  - imports unittest.mock
- **tests\test_runner_inline_progress.py**
  - imports __future__
  - imports core.cli.python_cli.workflow.runtime.graph
  - imports types
- **tests\test_runner_rewind_logic.py**
  - imports __future__
  - imports core.cli.python_cli.workflow.runtime.graph.runner_rewind
  - imports pathlib
  - imports sys
  - imports time
  - imports types
  - imports unittest.mock
- **tests\test_runner_rewind_pure.py**
  - imports core.cli.python_cli.workflow.runtime.graph.runner_rewind
  - imports datetime
  - imports pathlib
  - imports pytest
  - imports sys
  - imports time
  - imports unittest.mock
  - imports uuid
- **tests\test_runtime_config.py**
  - imports core.config.runtime_config
- **tests\test_sandbox_security.py**
  - imports __future__
  - imports agents.worker
  - imports core.sandbox._path_guard
  - imports core.sandbox.policy
  - imports core.storage.code_backup
  - imports pathlib
  - imports pytest
  - imports tempfile
  - imports unittest.mock
- **tests\test_secretary_proc.py**
  - imports __future__
  - imports aiteamruntime.secretary_proc
  - imports pathlib
  - imports pytest
  - imports sys
  - imports time
- **tests\test_security_and_config.py**
  - imports __future__
  - imports agents.base_agent
  - imports core.cli.python_cli.shell.state
  - imports core.config
  - imports core.config.settings
  - imports core.storage.knowledge.sqlite_repository
  - imports core.storage.knowledge_store
  - imports json
  - imports pathlib
  - imports unittest.mock
  - imports utils.env_guard
  - imports utils.input_validator
  - imports utils.tracker.tracker_openrouter
- **tests\test_session_monitor_manager.py**
  - imports core.cli.python_cli.workflow.runtime.session.session_monitor_manager
  - imports unittest.mock
- **tests\test_session_notification.py**
  - imports core.cli.python_cli.workflow.runtime.session.session_notification
  - imports pytest
  - imports time
  - imports unittest.mock
- **tests\test_session_notification_extra.py**
  - imports core.cli.python_cli.workflow.runtime.session.session_notification
  - imports pathlib
  - imports time
  - imports unittest.mock
- **tests\test_session_pause_manager.py**
  - imports core.cli.python_cli.workflow.runtime.session.session_pause_manager
  - imports unittest.mock
- **tests\test_session_pipeline_state.py**
  - imports core.cli.python_cli.workflow.runtime.session.session_pipeline_state
  - imports pytest
  - imports unittest.mock
- **tests\test_session_pipeline_state_extra.py**
  - imports core.cli.python_cli.workflow.runtime.session.session_pipeline_state
  - imports time
  - imports unittest.mock
- **tests\test_session_pipeline_state_uncovered.py**
  - imports __future__
  - imports core.cli.python_cli.workflow.runtime.session.session_pipeline_state
  - imports types
  - imports unittest.mock
- **tests\test_session_store.py**
  - imports core.cli.python_cli.workflow.runtime.session.session_store
  - imports json
  - imports pathlib
  - imports threading
  - imports unittest.mock
- **tests\test_skills_registry.py**
  - imports core.domain.skills
  - imports pytest
- **tests\test_sqlite_repository_extra.py**
  - imports __future__
  - imports core.storage.knowledge.sqlite_repository
  - imports logging
  - imports os
  - imports pathlib
  - imports pytest
  - imports sqlite3
  - imports sys
  - imports unittest.mock
- **tests\test_team_map_routing.py**
  - imports agents.team_map._team_map
  - imports pytest
  - imports sys
  - imports unittest.mock
- **tests\test_tracker_aggregate.py**
  - imports pytest
  - imports unittest.mock
  - imports utils.tracker.tracker_aggregate
- **tests\test_tracker_aggregate_extra.py**
  - imports datetime
  - imports unittest.mock
  - imports utils.tracker.tracker_aggregate
  - imports utils.tracker.tracker_cache
- **tests\test_tracker_batches.py**
  - imports datetime
  - imports json
  - imports pathlib
  - imports unittest.mock
  - imports utils.tracker.tracker_batches
- **tests\test_tracker_batches_summarize.py**
  - imports __future__
  - imports datetime
  - imports unittest.mock
  - imports utils.tracker.tracker_batches
- **tests\test_tracker_budget.py**
  - imports pytest
  - imports utils.tracker.tracker_budget
- **tests\test_tracker_cache.py**
  - imports time
  - imports unittest.mock
  - imports utils.tracker.tracker_cache
- **tests\test_tracker_dashboard_summary.py**
  - imports __future__
  - imports utils
- **tests\test_tracker_helpers.py**
  - imports datetime
  - imports os
  - imports pathlib
  - imports pytest
  - imports tempfile
  - imports utils.tracker.tracker_helpers
- **tests\test_tracker_usage.py**
  - imports io
  - imports json
  - imports pytest
  - imports unittest.mock
  - imports utils.tracker.tracker_usage
- **tests\test_vault_key.py**
  - imports core.storage.knowledge.vault_key
  - imports os
  - imports pathlib
  - imports pytest
  - imports unittest.mock
- **tests\test_workflow_activity_format.py**
  - imports __future__
  - imports core.cli.python_cli.workflow.runtime.persist.activity_log
- **tests\test_workflow_toast_queue.py**
  - imports __future__
  - imports core.cli.python_cli.workflow.runtime
  - imports core.cli.python_cli.workflow.runtime.session
  - imports pytest
- **utils\activity_badges.py**
  - imports __future__
- **utils\ask_history.py**
  - imports core.storage.ask_history
- **utils\budget_guard.py**
  - imports __future__
  - imports core.app_state.settings
  - imports dataclasses
  - imports utils
- **utils\delta_brief.py**
  - imports core.domain.delta_brief
- **utils\env_guard.py**
  - imports __future__
  - imports core.config.constants
  - imports logging
  - imports os
  - imports pathlib
  - imports re
  - imports stat
  - imports utils.file_manager
- **utils\file_manager.py**
  - imports __future__
  - imports core.config
  - imports core.domain.delta_brief
  - imports dataclasses
  - imports os
  - imports pathlib
  - imports tempfile
- **utils\free_model_finder.py**
  - imports __future__
  - imports core.app_state
  - imports core.cli.python_cli.i18n
  - imports core.cli.python_cli.ui.ui
  - imports core.config
  - imports json
  - imports logging
  - imports rich.box
  - imports rich.panel
  - imports rich.prompt
  - imports rich.style
  - imports rich.table
  - imports typing
  - imports urllib.request
- **utils\graphrag_utils.py**
  - imports __future__
  - imports core.storage.graphrag_store
  - imports logging
  - imports pathlib
  - imports typing
- **utils\input_validator.py**
  - imports __future__
- **utils\json_utils.py**
  - imports __future__
  - imports json
  - imports re
- **utils\logger.py**
  - imports __future__
  - imports core.app_state
  - imports core.cli.python_cli.workflow.runtime.persist.activity_log
  - imports pathlib
  - imports typing
- **utils\tracker\__init__.py**
  - imports __future__
  - imports tracker_aggregate
  - imports tracker_batches
  - imports tracker_budget
  - imports tracker_cache
  - imports tracker_helpers
  - imports tracker_openrouter
  - imports tracker_usage
  - imports typing
- **utils\tracker\tracker_aggregate.py**
  - imports __future__
  - imports collections
  - imports datetime
  - imports tracker_cache
  - imports tracker_helpers
  - imports tracker_usage
  - imports typing
- **utils\tracker\tracker_batches.py**
  - imports __future__
  - imports datetime
  - imports json
  - imports logging
  - imports tracker_cache
  - imports tracker_helpers
  - imports tracker_usage
  - imports typing
- **utils\tracker\tracker_budget.py**
  - imports __future__
  - imports dataclasses
  - imports typing
- **utils\tracker\tracker_cache.py**
  - imports __future__
  - imports logging
  - imports time
  - imports typing
- **utils\tracker\tracker_helpers.py**
  - imports __future__
  - imports core.config.constants
  - imports datetime
  - imports logging
  - imports os
  - imports pathlib
  - imports typing
- **utils\tracker\tracker_openrouter.py**
  - imports __future__
  - imports logging
  - imports os
  - imports requests
  - imports typing
- **utils\tracker\tracker_usage.py**
  - imports __future__
  - imports core.config
  - imports datetime
  - imports json
  - imports logging
  - imports tracker_cache
  - imports tracker_helpers
  - imports typing

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
  - **Using**: Per-command branches with individual status dots (o/X) and collapsible output.
  - **Update**: Independent system state showing colored diffs (+green/-red) immediately after each file write.

### 2. Architecture Clarification
- **core/app_state**: The project's runtime configuration hub. Manages model overrides, context state, and CLI settings.
- **core/cli/app**: Unrelated boilerplate remnants (Django models/views). Not part of the `ai-team` logic.
- **Explainer @codebase**: Token-optimized scanning using tools (`tree`, `grep`, `wc`) instead of LLM-per-file reading.

### 3. Tool Curator Integration (Completed)
- Fully integrated into LangGraph pipeline: Human Gate -> Tool Curator -> Worker -> Secretary -> Finalize.
- Purpose: Reads context.md, analyzes venv via sys.executable, generates tools.md.

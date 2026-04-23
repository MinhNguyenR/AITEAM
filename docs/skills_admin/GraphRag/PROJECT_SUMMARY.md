# Project Architecture Summary

- Root: `D:\Profolio\Programming Language\Python\AI\ML\DL\Research\AI Agentic\ai-team`
- Database: `D:\Profolio\Programming Language\Python\AI\ML\DL\Research\AI Agentic\ai-team\.graphrag\graphrag.sqlite`
- Files: 101
- Chunks: 295
- Edges: 1118
- Symbols: 614

## Repository Tree
- ai-team
- ├── .graphrag/
- │   └── graphrag.sqlite
- ├── agents/
- │   ├── teamMap/
- │   │   ├── __init__.py
- │   │   └── _team_map.py
- │   ├── __init__.py
- │   ├── ambassador.py
- │   ├── base_agent.py
- │   ├── browser.py
- │   ├── commander.py
- │   ├── expert.py
- │   ├── final_reviewer.py
- │   ├── fix_worker.py
- │   ├── leader.py
- │   ├── researcher.py
- │   ├── reviewer.py
- │   ├── secretary.py
- │   ├── test_agent.py
- │   ├── tool_curator.py
- │   └── worker.py
- ├── aiteam.egg-info/
- │   ├── dependency_links.txt
- │   ├── entry_points.txt
- │   ├── PKG-INFO
- │   ├── requires.txt
- │   ├── SOURCES.txt
- │   └── top_level.txt
- ├── core/
- │   ├── cli/
- │   │   ├── workflow/
- │   │   │   ├── __init__.py
- │   │   │   ├── activity_log.py
- │   │   │   ├── checkpointer.py
- │   │   │   ├── display_policy.py
- │   │   │   ├── list_view.py
- │   │   │   ├── monitor.py
- │   │   │   ├── runner.py
- │   │   │   └── session.py
- │   │   ├── __init__.py
- │   │   ├── app.py
- │   │   ├── ask_flow.py
- │   │   ├── change_flow.py
- │   │   ├── choice_lists.py
- │   │   ├── cli_prompt.py
- │   │   ├── command_registry.py
- │   │   ├── context_flow.py
- │   │   ├── dashboard_flow.py
- │   │   ├── help_terminal.py
- │   │   ├── helpbox.py
- │   │   ├── palette.py
- │   │   ├── settings_flow.py
- │   │   ├── start_flow.py
- │   │   ├── state.py
- │   │   └── ui.py
- │   ├── config/
- │   │   ├── __init__.py
- │   │   ├── constants.py
- │   │   ├── hardware.py
- │   │   ├── pricing.py
- │   │   ├── registry.py
- │   │   ├── service.py
- │   │   └── settings.py
- │   ├── dashboard/
- │   │   ├── __init__.py
- │   │   ├── app.py
- │   │   ├── render.py
- │   │   ├── state.py
- │   │   └── utils.py
- │   ├── storage/
- │   │   ├── __init__.py
- │   │   ├── ask_chat_store.py
- │   │   ├── graphrag_store.py
- │   │   └── knowledge_store.py
- │   ├── __init__.py
- │   ├── orchestrator.py
- │   ├── pipeline_state.py
- │   ├── prompts.py
- │   ├── routing_map.py
- │   └── skills/
- ├── graphrag_standalone/
- │   ├── __init__.py
- │   ├── __main__.py
- │   ├── cli.py
- │   ├── indexer.py
- │   ├── PROJECT_MAP.md
- │   └── README.md
- ├── tests/
- │   ├── conftest.py
- │   ├── test_dashboard_batches_browser.py
- │   ├── test_dashboard_helpers.py
- │   ├── test_dashboard_history_browser.py
- │   ├── test_dashboard_pdf.py
- │   ├── test_dashboard_pdf_font_fallback.py
- │   ├── test_dashboard_range_picker.py
- │   ├── test_dashboard_render.py
- │   ├── test_dashboard_turn_views.py
- │   ├── test_security_and_config.py
- │   └── test_tracker_dashboard_summary.py
- ├── utils/
- │   ├── __init__.py
- │   ├── activity_badges.py
- │   ├── ask_history.py
- │   ├── budget_guard.py
- │   ├── delta_brief.py
- │   ├── env_guard.py
- │   ├── file_manager.py
- │   ├── free_model_finder.py
- │   ├── logger.py
- │   └── tracker.py
- ├── __init__.py
- ├── cli.py
- ├── LICENSE
- ├── docs/notes/memory.md
- ├── PROJECT_MAP.md
- ├── pyproject.toml
- ├── README.md
- ├── test_leader_flow.py
- └── times.ttf

## Top Directories
- `.` — 101 files

## Files by Extension
- `.py` — 91
- `.txt` — 5
- `.md` — 4
- `.toml` — 1

## Largest Files
- `core\cli\workflow\monitor.py` — 30456 bytes
- `graphrag_standalone\indexer.py` — 27487 bytes
- `agents\base_agent.py` — 26649 bytes
- `utils\tracker.py` — 21680 bytes
- `core\cli\workflow\runner.py` — 20944 bytes
- `core\cli\workflow\session.py` — 17500 bytes
- `core\cli\ask_flow.py` — 17099 bytes
- `core\prompts.py` — 16114 bytes
- `core\storage\knowledge_store.py` — 16024 bytes
- `core\cli\context_flow.py` — 15019 bytes
- `core\cli\app.py` — 15015 bytes
- `agents\ambassador.py` — 14161 bytes
- `core\cli\change_flow.py` — 13936 bytes
- `README.md` — 12225 bytes
- `core\dashboard\app.py` — 12067 bytes
- `agents\expert.py` — 12059 bytes
- `core\dashboard\render.py` — 10588 bytes
- `core\storage\ask_chat_store.py` — 10159 bytes
- `core\cli\start_flow.py` — 9589 bytes
- `PROJECT_MAP.md` — 9455 bytes

## Important Modules
- `core.dashboard.utils` → `core\dashboard\utils.py`
- `agents.__init__` → `agents\__init__.py`
- `agents.ambassador` → `agents\ambassador.py`
- `agents.base_agent` → `agents\base_agent.py`
- `agents.browser` → `agents\browser.py`
- `agents.commander` → `agents\commander.py`
- `agents.expert` → `agents\expert.py`
- `agents.final_reviewer` → `agents\final_reviewer.py`
- `agents.fix_worker` → `agents\fix_worker.py`
- `agents.leader` → `agents\leader.py`
- `agents.researcher` → `agents\researcher.py`
- `agents.reviewer` → `agents\reviewer.py`
- `agents.secretary` → `agents\secretary.py`
- `agents.teammap.__init__` → `agents\teamMap\__init__.py`
- `agents.teammap._team_map` → `agents\teamMap\_team_map.py`
- `agents.test_agent` → `agents\test_agent.py`
- `agents.tool_curator` → `agents\tool_curator.py`
- `agents.worker` → `agents\worker.py`
- `core.__init__` → `core\__init__.py`
- `core.cli.__init__` → `core\cli\__init__.py`

## Project Map
### core
Application orchestration, CLI, configuration, dashboard, and storage
- `core.__init__`
- `core.cli.__init__`
- `core.cli.app`
- `core.cli.ask_flow`
- `core.cli.change_flow`
- `core.cli.choice_lists`
- `core.cli.cli_prompt`
- `core.cli.command_registry`
- `core.cli.context_flow`
- `core.cli.dashboard_flow`
- `core.cli.help_terminal`
- `core.cli.helpbox`
- `core.cli.palette`
- `core.cli.settings_flow`
- `core.cli.start_flow`
- `core.cli.state`
- `core.cli.ui`
- `core.cli.workflow.__init__`
- `core.cli.workflow.activity_log`
- `core.cli.workflow.checkpointer`

### agents
Agent roles, routing, team map, and execution helpers
- `agents.__init__`
- `agents.ambassador`
- `agents.base_agent`
- `agents.browser`
- `agents.commander`
- `agents.expert`
- `agents.final_reviewer`
- `agents.fix_worker`
- `agents.leader`
- `agents.researcher`
- `agents.reviewer`
- `agents.secretary`
- `agents.teammap.__init__`
- `agents.teammap._team_map`
- `agents.test_agent`
- `agents.tool_curator`
- `agents.worker`

### utils
Shared helpers for tracking, logging, environment, and files
- `core.dashboard.utils`
- `utils.__init__`
- `utils.activity_badges`
- `utils.ask_history`
- `utils.budget_guard`
- `utils.delta_brief`
- `utils.env_guard`
- `utils.file_manager`
- `utils.free_model_finder`
- `utils.logger`
- `utils.tracker`

### tests
Automated validation and regression coverage
- `tests.conftest`
- `tests.test_dashboard_batches_browser`
- `tests.test_dashboard_helpers`
- `tests.test_dashboard_history_browser`
- `tests.test_dashboard_pdf`
- `tests.test_dashboard_pdf_font_fallback`
- `tests.test_dashboard_range_picker`
- `tests.test_dashboard_render`
- `tests.test_dashboard_turn_views`
- `tests.test_security_and_config`
- `tests.test_tracker_dashboard_summary`

### graphrag_standalone
Self-contained repository graph index used internally for retrieval
- `graphrag_standalone.readme`
- `graphrag_standalone.__init__`
- `graphrag_standalone.__main__`
- `graphrag_standalone.cli`
- `graphrag_standalone.indexer`

## Symbol Hotspots
- `Ambassador` (class) in `agents\ambassador.py`:27
- `_classify_tier_fallback` (function) in `agents\ambassador.py`:75
- `BudgetExceeded` (class) in `agents\base_agent.py`:41
- `BaseAgent` (class) in `agents\base_agent.py`:46
- `Expert` (class) in `agents\expert.py`:37
- `BaseLeader` (class) in `agents\leader.py`:51
- `LeaderLow` (class) in `agents\leader.py`:222
- `LeaderMed` (class) in `agents\leader.py`:243
- `LeaderHigh` (class) in `agents\leader.py`:261
- `TeamState` (class) in `agents\teamMap\_team_map.py`:29
- `WorkflowDisplayPolicy` (class) in `core\cli\workflow\display_policy.py`:7
- `_project_root_default` (function) in `core\cli\workflow\monitor.py`:30
- `CheckpointSearchScreen` (class) in `core\cli\workflow\monitor.py`:303
- `ActivityLogScreen` (class) in `core\cli\workflow\monitor.py`:327
- `ContextFilePreviewScreen` (class) in `core\cli\workflow\monitor.py`:346
- `RegeneratePromptScreen` (class) in `core\cli\workflow\monitor.py`:381
- `ContextReviewScreen` (class) in `core\cli\workflow\monitor.py`:411
- `WorkflowMonitorApp` (class) in `core\cli\workflow\monitor.py`:492
- `MEMORYSTATUSEX` (class) in `core\config\hardware.py`:65
- `ConfigError` (class) in `core\config\service.py`:23

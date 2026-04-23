# Workflow Overhaul — Design Prompt

Use this prompt when you want to continue evolving the workflow monitor layer.
Hand it to a coding agent verbatim; it contains all the context needed.

---

## Context

The AI Team framework (`ai-team`) has two live workflow monitors:

| View | File | Technology |
|------|------|-----------|
| **Chain** | `core/cli/workflow/tui/monitor_app.py` | Textual TUI, 0.25 s tick |
| **List**  | `core/cli/workflow/tui/list_view.py`   | Rich CLI, accumulating log |

Both share a data layer:
- **Session state** — `core/cli/workflow/runtime/session.py` (facade over `session_pipeline_state.py` etc.)
- **Agent cards** — `core/cli/workflow/tui/agent_cards.py` — `AgentCard` dataclass + renderers; single source of truth for per-node status, model name, streaming preview
- **Pipeline chain markup** — `core/cli/workflow/runtime/pipeline_markdown.py` — `build_pipeline_markup()`
- **Monitor helpers** — `core/cli/workflow/tui/monitor_helpers.py` — `_steps_for_tier`, `_compute_visual_states`, `_build_pipeline_markup` wrapper

Pipeline nodes (in order, tier-dependent):
```
ambassador → leader_generate → [expert_coplan] → human_context_gate → finalize_phase1
           ↘ expert_solo ↗             ↓
                                   end_failed
```

Each node calls `ws.update_workflow_node_status(node, status, detail)` and
`ws.append_leader_stream_chunk(text)` for live streaming.

---

## Current Design (as of Phase 3 overhaul)

### Chain view (`monitor_app.py`)
```
Header (clock)
hint bar          — toast + step/tier
pipeline bar      — full-width horizontal chain with active_detail line
────────────────────────────────────────────
left 50%: activity log (RichLog, accumulating)
right 50%: agent cards (Static, per-node status + stream preview)
           status bar (slim)
────────────────────────────────────────────
cmd input (dock bottom)
Footer
```

Commands: `log`, `search`, `model <id>`, `agents`, `btw`, `stream`, `tier`,
`check`, `dismiss <id>`, `view <id>`, `exit`

### List view (`list_view.py`)
- Never clears terminal; log accumulates naturally.
- Prints workflow table at start + every 200 lines (`_LineTracker`).
- Commands same as chain plus `status`/`snap`.

### Agent cards (`agent_cards.py`)
- `AgentCard(node_id, display_name, model_name, status, detail, stream_tail)`
- `get_agent_cards(snap, steps)` — builds from session snapshot
- `render_cards_markup(cards, spin_idx)` — returns Rich markup string
- `model_for_node(node_id, tier, selected_leader)` — looks up model from config registry
- Scalable: add new roles by updating `monitor_helpers._steps_for_tier` +
  `_display_name` + `_registry_key_for_step`.

---

## Planned Next Improvements

### 1 — Multi-model parallel cards (Phase 4)
When multiple nodes can run concurrently (future multi-expert tier), the agent
cards panel should show each agent in its own bordered sub-panel rather than a
flat list. Consider using Textual's `Grid` or `DataTable` widget.

Design hint: `AgentCard` already has all fields needed. The renderer
`render_cards_markup` should accept a `layout: "flat" | "grid"` parameter.

### 2 — Model search in chain view
The `model <id>` command currently pushes `CheckpointSearchScreen` (same as
`search`). Improve it to:
- Filter activity log to entries from nodes whose model name matches `<id>`.
- Show matching `AgentCard` inline as a Textual notification.
- Use `agent_cards.get_agent_cards` + filter on `c.model_name`.

### 3 — Persistent stream panel
Add an optional third column (collapsible, `#stream_col`) in the chain view
that shows the live `leader_stream_buffer` in a scrolling `RichLog`. Toggle
with `stream` command.

### 4 — Notification inbox screen
Replace the `notify()` toast in `agents` command with a proper
`NotificationInboxScreen` (Textual modal) listing all agent cards in a
`DataTable` with sortable columns (name, model, status, last-updated).

### 5 — btw pinning (terminal approach)
For list view: instead of `_LineTracker`, use `rich.live.Live` as context
manager with a `rich.layout.Layout`:
```
Layout.split_column(
    Layout(name="header", size=<table_height>),
    Layout(name="log"),
)
```
The header updates every tick; the log body accumulates below.
Challenge: `Prompt.ask` must be called inside the `Live` context and flushed
before re-rendering. Use `console.input()` instead of `Prompt.ask`.

### 6 — Role-scoped logs
Add `ws.append_role_event(role, action, detail)` that tags events by role
(ambassador / leader / expert / gate / finalize). `model <id>` then filters by
role name too.

### 7 — Export snapshot
`btw --save` command writes a JSON snapshot of current agent card states +
last 50 log lines to `~/.ai-team/snapshots/<ts>.json` for post-mortem review.

---

## Adding a New Node / Role

1. Add the node function in `agents/team_map/_team_map.py` (follow existing
   pattern: `ws.set_pipeline_active_step`, `ws.update_workflow_node_status`,
   `workflow_event`).
2. Add the node to `_build_graph()` with correct edges.
3. Add it to the relevant pipeline list in `monitor_helpers.py`:
   - `PIPELINE_EXPERT`, `PIPELINE_LEADER`, or `PIPELINE_HARD`
   - `_steps_for_tier()` switch
   - `_display_name()` mapping
   - `_registry_key_for_step()` mapping (if it calls the LLM)
4. Add a config entry in `core/config/workers.yaml` (or equivalent) so
   `model_for_node()` resolves its model name.
5. No changes needed in `agent_cards.py` or either view — they read steps
   dynamically from `_steps_for_tier`.

---

## Key Invariants to Preserve

- `run_workflow_list_view(project_root: str) -> None` signature unchanged.
- `WorkflowMonitorApp(view_mode=None)` class name + constructor unchanged.
- `_steps_for_tier` drives all node lists — never hardcode node arrays in views.
- Session state is the single source of truth; views are read-only consumers.
- Gate handling: when `paused_at_gate`, always call `confirm_context` and
  forward decision via `ws.enqueue_monitor_command`.
- Global commands `log`, `exit`, `back` must always work in both views.
- All test files in `tests/` must still pass after any change.

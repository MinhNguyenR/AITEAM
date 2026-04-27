# Central registry for CLI command keys and copy.
# Global commands:
#   shutdown — exit the application (sys.exit)
#   exit     — return to main menu
#   back     — go up one level (no-op at root)

from __future__ import annotations

# ── Main menu ─────────────────────────────────────────────────────────────────
MAIN_MENU_BY_NUMBER: dict[str, str] = {
    "0": "shutdown",
    "1": "start",
    "2": "check",
    "3": "status",
    "4": "info",
    "5": "dashboard",
    "6": "settings",
    "7": "help",
    "8": "workflow",
}

MAIN_MENU_ALIASES: tuple[str, ...] = tuple(MAIN_MENU_BY_NUMBER.values()) + ("exit",)
MAIN_MENU_VALID_CHOICES: tuple[str, ...] = (
    tuple(MAIN_MENU_BY_NUMBER.keys()) + MAIN_MENU_ALIASES + ("back",)
)

MAIN_PROMPT_LABEL = ">"

# start → mode select
START_MODE_BY_NUMBER: dict[str, str] = {
    "1": "ask",
    "2": "agent",
    "3": "back",
    "4": "exit",
}

# ── Palette rows: (key_display, cmd_name, description) ───────────────────────
MENU_PALETTE_ROWS: tuple[tuple[str, str, str], ...] = (
    ("[1]", "start",     "Select mode (ask / agent) then enter a task"),
    ("[2]", "check",     "Review and confirm context.md"),
    ("[3]", "status",    "System info: GPU, RAM, API connection"),
    ("[4]", "info",      "Agent registry — models, roles, overrides"),
    ("[5]", "dashboard", "Usage, budget, spending history"),
    ("[6]", "settings",  "View mode, auto-accept, context action"),
    ("[7]", "help",      "Reference guide"),
    ("[8]", "workflow",  "Open workflow monitor (Textual TUI)"),
    ("[0]", "shutdown",  "Exit"),
)


def menu_commands() -> list[tuple[str, str, str]]:
    return list(MENU_PALETTE_ROWS)


# ── Help markdown ─────────────────────────────────────────────────────────────
HELP_SCREEN_MARKDOWN = """
# AI-team — CLI Reference

## Global commands

| Command    | Effect |
|------------|--------|
| `exit`     | Return to main menu (or quit if at root) |
| `back`     | Go up one level |
| `shutdown` | Exit the application (`sys.exit`) — also **0** from main menu |

---

## Main menu

| Key / name     | Action |
|----------------|--------|
| **1** `start`  | Choose **ask** or **agent** mode, then enter a task |
| **2** `check`  | View / accept / delete `context.md` |
| **3** `status` | Hardware, API key, paths |
| **4** `info`   | Agent registry — inspect / override models and prompts |
| **5** `dashboard` | Wallet balance, token usage, budget, batch history |
| **6** `settings`  | Toggle auto-accept, workflow view, context action |
| **7** `help`   | This screen |
| **8** `workflow` | Textual TUI workflow monitor |
| **0** `shutdown` | Exit |

---

## start

- **ask** — conversational mode; code-related queries show a disclaimer.
- **agent** — runs the full Ambassador → pipeline. Question-like prompts auto-route to ask.
- **back** — cancel and return to menu.

---

## check (context.md viewer)

| Command      | Effect |
|--------------|--------|
| `back`       | Close viewer (keeps pause gate if active) |
| `edit`       | Open file in `$EDITOR` |
| `delete`     | Delete context + clean state |
| `run`        | Accept context and resume pipeline |
| `regenerate` | Delete context and prompt for a new task |
| `exit`       | Return to main menu |

---

## workflow monitor commands

| Command         | Effect |
|-----------------|--------|
| `log`           | Open activity log |
| `btw [msg]`     | Print snapshot; if msg provided → CompactWorker synthesis |
| `task <text>`   | Queue a new task (only when pipeline is idle) |
| `model <id>`    | Search checkpoints by model or node |
| `check`         | Open context review screen |
| `delete`        | Delete context and exit monitor |
| `dismiss <id>`  | Dismiss a notification |
| `exit / q`      | Quit monitor |

---

## dashboard

- **history** — usage by day/range
- **total**   — aggregate by model / role
- **budget**  — set daily / monthly / yearly limits
- `back` / `0` — return · `exit` — main menu

---

## settings

| # | Setting | Values |
|---|---------|--------|
| 1 | Auto-accept context.md | on / off |
| 2 | Workflow view | chain / list |
| 3 | Context action (post-delete) | ask · accept · decline |
| 4 | Help: external terminal | on / off |

---

## ask (chat mode)

- `ask thinking` / `ask standard` — switch model tier mid-chat
- `back` — exit chat
- `exit` — return to main menu
""".strip()


__all__ = [
    "MAIN_MENU_BY_NUMBER",
    "MAIN_MENU_ALIASES",
    "MAIN_MENU_VALID_CHOICES",
    "MAIN_PROMPT_LABEL",
    "START_MODE_BY_NUMBER",
    "menu_commands",
    "HELP_SCREEN_MARKDOWN",
]

# Central registry for CLI command keys and copy.
# Global commands:
#   shutdown — exit the application (sys.exit)
#   exit     — return to main menu
#   back     — go up one level (no-op at root)

from __future__ import annotations
from core.cli.python_cli.i18n import t

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


def menu_palette_rows() -> tuple[tuple[str, str, str], ...]:
    """Returns localized palette rows for the main menu."""
    return (
        ("", "/start",     t("cmd.start")),
        ("", "/check",     t("cmd.check")),
        ("", "/status",    t("cmd.status")),
        ("", "/info",      t("cmd.info")),
        ("", "/dashboard", t("cmd.dashboard")),
        ("", "/settings",  t("cmd.settings")),
        ("", "/help",      t("cmd.help")),
        ("", "/workflow",  t("cmd.workflow")),
        ("", "/shutdown",  t("cmd.shutdown")),
    )


def menu_commands() -> list[tuple[str, str, str]]:
    return list(menu_palette_rows())


def help_screen_markdown() -> str:
    """Returns localized help screen markdown."""
    return f"""
# {t('help.header')}

## {t('help.global')}

| {t('ui.col_cmd')}    | {t('ui.col_effect')} |
|------------|--------|
| `exit`     | {t('nav.exit')} |
| `back`     | {t('nav.back')} |
| `shutdown` | {t('menu.shutdown.desc')} |

---

## {t('status.header')}

| {t('ui.col_key')} / {t('ui.col_cmd').lower()}     | {t('ui.col_effect')} |
|----------------|--------|
| **1** `start`  | {t('menu.start.desc')} |
| **2** `check`  | {t('menu.check.desc')} |
| **3** `status` | {t('menu.status.desc')} |
| **4** `info`   | {t('menu.info.desc')} |
| **5** `dashboard` | {t('menu.dashboard.desc')} |
| **6** `settings`  | {t('menu.settings.desc')} |
| **7** `help`   | {t('menu.help.desc')} |
| **8** `workflow` | {t('menu.workflow.desc')} |
| **0** `shutdown` | {t('menu.shutdown.desc')} |

---

## {t('nav.start').lower()}

- **ask** — {t('help.ask_desc')}
- **agent** — {t('help.agent_desc')}
- **back** — {t('nav.back')}

---

## {t('context.viewer_header')}

| {t('ui.col_cmd')}      | {t('ui.col_effect')} |
|--------------|--------|
| `back`       | {t('context.back_desc')} |
| `edit`       | {t('context.edit_hint')} |
| `delete`     | {t('context.delete_desc')} |
| `run`        | {t('context.accept_desc')} |
| `regenerate` | {t('context.regen_desc')} |
| `exit`       | {t('nav.exit')} |

---

## {t('menu.workflow.desc')}

{t('help.workflow_tip')}

| {t('ui.col_cmd')}              | {t('ui.col_effect')} |
|----------------------|--------|
| `/ask <q>`           | {t('cmd.ask_usage')} |
| `/agent <task>`      | {t('cmd.agent_usage')} |
| `/btw <note>`        | {t('cmd.btw_note_hint')} |
| `/check`             | {t('menu.check.desc')} |
| `/accept`            | {t('context.accepted')} |
| `/delete`            | {t('context.deleted')} |
| `/log`               | {t('dash.history_label')} |
| `/info`              | {t('menu.info.desc')} |

---

## {t('menu.dashboard.desc')}

- **history** — {t('dash.history_label')}
- **total**   — {t('dash.total_label')}
- **budget**  — {t('dash.budget_label')}
- `back` / `0` — {t('nav.back')} · `exit` — {t('nav.exit')}

---

## {t('settings.header')}

| # | {t('ui.col_setting')} |
|---|---------|
| 1 | {t('settings.auto_accept')} |
| 2 | {t('settings.context_act')} |
| 3 | {t('settings.help_ext')} |
| 4 | {t('settings.lang')} |
""".strip()


MENU_PALETTE_ROWS = menu_palette_rows()
HELP_SCREEN_MARKDOWN = help_screen_markdown()


__all__ = [
    "MAIN_MENU_BY_NUMBER",
    "MAIN_MENU_ALIASES",
    "MAIN_MENU_VALID_CHOICES",
    "MAIN_PROMPT_LABEL",
    "START_MODE_BY_NUMBER",
    "MENU_PALETTE_ROWS",
    "HELP_SCREEN_MARKDOWN",
    "menu_palette_rows",
    "menu_commands",
    "help_screen_markdown",
]

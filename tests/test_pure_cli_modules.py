"""Tests for several small pure-function CLI modules."""
import sys
import pytest

# Some test stubs (test_ask_chat_manager, test_dashboard_history_pure) install
# MagicMocks for these modules via sys.modules.setdefault. Force-remove them
# so we get the real implementations here.
for _m in [
    "core.cli.nav",
    "core.cli.workflow.tui.display_policy",
    "core.cli.workflow.runtime.pipeline_markdown",
]:
    sys.modules.pop(_m, None)

# ── command_registry ──────────────────────────────────────────────────────────
from core.cli.command_registry import (
    MAIN_MENU_BY_NUMBER,
    MAIN_MENU_VALID_CHOICES,
    MENU_PALETTE_ROWS,
    START_MODE_BY_NUMBER,
    HELP_SCREEN_MARKDOWN,
    menu_commands,
)


class TestCommandRegistry:
    def test_main_menu_has_expected_keys(self):
        assert "0" in MAIN_MENU_BY_NUMBER
        assert "1" in MAIN_MENU_BY_NUMBER
        assert MAIN_MENU_BY_NUMBER["0"] == "shutdown"
        assert MAIN_MENU_BY_NUMBER["1"] == "start"

    def test_valid_choices_include_numbers_and_names(self):
        assert "0" in MAIN_MENU_VALID_CHOICES
        assert "shutdown" in MAIN_MENU_VALID_CHOICES
        assert "back" in MAIN_MENU_VALID_CHOICES

    def test_start_mode_keys(self):
        assert START_MODE_BY_NUMBER["1"] == "ask"
        assert START_MODE_BY_NUMBER["2"] == "agent"

    def test_menu_commands_returns_list_of_tuples(self):
        rows = menu_commands()
        assert isinstance(rows, list)
        assert len(rows) == len(MENU_PALETTE_ROWS)
        for row in rows:
            assert isinstance(row, tuple)
            assert len(row) == 3

    def test_help_markdown_is_string(self):
        assert isinstance(HELP_SCREEN_MARKDOWN, str)
        assert len(HELP_SCREEN_MARKDOWN) > 50


# ── nav ───────────────────────────────────────────────────────────────────────
from core.cli.nav import NavBack, NavToMain, is_nav_back, is_nav_exit, raise_if_global_nav


class TestNav:
    def test_is_nav_exit_true(self):
        assert is_nav_exit("exit") is True
        assert is_nav_exit("EXIT") is True
        assert is_nav_exit("  exit  ") is True

    def test_is_nav_exit_false(self):
        assert is_nav_exit("back") is False
        assert is_nav_exit("") is False

    def test_is_nav_back_true(self):
        assert is_nav_back("back") is True
        assert is_nav_back("BACK") is True

    def test_is_nav_back_false(self):
        assert is_nav_back("exit") is False

    def test_raise_if_global_nav_exit(self):
        with pytest.raises(NavToMain):
            raise_if_global_nav("exit")

    def test_raise_if_global_nav_back(self):
        with pytest.raises(NavBack):
            raise_if_global_nav("back")

    def test_raise_if_global_nav_other(self):
        raise_if_global_nav("start")  # must not raise

    def test_raise_if_global_nav_empty(self):
        raise_if_global_nav("")  # must not raise


# ── display_policy ────────────────────────────────────────────────────────────
from core.cli.workflow.tui.display_policy import WorkflowDisplayPolicy, resolve_display_policy


class TestDisplayPolicy:
    def test_chain_default(self):
        policy = resolve_display_policy({})
        assert policy.view_mode == "chain"
        assert policy.use_chain is True

    def test_list_mode(self):
        policy = resolve_display_policy({"workflow_view_mode": "list"})
        assert policy.view_mode == "list"
        assert policy.use_chain is False

    def test_unknown_value_defaults_to_chain(self):
        policy = resolve_display_policy({"workflow_view_mode": "something_else"})
        assert policy.view_mode == "chain"

    def test_frozen_dataclass(self):
        policy = WorkflowDisplayPolicy(view_mode="chain", use_chain=True)
        with pytest.raises(Exception):
            policy.view_mode = "list"  # type: ignore[misc]


# ── routing_map ───────────────────────────────────────────────────────────────
from core.domain.routing_map import pipeline_registry_key_for_tier, selected_leader_for_tier


class TestRoutingMap:
    def test_low_tier_routes_to_leader_medium(self):
        assert pipeline_registry_key_for_tier("LOW") == "LEADER_MEDIUM"

    def test_medium_tier(self):
        assert pipeline_registry_key_for_tier("MEDIUM") == "LEADER_MEDIUM"

    def test_expert_tier(self):
        assert pipeline_registry_key_for_tier("EXPERT") == "EXPERT"

    def test_hard_tier(self):
        assert pipeline_registry_key_for_tier("HARD") == "LEADER_HIGH"

    def test_unknown_defaults_to_medium(self):
        assert pipeline_registry_key_for_tier("UNKNOWN") == "LEADER_MEDIUM"

    def test_case_insensitive(self):
        assert pipeline_registry_key_for_tier("low") == pipeline_registry_key_for_tier("LOW")

    def test_selected_leader_expert(self):
        assert selected_leader_for_tier("EXPERT") == "EXPERT_MIMO"

    def test_selected_leader_hard(self):
        assert selected_leader_for_tier("HARD") == "LEADER_HIGH"

    def test_selected_leader_unknown_defaults(self):
        assert selected_leader_for_tier("NOPE") == "LEADER_MEDIUM"


# ── pipeline_markdown ─────────────────────────────────────────────────────────
from core.cli.workflow.runtime.pipeline_markdown import SPINNER, build_pipeline_markup


class TestPipelineMarkdown:
    def _dn(self, sid): return sid.replace("_", " ").title()
    def _rs(self, sid, tier, leader): return f"{leader}:{sid}"

    def test_spinner_not_empty(self):
        assert len(SPINNER) > 0

    def test_glyph_done_contains_green(self):
        from core.cli.workflow.runtime.pipeline_markdown import _glyph
        result = _glyph("done", "|", True)
        assert "green" in result

    def test_glyph_error_contains_red(self):
        from core.cli.workflow.runtime.pipeline_markdown import _glyph
        result = _glyph("error", "|", False)
        assert "red" in result

    def test_glyph_pending(self):
        from core.cli.workflow.runtime.pipeline_markdown import _glyph
        result = _glyph("pending", "|", True)
        assert result  # non-empty

    def test_glyph_spin(self):
        from core.cli.workflow.runtime.pipeline_markdown import _glyph
        result = _glyph("spin", "|", True)
        assert "|" in result

    def test_glyph_wait(self):
        from core.cli.workflow.runtime.pipeline_markdown import _glyph
        result = _glyph("wait", "|", True)
        assert "*" in result

    def test_glyph_unknown(self):
        from core.cli.workflow.runtime.pipeline_markdown import _glyph
        result = _glyph("unknown_state", "|", True)
        assert result  # default fallback

    def test_build_returns_two_lines(self):
        steps = ["ambassador", "leader_generate"]
        states = {"ambassador": "done", "leader_generate": "spin"}
        result = build_pipeline_markup(
            steps, states, "MEDIUM", "LEADER_MEDIUM", 0, self._dn, self._rs
        )
        lines = result.split("\n")
        assert len(lines) == 2

    def test_build_empty_steps(self):
        result = build_pipeline_markup([], {}, None, "", 0, self._dn, self._rs)
        assert "\n" in result  # still produces line1 + "\n" + line2

"""Tests for core/cli/flows/ask_chat_manager.py — pure string and index helpers."""
import re
from unittest.mock import patch, MagicMock

import pytest


# Patch the heavy UI imports before loading the module
_DUMMY_CONSOLE = MagicMock()
_PATCHES = {
    "rich.box": MagicMock(ROUNDED=MagicMock()),
    "rich.prompt": MagicMock(Prompt=MagicMock()),
    "rich.table": MagicMock(Table=MagicMock()),
    "core.cli.chrome.ui": MagicMock(
        PASTEL_BLUE="blue", clear_screen=MagicMock(), console=_DUMMY_CONSOLE
    ),
    "core.cli.nav": MagicMock(NavToMain=Exception),
    "core.cli.state": MagicMock(log_system_action=MagicMock()),
    "core.cli.flows.ask_history_renderer": MagicMock(_ask_input_with_header=MagicMock()),
    "core.cli.flows.ask_model_selector": MagicMock(
        _chat_model_settings=MagicMock(return_value=("gpt-4", 2048, 0.7, 1.0))
    ),
}

import sys
for mod, mock in _PATCHES.items():
    sys.modules.setdefault(mod, mock)

from core.cli.flows.ask_chat_manager import (
    _is_temp_chat_name,
    _new_chat_name,
    _parse_index_list,
    _resolve_chat_name,
)


class TestIsTempChatName:
    def test_new_chat_prefix(self):
        assert _is_temp_chat_name("new-chat-20240101-1200") is True

    def test_chat_prefix(self):
        assert _is_temp_chat_name("chat-some-name") is True

    def test_real_name(self):
        assert _is_temp_chat_name("My Project Refactor") is False

    def test_empty_string(self):
        assert _is_temp_chat_name("") is False

    def test_case_insensitive(self):
        assert _is_temp_chat_name("NEW-CHAT-20240101") is True


class TestNewChatName:
    def test_starts_with_prefix(self):
        name = _new_chat_name()
        assert name.startswith("new-chat-")

    def test_contains_date(self):
        name = _new_chat_name()
        # Should contain digits
        assert any(c.isdigit() for c in name)


class TestResolveChat:
    def _chats(self, *names):
        return [{"name": n} for n in names]

    def test_numeric_resolves_by_position(self):
        chats = self._chats("alpha", "beta", "gamma")
        assert _resolve_chat_name("2", chats) == "beta"

    def test_out_of_range_returns_token(self):
        chats = self._chats("alpha")
        result = _resolve_chat_name("5", chats)
        assert result == "5"

    def test_name_token_returned_as_is(self):
        chats = self._chats("alpha")
        assert _resolve_chat_name("my-chat", chats) == "my-chat"

    def test_empty_returns_none(self):
        assert _resolve_chat_name("", []) is None


class TestParseIndexList:
    def test_single_index(self):
        assert _parse_index_list("2", 5) == [2]

    def test_range_two_tokens(self):
        result = _parse_index_list("2 4", 5)
        assert result == [2, 3, 4]

    def test_out_of_range_excluded(self):
        result = _parse_index_list("10", 5)
        assert result == []

    def test_zero_excluded(self):
        assert _parse_index_list("0", 5) == []

    def test_multiple_space_separated(self):
        result = _parse_index_list("1 3 5", 5)
        assert 1 in result and 3 in result and 5 in result

    def test_empty_string_returns_empty(self):
        assert _parse_index_list("", 5) == []

    def test_reversed_range_works(self):
        result = _parse_index_list("4 2", 5)
        assert result == [2, 3, 4]

    def test_deduplicated(self):
        result = _parse_index_list("2 2", 5)
        assert result.count(2) == 1

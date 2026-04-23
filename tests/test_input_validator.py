"""Tests for utils/input_validator.py — boundary input validation."""
import pytest
from utils.input_validator import (
    MAX_PROMPT_CHARS,
    PromptInvalid,
    PromptTooLong,
    validate_user_prompt,
)


class TestValidateUserPrompt:
    def test_valid_prompt_returned(self):
        assert validate_user_prompt("Hello world") == "Hello world"

    def test_strips_whitespace(self):
        assert validate_user_prompt("  hello  ") == "hello"

    def test_empty_string_raises(self):
        with pytest.raises(PromptInvalid):
            validate_user_prompt("")

    def test_whitespace_only_raises(self):
        with pytest.raises(PromptInvalid):
            validate_user_prompt("   ")

    def test_null_bytes_raises(self):
        with pytest.raises(PromptInvalid, match="null bytes"):
            validate_user_prompt("hello\x00world")

    def test_too_long_raises(self):
        with pytest.raises(PromptTooLong):
            validate_user_prompt("x" * (MAX_PROMPT_CHARS + 1))

    def test_at_max_length_ok(self):
        result = validate_user_prompt("x" * MAX_PROMPT_CHARS)
        assert len(result) == MAX_PROMPT_CHARS

    def test_non_string_raises(self):
        with pytest.raises(PromptInvalid):
            validate_user_prompt(123)

    def test_unicode_prompt_ok(self):
        text = "Viết hàm Python để phân loại văn bản"
        assert validate_user_prompt(text) == text

    def test_prompt_too_long_message_includes_count(self):
        long_text = "a" * (MAX_PROMPT_CHARS + 100)
        with pytest.raises(PromptTooLong, match="maximum is"):
            validate_user_prompt(long_text)

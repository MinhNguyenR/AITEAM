"""Tests for utils/json_utils.py — resilient JSON parsing."""
import json
import pytest
from utils.json_utils import parse_json_resilient, strip_markdown_fences


class TestStripMarkdownFences:
    def test_removes_json_fence(self):
        result = strip_markdown_fences("```json\n{\"a\": 1}\n```")
        assert result == '{"a": 1}'

    def test_removes_plain_fence(self):
        result = strip_markdown_fences("```\n{\"b\": 2}\n```")
        assert result == '{"b": 2}'

    def test_no_fence_unchanged(self):
        text = '{"c": 3}'
        assert strip_markdown_fences(text) == text

    def test_strips_whitespace(self):
        assert strip_markdown_fences("  hello  ") == "hello"

    def test_empty_string(self):
        assert strip_markdown_fences("") == ""


class TestParseJsonResilient:
    def test_direct_parse(self):
        result = parse_json_resilient('{"tier": "LOW", "score": 0.3}')
        assert result == {"tier": "LOW", "score": 0.3}

    def test_fenced_json(self):
        result = parse_json_resilient('```json\n{"tier": "HIGH"}\n```')
        assert result["tier"] == "HIGH"

    def test_embedded_json_with_prefix(self):
        result = parse_json_resilient('Sure! Here is the result:\n{"tier": "MEDIUM"}')
        assert result["tier"] == "MEDIUM"

    def test_trailing_comma_fixed(self):
        result = parse_json_resilient('{"a": 1, "b": 2,}')
        assert result == {"a": 1, "b": 2}

    def test_invalid_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_json_resilient("not json at all")

    def test_empty_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_json_resilient("")

    def test_nested_object(self):
        result = parse_json_resilient('{"params": {"a": 1}}')
        assert result["params"]["a"] == 1

    def test_array_value(self):
        result = parse_json_resilient('{"items": [1, 2, 3]}')
        assert result["items"] == [1, 2, 3]

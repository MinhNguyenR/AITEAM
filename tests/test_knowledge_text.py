"""Tests for core/storage/knowledge_text.py — keyword extraction and FTS helpers."""
import sqlite3

from core.storage.knowledge_text import (
    escape_like,
    extract_keywords,
    fts_match_expression,
    fts_token_terms,
    like_fallback_rows,
)


class TestExtractKeywords:
    def test_empty_string_returns_empty(self):
        assert extract_keywords("") == []

    def test_short_string_returns_empty(self):
        assert extract_keywords("hi") == []

    def test_all_digits_returns_empty(self):
        # No alphabetic tokens → empty token list
        assert extract_keywords("123 456 789 000") == []

    def test_all_stop_words_returns_empty(self):
        # All tokens are stop words
        result = extract_keywords("the a an is are was were be been")
        assert result == []

    def test_basic_keywords(self):
        text = "Python programming language for machine learning applications"
        result = extract_keywords(text, top_k=3)
        assert isinstance(result, list)
        assert len(result) <= 3
        # Should include non-stop words
        assert any(w in result for w in ("python", "programming", "language", "machine", "learning"))

    def test_top_k_limits(self):
        text = "apple banana cherry date elderberry fig grape honeydew iris"
        result = extract_keywords(text, top_k=3)
        assert len(result) <= 3

    def test_repeated_words_ranked_higher(self):
        text = "python python python is great language"
        result = extract_keywords(text, top_k=5)
        assert "python" in result
        assert result[0] == "python"


class TestFtsTokenTerms:
    def test_basic_terms(self):
        result = fts_token_terms(["python", "code"], "python code")
        assert "python" in result
        assert "code" in result

    def test_deduplication(self):
        result = fts_token_terms(["python", "python", "code"], "")
        assert result.count("python") == 1

    def test_short_term_skipped(self):
        result = fts_token_terms(["a"], "")
        assert "a" not in result

    def test_fallback_from_query(self):
        # Empty keywords → falls back to extracting from query_text
        result = fts_token_terms([], "machine learning")
        assert len(result) > 0
        assert "machine" in result or "learning" in result

    def test_empty_both(self):
        result = fts_token_terms([], "")
        assert result == []

    def test_limit_at_8(self):
        result = fts_token_terms([], "one two three four five six seven eight nine ten")
        assert len(result) <= 8


class TestFtsMatchExpression:
    def test_single_term(self):
        expr = fts_match_expression(["python"])
        assert expr is not None
        assert '"python"' in expr

    def test_multiple_terms(self):
        expr = fts_match_expression(["python", "code"])
        assert "OR" in expr

    def test_empty_terms_returns_none(self):
        assert fts_match_expression([]) is None

    def test_null_byte_filtered(self):
        # Term with null byte should be skipped
        expr = fts_match_expression(["\x00bad"])
        assert expr is None

    def test_newline_filtered(self):
        expr = fts_match_expression(["good", "bad\nterm"])
        assert expr is not None
        assert "bad" not in expr

    def test_all_invalid_returns_none(self):
        assert fts_match_expression(["\x00a", "\rb"]) is None

    def test_quote_escaped(self):
        expr = fts_match_expression(['say "hi"'])
        assert expr is not None
        assert '""hi""' in expr or '""' in expr


class TestEscapeLike:
    def test_percent_escaped(self):
        assert escape_like("100%") == "100\\%"

    def test_underscore_escaped(self):
        assert escape_like("one_two") == "one\\_two"

    def test_backslash_escaped(self):
        assert escape_like("a\\b") == "a\\\\b"

    def test_clean_string(self):
        assert escape_like("hello") == "hello"


class TestLikeFallbackRows:
    def test_returns_rows(self):
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE knowledge_index (id TEXT, title TEXT, tags TEXT, path TEXT, updated_at TEXT)"
        )
        conn.execute(
            "INSERT INTO knowledge_index VALUES ('1', 'Python guide', 'python code', '/path', '2024-01-01')"
        )
        conn.commit()
        cursor = conn.cursor()
        rows = like_fallback_rows(cursor, ["python"], limit=10)
        assert len(rows) == 1
        assert rows[0][1] == "Python guide"
        conn.close()

    def test_empty_terms_returns_empty(self):
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        rows = like_fallback_rows(cursor, [], limit=10)
        assert rows == []
        conn.close()

    def test_no_match(self):
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE knowledge_index (id TEXT, title TEXT, tags TEXT, path TEXT, updated_at TEXT)"
        )
        conn.commit()
        cursor = conn.cursor()
        rows = like_fallback_rows(cursor, ["xyz_no_match"], limit=10)
        assert rows == []
        conn.close()

"""Tests for agents/leader.py pure helpers and write_no_context — no API calls."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.leader import _truncate_state, BaseLeader
from core.config.constants import STATE_CHAR_LIMIT_DEFAULT


# ---------------------------------------------------------------------------
# _truncate_state
# ---------------------------------------------------------------------------

class TestTruncateState:
    def test_small_dict_unchanged(self):
        data = {"task": "hello", "tier": "LOW"}
        result = _truncate_state(data, char_limit=100000)
        assert json.loads(result) == data

    def test_large_dict_truncated(self):
        data = {"key": "x" * 10000}
        result = _truncate_state(data, char_limit=500)
        assert len(result) <= 500 + 100  # +100 for truncation message
        assert "TRUNCATED" in result

    def test_truncation_marker_appended(self):
        data = {"a": "b" * 50000}
        result = _truncate_state(data, char_limit=100)
        assert result.endswith("... [TRUNCATED — state too large, key fields shown above]")

    def test_exact_limit_not_truncated(self):
        data = {"k": "v"}
        raw = json.dumps(data, ensure_ascii=False, indent=2)
        result = _truncate_state(data, char_limit=len(raw))
        assert "TRUNCATED" not in result

    def test_default_limit_large_enough_for_normal_state(self):
        data = {"task": "write an API", "tier": "MEDIUM", "files": ["a.py", "b.py"]}
        result = _truncate_state(data)
        assert "TRUNCATED" not in result


# ---------------------------------------------------------------------------
# BaseLeader._write_no_context — pure file write
# ---------------------------------------------------------------------------

def _make_leader(tmp_path) -> BaseLeader:
    """Build a concrete BaseLeader subclass without network."""
    mock_cfg = MagicMock()
    mock_cfg.api_key = "sk-test"
    mock_cfg.BASE_DIR = tmp_path
    mock_cfg.get_worker = MagicMock(return_value=None)

    class _ConcreteLeader(BaseLeader):
        def format_output(self, r): return r

    with patch("agents.base_agent.make_openai_client"):
        leader = _ConcreteLeader(
            agent_name="LeaderTest",
            model_name="test-model",
            max_tokens=1024,
            temperature=0.3,
            registry_role_key="LEADER_MEDIUM",
        )
    # Override data_dir so log_action writes to tmp_path
    leader.data_dir = tmp_path
    return leader


class TestWriteNoContext:
    def test_writes_sentinel_file(self, tmp_path):
        leader = _make_leader(tmp_path)
        state_path = tmp_path / "task_abc" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text("{}", encoding="utf-8")

        written = {}
        def _fake_write(path, text, encoding="utf-8"):
            written["path"] = path
            written["text"] = text

        with patch("agents.leader.atomic_write_text", side_effect=_fake_write):
            result = leader._write_no_context(state_path, reason="API timeout")
        assert result.endswith("context.md")
        assert "NO_CONTEXT" in written["text"]
        assert "API timeout" in written["text"]

    def test_returns_string_path(self, tmp_path):
        leader = _make_leader(tmp_path)
        state_path = tmp_path / "state.json"
        state_path.write_text("{}", encoding="utf-8")
        with patch("agents.leader.atomic_write_text"):
            result = leader._write_no_context(state_path, "reason")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# format_output strip/clean
# ---------------------------------------------------------------------------

class TestLeaderFormatOutput:
    """LeaderMed.format_output strips fences and leading noise."""
    def _make_leader_med(self, tmp_path):
        from agents.leader import LeaderMed
        with patch("agents.base_agent.make_openai_client"), \
             patch("agents.leader.config") as mc:
            mc.get_worker.return_value = {
                "model": "test", "max_tokens": 512, "temperature": 0.5
            }
            leader = LeaderMed()
        leader.data_dir = tmp_path
        return leader

    def test_strips_fences(self, tmp_path):
        leader = self._make_leader_med(tmp_path)
        result = leader.format_output("```markdown\n# Plan\n## Tasks\n```")
        assert "# Plan" in result
        assert "```" not in result

    def test_empty_returns_empty(self, tmp_path):
        leader = self._make_leader_med(tmp_path)
        assert leader.format_output("") == ""

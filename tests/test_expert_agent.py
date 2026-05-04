"""Tests for agents/expert.py — SOLO mode, COPLAN mode, helpers."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_expert():
    from agents.expert import Expert
    cfg = {
        "model": "mimo-v2",
        "max_tokens": 4096,
        "temperature": 0.3,
        "context_window": 1_000_000,
    }
    with patch("agents.base_agent.make_openai_client"), \
         patch("agents.expert.config") as mc:
        mc.get_worker.return_value = cfg
        expert = Expert()
    return expert


def _write_state(tmp_path, data=None):
    task_dir = tmp_path / "task_xyz"
    task_dir.mkdir(exist_ok=True)
    state_path = task_dir / "state.json"
    state_path.write_text(
        json.dumps(data or {"task": "build API", "tier": "EXPERT"}),
        encoding="utf-8",
    )
    return state_path


class TestExpertInit:
    def test_sets_context_window(self):
        expert = _make_expert()
        assert expert._context_window == 1_000_000

    def test_agent_name(self):
        expert = _make_expert()
        assert expert.agent_name == "Expert"


class TestGenerateContextSolo:
    def test_raises_file_not_found_when_missing(self, tmp_path):
        expert = _make_expert()
        with pytest.raises(FileNotFoundError):
            expert.generate_context(str(tmp_path / "no_dir" / "state.json"))

    def test_writes_context_md(self, tmp_path):
        expert = _make_expert()
        state_path = _write_state(tmp_path)

        with patch.object(expert, "call_api", return_value="## 1. DIRECTORY\nContent"), \
             patch("agents.expert.atomic_write_text") as mock_write, \
             patch.object(expert, "save_knowledge"), \
             patch.object(expert, "log_action"), \
             patch("utils.graphrag_utils.try_ingest_context"):
            result = expert.generate_context(str(state_path))

        assert mock_write.called
        assert result.endswith("context.md")

    def test_stream_mode_uses_call_api_stream(self, tmp_path):
        expert = _make_expert()
        state_path = _write_state(tmp_path)

        with patch.object(expert, "call_api_stream", return_value="## 1. DIRECTORY\nContent") as mock_stream, \
             patch("agents.expert.atomic_write_text"), \
             patch.object(expert, "save_knowledge"), \
             patch.object(expert, "log_action"), \
             patch("utils.graphrag_utils.try_ingest_context"):
            expert.generate_context(str(state_path), stream_to_monitor=True)

        mock_stream.assert_called_once()

    def test_injects_prior_knowledge_when_found(self, tmp_path):
        expert = _make_expert()
        state_path = _write_state(tmp_path, {"task": "build FastAPI service"})

        with patch.object(expert, "call_api", return_value="## 1. DIRECTORY\nok"), \
             patch.object(expert, "search_knowledge", return_value=[{"title": "prior", "content": "ctx"}]) as mock_sk, \
             patch("agents.expert.atomic_write_text"), \
             patch.object(expert, "save_knowledge"), \
             patch.object(expert, "log_action"), \
             patch("utils.graphrag_utils.try_ingest_context"):
            expert.generate_context(str(state_path))

        mock_sk.assert_called_once()


class TestReadValidationInputs:
    def test_raises_when_draft_missing(self, tmp_path):
        expert = _make_expert()
        with pytest.raises(FileNotFoundError):
            expert._read_validation_inputs(
                draft_context_path=tmp_path / "missing.md",
                state_path=tmp_path / "state.json",
            )

    def test_returns_draft_and_state(self, tmp_path):
        expert = _make_expert()
        draft = tmp_path / "context.md"
        draft.write_text("## 1. DIRECTORY\nContent", encoding="utf-8")
        state = tmp_path / "state.json"
        state.write_text(json.dumps({"task": "test"}), encoding="utf-8")

        text, data = expert._read_validation_inputs(draft, state)
        assert "DIRECTORY" in text
        assert data["task"] == "test"

    def test_returns_empty_state_when_state_missing(self, tmp_path):
        expert = _make_expert()
        draft = tmp_path / "context.md"
        draft.write_text("Draft content", encoding="utf-8")

        text, data = expert._read_validation_inputs(draft, tmp_path / "no_state.json")
        assert text == "Draft content"
        assert data == {}

    def test_returns_empty_state_on_json_error(self, tmp_path):
        expert = _make_expert()
        draft = tmp_path / "context.md"
        draft.write_text("Draft content", encoding="utf-8")
        state = tmp_path / "state.json"
        state.write_text("not valid json", encoding="utf-8")

        text, data = expert._read_validation_inputs(draft, state)
        assert data == {}


class TestExtractStatus:
    def test_approved(self):
        expert = _make_expert()
        report = "Some intro\n### Status: APPROVED\nDetails"
        assert expert._extract_status(report) == "APPROVED"

    def test_needs_revision(self):
        expert = _make_expert()
        report = "### Status: NEEDS_REVISION\nFix these issues"
        assert expert._extract_status(report) == "NEEDS_REVISION"

    def test_escalate(self):
        expert = _make_expert()
        report = "### Status: ESCALATE_TO_COMMANDER\nToo complex"
        assert expert._extract_status(report) == "ESCALATE_TO_COMMANDER"

    def test_default_when_no_status_line(self):
        expert = _make_expert()
        report = "No status line here at all"
        assert expert._extract_status(report) == "NEEDS_REVISION"

    def test_approved_clean_line(self):
        expert = _make_expert()
        report = "### Status: APPROVED — all checks passed\n"
        assert expert._extract_status(report) == "APPROVED"


class TestValidatePlan:
    def _setup_files(self, tmp_path):
        draft = tmp_path / "context.md"
        draft.write_text("## 1. DIRECTORY\nDraft content", encoding="utf-8")
        state = tmp_path / "state.json"
        state.write_text(json.dumps({"task": "test task"}), encoding="utf-8")
        return draft, state

    def test_returns_approved_status(self, tmp_path):
        expert = _make_expert()
        draft, state = self._setup_files(tmp_path)

        with patch.object(expert, "call_api", return_value="### Status: APPROVED\nLooks good"), \
             patch("agents.expert.atomic_write_text"), \
             patch.object(expert, "save_knowledge"), \
             patch.object(expert, "log_action"):
            result = expert.validate_plan(str(draft), str(state))

        assert result == "APPROVED"

    def test_needs_revision_calls_apply_revisions(self, tmp_path):
        expert = _make_expert()
        draft, state = self._setup_files(tmp_path)

        with patch.object(expert, "call_api", return_value="### Status: NEEDS_REVISION\n### Revised Tasks\nFix something"), \
             patch("agents.expert.atomic_write_text"), \
             patch.object(expert, "save_knowledge"), \
             patch.object(expert, "log_action"), \
             patch.object(expert, "_apply_revisions") as mock_rev:
            result = expert.validate_plan(str(draft), str(state))

        assert result == "NEEDS_REVISION"
        mock_rev.assert_called_once()

    def test_approved_does_not_call_apply_revisions(self, tmp_path):
        expert = _make_expert()
        draft, state = self._setup_files(tmp_path)

        with patch.object(expert, "call_api", return_value="### Status: APPROVED\nAll good"), \
             patch("agents.expert.atomic_write_text"), \
             patch.object(expert, "save_knowledge"), \
             patch.object(expert, "log_action"), \
             patch.object(expert, "_apply_revisions") as mock_rev:
            expert.validate_plan(str(draft), str(state))

        mock_rev.assert_not_called()


class TestApplyRevisions:
    def test_no_revised_section_skips_patch(self, tmp_path):
        expert = _make_expert()
        ctx = tmp_path / "context.md"
        ctx.write_text("## Original content", encoding="utf-8")
        original_content = ctx.read_text(encoding="utf-8")

        with patch("agents.expert.atomic_write_text") as mock_write, \
             patch("utils.graphrag_utils.try_ingest_context"):
            expert._apply_revisions(ctx, "No revised section here")

        mock_write.assert_not_called()

    def test_with_revised_section_calls_write(self, tmp_path):
        expert = _make_expert()
        ctx = tmp_path / "context.md"
        ctx.write_text("## Original content", encoding="utf-8")

        report = "### Revised Tasks\nFix the auth module\nAdd rate limiting\n"

        with patch("agents.expert.atomic_write_text") as mock_write, \
             patch("utils.graphrag_utils.try_ingest_context"):
            expert._apply_revisions(ctx, report)

        mock_write.assert_called_once()
        written_content = mock_write.call_args[0][1]
        assert "REVISIONS" in written_content


class TestExtractSection:
    def test_extracts_section_content(self):
        expert = _make_expert()
        text = "Intro\n### Revised Tasks\nFix A\nFix B\n### Another Section\nOther"
        result = expert._extract_section(text, "Revised Tasks")
        assert result is not None
        assert "Fix A" in result

    def test_returns_none_when_section_missing(self):
        expert = _make_expert()
        text = "No sections here"
        assert expert._extract_section(text, "Revised Tasks") is None


class TestFormatOutput:
    def test_empty_returns_empty(self):
        expert = _make_expert()
        assert expert.format_output("") == ""

    def test_strips_fences(self):
        expert = _make_expert()
        raw = "```\n## 1. DIRECTORY\nContent\n```"
        result = expert.format_output(raw)
        assert "## 1. DIRECTORY" in result
        assert "```" not in result

    def test_finds_directory_marker(self):
        expert = _make_expert()
        raw = "Preamble text\n## 1. DIRECTORY\nActual content"
        result = expert.format_output(raw)
        assert result.startswith("## 1.")
        assert "Preamble" not in result

    def test_no_marker_returns_stripped(self):
        expert = _make_expert()
        raw = "   Some plain content   "
        result = expert.format_output(raw)
        assert result == "Some plain content"


class TestExecute:
    def test_execute_delegates_to_generate_context(self, tmp_path):
        expert = _make_expert()
        state_path = _write_state(tmp_path)

        with patch.object(expert, "generate_context", return_value="ctx.md") as mock_gen:
            result = expert.execute(str(state_path))

        mock_gen.assert_called_once_with(str(state_path))
        assert result == "ctx.md"

    def test_execute_uses_state_path_when_provided(self, tmp_path):
        expert = _make_expert()
        state_path = _write_state(tmp_path)

        with patch.object(expert, "generate_context", return_value="ctx.md") as mock_gen:
            expert.execute("ignored_task", state_path=str(state_path))

        mock_gen.assert_called_once_with(str(state_path))

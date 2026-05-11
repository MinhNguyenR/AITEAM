"""
AI Agentic Framework - Tool Curator Agent
==========================================
Reads context.md -> LLM -> writes tools.md (same dir).


Pipeline: Ambassador -> Leader -> Human Gate -> Tool Curator -> Finalize.


Substates pushed to workflow session (TUI tree):
    reading      -> reading context.md
    thinking     -> LLM analyzing dependencies
    looking_for  -> scanning project for installed packages (pip list)
    writing      -> writing tools.md
"""

from __future__ import annotations


import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


from agents.base_agent import BaseAgent
from core.config import config
from utils.file_manager import atomic_write_text


logger = logging.getLogger(__name__)


_TOOL_CURATOR_SYSTEM_PROMPT = """You are TOOL_CURATOR - a senior dependency / tooling advisor.


You receive a Leader's context.md describing a coding task plus a list of
packages already installed in the project venv. You must produce a concise
tools.md aimed at human readers.
Setup commands are Secretary-only. Workers must never receive setup/scaffold
commands as their own work.


Output (Markdown only, no JSON, no fences):


# Recommended Tools


## Already Installed
- `package-name` - one-line purpose for this task


## Setup Commands
```bash
pip install pkg-a pkg-b
```


## Install
- `package-name` - why it is needed


## Notes
- (only if relevant) brief tip on version pinning, optional extras, or alternatives.


Rules:
- Only list packages truly needed by the context.md task.
- If the task needs project scaffolding or dependency installation, put exact safe terminal commands under Setup Commands.
- Setup Commands are for Secretary only and must run before workers start.
- If a project scaffold already exists, say "No setup required" instead of emitting scaffold commands.
- For React/Vite/new frontend projects in an empty workspace, include the project creation command before any worker-facing notes.
- Do not invent packages. Prefer stdlib when sufficient and say so.
- Keep it under ~40 lines. Be terse.
"""


class ToolCurator(BaseAgent):
    """Generates tools.md after the human accepts context.md."""

    def __init__(self, budget_limit_usd: Optional[float] = None):
        cfg = config.get_worker("TOOL_CURATOR") or {}
        super().__init__(
            agent_name="TOOL_CURATOR",
            model_name=cfg.get("model", "deepseek/deepseek-v4-flash"),
            system_prompt=_TOOL_CURATOR_SYSTEM_PROMPT,
            max_tokens=int(cfg.get("max_tokens", 4096)),
            temperature=float(cfg.get("temperature", 0.2)),
            budget_limit_usd=budget_limit_usd,
            registry_role_key="TOOL_CURATOR",
        )

    # ===== CORE =====

    def generate_tools(self, context_path: str | Path) -> str:
        """Read context.md -> LLM -> write tools.md.


        Returns the path to tools.md (string).
        Raises on hard failure so the orchestrator can surface a curator_failed flag.
        """
        ctx_path = Path(context_path)
        if not ctx_path.exists():
            raise FileNotFoundError(f"context.md not found: {ctx_path}")

        # 1. reading
        self._set_substate("reading", f"context.md ({ctx_path.name})")
        context_text = ctx_path.read_text(encoding="utf-8", errors="replace")
        logger.info(
            "[%s] Loaded context: %s (%d chars)",
            self.agent_name,
            ctx_path,
            len(context_text),
        )

        # 3. looking_for: pip list
        # NOTE: ordered "reading -> thinking -> looking_for -> writing" per spec,
        # but we collect the pip snapshot before LLM call so the prompt can
        # reference installed packages. Push the substate transition reading ->
        # looking_for -> thinking explicitly so the TUI tree still tells the story.
        self._set_substate("looking_for", "pyproject.toml, pip list")
        installed = self._installed_packages()

        # 2. thinking
        self._set_substate("thinking", "analyzing dependencies")
        user_prompt = self._build_prompt(context_text, installed)
        try:
            response = self.call_api(user_prompt)
        except (ValueError, OSError, RuntimeError, TypeError, KeyError) as e:
            logger.error("[%s] call_api failed: %s", self.agent_name, e)
            self._clear_substate()
            raise

        tools_content = self.format_output(response)
        if not tools_content.strip():
            self._clear_substate()
            raise ValueError("Tool curator returned empty content")

        # 4. writing
        self._set_substate("writing", "tools.md")
        tools_path = ctx_path.parent / "tools.md"
        atomic_write_text(tools_path, tools_content, encoding="utf-8")
        logger.info(
            "[%s] tools.md written (%d chars) -> %s",
            self.agent_name,
            len(tools_content),
            tools_path,
        )

        self.save_knowledge(
            title=f"Tool list - {self.agent_name}",
            content=tools_content,
            tags=["tools", "dependencies", self.agent_name.lower()],
        )
        self.log_action(
            decision="Generated tool recommendations",
            action=f"Wrote tools.md ({len(tools_content)} chars)",
            cost=self.session_cost,
        )

        from utils.graphrag_utils import try_ingest_context, try_ingest_prompt_doc

        try_ingest_context(tools_path, {"source": "tool_curator"}, self.agent_name)
        # Best-effort task_uuid recovery from run_dir name (cache/runs/<uuid>/...)
        task_uuid = ctx_path.parent.name
        try_ingest_prompt_doc(
            task_uuid,
            self.agent_name,
            "generate_tools",
            user_prompt[:8000],
            tools_content[:8000],
        )

        self._clear_substate()
        return str(tools_path)

    # ===== HELPERS =====

    def _build_prompt(self, context_text: str, installed: List[str]) -> str:
        installed_block = (
            "\n".join(f"- {p}" for p in installed[:200])
            if installed
            else "(no packages detected)"
        )
        return (
            "Below is the Leader's context.md for this task. "
            "Recommend the minimal set of tools / pip packages that the "
            "human implementer will actually need. Be terse and do not "
            "invent packages.\n\n"
            "## context.md\n"
            f"{context_text[:12000]}\n\n"
            "## Already installed in the project venv\n"
            f"{installed_block}\n"
        )

    def _installed_packages(self) -> List[str]:
        """Return a sorted list of `name==version` strings from `pip list` in
        the active Python interpreter. Empty on failure."""
        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "list",
                    "--format=freeze",
                    "--disable-pip-version-check",
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as e:
            logger.debug("[%s] pip list failed: %s", self.agent_name, e)
            return []
        if proc.returncode != 0:
            logger.debug(
                "[%s] pip list rc=%s stderr=%s",
                self.agent_name,
                proc.returncode,
                proc.stderr[:200],
            )
            return []
        lines = [
            ln.strip()
            for ln in (proc.stdout or "").splitlines()
            if ln.strip() and "==" in ln
        ]
        return sorted(lines)

    def _set_substate(self, substate: str, detail: str = "") -> None:
        try:
            from core.runtime import session as ws

            ws.set_curator_substate(substate, detail)
        except (ImportError, RuntimeError):
            pass

    def _clear_substate(self) -> None:
        try:
            from core.runtime import session as ws

            ws.clear_curator_substate()
        except (ImportError, RuntimeError):
            pass

    # ===== ABSTRACT IMPLEMENTATIONS =====

    def execute(self, task: str, **kwargs) -> str:
        return self.generate_tools(task)

    def format_output(self, response: str) -> str:
        if not response:
            return ""
        text = self._strip_markdown_fences(response).strip()
        if not text:
            return ""
        # Prefer the first H1 if the model added preamble.
        m = re.search(r"^# .+", text, re.MULTILINE)
        if m:
            return text[m.start() :].strip()
        return text


__all__ = ["ToolCurator"]

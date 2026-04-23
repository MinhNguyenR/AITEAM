"""
AI Agentic Framework v6.2 — Expert Agent
=========================================
Expert: Architecture validator and co-planner for EXPERT-tier tasks.

Role in pipeline:
  Ambassador (EXPERT tier) → Expert → context.md → Workers

Responsibilities:
  - Deep architectural validation (>5 files scope)
  - Co-plan with LeaderHigh on HARD tasks (called by orchestrator)
  - 1M context window — can ingest entire codebase
  - Never writes implementation code; only stubs, interfaces, validation reports

Model: xiaomi/mimo-v2-pro
Specialty: Opus-level coding reasoning, 1M ctx, SWE-Bench competitive

Author: Nguyễn Đặng Tường Minh
"""

import json
import logging
from pathlib import Path
from typing import Optional

from agents.base_agent import BaseAgent
from core.config import config
from core.domain.prompts import (
    EXPERT_SYSTEM_PROMPT,
    EXPERT_COPLAN_SYSTEM_PROMPT,
    build_expert_solo_prompt,
    build_expert_coplan_prompt,
)
from utils.file_manager import atomic_write_text

logger = logging.getLogger(__name__)

class Expert(BaseAgent):
    """
    Expert agent (1M context worker from config).

    Two modes:
      1. SOLO mode: Generate context.md directly from state.json (EXPERT tier tasks)
      2. COPLAN mode: Validate and revise a LeaderHigh's context.md draft (HARD tier)

    The orchestrator chooses mode based on DeltaBrief.tier:
      - EXPERT → solo mode (Ambassador routes directly here)
      - HARD   → coplan mode (LeaderHigh drafts first, Expert validates)
    """

    def __init__(self, budget_limit_usd: Optional[float] = None):
        cfg = config.get_worker("EXPERT")
        super().__init__(
            agent_name="Expert",
            model_name=cfg["model"],
            system_prompt=EXPERT_SYSTEM_PROMPT,
            max_tokens=cfg["max_tokens"],
            temperature=cfg["temperature"],
            budget_limit_usd=budget_limit_usd,
            registry_role_key="EXPERT",
        )
        self._context_window = cfg.get("context_window", 1_000_000)

    # ===== SOLO MODE =====

    def generate_context(self, state_path: str | Path, *, stream_to_monitor: bool = False) -> str:
        """
        SOLO mode: Read state.json → generate context.md independently.

        Used when Ambassador routes an EXPERT-tier task directly here,
        bypassing Leaders entirely.

        Args:
            state_path: Path to state.json

        Returns:
            Path to generated context.md
        """
        state_path = Path(state_path)

        if not state_path.exists():
            raise FileNotFoundError(f"State file not found: {state_path}")

        with open(state_path, "r", encoding="utf-8") as f:
            state_data = json.load(f)

        logger.info(f"[{self.agent_name}] SOLO mode — loaded state: {state_path}")

        # Search prior knowledge for related work
        query = state_data.get("task", "") or state_data.get("description", "")
        if query:
            prior = self.search_knowledge(query[:100], max_results=2)
            if prior:
                logger.info(f"[{self.agent_name}] Injecting {len(prior)} prior knowledge entries")

        user_prompt = self._build_solo_prompt(state_data)
        if stream_to_monitor:
            response = self.call_api_stream(user_prompt)
        else:
            response = self.call_api(user_prompt)
        context_content = self.format_output(response)

        context_path = state_path.parent / "context.md"
        atomic_write_text(context_path, context_content, encoding="utf-8")

        logger.info(f"[{self.agent_name}] context.md written → {context_path}")

        self.save_knowledge(
            title=f"Expert context plan — {state_data.get('task', 'unknown')[:60]}",
            content=context_content,
            tags=["context", "expert", "plan"],
        )

        self.log_action(
            decision="Generated expert architecture plan (SOLO mode)",
            action=f"Wrote context.md ({len(context_content)} chars)",
            cost=self.session_cost,
        )

        from utils.graphrag_utils import try_ingest_context
        try_ingest_context(context_path, state_data, self.agent_name)

        return str(context_path)

    def _build_solo_prompt(self, state_data: dict) -> str:
        """Build prompt for SOLO mode context generation."""
        return build_expert_solo_prompt(state_data)

    # ===== COPLAN MODE =====

    def _read_validation_inputs(
        self,
        draft_context_path: Path,
        state_path: Path,
    ) -> tuple:
        """Read draft context text and state dict from disk.

        Returns (draft_text, state_data). Raises FileNotFoundError if draft missing.
        """
        if not draft_context_path.exists():
            raise FileNotFoundError(f"Draft context not found: {draft_context_path}")
        draft = draft_context_path.read_text(encoding="utf-8")
        state_data: dict = {}
        if state_path.exists():
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("[%s] Could not read state.json: %s", self.agent_name, e)
        return draft, state_data

    def validate_plan(self, draft_context_path: str | Path, state_path: str | Path) -> str:
        """
        COPLAN mode: Validate a LeaderHigh draft context.md.

        Called by the orchestrator after LeaderHigh.generate_context() on HARD tasks.
        Produces a VALIDATION REPORT; if NEEDS_REVISION, also rewrites affected tasks.

        Args:
            draft_context_path: Path to LeaderHigh's context.md
            state_path: Path to original state.json (for full context)

        Returns:
            Validation status: "APPROVED" | "NEEDS_REVISION" | "ESCALATE_TO_COMMANDER"
        """
        draft_context_path = Path(draft_context_path)
        state_path = Path(state_path)
        draft, state_data = self._read_validation_inputs(draft_context_path, state_path)

        logger.info(f"[{self.agent_name}] COPLAN mode — validating {draft_context_path}")

        user_prompt = self._build_coplan_prompt(draft, state_data)

        # Switch to co-plan system prompt for this call
        response = self.call_api(
            user_prompt,
            system_prompt=EXPERT_COPLAN_SYSTEM_PROMPT,
            temperature=0.1,  # Low temp for precise validation
        )

        validation_report = response.strip()

        # Extract status line
        status = self._extract_status(validation_report)
        logger.info(f"[{self.agent_name}] Validation result: {status}")

        # Write validation report next to context.md
        report_path = draft_context_path.parent / "validation_report.md"
        atomic_write_text(report_path, validation_report, encoding="utf-8")

        # If revision needed, apply patches to context.md
        if status == "NEEDS_REVISION":
            self._apply_revisions(draft_context_path, validation_report)

        self.save_knowledge(
            title=f"Validation report — {status}",
            content=validation_report,
            tags=["validation", "coplan", status.lower()],
        )

        self.log_action(
            decision=f"Validated LeaderHigh plan → {status}",
            action=f"Wrote validation_report.md ({len(validation_report)} chars)",
            cost=self.session_cost,
        )

        return status

    def _build_coplan_prompt(self, draft: str, state_data: dict) -> str:
        """Build prompt for COPLAN validation."""
        return build_expert_coplan_prompt(draft, state_data)

    def _extract_status(self, report: str) -> str:
        """
        Parse validation status from report header.

        Looks for: '### Status: APPROVED | NEEDS_REVISION | ESCALATE_TO_COMMANDER'
        Falls back to NEEDS_REVISION if not found.
        """
        for line in report.splitlines():
            if "### Status:" in line:
                line_upper = line.upper()
                if "APPROVED" in line_upper and "NEEDS_REVISION" not in line_upper:
                    return "APPROVED"
                if "ESCALATE" in line_upper:
                    return "ESCALATE_TO_COMMANDER"
                return "NEEDS_REVISION"
        logger.warning(f"[{self.agent_name}] Could not parse status from report — defaulting to NEEDS_REVISION")
        return "NEEDS_REVISION"

    def _apply_revisions(self, context_path: Path, validation_report: str) -> None:
        """
        Apply revised tasks from validation report into context.md.

        Strategy: Extract '### Revised Tasks' section from report,
        append as a '## REVISIONS' section to context.md.
        Workers must prefer REVISIONS over original tasks on conflict.
        """
        # Extract revised tasks section
        revised_section = self._extract_section(validation_report, "Revised Tasks")
        if not revised_section:
            logger.info(f"[{self.agent_name}] No revised tasks found in report — no patch applied")
            return

        original = context_path.read_text(encoding="utf-8")

        patch = (
            "\n\n---\n"
            "## REVISIONS (Expert Override)\n"
            "_Workers: These revisions take precedence over the original tasks above._\n\n"
            + revised_section.strip()
        )

        atomic_write_text(context_path, original + patch, encoding="utf-8")
        logger.info(f"[{self.agent_name}] Patched context.md with Expert revisions")
        st = context_path.parent / "state.json"
        state_data = {}
        if st.exists():
            try:
                with open(st, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
            except (OSError, json.JSONDecodeError):
                pass
        from utils.graphrag_utils import try_ingest_context
        try_ingest_context(context_path, state_data, self.agent_name)

    def _extract_section(self, text: str, section_name: str) -> Optional[str]:
        """Extract content under a '### Section Name' header."""
        import re
        pattern = rf"^### {re.escape(section_name)}\s*\n(.*?)(?=^### |\Z)"
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        return match.group(1).strip() if match else None

    # ===== ABSTRACT IMPLEMENTATIONS =====

    def execute(self, task: str, state_path: Optional[str] = None, **kwargs) -> str:
        """
        Main execution. Defaults to SOLO mode.

        For COPLAN mode, call validate_plan() directly from the orchestrator.

        Args:
            task: Task description or path to state.json
            state_path: Explicit path to state.json (overrides task if given)
            **kwargs: Unused

        Returns:
            Path to generated context.md
        """
        path = state_path or task
        return self.generate_context(path)

    def format_output(self, response: str) -> str:
        """Strip fences and leading noise; keep pure architecture content."""
        if not response:
            return ""

        response = self._strip_markdown_fences(response)

        # Find canonical start marker
        for marker in ("## 1.", "## DIRECTORY", "# DIRECTORY"):
            idx = response.find(marker)
            if idx != -1:
                response = response[idx:]
                break

        return response.strip()


ExpertMimo = Expert


# ===== QUICK TEST =====

if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel
    import tempfile
    import json

    console = Console()

    # Create a temp state.json for testing
    state = {
        "task": "Build a FastAPI service with async PostgreSQL, JWT auth, and rate limiting",
        "requirements": ["Python 3.11", "asyncpg", "jose", "slowapi"],
        "target": "RTX 5080 deployment",
        "complexity": "EXPERT",
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "state.json"
        state_path.write_text(json.dumps(state, indent=2))

        console.print("[bold cyan]Testing Expert SOLO mode...[/bold cyan]")
        expert = Expert(budget_limit_usd=2.0)
        console.print(f"Model: [green]{expert.model_name}[/green]")
        console.print(Panel(repr(expert), title="Agent Info"))
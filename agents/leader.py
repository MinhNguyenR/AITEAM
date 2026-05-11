"""
AI Agentic Framework v6.2 â€” Leader Agents
==========================================
Leader agents: parse state.json â†’ generate context.md for Workers.


Classes:
  - BaseLeader: Abstract base vá»›i shared logic
  - LeaderLow:  DeepSeek-V3.2-Speciale  (LOW  â€” Q&A, skeleton, small fix)
  - LeaderMed:  Kimi-K2.5               (MEDIUM â€” code vá»«a, train AI, CRUD)
  - LeaderHigh: Gemini-3.1-Pro          (HARD  â€” architecture, CUDA, há»‡ thá»‘ng)


context.md format (báº¯t buá»™c):
  ## 1. DIRECTORY STRUCTURE
  ## 2. FILE MAP          â† má»—i file + hÃ m theo format chuáº©n
  ## 3. DATA FLOW
  ## 4. ATOMIC TASKS


Author: Nguyá»…n Äáº·ng TÆ°á»ng Minh
"""


import json
import logging
from pathlib import Path
from typing import Optional


from agents.base_agent import BaseAgent
from agents.support._leader_format import strip_clarification_blocks, trim_to_context_start
from core.config import config
from core.config.constants import STATE_CHAR_LIMIT_DEFAULT, STATE_CHAR_LIMIT_LOW
from core.domain.prompts import (
    LEADER_SYSTEM_PROMPT,
    build_leader_medium_prompt,
    build_leader_low_prompt,
    build_leader_high_prompt,
)
from core.domain.delta_brief import is_no_context
from utils.file_manager import atomic_write_text


logger = logging.getLogger(__name__)


def _truncate_state(state_data: dict, char_limit: int = STATE_CHAR_LIMIT_DEFAULT) -> str:
    """
    Serialize state_data to JSON string, truncate if too large.
    Adds a warning comment so the model knows data was cut.
    """
    raw = json.dumps(state_data, ensure_ascii=False, indent=2)
    if len(raw) <= char_limit:
        return raw
    truncated = raw[:char_limit]
    return truncated + "\n... [TRUNCATED — state too large, key fields shown above]"




class BaseLeader(BaseAgent):
    """
    Abstract base for all Leader agents.


    Pipeline:
      state.json â†’ _build_prompt() â†’ call_api() â†’ format_output() â†’ context.md


    Fail handling:
      - finish_reason=length â†’ raise immediately (don't burn retries)
      - empty content x6 â†’ write NO_CONTEXT sentinel file
      - Any other exception â†’ re-raise to orchestrator
    """


    def __init__(
        self,
        agent_name: str,
        model_name: str,
        max_tokens: int,
        temperature: float,
        budget_limit_usd: Optional[float] = None,
        registry_role_key: Optional[str] = None,
    ):
        super().__init__(
            agent_name=agent_name,
            model_name=model_name,
            system_prompt=LEADER_SYSTEM_PROMPT,
            max_tokens=max_tokens,
            temperature=temperature,
            budget_limit_usd=budget_limit_usd,
            registry_role_key=registry_role_key or agent_name,
        )


    # ===== CORE =====


    def generate_context(self, state_path: str | Path, *, stream_to_monitor: bool = False) -> str:
        """
        Read state.json â†’ LLM â†’ write context.md.


        Returns:
            Path to context.md (may be NO_CONTEXT sentinel on total failure)
        """
        state_path = Path(state_path)


        if not state_path.exists():
            raise FileNotFoundError(f"State file not found: {state_path}")


        # Phase 1: Reading state.json
        try:
            from core.runtime import session as _ws
            _ws.set_leader_action("reading state.json")
            _ws.set_leader_substate("reading", "state.json")
        except Exception:
            pass


        with open(state_path, "r", encoding="utf-8") as f:
            state_data = json.load(f)


        logger.info(f"[{self.agent_name}] Loaded state: {state_path}")


        # Phase 2: Thinking (LLM generation)
        try:
            from core.runtime import session as _ws
            _ws.clear_leader_action()
            _ws.set_leader_substate("thinking")
        except Exception:
            pass


        user_prompt = self._build_prompt(state_data)
        logger.debug(f"[{self.agent_name}] Prompt size: {len(user_prompt)} chars")


        try:
            if stream_to_monitor:
                response = self.call_api_stream(user_prompt)
            else:
                response = self.call_api(user_prompt)
        except ValueError as e:
            # finish_reason=length or all retries empty
            logger.error(f"[{self.agent_name}] call_api failed: {e}")
            try:
                from core.runtime import session as _ws
                _ws.clear_leader_substate()
            except Exception:
                pass
            return self._write_no_context(state_path, reason=str(e))
        except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
            logger.error(f"[{self.agent_name}] Unexpected error: {e}")
            try:
                from core.runtime import session as _ws
                _ws.clear_leader_substate()
            except Exception:
                pass
            raise


        context_content = self.format_output(response)


        if not context_content.strip():
            try:
                from core.runtime import session as _ws
                _ws.clear_leader_substate()
            except Exception:
                pass
            return self._write_no_context(state_path, reason="format_output returned empty")


        # Phase 3: Writing context.md
        try:
            from core.runtime import session as _ws
            _ws.set_leader_substate("writing", "context.md")
        except Exception:
            pass


        context_path = state_path.parent / "context.md"
        atomic_write_text(context_path, context_content, encoding="utf-8")
        logger.info(
            f"[{self.agent_name}] context.md written "
            f"({len(context_content)} chars) â†’ {context_path}"
        )


        try:
            from core.runtime import session as _ws
            _ws.clear_leader_substate()
        except Exception:
            pass


        self.save_knowledge(
            title=f"Context plan â€” {self.agent_name}",
            content=context_content,
            tags=["context", "plan", self.agent_name.lower()],
        )
        self.log_action(
            decision="Generated architecture plan",
            action=f"Wrote context.md ({len(context_content)} chars)",
            cost=self.session_cost,
        )


        from utils.graphrag_utils import try_ingest_context, try_ingest_prompt_doc
        try_ingest_context(context_path, state_data, self.agent_name)
        try_ingest_prompt_doc(
            str(state_data.get("task_uuid") or ""),
            self.agent_name,
            "generate_context",
            user_prompt[:8000],
            context_content[:8000],
        )


        return str(context_path)


    def _write_no_context(self, state_path: Path, reason: str) -> str:
        """
        Write NO_CONTEXT sentinel when generation totally fails.
        Orchestrator checks this and can retry or escalate.
        """
        sentinel = state_path.parent / "context.md"
        content = (
            "# NO_CONTEXT\n\n"
            f"**Agent:** {self.agent_name}\n"
            f"**Reason:** {reason}\n\n"
            "_Failure sentinel. Orchestrator should retry or escalate._\n"
        )
        atomic_write_text(sentinel, content, encoding="utf-8")
        logger.warning(f"[{self.agent_name}] Wrote NO_CONTEXT sentinel â†’ {sentinel}")
        self.log_action(
            decision="Context generation failed",
            action=f"NO_CONTEXT: {reason[:120]}",
            cost=self.session_cost,
        )
        return str(sentinel)


    def _build_prompt(self, state_data: dict) -> str:
        """
        Default prompt for MEDIUM/base tier.
        LeaderLow and LeaderHigh override this.
        """
        state_str = _truncate_state(state_data)
        return build_leader_medium_prompt(state_str)


    # ===== ABSTRACT IMPLEMENTATIONS =====


    def execute(self, task: str, state_path: Optional[str] = None, **kwargs) -> str:
        path = state_path or task
        return self.generate_context(path)


    def format_output(self, response: str) -> str:
        """Strip fences, trim noise before the H1 title or first section."""
        if not response:
            return ""


        # 1. Strip markdown fences
        response = self._strip_markdown_fences(response).strip()
        if not response:
            return ""


        backup = response


        response = strip_clarification_blocks(response)


        # 3. If cleaning made it empty, the model might have wrapped EVERYTHING in tags.
        # Restore backup to avoid failing with NO_CONTEXT.
        if not response:
            response = backup


        return trim_to_context_start(response)


    @staticmethod
    def is_no_context(context_path: str | Path) -> bool:
        """Check if a context.md is a NO_CONTEXT sentinel."""
        return is_no_context(context_path)




# ===== CONCRETE LEADERS =====


class LeaderLow(BaseLeader):
    """
    LOW tier â€” DeepSeek-V3.2-Speciale.
    Tasks: Q&A, concept explanation, code skeleton, small bug fix, simple functions.
    Lighter prompt â€” fewer tasks, smaller state window.
    """


    def __init__(self, **kwargs):
        cfg = config.get_worker("LEADER_LOW")
        super().__init__(
            agent_name="LEADER_LOW",
            model_name=cfg["model"],
            max_tokens=cfg["max_tokens"],
            temperature=cfg["temperature"],
            **kwargs,
        )


    def _build_prompt(self, state_data: dict) -> str:
        state_str = _truncate_state(state_data, char_limit=STATE_CHAR_LIMIT_LOW)
        return build_leader_low_prompt(state_str)




class LeaderMed(BaseLeader):
    """
    MEDIUM tier â€” Kimi-K2.5.
    Tasks: Feature dev, CRUD, REST API, web logic, moderate AI training tasks.
    Uses default _build_prompt().
    """


    def __init__(self, **kwargs):
        cfg = config.get_worker("LEADER_MEDIUM")
        super().__init__(
            agent_name="LEADER_MEDIUM",
            model_name=cfg["model"],
            max_tokens=cfg["max_tokens"],
            temperature=cfg["temperature"],
            **kwargs,
        )




class LeaderHigh(BaseLeader):
    """
    HARD tier â€” Gemini-3.1-Pro.
    Tasks: System architecture, CUDA, hardware-bound, distributed systems.
    Extended prompt with Risk Register section.
    """


    def __init__(self, **kwargs):
        cfg = config.get_worker("LEADER_HIGH")
        super().__init__(
            agent_name="LEADER_HIGH",
            model_name=cfg["model"],
            max_tokens=cfg["max_tokens"],
            temperature=cfg["temperature"],
            **kwargs,
        )


    def _build_prompt(self, state_data: dict) -> str:
        state_str = _truncate_state(state_data)
        return build_leader_high_prompt(state_str)

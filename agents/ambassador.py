"""
Ambassador Agent - Phase 0
==========================
Input Parser & Task Router for Multi-Agent System v6.2
Author: Nguyá»…n Äáº·ng TÆ°á»ng Minh
Hardware Target: RTX 5080 (16GB VRAM)
"""


import json
import logging
import re
from typing import Optional, Dict, Any


logger = logging.getLogger(__name__)


from core.bootstrap import ensure_project_root


ensure_project_root()




from core.config import config
from core.domain.routing_map import selected_leader_for_tier
from core.domain.prompts import AMBASSADOR_SYSTEM_PROMPT
from utils.tracker import append_usage_log, compute_cost_usd
from agents.base_agent import BaseAgent
from core.domain.delta_brief import DeltaBrief
from utils.input_validator import validate_user_prompt
from utils.json_utils import parse_json_resilient, strip_markdown_fences





from .support._ambassador_classify import (
    _extract_vram as _extract_vram_impl,
    _detect_language as _detect_language_impl,
    _classify_tier_fallback as _classify_tier_fallback_impl,
    _apply_tier_upgrade_rules as _apply_tier_upgrade_rules_impl,
    _is_restore_request as _is_restore_request_impl,
)


class Ambassador(BaseAgent):
    """
    Phase 0 Agent: Parses user input â†’ classifies tier â†’ routes to appropriate agent.


    Inherits from BaseAgent with:
    - OpenRouter API integration
    - Budget guard, retry logic
    - Knowledge retrieval
    - Session logging
    """


    def __init__(self, budget_limit_usd: Optional[float] = None):
        """Initialize Ambassador with its own registry model (gpt-5.4-nano)."""
        cfg = config.get_worker("AMBASSADOR")
        super().__init__(
            agent_name="Ambassador",
            model_name=cfg["model"],        # openai/gpt-5.4-nano â€” NOT tier model
            system_prompt=AMBASSADOR_SYSTEM_PROMPT,
            max_tokens=cfg["max_tokens"],   # 300
            temperature=cfg["temperature"], # 0.1
            budget_limit_usd=budget_limit_usd,
            registry_role_key="AMBASSADOR",
        )
        self.last_usage_event: Dict[str, Any] = {}


    # ----- lightweight helpers -----


    _extract_vram = staticmethod(_extract_vram_impl)
    _detect_language = staticmethod(_detect_language_impl)
    _classify_tier_fallback = staticmethod(_classify_tier_fallback_impl)

    # ----- helpers -----

    def _call_parse_api(self, user_input: str) -> Dict[str, Any]:
        """Call the API and return the parsed LLM dict. Raises on any failure."""
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": AMBASSADOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"},
            extra_headers={"X-OpenRouter-Cache": "true", "X-OpenRouter-Cache-TTL": "300"},
        )
        usage = getattr(resp, "usage", None)
        p_tok = int(getattr(usage, "prompt_tokens", 0) or 0)
        c_tok = int(getattr(usage, "completion_tokens", 0) or 0)
        if p_tok or c_tok:
            evt: Dict[str, Any] = {
                "agent": "Ambassador",
                "model": self.model_name,
                "prompt_tokens": p_tok,
                "completion_tokens": c_tok,
                "total_tokens": p_tok + c_tok,
            }
            evt["cost_usd"] = compute_cost_usd(evt)
            append_usage_log(evt)
            self.last_usage_event = evt
            try:
                from utils.logger import workflow_event as _wfe
                _wfe("ambassador", "usage",
                     f"model={self.model_name} prompt_tokens={p_tok} completion_tokens={c_tok}")
                from core.runtime import session as _ws
                _ws.set_stream_prompt_tokens(p_tok)
                _ws.set_stream_completion_tokens(c_tok)
            except Exception:
                pass
        content = resp.choices[0].message.content
        if not content:
            raise ValueError("API returned empty content")
        return parse_json_resilient(strip_markdown_fences(content.strip()))


    _apply_tier_upgrade_rules = staticmethod(_apply_tier_upgrade_rules_impl)
    _is_restore_request = staticmethod(_is_restore_request_impl)


    def _build_delta_brief(
        self,
        user_input: str,
        llm: Dict[str, Any],
        vram: Optional[float],
        lang: str,
    ) -> DeltaBrief:
        """Build a DeltaBrief from parsed LLM response dict."""
        tier = llm.get("tier", self._classify_tier_fallback(user_input)).upper()
        is_cuda = bool(llm.get("is_cuda_required", False))
        complexity = float(llm.get("complexity_score", 0.5))
        is_hw = bool(llm.get("is_hardware_bound", False))
        tier = self._apply_tier_upgrade_rules(tier, is_cuda, complexity, is_hw)
        params = dict(llm.get("parameters", {}) or {})
        if self._is_restore_request(user_input):
            params["fast_path"] = "restore"
        return DeltaBrief(
            original_prompt=user_input,
            summary=llm.get("summary", user_input[:100]),
            tier=tier,
            target_model=config.get_model_for_tier(tier),
            selected_leader=selected_leader_for_tier(tier),
            intent=llm.get("intent", "agent"),
            is_cuda_required=is_cuda,
            estimated_vram_usage=llm.get("estimated_vram_usage") or vram,
            is_hardware_bound=is_hw,
            parameters=params,
            language_detected=llm.get("language_detected", lang),
            complexity_score=complexity,
        )


    def _build_fallback_delta_brief(self, user_input: str, vram: Optional[float], lang: str) -> DeltaBrief:
        """Build a DeltaBrief using rule-based fallback (no API)."""
        tier = self._classify_tier_fallback(user_input)
        is_cuda = bool(re.search(r"cuda|gpu|kernel", user_input, re.IGNORECASE))
        is_hw = bool(re.search(r"vram|memory|rtx|hardware", user_input, re.IGNORECASE))
        complexity = {"LOW": 0.3, "MEDIUM": 0.6, "HARD": 0.9}.get(tier, 0.5)
        tier = self._apply_tier_upgrade_rules(tier, is_cuda, complexity, is_hw)
        params = {"fast_path": "restore"} if self._is_restore_request(user_input) else {}
        return DeltaBrief(
            original_prompt=user_input,
            summary=user_input[:100],
            tier=tier,
            target_model=config.get_model_for_tier(tier),
            selected_leader=selected_leader_for_tier(tier),
            is_cuda_required=is_cuda,
            estimated_vram_usage=vram,
            is_hardware_bound=is_hw,
            parameters=params,
            language_detected=lang,
            complexity_score=complexity,
        )


    # ----- core -----


    def parse(self, user_input: str) -> DeltaBrief:
        """Parse user input â†’ DeltaBrief with tier + model from config."""
        user_input = validate_user_prompt(user_input)
        vram = self._extract_vram(user_input)
        lang = self._detect_language(user_input)


        # Phase 1: Reading user input
        try:
            from core.runtime import session as _ws
            _ws.set_ambassador_substate("reading", "User input")
            _ws.clear_leader_stream_buffer()
        except Exception:
            pass


        # Phase 2: Thinking (LLM call)
        try:
            from core.runtime import session as _ws
            _ws.set_ambassador_substate("thinking")
            _ws.append_leader_stream_chunk(f"Analyzing: {user_input[:120]}â€¦")
        except Exception:
            pass


        try:
            llm = self._call_parse_api(user_input)
            brief = self._build_delta_brief(user_input, llm, vram, lang)
        except (OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError) as e:
            logger.warning("[Ambassador] API error: %s â€” using fallback", e)
            brief = self._build_fallback_delta_brief(user_input, vram, lang)


        # Phase 3: Writing routing decision
        try:
            from core.runtime import session as _ws
            _ws.set_ambassador_substate("writing", "state.json")
            _ws.clear_leader_stream_buffer()
            _lines = [
                f"tier: {brief.tier}",
                f"model: {brief.target_model}",
                f"leader: {brief.selected_leader}",
                f"summary: {brief.summary[:180]}",
                f"language: {brief.language_detected}  complexity: {brief.complexity_score:.2f}",
            ]
            _ws.append_leader_stream_chunk("\n".join(_lines))
        except Exception:
            pass


        try:
            from utils.graphrag_utils import try_ingest_prompt_doc
            try_ingest_prompt_doc(
                str(brief.task_uuid),
                "Ambassador",
                "parse",
                user_input[:2000],
                json.dumps({"tier": brief.tier, "summary": brief.summary, "model": brief.target_model}, ensure_ascii=False),
            )
        except (OSError, json.JSONDecodeError, ValueError, TypeError, RuntimeError) as e:
            logger.debug("[Ambassador] GraphRAG ingest skipped: %s", type(e).__name__)
        return brief


    def parse_to_dict(self, user_input: str) -> Dict[str, Any]:
        return self.parse(user_input).model_dump()


    @staticmethod
    def get_tier_info(tier: str) -> Dict[str, str]:
        """Get tier description and model from config."""
        tier = tier.upper()
        return {
            "tier": tier,
            "model": config.get_model_for_tier(tier),
            "description": {
                "LOW": "Q&A, explanation, docs, small fixes",
                "MEDIUM": "Feature writing, CRUD, web logic",
                "HARD": "System architecture, high-complexity reasoning, CUDA, kernel, or hardware-bound work",
            }.get(tier, ""),
        }




    def execute(self, task: str, **kwargs) -> str:
        """
        Main execution logic for Ambassador:
        1. Parse user input â†’ DeltaBrief (with 3-tier classification)
        2. Apply auto-upgrade rules (CUDA or high complexity â†’ HARD)
        3. Return JSON routing decision for orchestrator
        """
        # Parse input using existing parse() method
        brief = self.parse(task)


        # Get selected_leader from DeltaBrief (already computed in parse)
        selected_route = brief.selected_leader


        # Determine escalation (only for HARD tier)
        is_escalated = (brief.tier == "HARD")


        # Build scope (file patterns from language detection)
        scope = []
        if brief.language_detected not in ("unknown", "natural"):
            ext_map = {
                "python": ".py",
                "cuda": ".cu",
                "cpp": ".cpp",
                "javascript": ".js",
                "rust": ".rs",
            }
            ext = ext_map.get(brief.language_detected, f".{brief.language_detected}")
            scope = [f"*{ext}"]


        # Build constraints from brief
        constraints = []
        if brief.is_cuda_required:
            constraints.append("CUDA required")
        if brief.estimated_vram_usage:
            constraints.append(f"VRAM: {brief.estimated_vram_usage}")
        if brief.is_hardware_bound:
            constraints.append("Hardware-bound optimization")


        # Construct output JSON
        output = {
            "task_id": brief.task_uuid,
            "difficulty": brief.tier,
            "selected_route": selected_route,
            "is_escalated": is_escalated,
            "brief": {
                "intent": brief.summary,
                "scope": scope,
                "constraints": constraints,
            },
            "next_step": "CREATE_CONTEXT_MD",
        }


        # Log action
        self.log_action(
            decision=f"Routed task to {selected_route} (tier: {brief.tier})",
            action="Ambassador routing completed",
            cost=self.session_cost,
        )


        # Return JSON string
        return json.dumps(output, indent=2)


    def format_output(self, response: str) -> str:
        """
        Post-process Ambassador output.
        Expected: Clean JSON string without markdown fences.
        """
        # Remove any markdown fences that might wrap JSON
        cleaned = self._strip_markdown_fences(response)
        # Remove greetings
        cleaned = self._remove_greetings(cleaned)
        # Ensure it's valid JSON (parse and re-serialize for consistency)
        try:
            parsed = json.loads(cleaned)
            return json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            # If not valid JSON, return as-is (orchestrator will handle error)
            return cleaned




# Quick test
if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel


    console = Console()
    ambassador = Ambassador(budget_limit_usd=1.0)  # Test with $1 budget
    console.print("[bold green]âœ“ Ambassador initialized[/bold green]")


    for test in [
        "Explain Python decorators",
        "Write a CUDA kernel for matrix multiplication on RTX 5080 16GB",
        "Create a FastAPI endpoint with PostgreSQL",
    ]:
        console.print(f"\n[bold cyan]Input:[/bold cyan] {test}")
        result = ambassador.execute(test)
        console.print(Panel(
            result,
            title="[bold]Routing Output[/bold]",
            border_style="green",
        ))

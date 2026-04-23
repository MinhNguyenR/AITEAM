"""
Ambassador Agent - Phase 0
==========================
Input Parser & Task Router for Multi-Agent System v6.2
Author: Nguyễn Đặng Tường Minh
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


class Ambassador(BaseAgent):
    """
    Phase 0 Agent: Parses user input → classifies tier → routes to appropriate agent.

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
            model_name=cfg["model"],        # openai/gpt-5.4-nano — NOT tier model
            system_prompt=AMBASSADOR_SYSTEM_PROMPT,
            max_tokens=cfg["max_tokens"],   # 300
            temperature=cfg["temperature"], # 0.1
            budget_limit_usd=budget_limit_usd,
            registry_role_key="AMBASSADOR",
        )
        self.last_usage_event: Dict[str, Any] = {}

    # ----- lightweight helpers -----

    @staticmethod
    def _extract_vram(text: str) -> Optional[str]:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(GB|MB)", text, re.IGNORECASE)
        return f"{m.group(1)}{m.group(2)}" if m else None

    @staticmethod
    def _detect_language(text: str) -> str:
        patterns = {
            "cuda": r"\b(cuda|__global__|__device__|threadIdx)\b",
            "python": r"\b(python|def\s+\w+|import\s+\w+)\b",
            "cpp": r"\b(c\+\+|cpp|#include|std::)\b",
            "javascript": r"\b(const\s+\w+=|console\.log)\b",
            "rust": r"\b(fn\s+\w+|let\s+mut)\b",
        }
        for lang, pat in patterns.items():
            if re.search(pat, text, re.IGNORECASE):
                return lang
        return "natural"

    @staticmethod
    def _classify_tier_fallback(text: str) -> str:
        """
        Rule-based fallback classification (4 tiers).
        Used when Ambassador API is unavailable (rate limit, timeout, etc).
        Supports both English and Vietnamese keywords.
        """
        t = text.lower()

        # HARD: CUDA, kernel, hardware-bound
        hard_kw = (
            "cuda", "kernel", "vram", "tensor core", "multi-gpu", "nccl", "nvlink",
            "gpu computing", "parallel computing", "sm_90", "tensor cores",
            "rtx", "low-level", "assembly", "write kernel", "memory bound",
            "gpu memory", "warp", "threadidx", "blockidx", "__global__",
        )
        if any(kw in t for kw in hard_kw):
            return "HARD"

        # EXPERT: Complex system design, multi-file architecture
        expert_kw = (
            "system design", "architecture", "distributed", "microservice",
            "theorem", "proof", "numerical", "statistical",
            "backpropagation", "loss function", "convergence",
            "derive", "prove", "thiết kế hệ thống", "kiến trúc",
            "multi-agent", "orchestrat", "pipeline phức",
        )
        if any(kw in t for kw in expert_kw):
            return "EXPERT"

        # MEDIUM: Feature implementation, AI/ML tasks, CRUD, web
        medium_kw = (
            # English
            "write", "create", "implement", "build", "develop", "code",
            "function", "class", "endpoint", "api", "database", "crud",
            "fastapi", "flask", "django", "rest", "sql", "orm",
            "train", "fine-tune", "finetune", "embedding", "vector",
            "rag", "retrieval", "langchain", "llm", "chatbot", "agent",
            "scrape", "parse", "pipeline", "workflow", "integration",
            "machine learning", "deep learning", "neural", "transformer",
            "attention", "gradient", "matrix", "tensor", "model",
            # Vietnamese
            "tạo", "viết", "xây dựng", "lập trình", "thiết kế",
            "huấn luyện", "nhúng", "truy xuất", "mô hình",
            "học máy", "mạng nơ-ron", "phân loại", "dự đoán",
        )
        if any(kw in t for kw in medium_kw):
            return "MEDIUM"

        # LOW: Q&A, explanation, concept
        qa_kw = (
            "what", "why", "how", "explain", "define", "meaning", "purpose",
            "what is", "what are", "?",
            "vì sao", "là gì", "như thế nào", "tại sao", "giải thích",
            "khái niệm", "định nghĩa",
        )
        if any(kw in t for kw in qa_kw):
            return "LOW"

        # Default: MEDIUM (safer than LOW for ambiguous tasks)
        return "MEDIUM"

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
        content = resp.choices[0].message.content
        if not content:
            raise ValueError("API returned empty content")
        return parse_json_resilient(strip_markdown_fences(content.strip()))

    @staticmethod
    def _apply_tier_upgrade_rules(tier: str, is_cuda: bool, complexity: float, is_hardware_bound: bool) -> str:
        """Apply CUDA and complexity upgrade rules to the initial tier."""
        if is_cuda:
            return "HARD"
        if complexity > 0.8 and not is_hardware_bound:
            return "EXPERT"
        return tier

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
        return DeltaBrief(
            original_prompt=user_input,
            summary=llm.get("summary", user_input[:100]),
            tier=tier,
            target_model=config.get_model_for_tier(tier),
            selected_leader=selected_leader_for_tier(tier),
            is_cuda_required=is_cuda,
            estimated_vram_usage=llm.get("estimated_vram_usage") or vram,
            is_hardware_bound=is_hw,
            parameters=llm.get("parameters", {}),
            language_detected=llm.get("language_detected", lang),
            complexity_score=complexity,
        )

    def _build_fallback_delta_brief(self, user_input: str, vram: Optional[float], lang: str) -> DeltaBrief:
        """Build a DeltaBrief using rule-based fallback (no API)."""
        tier = self._classify_tier_fallback(user_input)
        is_cuda = bool(re.search(r"cuda|gpu|kernel", user_input, re.IGNORECASE))
        is_hw = bool(re.search(r"vram|memory|rtx|hardware", user_input, re.IGNORECASE))
        complexity = {"LOW": 0.3, "MEDIUM": 0.6, "EXPERT": 0.85, "HARD": 0.95}.get(tier, 0.5)
        tier = self._apply_tier_upgrade_rules(tier, is_cuda, complexity, is_hw)
        return DeltaBrief(
            original_prompt=user_input,
            summary=user_input[:100],
            tier=tier,
            target_model=config.get_model_for_tier(tier),
            selected_leader=selected_leader_for_tier(tier),
            is_cuda_required=is_cuda,
            estimated_vram_usage=vram,
            is_hardware_bound=is_hw,
            parameters={},
            language_detected=lang,
            complexity_score=complexity,
        )

    # ----- core -----

    def parse(self, user_input: str) -> DeltaBrief:
        """Parse user input → DeltaBrief with tier + model from config."""
        user_input = validate_user_prompt(user_input)
        vram = self._extract_vram(user_input)
        lang = self._detect_language(user_input)
        try:
            llm = self._call_parse_api(user_input)
            brief = self._build_delta_brief(user_input, llm, vram, lang)
        except (OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError) as e:
            logger.warning("[Ambassador] API error: %s — using fallback", e)
            brief = self._build_fallback_delta_brief(user_input, vram, lang)
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
                "EXPERT": "Complex logic, math, optimization, multi-step reasoning",
                "HARD": "System architecture, CUDA, kernel, hardware-bound",
            }.get(tier, ""),
        }


    def execute(self, task: str, **kwargs) -> str:
        """
        Main execution logic for Ambassador:
        1. Parse user input → DeltaBrief (with 4-tier classification)
        2. Apply auto-upgrade rules (CUDA → HARD, high complexity → EXPERT)
        3. Return JSON routing decision for orchestrator
        """
        # Parse input using existing parse() method
        brief = self.parse(task)

        # Get selected_leader from DeltaBrief (already computed in parse)
        selected_route = brief.selected_leader

        # Determine escalation (only for EXPERT tier)
        is_escalated = (brief.tier == "EXPERT")
        
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
    console.print("[bold green]✓ Ambassador initialized[/bold green]")

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
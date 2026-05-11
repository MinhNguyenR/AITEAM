import json
import logging
import re
from utils.file_manager import paths_for_task
from agents.support._api_client import make_openai_client
from core.config import config as _cfg
from core.config.settings import openrouter_base_url
from core.domain.prompts import build_clarification_qa_prompt

logger = logging.getLogger(__name__)


def is_ambiguous_task(task_text: str) -> bool:
    """Heuristic: does this task need clarification before generation?
    User explicitly requested that the Leader ALWAYS asks for clarification.
    """
    return True


def _strip_fences(text: str) -> str:
    """Remove ```json...``` or ```...``` markdown fences from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?\s*```$", "", text)
    return text.strip()


def generate_clarification_qa(task_text: str, brief, project_root: str) -> list[dict]:
    """Call leader model to generate clarification questions based on actual state.json.
    Returns [] on failure or when no clarification is needed -- no fallback.
    """
    try:
        key   = "LEADER_MEDIUM"
        wcfg  = _cfg.get_worker(key) or {}
        model = str(wcfg.get("model") or getattr(_cfg, "ASK_CHAT_STANDARD_MODEL", ""))
        if not model:
            raise ValueError("no model configured")

        state_str = "(Không có state.json)"
        if getattr(brief, 'task_uuid', None):
            state_path = paths_for_task(brief.task_uuid).state_path
            if state_path.exists():
                with open(state_path, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
                state_str = json.dumps(state_data, ensure_ascii=False, indent=2)[:3000]

        system = build_clarification_qa_prompt()
        user_msg = (
            f"Task: {task_text}\n"
            f"Tier: {getattr(brief, 'tier', 'MEDIUM')}\n\n"
            f"Project State:\n{state_str}\n\n"
            "OUTPUT: a JSON array only. No explanation. No markdown. Just the array."
        )

        client = make_openai_client(_cfg.api_key, openrouter_base_url())
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=1500,
            temperature=0.3,
            response_format={"type": "json_object"},
            extra_body={"reasoning": {"effort": "medium"}},
        )
        raw = _strip_fences(resp.choices[0].message.content or "")

        if not raw or raw == "[]":
            return []

        # response_format=json_object forces a wrapper object -- unwrap it
        if raw.startswith("{"):
            obj = json.loads(raw)
            # Try known wrapper keys first
            for key in ("questions", "clarifications", "items", "data", "result", "output"):
                if isinstance(obj.get(key), list):
                    raw = json.dumps(obj[key])
                    break
            else:
                # Dict with question/options directly (single question)
                if obj.get("question"):
                    raw = json.dumps([obj])
                else:
                    # Last resort: find any list value in the object
                    for val in obj.values():
                        if isinstance(val, list) and val:
                            raw = json.dumps(val)
                            break
                    else:
                        return []

        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list) or not data:
            return []

        result = []
        for item in data:
            q    = str(item.get("question") or "").strip()
            opts = item.get("options") or []
            if q and isinstance(opts, list) and opts:
                result.append({"question": q, "options": [str(o) for o in opts]})

        return result

    except Exception as e:
        logger.warning("Clarification generation failed: %s", e)
        return []

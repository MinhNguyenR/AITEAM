import json
import logging
from utils.file_manager import paths_for_task
from agents._api_client import make_openai_client
from core.config import config as _cfg
from core.config.settings import openrouter_base_url
from core.domain.prompts import build_clarification_qa_prompt

logger = logging.getLogger(__name__)

def is_ambiguous_task(task_text: str) -> bool:
    """Heuristic: does this task need clarification before generation?
    User explicitly requested that the Leader ALWAYS asks for clarification.
    """
    return True

def generate_clarification_qa(task_text: str, brief, project_root: str) -> list[dict]:
    """Call leader model to generate a clarification question + options based on actual state.json."""
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
        client = make_openai_client(_cfg.api_key, openrouter_base_url())
        resp   = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": f"Task: {task_text}\\nTier: {getattr(brief, 'tier', 'MEDIUM')}\\n\\nProject State:\\n{state_str}"},
            ],
            max_tokens=250, temperature=0.7,
        )
        raw  = (resp.choices[0].message.content or "").strip()
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data] # fallback
        if not isinstance(data, list):
            raise ValueError("Không trả về list")
        
        # Validate elements
        for item in data:
            if not isinstance(item.get("options"), list) or len(item.get("options")) == 0:
                item["options"] = ["Phương án MVP cơ bản", "Phương án đầy đủ hơn", "Tối ưu hiệu năng ngay từ đầu", "Dễ bảo trì và mở rộng"]
            if not item.get("question"):
                item["question"] = f"Bạn muốn '{task_text[:40]}' cụ thể là gì?"
        
        return data
    except Exception as e:
        logger.warning("Clarification generation failed: %s", e)
        return []

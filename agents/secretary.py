"""Secretary Agent. Runs whitelisted commands, handles fallbacks."""

from __future__ import annotations


import logging
import json
import re
from pathlib import Path
from typing import Optional


from agents.base_agent import BaseAgent
from core.config import config


logger = logging.getLogger(__name__)


SECRETARY_SYSTEM_PROMPT = """\
You are Secretary. Given a task plan, output the exact shell commands to run.


Output format:
--- COMMANDS ---
command_one
command_two
--- END COMMANDS ---


Rules:
- Only output commands, no explanations
- Secretary is terminal-only: do not read or write project files directly.
- No destructive ops (rm -rf, sudo rm, mkfs, format, dd)
- Keep commands fast (<120s each)
- Max 8 commands
"""


SECRETARY_INPUT_ANALYSIS_PROMPT = """\
You are the Secretary input analyst. Read the user's raw request before routing.


Your job:
- Decide whether the request is clear enough for Ambassador routing.
- Ask only when missing information would materially change scope, architecture, files, budget, or acceptance criteria.
- Do not ask implementation trivia. Prefer clear assumptions when safe.
- For broad requests like "code an app", ask for enough product detail to make the next plan useful:
  app type/domain, target users, platform, key screens/workflows, data/storage, auth/backend needs, visual style, and success criteria.
- Prefer 2-3 specific questions over one generic question.
- Options must be concrete product choices, not vague labels like "other" or "custom".


Output JSON only:
{"questions":[{"question":"...","options":["...","...","..."]}]}


Rules:
- Return {"questions":[]} when no clarification is needed.
- Ask as many questions as needed to make the request clear.
- Each question must have 2-5 concrete options.
"""


class Secretary(BaseAgent):
    """Executes validation/setup commands from the Worker's plan."""

    def __init__(self, budget_limit_usd: float = 1.0):
        cfg = config.get_worker("SECRETARY") or {}
        super().__init__(
            agent_name="Secretary",
            model_name=cfg.get("model", "xiaomi/mimo-v2-flash"),
            system_prompt=SECRETARY_SYSTEM_PROMPT,
            max_tokens=cfg.get("max_tokens", 2048),
            temperature=cfg.get("temperature", 0.1),
            budget_limit_usd=budget_limit_usd,
            registry_role_key="SECRETARY",
        )

    def execute_commands(
        self,
        context_path: str | Path,
        tools_path: str | Path | None = None,
        project_root: str | None = None,
        commands: list[str] | None = None,
    ) -> dict:
        """Run commands. If none provided, ask LLM to derive them from context."""
        ctx_path = Path(context_path)
        project_root = project_root or str(ctx_path.parent)
        _ws = self._session()

        # Secretary is terminal-only. Reading context text here is prompt assembly,
        # not a TUI "reading files" phase.
        ctx_text = (
            ctx_path.read_text(encoding="utf-8", errors="replace")
            if ctx_path.exists()
            else ""
        )
        tools_text = ""
        if tools_path:
            tp = Path(tools_path)
            tools_text = (
                tp.read_text(encoding="utf-8", errors="replace") if tp.exists() else ""
            )

        # Derive commands via LLM if not provided
        if not commands:
            user_prompt = (
                f"## Context\n{ctx_text[:3000]}\n\n"
                f"## Tools\n{tools_text[:1500]}\n\n"
                "List validation/setup commands to run after the code changes."
            )
            raw = self.call_api(user_prompt)
            commands = self._parse_commands(raw)

        # Phase 2: Using
        results: list[dict] = []
        normalized_commands: list[str] = []
        for cmd in commands:
            normalized_commands.extend(self._normalize_command(cmd))
        for cmd in normalized_commands[:8]:
            from core.sandbox.policy import is_command_safe

            safe, reason = is_command_safe(cmd)
            if not safe:
                results.append(
                    {"cmd": cmd, "success": False, "output": "BLOCKED: unsafe command"}
                )
                logger.warning(
                    "[Secretary] blocked unsafe command: %s (%s)", cmd, reason
                )
                continue

            self._sub("using", _ws, cmd)
            if _ws:
                try:
                    _ws.set_secretary_substate("using", cmd)
                except Exception:
                    pass

            result = self._run(cmd, project_root, _ws)
            results.append(result)

            # Fallback on failure
            if not result["success"]:
                self._sub("fallback", _ws, cmd)
                fb = self._get_fallback(cmd, result["output"])
                fb_items = self._normalize_command(fb or "")
                fb = fb_items[0] if fb_items else ""
                safe_fb, _ = is_command_safe(fb)
                if fb and safe_fb:
                    self._sub("using", _ws, fb)
                    if _ws:
                        try:
                            _ws.set_secretary_substate("using", fb)
                        except Exception:
                            pass
                    results.append(self._run(fb, project_root, _ws))

        self._clear(_ws)
        return {"commands_run": results}

    def analyze_input(
        self, task_text: str, project_root: str | None = None
    ) -> list[dict]:
        """Analyze raw user input and return clarification questions for the TUI gate."""
        _ws = self._session()
        self._sub("asking", _ws, "analyzing input")
        prompt = (
            f"Project root: {project_root or ''}\n\n"
            f"User request:\n{str(task_text or '').strip()}\n\n"
            "Return JSON only."
        )
        try:
            raw = self.call_api(
                prompt,
                max_tokens=900,
                temperature=0.2,
                system_prompt=SECRETARY_INPUT_ANALYSIS_PROMPT,
            )
            questions = self._parse_questions(raw)
            if questions:
                self._sub("asking", _ws, f"{len(questions)} question(s)")
            return questions
        except Exception as exc:
            logger.warning("[Secretary] input analysis skipped: %s", exc)
            return []
        finally:
            try:
                from utils.graphrag_utils import try_ingest_prompt_doc

                try_ingest_prompt_doc(
                    "preflight",
                    "Secretary",
                    "input_analysis",
                    str(task_text or "")[:2000],
                    "clarification analysis completed",
                )
            except Exception:
                pass

    @staticmethod
    def should_redirect_to_ask(task_text: str) -> bool:
        text = str(task_text or "").strip().lower()
        if not text:
            return False
        greeting = {"hi", "hello", "hey", "xin chào", "chào", "chao", "alo"}
        if text in greeting:
            return True
        build_words = (
            "code",
            "build",
            "create",
            "make",
            "fix",
            "implement",
            "write",
            "sửa",
            "tạo",
            "viết",
            "làm",
            "xây",
            "app",
            "web",
            "api",
            "file",
        )
        if any(word in text for word in build_words):
            return False
        question_markers = (
            "?",
            "là gì",
            "như nào",
            "how ",
            "what ",
            "why ",
            "explain",
            "giải thích",
        )
        return any(marker in text for marker in question_markers)

    # Helpers

    def _session(self):
        try:
            from core.runtime import session as ws

            return ws
        except Exception:
            return None

    def _sub(self, sub: str, _ws, detail: str = "") -> None:
        if _ws:
            try:
                _ws.set_secretary_substate(sub, detail)
            except Exception:
                pass

    def _clear(self, _ws) -> None:
        if _ws:
            try:
                _ws.clear_secretary_substate()
            except Exception:
                pass

    def _parse_commands(self, raw: str) -> list[str]:
        m = re.search(
            r"--- COMMANDS ---(.*?)(?:--- END COMMANDS ---|$)", raw, re.DOTALL
        )
        if m:
            lines = [ln.strip() for ln in m.group(1).split("\n") if ln.strip()]
        else:
            lines = [
                ln.strip()
                for ln in raw.split("\n")
                if ln.strip() and re.match(r"^[a-zA-Z]", ln.strip())
            ]
        out: list[str] = []
        for line in lines:
            out.extend(Secretary._normalize_command(line))
        return out[:8]

    @staticmethod
    def _normalize_command(cmd: str) -> list[str]:
        """Convert shell-y fallback commands into safe standalone commands."""
        raw = str(cmd or "").strip().strip("`")
        if not raw:
            return []
        raw = re.sub(r"\s+[12]?>\s*\S+", "", raw)
        parts = re.split(r"\s*(?:&&|\|\||;)\s*", raw)
        cleaned: list[str] = []
        for part in parts:
            s = part.strip()
            if not s or s.lower().startswith("echo "):
                continue
            if "|" in s or ">" in s or "<" in s or "`" in s or "$(" in s:
                continue
            cleaned.append(s)
        return cleaned[:4]

    def _parse_questions(self, raw: str) -> list[dict]:
        text = str(raw or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            text = re.sub(r"\n?\s*```$", "", text).strip()
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return []
            try:
                obj = json.loads(match.group(0))
            except json.JSONDecodeError:
                return []
        data = obj.get("questions", obj) if isinstance(obj, dict) else obj
        if not isinstance(data, list):
            return []
        result: list[dict] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question") or "").strip()
            options = item.get("options") or []
            if question and isinstance(options, list) and options:
                result.append(
                    {
                        "question": question,
                        "options": [str(o) for o in options if str(o).strip()],
                    }
                )
        return result

    def _run(self, cmd: str, cwd: str, _ws) -> dict:
        from core.sandbox.executor import run_sandboxed

        result = run_sandboxed(cmd, cwd=cwd, timeout=120, use_project_venv=True)
        out = result.output.strip()
        success = result.success

        if _ws:
            try:
                _ws.push_secretary_command_result(cmd, success, out[:500])
            except Exception:
                pass
        return {"cmd": cmd, "success": success, "output": out[:2000]}

    def _get_fallback(self, failed_cmd: str, error: str) -> Optional[str]:
        try:
            from agents.support._api_client import make_openai_client
            from core.config.settings import openrouter_base_url

            client = make_openai_client(config.api_key, openrouter_base_url())
            resp = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": f"Command failed: `{failed_cmd}`\nError: {error[:400]}\n"
                        "Output ONE corrected shell command (just the command, no explanation):",
                    }
                ],
                max_tokens=80,
                temperature=0.1,
            )
            raw = (resp.choices[0].message.content or "").strip()
            for line in raw.split("\n"):
                line = line.strip().strip("`")
                if line and re.match(r"^[a-zA-Z]", line):
                    return line
        except Exception:
            pass
        return None

    def format_output(self, response: str) -> str:
        return response.strip()

    def execute(self, task: str, **kwargs) -> str:
        return str(self.execute_commands(task))

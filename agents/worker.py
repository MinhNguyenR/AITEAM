"""Worker Agent - reads context.md + source files, implements code changes, validates."""
from __future__ import annotations


import difflib
import json
import logging
import re
from pathlib import Path
from typing import Optional


from agents.base_agent import BaseAgent
from core.config import config


logger = logging.getLogger(__name__)


WORKER_SYSTEM_PROMPT = """\
You are a senior software engineer implementing a precise technical plan.


Input: context.md (architecture + file list) and the current source files.
Output: ALL files that need to change + validation commands.


Output format (STRICT - use exactly these delimiters):


--- FILE: path/to/file.py ---
<complete new file content>
--- END FILE ---


--- FILE: path/to/another.py ---
<complete new file content>
--- END FILE ---


--- COMMANDS ---
pytest tests/test_feature.py
python -m mypy path/to/file.py
--- END COMMANDS ---


Rules:
- Output COMPLETE file content (not diffs)
- Use exact relative paths from project root
- Max 5 validation commands
- For restore/rollback tasks, restore the requested original file content from the project-scoped backup store when available; do not invent replacement code.
- If you need one quick clarification: [ASK]{"question": "..."}[/ASK] before files
"""




class Worker(BaseAgent):
    """Implements code changes from context.md, emits diffs, runs validation commands."""


    def __init__(self, worker_key: str = "WORKER_A", budget_limit_usd: float = 3.0):
        cfg = config.get_worker(worker_key) or config.get_worker("WORKER_A") or {}
        super().__init__(
            agent_name=worker_key,
            model_name=cfg.get("model", "deepseek/deepseek-v3.2"),
            system_prompt=WORKER_SYSTEM_PROMPT,
            max_tokens=cfg.get("max_tokens", 4096),
            temperature=cfg.get("temperature", 0.2),
            budget_limit_usd=budget_limit_usd,
            registry_role_key=worker_key,
        )
        self._worker_key = worker_key


    # Public entry point


    def execute_task(
        self,
        context_path: str | Path,
        tools_path: str | Path | None = None,
        project_root: str | None = None,
        task_uuid: str = "",
        assignment_text: str = "",
        allowed_paths: list[str] | None = None,
    ) -> dict:
        """Full Worker pipeline: read -> think -> write -> use."""
        ctx_path = Path(context_path)
        project_root = project_root or str(ctx_path.parent)
        _ws = self._session()


        # Phase 1: Reading
        self._sub("reading", _ws)
        context_text, tools_text, sources = self._read_inputs(
            ctx_path, tools_path, project_root, _ws, allowed_paths=allowed_paths
        )
        if self._looks_like_restore(context_text, assignment_text):
            restored, errors = self._restore_from_backup(context_text, project_root, task_uuid, _ws, allowed_paths=allowed_paths)
            if restored or errors:
                self._clear(_ws)
                return {"files_written": restored, "commands": [], "commands_run": [], "errors": errors}


        # Phase 2: Thinking
        self._sub("thinking", _ws)
        user_prompt = self._build_prompt(context_text, tools_text, sources, assignment_text)
        raw = self.call_api_stream(user_prompt)


        # Phase 2b: optional ask
        ask_m = re.search(r'\[ASK\](.*?)\[/ASK\]', raw, re.DOTALL)
        if ask_m:
            try:
                q = json.loads(ask_m.group(1)).get("question", "")
                if q:
                    self._sub("asking", _ws)
                    answer = self._ask_leader(q)
                    raw = re.sub(r'\[ASK\].*?\[/ASK\]', '', raw, flags=re.DOTALL).strip()
                    if answer:
                        self._sub("thinking", _ws)
                        follow = user_prompt + f"\n\nAnswer: {answer}\n\nNow generate all files."
                        raw = self.call_api_stream(follow)
            except Exception as e:
                logger.warning("[%s] ask-block parse failed: %s", self.agent_name, e)


        # Phase 3: Writing
        self._sub("writing", _ws)
        files_written, errors = self._write_files(raw, project_root, task_uuid, _ws, allowed_paths=allowed_paths)

        # Phase 4: Using
        commands = self._parse_commands(raw)


        self._clear(_ws)
        return {"files_written": files_written, "commands": commands, "commands_run": [], "errors": errors}

    # Helpers


    def _session(self):
        try:
            from core.runtime import session as ws
            return ws
        except Exception:
            return None


    def _sub(self, substate: str, _ws, detail: str = "") -> None:
        if _ws:
            try:
                _ws.set_worker_substate(self._worker_key, substate, detail)
            except Exception:
                pass


    def _clear(self, _ws) -> None:
        if _ws:
            try:
                _ws.clear_worker_substate(self._worker_key)
            except Exception:
                pass


    def _read_inputs(
        self, ctx_path: Path, tools_path, project_root: str, _ws, *, allowed_paths: list[str] | None = None
    ) -> tuple[str, str, dict[str, str]]:
        ctx_text = ctx_path.read_text(encoding="utf-8", errors="replace") if ctx_path.exists() else ""
        tools_text = ""
        if tools_path:
            tp = Path(tools_path)
            if tp.exists():
                tools_text = tp.read_text(encoding="utf-8", errors="replace")


        for fname in (ctx_path.name, Path(tools_path).name if tools_path else None):
            if fname and _ws:
                try:
                    _ws.push_worker_reading_file(self._worker_key, fname)
                except Exception:
                    pass


        sources: dict[str, str] = {}
        root = Path(project_root)
        allowed = self._normalize_allowed_paths(allowed_paths or [])
        for m in re.finditer(r'`([^`]+\.[a-zA-Z0-9]+)`', ctx_text):
            rel = m.group(1).strip()
            if ('/' in rel or '\\' in rel) and len(rel) < 120:
                p = root / rel
                if p.exists() and p.is_file() and p.stat().st_size < 60_000:
                    try:
                        sources[rel] = p.read_text(encoding="utf-8", errors="replace")
                        if _ws:
                            try:
                                _ws.push_worker_reading_file(self._worker_key, rel)
                            except Exception:
                                pass
                    except OSError:
                        pass
        return ctx_text, tools_text, sources


    def _build_prompt(self, ctx: str, tools: str, sources: dict[str, str], assignment_text: str = "") -> str:
        parts = [f"## Context Plan\n{ctx[:8000]}"]
        if assignment_text:
            parts.append(f"\n## Your Worker Assignment\n{assignment_text[:3000]}\n\nOnly modify files assigned to you.")
        if tools:
            parts.append(f"\n## Tools Available\n{tools[:2000]}")
        if sources:
            parts.append("\n## Current Source Files")
            for path, content in list(sources.items())[:8]:
                parts.append(f"\n### {path}\n```\n{content[:3000]}\n```")
        parts.append("\n\nImplement ALL changes in the context plan. Output every file completely.")
        return "\n".join(parts)


    def _write_files(
        self, raw: str, project_root: str, task_uuid: str, _ws, *, allowed_paths: list[str] | None = None
    ) -> tuple[list[str], list[str]]:
        from core.sandbox._path_guard import resolve_under_project_root

        files_written: list[str] = []
        errors: list[str] = []
        root = Path(project_root).resolve()
        allowed = self._normalize_allowed_paths(allowed_paths or [])

        pattern = re.compile(
            r'--- FILE: (.+?) ---\n(.*?)(?=\n--- FILE: |\n--- COMMANDS ---|--- END FILE ---|$)',
            re.DOTALL,
        )
        for m in pattern.finditer(raw):
            rel = m.group(1).strip()
            new_content = m.group(2).rstrip("\n").strip("\n")
            if not rel or not new_content:
                continue

            abs_path = resolve_under_project_root(root, rel)
            if abs_path is None:
                errors.append(f"{rel}: path rejected (traversal or absolute)")
                logger.warning("[%s] rejected unsafe path: %s", self.agent_name, rel)
                continue

            safe_rel = abs_path.relative_to(root).as_posix()
            if allowed and not self._path_allowed(safe_rel, allowed):
                errors.append(f"{safe_rel}: not assigned to {self._worker_key}")
                logger.warning("[%s] rejected unassigned file: %s", self.agent_name, safe_rel)
                continue

            self._sub("writing", _ws, safe_rel)


            old_content = ""
            existed = abs_path.exists()
            if existed:
                try:
                    old_content = abs_path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    pass


            self._backup(safe_rel, old_content, task_uuid, str(root))


            try:
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                abs_path.write_text(new_content, encoding="utf-8")
                files_written.append(safe_rel)
                status = "UPDATE" if existed else "CREATE"
                self._emit_update(_ws, safe_rel, old_content, new_content, status=status)
                try:
                    from utils.logger import artifact_detail, workflow_event
                    detail = artifact_detail(abs_path, task_id=task_uuid, producer_node=self._worker_key)
                    detail["status"] = status
                    workflow_event("worker", "file_written", detail)
                except Exception:
                    pass
            except OSError as e:
                errors.append(f"{rel}: {e}")
                logger.warning("[%s] write failed %s: %s", self.agent_name, rel, e)


        return files_written, errors

    @staticmethod
    def _looks_like_restore(context_text: str, assignment_text: str = "") -> bool:
        text = f"{context_text}\n{assignment_text}".lower()
        return bool(re.search(r"\b(restore|rollback|revert|undo)\b|khôi\s*phục|hoàn\s*tác", text, re.IGNORECASE))

    def _restore_from_backup(
        self,
        context_text: str,
        project_root: str,
        task_uuid: str,
        _ws,
        *,
        allowed_paths: list[str] | None = None,
    ) -> tuple[list[str], list[str]]:
        from core.storage.code_backup import restore_backup, search_backups

        root = Path(project_root).resolve()
        candidates = self._normalize_allowed_paths(allowed_paths or [])
        if not candidates:
            candidates = [
                m.group(1).strip()
                for m in re.finditer(r'`([^`]+\.[a-zA-Z0-9]+)`', context_text)
                if len(m.group(1).strip()) < 160
            ]
        restored: list[str] = []
        errors: list[str] = []
        for rel in dict.fromkeys(candidates):
            try:
                target = root / rel
                old = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
                hits = search_backups(rel, limit=1, project_root=str(root))
                if not hits:
                    errors.append(f"{rel}: no backup found")
                    continue
                result = restore_backup(int(hits[0]["id"]), str(root))
                safe_rel = str(result.get("file_path") or rel).replace("\\", "/")
                new = (root / safe_rel).read_text(encoding="utf-8", errors="replace")
                self._emit_update(_ws, safe_rel, old, new, status="UPDATE")
                restored.append(safe_rel)
            except Exception as exc:
                errors.append(f"{rel}: {exc}")
        return restored, errors


    @staticmethod
    def _normalize_allowed_paths(paths: list[str]) -> list[str]:
        out: list[str] = []
        for p in paths:
            s = str(p or "").strip().strip("`").replace("\\", "/")
            if s:
                out.append(s)
        return out


    @staticmethod
    def _path_allowed(rel: str, allowed: list[str]) -> bool:
        candidate = rel.replace("\\", "/").strip("/")
        for raw in allowed:
            item = raw.strip("/")
            if not item:
                continue
            if item.endswith("/**") and candidate.startswith(item[:-3].rstrip("/") + "/"):
                return True
            if item.endswith("/*") and candidate.startswith(item[:-2].rstrip("/") + "/"):
                return True
            if candidate == item or candidate.startswith(item.rstrip("/") + "/"):
                return True
        return False


    def _parse_commands(self, raw: str) -> list[str]:
        m = re.search(r'--- COMMANDS ---(.*?)(?:--- END COMMANDS ---|$)', raw, re.DOTALL)
        if not m:
            return []
        return [ln.strip() for ln in m.group(1).split('\n') if ln.strip()][:5]


    def _ask_leader(self, question: str) -> str:
        try:
            from agents.support._api_client import make_openai_client
            from core.config.settings import openrouter_base_url
            leader_key = "LEADER_MEDIUM"
            try:
                from core.runtime import session as ws
                snap = ws.get_pipeline_snapshot()
                leader_key = str(snap.get("brief_selected_leader") or leader_key).upper()
            except Exception:
                pass
            cfg = config.get_worker(leader_key) or config.get_worker("LEADER_MEDIUM") or {}
            model = cfg.get("model", "")
            if not model:
                return ""
            client = make_openai_client(config.api_key, openrouter_base_url())
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a technical lead. Answer briefly (max 150 words)."},
                    {"role": "user", "content": question[:600]},
                ],
                max_tokens=300, temperature=0.2,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            logger.warning("[%s] _ask_leader failed: %s", self.agent_name, e)
            return ""


    def _backup(self, rel: str, content: str, task_uuid: str, project_root: str = "") -> None:
        try:
            from core.storage.code_backup import backup_file
            backup_file(rel, content, task_uuid, project_root=project_root)
        except Exception:
            pass


    def _emit_update(self, _ws, rel: str, old: str, new: str, *, status: str = "UPDATE") -> None:
        try:
            diff_lines = self._build_diff(old, new)
            added = sum(1 for d in diff_lines if d.get("type") == "add")
            removed = sum(1 for d in diff_lines if d.get("type") == "remove")
            if _ws:
                _ws.push_update_diff(
                    rel,
                    added,
                    removed,
                    diff_lines,
                    status=status,
                    role_name=self.agent_name,
                    full_new_content=new,
                    old_content=old,
                )
        except Exception as e:
            logger.debug("[%s] emit_update failed: %s", self.agent_name, e)


    def _build_diff(self, old: str, new: str) -> list[dict]:
        old_lines = old.splitlines() if old else []
        new_lines = new.splitlines()
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm='', n=6))
        result: list[dict] = []
        line_num = 1
        for d in diff[2:]:
            if d.startswith('@@'):
                m = re.search(r'\+(\d+)', d)
                if m:
                    line_num = int(m.group(1))
                continue
            if d.startswith('+'):
                result.append({"num": line_num, "type": "add", "text": d[1:]})
                line_num += 1
            elif d.startswith('-'):
                result.append({"num": None, "type": "remove", "text": d[1:]})
            else:
                result.append({"num": line_num, "type": "ctx", "text": d[1:]})
                line_num += 1
        return result


    def format_output(self, response: str) -> str:
        return response.strip()


    def execute(self, task: str, **kwargs) -> str:
        return str(self.execute_task(task))

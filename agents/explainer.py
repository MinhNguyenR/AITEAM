"""Explainer Agent — explains code (@file) or full codebase (@codebase)."""
from __future__ import annotations

import logging
import difflib
import re
import subprocess
from pathlib import Path
from typing import Optional

from agents.base_agent import BaseAgent
from core.config import config

logger = logging.getLogger(__name__)

EXPLAINER_SYSTEM_PROMPT = """\
You are an expert code explainer and documentation writer.

For @codebase: Write a comprehensive codebase.md covering architecture, components, and data flow.
For @file: Explain the purpose, structure, and key functions of each file.

Output format for codebase.md:
# Codebase Overview
## Directory Tree
## Key Components
## Architecture
## Data Flow
## Getting Started

Be concise but complete. Focus on what each component DOES and how they interact.
"""

_SCAN_IGNORE = "__pycache__|*.pyc|.git|node_modules|.venv|dist|build|*.egg-info"
_CODE_EXTS = {'.py', '.ts', '.js', '.tsx', '.jsx', '.go', '.rs', '.java', '.cpp', '.c', '.cs'}
_COMMENT_PREFIX = {
    ".py": "#",
    ".sh": "#",
    ".ps1": "#",
    ".js": "//",
    ".jsx": "//",
    ".ts": "//",
    ".tsx": "//",
    ".go": "//",
    ".rs": "//",
    ".java": "//",
    ".cpp": "//",
    ".c": "//",
    ".cs": "//",
    ".css": "/*",
    ".html": "<!--",
    ".md": "<!--",
}


class Explainer(BaseAgent):
    """AI Explainer — generates code documentation."""

    def __init__(self, budget_limit_usd: float = 2.0):
        cfg = config.get_worker("EXPLAINER") or {}
        super().__init__(
            agent_name="Explainer",
            model_name=cfg.get("model", "nvidia/nemotron-3-super-120b-a12b"),
            system_prompt=EXPLAINER_SYSTEM_PROMPT,
            max_tokens=cfg.get("max_tokens", 4096),
            temperature=cfg.get("temperature", 0.2),
            budget_limit_usd=budget_limit_usd,
            registry_role_key="EXPLAINER",
        )

    def explain_codebase(self, project_root: str | Path) -> Path:
        """@codebase: scan with tools → LLM → write codebase.md."""
        root = Path(project_root)
        _ws = self._session()

        # Phase 1: Using (scan tools)
        self._sub("using", _ws, "tree")
        scan = self._scan_project(root, _ws)

        # Phase 2: Thinking (LLM)
        self._sub("thinking", _ws)
        user_prompt = f"## Project Scan\n{scan}\n\nWrite a comprehensive codebase.md for this project."
        content = self.call_api_stream(user_prompt)

        # Phase 3: Writing
        self._sub("writing", _ws, "codebase.md")
        out = root / "codebase.md"
        out.write_text(content, encoding="utf-8")
        self._clear(_ws)
        logger.info("[Explainer] codebase.md → %s (%d chars)", out, len(content))
        return out

    def explain_files(self, file_paths: list[str | Path], project_root: str | Path) -> str:
        """@file: read files → LLM → return explanation string."""
        root = Path(project_root)
        _ws = self._session()

        # Phase 1: Reading
        self._sub("reading", _ws)
        parts: list[str] = []
        for fp in file_paths[:12]:
            p = root / fp if not Path(fp).is_absolute() else Path(fp)
            if p.exists():
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                    parts.append(f"### {fp}\n```\n{text[:6000]}\n```")
                    if _ws:
                        try:
                            _ws.set_explainer_substate("reading", str(fp))
                        except Exception:
                            pass
                except OSError:
                    pass

        # Phase 2: Thinking
        self._sub("thinking", _ws)
        prompt = "Explain these files in detail:\n\n" + "\n\n".join(parts)
        content = self.call_api_stream(prompt)

        # Phase 3: Writing (TUI display only, no file output)
        self._sub("writing", _ws)
        self._clear(_ws)
        return content


    def annotate_files(
        self,
        file_paths: list[str | Path],
        project_root: str | Path,
        *,
        task_uuid: str = "explainer",
        display_language: str = "vi",
    ) -> dict:
        """Annotate files in place and emit monitor Update/Create diffs."""
        root = Path(project_root).resolve()
        _ws = self._session()
        changed: list[str] = []
        errors: list[str] = []
        self._sub("reading", _ws, f"{len(file_paths)} file(s)")
        for fp in file_paths[:12]:
            try:
                path = self._resolve_under_root(root, fp)
                if path is None or not path.is_file():
                    errors.append(f"{fp}: not found")
                    continue
                rel = path.relative_to(root).as_posix()
                old = path.read_text(encoding="utf-8", errors="replace")
                if _ws:
                    _ws.set_explainer_substate("reading", rel)
                self._backup(rel, old, task_uuid, str(root))
                self._sub("thinking", _ws, rel)
                new = self._annotate_content(rel, old, path.suffix.lower(), display_language)
                if new.strip() == old.strip():
                    continue
                self._sub("writing", _ws, rel)
                path.write_text(new, encoding="utf-8")
                self._emit_update(_ws, rel, old, new, status="UPDATE")
                changed.append(rel)
            except Exception as exc:
                errors.append(f"{fp}: {exc}")
                logger.warning("[Explainer] annotate failed %s: %s", fp, exc)
        self._clear(_ws)
        return {"files_written": changed, "errors": errors}


    def select_codebase_files(self, project_root: str | Path, limit: int = 12) -> list[str]:
        root = Path(project_root).resolve()
        candidates: list[Path] = []
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in _CODE_EXTS:
                continue
            if any(part in {".git", "__pycache__", "node_modules", ".venv", "venv"} for part in p.parts):
                continue
            try:
                if p.stat().st_size > 80_000:
                    continue
            except OSError:
                continue
            candidates.append(p)
        priority = ("main", "app", "index", "server", "router", "views", "models", "flow", "runner")
        candidates.sort(key=lambda p: (0 if any(x in p.stem.lower() for x in priority) else 1, len(p.parts), p.as_posix()))
        return [p.relative_to(root).as_posix() for p in candidates[: max(1, int(limit))]]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _session(self):
        try:
            from core.runtime import session as ws
            return ws
        except Exception:
            return None

    def _sub(self, sub: str, _ws, detail: str = "") -> None:
        if _ws:
            try:
                _ws.set_explainer_substate(sub, detail)
            except Exception:
                pass

    def _clear(self, _ws) -> None:
        if _ws:
            try:
                _ws.clear_explainer_substate()
            except Exception:
                pass

    @staticmethod
    def _resolve_under_root(root: Path, fp: str | Path) -> Path | None:
        raw = str(fp).strip().lstrip("@")
        if raw == "file":
            return None
        path = Path(raw)
        candidate = path if path.is_absolute() else root / path
        try:
            resolved = candidate.resolve()
            resolved.relative_to(root)
            return resolved
        except (OSError, ValueError):
            return None

    def _annotate_content(self, rel: str, content: str, suffix: str, display_language: str) -> str:
        prefix = _COMMENT_PREFIX.get(suffix, "#")
        lang = "Vietnamese" if str(display_language).lower().startswith("vi") else "English"
        prompt = (
            f"Annotate this source file in {lang}. Return the complete file only. "
            "Only add comments that explain existing code. Do not change, delete, reorder, rename, reformat, "
            "or rewrite any executable code. Preserve every original code line exactly and insert concise "
            "comments immediately before the line being explained.\n\n"
            f"File: {rel}\n```\n{content[:12000]}\n```"
        )
        try:
            raw = self.call_api(prompt, max_tokens=self.max_tokens, temperature=0.1)
            text = self._strip_code_fence(raw)
            if text and len(text.splitlines()) >= max(1, len(content.splitlines()) // 2):
                return text
        except Exception as exc:
            logger.warning("[Explainer] LLM annotation fallback for %s: %s", rel, exc)
        return self._fallback_annotate(content, prefix, display_language)

    @staticmethod
    def _strip_code_fence(raw: str) -> str:
        text = str(raw or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```[A-Za-z0-9_-]*\s*\n?", "", text)
            text = re.sub(r"\n?```$", "", text).strip()
        return text

    @staticmethod
    def _fallback_annotate(content: str, prefix: str, display_language: str) -> str:
        vi = str(display_language).lower().startswith("vi")
        out: list[str] = []
        for idx, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if stripped and not stripped.startswith(("#", "//", "/*", "<!--")):
                msg = f"Giai thich dong {idx}: cau lenh/khai bao ben duoi." if vi else f"Line {idx}: explains the statement below."
                indent = line[: len(line) - len(line.lstrip())]
                if prefix == "<!--":
                    out.append(f"{indent}<!-- {msg} -->")
                elif prefix == "/*":
                    out.append(f"{indent}/* {msg} */")
                else:
                    out.append(f"{indent}{prefix} {msg}")
            out.append(line)
        return "\n".join(out) + ("\n" if content.endswith("\n") else "")

    def _backup(self, rel: str, content: str, task_uuid: str, project_root: str = "") -> None:
        try:
            from core.storage.code_backup import backup_file
            backup_file(rel, content, task_uuid or "explainer", project_root=project_root)
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
        except Exception:
            pass

    @staticmethod
    def _build_diff(old: str, new: str) -> list[dict]:
        old_lines = old.splitlines() if old else []
        new_lines = new.splitlines()
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm="", n=6))
        result: list[dict] = []
        line_num = 1
        for d in diff[2:]:
            if d.startswith("@@"):
                m = re.search(r"\+(\d+)", d)
                if m:
                    line_num = int(m.group(1))
                continue
            if d.startswith("+"):
                result.append({"num": line_num, "type": "add", "text": d[1:]})
                line_num += 1
            elif d.startswith("-"):
                result.append({"num": None, "type": "remove", "text": d[1:]})
            else:
                result.append({"num": line_num, "type": "ctx", "text": d[1:]})
                line_num += 1
        return result

    def _scan_project(self, root: Path, _ws) -> str:
        parts: list[str] = []

        # Tree
        if _ws:
            try:
                _ws.set_explainer_substate("using", "tree")
            except Exception:
                pass
        try:
            res = subprocess.run(
                ["tree", "--gitignore", "-I", _SCAN_IGNORE, "-L", "4"],
                capture_output=True, text=True, cwd=str(root), timeout=15,
            )
            if res.returncode == 0 and res.stdout.strip():
                parts.append(f"## Directory Tree\n{res.stdout[:3000]}")
        except Exception:
            try:
                dirs = sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith('.'))
                files = sorted(p.name for p in root.iterdir() if p.is_file())
                parts.append(f"## Top-level\nDirs: {', '.join(dirs)}\nFiles: {', '.join(files)}")
            except Exception:
                pass

        # File stats
        if _ws:
            try:
                _ws.set_explainer_substate("using", "wc -l")
            except Exception:
                pass
        try:
            ext_counts: dict[str, int] = {}
            total_lines = 0
            for p in root.rglob("*"):
                if (p.is_file() and p.suffix in _CODE_EXTS
                        and '__pycache__' not in p.parts and '.git' not in p.parts
                        and 'node_modules' not in p.parts):
                    try:
                        lines = p.read_text(encoding='utf-8', errors='replace').count('\n')
                        ext_counts[p.suffix] = ext_counts.get(p.suffix, 0) + 1
                        total_lines += lines
                    except OSError:
                        pass
            if ext_counts:
                summary = ", ".join(f"{ext}: {n}" for ext, n in sorted(ext_counts.items()))
                parts.append(f"## File Stats\nTotal lines: {total_lines:,}\nExtensions: {summary}")
        except Exception:
            pass

        return "\n\n".join(parts) or "Project scan unavailable."

    def format_output(self, response: str) -> str:
        return response.strip()

    def execute(self, task: str, **kwargs) -> str:
        return self.explain_files([task], kwargs.get("project_root", "."))

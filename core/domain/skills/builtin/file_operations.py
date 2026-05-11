"""Built-in file operation skills."""

from __future__ import annotations

from pathlib import Path

from .._categories import SkillCategory
from .._registry import SkillSpec, register


def read_file(path: str, start_line: int = 1, end_line: int | None = None) -> str:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(1, int(start_line or 1))
    end = int(end_line) if end_line else len(lines)
    return "\n".join(f"{idx}: {line}" for idx, line in enumerate(lines[start - 1:end], start=start))


def write_file(path: str, content: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return str(p)


def list_directory(path: str, recursive: bool = False, pattern: str = "*") -> list[str]:
    base = Path(path)
    globber = base.rglob if recursive else base.glob
    return [str(p) for p in globber(pattern) if p.exists()]


for spec in (
    SkillSpec("file.read", "Read file", "Read a line-bounded UTF-8 file snippet.", SkillCategory.FILE_OPS, tags=("file", "read"), callable=read_file),
    SkillSpec("file.write", "Write file", "Write UTF-8 content to a file.", SkillCategory.FILE_OPS, tags=("file", "write"), callable=write_file),
    SkillSpec("file.list", "List directory", "List files under a directory.", SkillCategory.FILE_OPS, tags=("file", "list"), callable=list_directory),
):
    try:
        register(spec)
    except ValueError:
        pass


__all__ = ["list_directory", "read_file", "write_file"]

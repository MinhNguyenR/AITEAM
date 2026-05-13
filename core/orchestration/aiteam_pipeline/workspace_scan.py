from __future__ import annotations

from pathlib import Path
from typing import Any

from aiteamruntime.resources.workspace import ResourceManager

CODE_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".html", ".md",
    ".yml", ".yaml", ".toml", ".go", ".rs", ".java", ".c", ".cpp", ".cs",
}
IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build", ".ai-team"}


def scan_workspace(project_root: str | Path, *, limit: int = 500) -> list[dict[str, Any]]:
    root = Path(project_root).resolve()
    out: list[dict[str, Any]] = []
    for path in root.rglob("*"):
        if len(out) >= limit:
            break
        if not path.is_file() or path.suffix.lower() not in CODE_EXTS:
            continue
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if set(Path(rel).parts) & IGNORE_DIRS:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        out.append(
            {
                "path": rel,
                "ext": path.suffix.lower(),
                "size": int(stat.st_size),
                "mtime": float(stat.st_mtime),
                "hash": ResourceManager.file_hash(path),
                "is_code": path.suffix.lower() in CODE_EXTS,
                "is_empty": int(stat.st_size) == 0,
            }
        )
    return out


def write_workspace_memory(project_root: str | Path, *, reason: str = "workspace scan") -> dict[str, str]:
    root = Path(project_root).resolve()
    items = scan_workspace(root)
    tree_lines = ["# Codebase Overview", "", f"Reason: {reason}", "", "## Files"]
    memory_lines = ["# Runtime Memory", "", f"Last scan reason: {reason}", "", "## Workspace Facts"]
    if not items:
        tree_lines.append("- No code files detected.")
        memory_lines.append("- Workspace has no detected code files yet.")
    for item in items:
        marker = "empty" if item["is_empty"] else f"{item['size']} bytes"
        tree_lines.append(f"- `{item['path']}` ({item['ext']}, {marker}, hash `{item['hash'][:12]}`)")
    codebase_path = root / "codebase.md"
    memory_path = root / "memory.md"
    codebase_path.write_text("\n".join(tree_lines) + "\n", encoding="utf-8")
    memory_lines.append(f"- Detected code-like files: {len(items)}")
    memory_lines.append("- Full file inventory is in `codebase.md`.")
    memory_path.write_text("\n".join(memory_lines) + "\n", encoding="utf-8")
    return {"codebase_path": str(codebase_path), "memory_path": str(memory_path), "files": str(len(items))}


__all__ = ["scan_workspace", "write_workspace_memory"]

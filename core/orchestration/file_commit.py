from __future__ import annotations

import json
import os
import py_compile
import shutil
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from aiteamruntime.resources.workspace import resolve_under_root


@dataclass(frozen=True)
class CommitResult:
    ok: bool
    path: str
    status: str
    base_hash: str = ""
    new_hash: str = ""
    backup_id: int = 0
    error: str = ""
    validator: str = ""


def sha256_file(path: str | Path) -> str:
    import hashlib

    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_candidate(path: Path) -> tuple[bool, str, str]:
    suffix = path.suffix.lower()
    try:
        if suffix == ".py":
            py_compile.compile(str(path), doraise=True)
            return True, "python -m py_compile", ""
        if suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
            return True, "json.loads", ""
        if suffix in {".js", ".mjs", ".cjs"} and shutil.which("node"):
            proc = subprocess.run(
                ["node", "--check", str(path)],
                capture_output=True,
                text=True,
                timeout=20,
            )
            ok = proc.returncode == 0
            return ok, "node --check", (proc.stderr or proc.stdout or "").strip()
    except (OSError, SyntaxError, py_compile.PyCompileError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        return False, suffix.lstrip(".") or "validator", str(exc)
    return True, "", ""


def safe_commit_text_file(
    root: str | Path,
    rel_path: str,
    content: str,
    *,
    expected_hash: str = "",
    task_uuid: str = "",
    create_backup: bool = True,
) -> CommitResult:
    try:
        root_path = Path(root).resolve(strict=True)
        target = resolve_under_root(root_path, rel_path, allow_missing_leaf=True)
    except (OSError, ValueError) as exc:
        return CommitResult(False, rel_path, "blocked", error=str(exc) or "path is outside project root")
    try:
        target.relative_to(root_path)
    except ValueError:
        return CommitResult(False, rel_path, "blocked", error="path is outside project root")

    current_hash = sha256_file(target)
    if expected_hash and current_hash != expected_hash:
        return CommitResult(
            False,
            rel_path,
            "conflict",
            base_hash=expected_hash,
            new_hash=current_hash,
            error="file changed since worker read it",
        )

    temp_root = root_path / ".ai-team" / "temp"
    temp_root.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix or ".candidate"
    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=suffix, dir=str(temp_root))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(content)
        ok, validator, error = _validate_candidate(temp_path)
        if not ok:
            return CommitResult(False, rel_path, "validation_error", base_hash=current_hash, error=error, validator=validator)

        latest_hash = sha256_file(target)
        if latest_hash != current_hash:
            return CommitResult(
                False,
                rel_path,
                "conflict",
                base_hash=current_hash,
                new_hash=latest_hash,
                error="file changed during validation",
                validator=validator,
            )
        backup_id = 0
        if create_backup and target.exists() and target.is_file():
            try:
                from core.storage.code_backup import backup_file

                backup_id = backup_file(
                    rel_path,
                    target.read_text(encoding="utf-8", errors="replace"),
                    task_uuid=task_uuid,
                    project_root=str(root_path),
                )
            except (OSError, UnicodeError, sqlite3.Error, ImportError) as exc:
                return CommitResult(False, rel_path, "backup_error", base_hash=current_hash, error=str(exc), validator=validator)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temp_path, target)
        return CommitResult(
            True,
            rel_path,
            "UPDATE" if current_hash else "CREATE",
            base_hash=current_hash,
            new_hash=sha256_file(target),
            backup_id=backup_id,
            validator=validator,
        )
    finally:
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass


__all__ = ["CommitResult", "safe_commit_text_file", "sha256_file"]

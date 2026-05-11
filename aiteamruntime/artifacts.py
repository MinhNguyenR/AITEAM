from __future__ import annotations

from pathlib import Path

_RUN_ARTIFACT_NAMES = {"context.md", "tools.md", "state.json"}


class ArtifactManager:
    def __init__(self, root: str | Path = ".ai-team") -> None:
        self.root = Path(root)

    def run_dir(self, run_id: str) -> Path:
        safe = "".join(ch for ch in str(run_id) if ch.isalnum() or ch in ("-", "_", "."))
        if not safe:
            raise ValueError("run_id is required")
        return self.root / "runs" / safe

    def cleanup_run(self, run_id: str) -> list[Path]:
        run_dir = self.run_dir(run_id).resolve()
        deleted: list[Path] = []
        if not run_dir.exists() or not run_dir.is_dir():
            return deleted
        for name in _RUN_ARTIFACT_NAMES:
            path = (run_dir / name).resolve()
            if path.parent != run_dir or not path.exists() or not path.is_file():
                continue
            path.unlink()
            deleted.append(path)
        return deleted

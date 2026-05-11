"""Auto-discovery for skill modules."""

from __future__ import annotations

import importlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def auto_discover(base_dirs: list[Path] | None = None) -> None:
    root = Path(__file__).resolve().parent
    dirs = base_dirs or [root / "builtin", root / "custom", root / "examples"]
    for base in dirs:
        if not base.exists():
            continue
        pkg = "core.domain.skills." + base.relative_to(root).as_posix().replace("/", ".")
        for file in base.glob("*.py"):
            if file.name.startswith("_") or file.name == "__init__.py":
                continue
            mod_name = f"{pkg}.{file.stem}"
            try:
                importlib.import_module(mod_name)
            except Exception as exc:
                logger.warning("Could not load skill module %s: %s", mod_name, exc)


__all__ = ["auto_discover"]

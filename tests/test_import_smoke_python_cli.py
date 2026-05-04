"""Import every submodule under core.cli.python_cli (guards broken paths after refactors)."""
from __future__ import annotations

import importlib
import pkgutil

import pytest

import core.cli.python_cli as _root


def _all_submodule_names() -> list[str]:
    return sorted({m.name for m in pkgutil.walk_packages(_root.__path__, _root.__name__ + ".")})


@pytest.mark.parametrize("mod_name", _all_submodule_names())
def test_import_python_cli_submodule(mod_name: str) -> None:
    importlib.import_module(mod_name)


def test_python_cli_submodule_count_reasonable() -> None:
    assert len(_all_submodule_names()) >= 80

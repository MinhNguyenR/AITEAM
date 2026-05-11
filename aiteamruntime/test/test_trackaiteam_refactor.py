from __future__ import annotations

import subprocess
import sys

from aiteamruntime.integrations.trackaiteam import (
    DEFAULT_AGENT_LANES,
    WORKER_REGISTRY,
    build_trackaiteam_pipeline,
    model_readiness,
    registry_model_summary,
)
from aiteamruntime.integrations.trackaiteam.planning import normalize_model_plan
from aiteamruntime.integrations.trackaiteam.setup import python_vite_react_project_command


def test_trackaiteam_public_exports_survive_refactor() -> None:
    pipeline = build_trackaiteam_pipeline()
    assert "Ambassador" in DEFAULT_AGENT_LANES
    assert "Worker A" in WORKER_REGISTRY
    assert any(role.agent_id == "Tool Curator" for role in pipeline.roles)
    assert isinstance(model_readiness(), dict)
    assert "AMBASSADOR" in registry_model_summary()


def test_trackaiteam_plan_normalizer_keeps_workers_and_safe_paths() -> None:
    plan = normalize_model_plan(
        "Build React dashboard",
        {
            "reasoning": "split work",
            "work_items": [
                {"title": "unsafe", "files": ["../escape.py"], "depends_on": ["x"], "timeout": 3},
            ],
            "dependencies": ["react"],
        },
        role_key="LEADER_MEDIUM",
    )
    assert len(plan["work_items"]) == len(WORKER_REGISTRY)
    assert plan["work_items"][0]["files"][0].startswith(".aiteamruntime/")
    assert plan["validation_commands"][0]["argv"][0] == sys.executable


def test_secretary_react_scaffold_command_creates_real_files(tmp_path) -> None:
    command = python_vite_react_project_command()
    result = subprocess.run(
        [str(part) for part in command["argv"]],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    for rel_path in command["creates"]:
        assert (tmp_path / rel_path).exists(), rel_path
    assert "vite" in (tmp_path / "package.json").read_text(encoding="utf-8")

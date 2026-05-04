from __future__ import annotations

from unittest.mock import patch

from core.cli.python_cli.workflow.tui.monitor import helpers as mh


def test_registry_key_for_leader_uses_tier_mapping():
    assert mh._registry_key_for_step("leader_generate", "LOW") == "LEADER_MEDIUM"
    assert mh._registry_key_for_step("leader_generate", "MEDIUM") == "LEADER_MEDIUM"
    assert mh._registry_key_for_step("leader_generate", "HARD") == "LEADER_HIGH"


def test_display_name_leader_uses_config_role():
    with patch.object(mh.config, "get_worker", return_value={"role": "Lead Low"}):
        assert mh._display_name("leader_generate", "LOW") == "Lead Low"

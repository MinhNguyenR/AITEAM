"""Tests for core/config/runtime_config.py — RuntimeConfig dataclass."""
from core.config.runtime_config import RuntimeConfig


class TestRuntimeConfig:
    def test_defaults(self):
        rc = RuntimeConfig()
        assert rc.orchestration_tags == {}
        assert rc.event_sink is None
        assert rc.persistence_uri is None
        assert rc.extra == {}

    def test_custom_values(self):
        rc = RuntimeConfig(
            orchestration_tags={"env": "test"},
            event_sink="sink",
            persistence_uri="sqlite:///test.db",
            extra={"key": "val"},
        )
        assert rc.orchestration_tags == {"env": "test"}
        assert rc.event_sink == "sink"
        assert rc.persistence_uri == "sqlite:///test.db"
        assert rc.extra == {"key": "val"}

    def test_independent_instances(self):
        a = RuntimeConfig(extra={"x": 1})
        b = RuntimeConfig(extra={"y": 2})
        assert a.extra != b.extra

    def test_mutable_defaults_are_independent(self):
        a = RuntimeConfig()
        b = RuntimeConfig()
        a.orchestration_tags["k"] = "v"
        assert "k" not in b.orchestration_tags

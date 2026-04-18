from __future__ import annotations

from typing import Any, Dict, Optional

from core.config.service import Config, ConfigError

config = Config()


def get_config() -> Config:
    return config


def get_hardware_info() -> Dict[str, Any]:
    return config.get_system_info()["hardware"]


def get_worker(worker_id: str) -> Optional[Dict[str, Any]]:
    return config.get_worker(worker_id)


def mask_api_key() -> str:
    return config.api_key_masked


__all__ = ["Config", "ConfigError", "config", "get_config", "get_hardware_info", "get_worker", "mask_api_key"]

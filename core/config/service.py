from __future__ import annotations

import platform
import os
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console

from core.config.hardware import build_hardware_string, detect_gpu_info, detect_total_ram_gb
from core.config.pricing import fetch_openrouter_pricing, sync_live_pricing
from core.config.registry import (
    ASK_CHAT_STANDARD_MODEL,
    ASK_CHAT_THINKING_MODEL,
    MODEL_REGISTRY,
    TIER_MODEL_MAP,
    get_model_for_tier,
    get_worker_config,
)
from core.config.settings import mask_api_key, openrouter_api_key, openrouter_base_url, require_openrouter_api_key, load_environment

console = Console()


class ConfigError(Exception):
    pass


class Config:
    _instance: Optional["Config"] = None
    _hardware_scanned: bool = False
    _gpu_name: str = "Unknown"
    _total_vram_gb: float = 0.0
    _total_ram_gb: float = 0.0
    _device: str = "cpu"
    _max_vram_limit: Optional[float] = None
    _pricing_cache: Dict[str, Dict[str, float]] = {}
    _pricing_fetched: bool = False
    BASE_DIR: Path = Path.home() / ".ai-team"
    AITEAM_CACHE_DIR_NAME: str = "aiteam-cache"

    MODEL_REGISTRY = MODEL_REGISTRY
    TIER_MODEL_MAP = TIER_MODEL_MAP
    ASK_CHAT_STANDARD_MODEL = ASK_CHAT_STANDARD_MODEL
    ASK_CHAT_THINKING_MODEL = ASK_CHAT_THINKING_MODEL

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        load_environment(console)
        try:
            require_openrouter_api_key(console)
        except RuntimeError as e:
            raise ConfigError(str(e)) from e
        self._detect_hardware()
        self._apply_user_overrides()
        self._sync_live_pricing()

    def _detect_hardware(self):
        if Config._hardware_scanned:
            return
        Config._hardware_scanned = True
        self._detect_gpu()
        self._detect_ram()
        console.print(
            f"[dim]✓ Hardware detected: {self._gpu_name} | VRAM: {self._total_vram_gb:.1f}GB | RAM: {self._total_ram_gb:.1f}GB[/dim]"
        )

    def _detect_gpu(self):
        device, gpu_name, total_vram_gb = detect_gpu_info()
        Config._device = device
        Config._gpu_name = gpu_name
        Config._total_vram_gb = total_vram_gb
        if device != "cuda":
            console.print("[yellow]⚠ No GPU detected. Running on CPU mode.[/yellow]")

    def _detect_ram(self):
        Config._total_ram_gb = detect_total_ram_gb()

    def _apply_user_overrides(self):
        max_vram = os.getenv("MAX_VRAM_LIMIT")
        if max_vram:
            try:
                Config._max_vram_limit = float(max_vram)
                console.print(f"[dim]✓ User VRAM limit applied: {Config._max_vram_limit:.1f}GB[/dim]")
            except ValueError:
                console.print(f"[yellow]⚠ Invalid MAX_VRAM_LIMIT value: {max_vram}[/yellow]")

    def _sync_live_pricing(self):
        live_prices = self.fetch_openrouter_pricing()
        sync_live_pricing(self.MODEL_REGISTRY, live_prices)

    @property
    def gpu_name(self) -> str:
        return Config._gpu_name

    @property
    def total_vram_gb(self) -> float:
        return Config._max_vram_limit if Config._max_vram_limit is not None else Config._total_vram_gb

    @property
    def total_ram_gb(self) -> float:
        return Config._total_ram_gb

    @property
    def device(self) -> str:
        return Config._device

    @property
    def available_vram_gb(self) -> float:
        return self.total_vram_gb * 0.8

    @property
    def api_key_masked(self) -> str:
        return mask_api_key()

    @property
    def api_key(self) -> str:
        return openrouter_api_key()

    @property
    def cache_root(self) -> Path:
        custom = os.getenv("AI_TEAM_CACHE_ROOT", "").strip()
        if custom:
            return Path(custom).expanduser()
        return self.BASE_DIR / self.AITEAM_CACHE_DIR_NAME

    def get_worker(self, worker_id: str) -> Optional[Dict[str, Any]]:
        cfg = get_worker_config(worker_id)
        if cfg is None:
            return None
        cfg = dict(cfg)
        try:
            from core.cli.state import get_model_overrides
            overrides = get_model_overrides()
            if worker_id.upper() in overrides:
                cfg["model"] = overrides[worker_id.upper()]
                cfg["is_overridden"] = True
            else:
                cfg["is_overridden"] = False
        except (ImportError, OSError, ValueError, TypeError):
            cfg["is_overridden"] = False
        cfg.setdefault("active", True)
        return cfg

    def get_model_for_tier(self, tier: str) -> str:
        return get_model_for_tier(tier)

    def get_fallback_worker(self, failed_worker_id: str) -> str:
        failed = failed_worker_id.upper()
        if failed in ["WORKER_A", "WORKER_B"]:
            return "WORKER_C"
        return "FIX_WORKER"

    def list_workers(self) -> list:
        try:
            from core.cli.state import get_model_overrides, get_prompt_overrides
            model_overrides = get_model_overrides()
            prompt_overrides = get_prompt_overrides()
        except (ImportError, OSError, ValueError, TypeError):
            model_overrides = {}
            prompt_overrides = {}
        result = []
        for wid, cfg in self.MODEL_REGISTRY.items():
            uid = wid.upper()
            prompt_info = prompt_overrides.get(uid, {})
            result.append({
                "id": wid,
                "model": model_overrides.get(uid, cfg["model"]),
                "default_model": cfg["model"],
                "role": cfg["role"],
                "tier": cfg.get("tier", ""),
                "priority": cfg.get("priority", 0),
                "temperature": cfg.get("temperature", 0.7),
                "top_p": cfg.get("top_p", 1.0),
                "max_tokens": cfg.get("max_tokens", 0),
                "pricing": cfg.get("pricing", {}),
                "active": cfg.get("active", True),
                "is_overridden": uid in model_overrides,
                "prompt_status": "overridden" if uid in prompt_overrides else "default",
                "prompt_updated_at": prompt_info.get("updated_at", ""),
            })
        return result

    def list_agents_by_tier(self, tier_level: int) -> list:
        return [{"id": wid, **cfg} for wid, cfg in self.MODEL_REGISTRY.items() if cfg.get("priority") == tier_level]

    def get_pricing_summary(self) -> Dict[str, Any]:
        summary = {}
        for wid, cfg in self.MODEL_REGISTRY.items():
            pricing = cfg.get("pricing", {})
            if pricing.get("per_query"):
                summary[wid] = "per-query"
            elif pricing.get("input") == 0 and pricing.get("output") == 0:
                summary[wid] = "free"
            else:
                summary[wid] = f"${pricing.get('input', 0):.2f}/${pricing.get('output', 0):.2f} per 1M tokens"
        return summary

    def fetch_openrouter_pricing(self, force: bool = False) -> Dict[str, Dict[str, float]]:
        Config._pricing_cache, Config._pricing_fetched = fetch_openrouter_pricing(
            self.api_key, Config._pricing_cache, Config._pricing_fetched, __import__("logging").getLogger(__name__), force=force
        )
        return Config._pricing_cache

    def get_live_pricing(self, model_id: str) -> Dict[str, float]:
        if model_id in self._pricing_cache:
            return self._pricing_cache[model_id]
        for cfg in self.MODEL_REGISTRY.values():
            if cfg.get("model") == model_id:
                return cfg.get("pricing", cfg.get("pricing_fallback", {"input": 0.0, "output": 0.0}))
        return {"input": 0.0, "output": 0.0}

    def get_hardware_string(self) -> str:
        return build_hardware_string(
            platform.system(),
            platform.release(),
            platform.machine(),
            self.total_ram_gb,
            self.device,
            self.gpu_name,
            self.total_vram_gb,
        )

    def get_system_info(self) -> Dict[str, Any]:
        return {
            "hardware": {
                "gpu": self.gpu_name,
                "device": self.device,
                "vram_total_gb": self.total_vram_gb,
                "vram_available_gb": self.available_vram_gb,
                "ram_total_gb": self.total_ram_gb,
                "user_vram_limit": self._max_vram_limit,
            },
            "api": {"key_masked": self.api_key_masked, "base_url": openrouter_base_url()},
            "agents": {"total": len(self.MODEL_REGISTRY), "by_tier": {level: len(self.list_agents_by_tier(level)) for level in range(4)}},
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python_version": platform.python_version(),
                "hardware_string": self.get_hardware_string(),
            },
        }

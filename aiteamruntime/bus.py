"""Compatibility facade for :mod:`aiteamruntime.core.bus`."""

from .core.bus import EventBus, EventSubscription

__all__ = ["EventBus", "EventSubscription"]

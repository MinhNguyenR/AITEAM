"""Compatibility facade for :mod:`aiteamruntime.resources.locks`."""

from .resources.locks import LockBlocked, LockManager, LockRequest

__all__ = ["LockBlocked", "LockManager", "LockRequest"]

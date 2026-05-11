"""Compatibility facade for :mod:`aiteamruntime.core.governor`."""

from .core.governor import GovernorLimits, GovernorState

__all__ = ["GovernorLimits", "GovernorState"]

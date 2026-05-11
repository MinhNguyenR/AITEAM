"""Compatibility facade for :mod:`aiteamruntime.core.contracts`."""

from .core.contracts import AgentContract, SchemaValidator, ValidationResult, dual_payload

__all__ = ["AgentContract", "SchemaValidator", "ValidationResult", "dual_payload"]

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
}


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...] = ()


class SchemaValidator:
    """Small JSON-Schema-compatible subset used by runtime contracts."""

    def validate(self, value: Any, schema: dict[str, Any] | None) -> ValidationResult:
        if not schema:
            return ValidationResult(True)
        errors: list[str] = []
        self._validate_node(value, schema, "$", errors)
        return ValidationResult(not errors, tuple(errors))

    def _validate_node(self, value: Any, schema: dict[str, Any], path: str, errors: list[str]) -> None:
        expected = str(schema.get("type") or "")
        if expected:
            py_type = _TYPE_MAP.get(expected)
            if py_type is not None and not isinstance(value, py_type):
                errors.append(f"{path}: expected {expected}")
                return
        if expected == "object" or isinstance(value, dict):
            if not isinstance(value, dict):
                errors.append(f"{path}: expected object")
                return
            for key in schema.get("required") or []:
                if key not in value:
                    errors.append(f"{path}.{key}: required")
            properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
            for key, child in properties.items():
                if key in value and isinstance(child, dict):
                    self._validate_node(value[key], child, f"{path}.{key}", errors)
        if expected == "array" and isinstance(value, list):
            item_schema = schema.get("items")
            if isinstance(item_schema, dict):
                for index, item in enumerate(value):
                    self._validate_node(item, item_schema, f"{path}[{index}]", errors)


@dataclass(frozen=True)
class AgentContract:
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    version: str = "v1"
    output_kinds: frozenset[str] = field(default_factory=frozenset)
    max_self_repair_attempts: int = 3
    max_secretary_repair_attempts: int = 2

    def should_validate_output(self, kind: str) -> bool:
        return bool(self.output_schema) and (not self.output_kinds or kind in self.output_kinds)


def dual_payload(
    *,
    ui_message: str = "",
    system_command: str = "",
    data: dict[str, Any] | None = None,
    refs: list[dict[str, Any]] | None = None,
    schema_version: str = "v1",
) -> dict[str, Any]:
    return {
        "ui_message": ui_message,
        "system_command": system_command,
        "data": dict(data or {}),
        "refs": list(refs or []),
        "schema_version": schema_version,
    }


__all__ = ["AgentContract", "SchemaValidator", "ValidationResult", "dual_payload"]

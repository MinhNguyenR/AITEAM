"""Utilities to inspect agent coverage, implementation status, and registry consistency."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AgentRecord:
    name: str
    path: str
    classes: list[str]
    functions: list[str]
    has_main_class: bool
    status: str


class AgentAuditStandalone:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.agents_dir = self.root / "agents"

    def inspect(self) -> dict[str, Any]:
        records = self._collect_agents()
        registry_path = self.root / "agents" / "__init__.py"
        registry_exports = self._read_registry_exports(registry_path)
        file_names = {record.name for record in records}
        exported_names = set(registry_exports)

        implemented = [r for r in records if r.status == "implemented"]
        partial = [r for r in records if r.status == "partial"]
        placeholder = [r for r in records if r.status == "placeholder"]

        return {
            "root": str(self.root),
            "agents_dir": str(self.agents_dir),
            "counts": {
                "total_agent_files": len(records),
                "implemented": len(implemented),
                "partial": len(partial),
                "placeholder": len(placeholder),
                "registry_exports": len(registry_exports),
            },
            "implemented_agents": [self._as_dict(r) for r in implemented],
            "partial_agents": [self._as_dict(r) for r in partial],
            "placeholder_agents": [self._as_dict(r) for r in placeholder],
            "registry": {
                "path": str(registry_path),
                "exports": registry_exports,
                "missing_exports": sorted(file_names - exported_names),
                "orphan_exports": sorted(exported_names - file_names),
            },
        }

    def summary_markdown(self) -> str:
        data = self.inspect()
        counts = data["counts"]
        lines = [
            "# Agent Audit Summary",
            "",
            f"- Root: `{data['root']}`",
            f"- Agents dir: `{data['agents_dir']}`",
            f"- Total agent files: {counts['total_agent_files']}",
            f"- Implemented: {counts['implemented']}",
            f"- Partial: {counts['partial']}",
            f"- Placeholder: {counts['placeholder']}",
            f"- Registry exports: {counts['registry_exports']}",
            "",
            "## Implemented Agents",
        ]

        implemented = data["implemented_agents"]
        if implemented:
            for item in implemented:
                lines.append(f"- `{item['name']}` → `{item['path']}`")
        else:
            lines.append("- None")

        lines.extend(["", "## Partial Agents"])
        partial = data["partial_agents"]
        if partial:
            for item in partial:
                lines.append(f"- `{item['name']}` → `{item['path']}`")
        else:
            lines.append("- None")

        lines.extend(["", "## Placeholder Agents"])
        placeholder = data["placeholder_agents"]
        if placeholder:
            for item in placeholder:
                lines.append(f"- `{item['name']}` → `{item['path']}`")
        else:
            lines.append("- None")

        registry = data["registry"]
        lines.extend(["", "## Registry Consistency"])
        if registry["missing_exports"]:
            lines.append("- Missing exports:")
            for name in registry["missing_exports"]:
                lines.append(f"  - `{name}`")
        else:
            lines.append("- Missing exports: none")

        if registry["orphan_exports"]:
            lines.append("- Orphan exports:")
            for name in registry["orphan_exports"]:
                lines.append(f"  - `{name}`")
        else:
            lines.append("- Orphan exports: none")

        return "\n".join(lines) + "\n"

    def export_summary_markdown(self, output_path: str | Path) -> Path:
        output = Path(output_path)
        if not output.is_absolute():
            output = self.root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.summary_markdown(), encoding="utf-8")
        return output

    def _collect_agents(self) -> list[AgentRecord]:
        if not self.agents_dir.exists():
            return []

        records: list[AgentRecord] = []
        for path in sorted(self.agents_dir.glob("*.py")):
            if path.name == "__init__.py":
                continue
            rel_path = path.relative_to(self.root).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
            status = self._classify_status(path.read_text(encoding="utf-8"), classes, functions)
            has_main_class = any(not name.startswith("_") for name in classes)
            records.append(
                AgentRecord(
                    name=path.stem,
                    path=rel_path,
                    classes=classes,
                    functions=functions,
                    has_main_class=has_main_class,
                    status=status,
                )
            )
        return records

    def _read_registry_exports(self, path: Path) -> list[str]:
        if not path.exists():
            return []
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        try:
                            value = ast.literal_eval(node.value)
                        except Exception:
                            return []
                        if isinstance(value, list):
                            return [str(item) for item in value]
        return []

    def _classify_status(self, source: str, classes: list[str], functions: list[str]) -> str:
        stripped = source.strip()
        if not stripped:
            return "placeholder"
        if len(classes) == 0 and len(functions) <= 1:
            return "placeholder"
        if "TODO" in source or "NotImplementedError" in source or "pass\n" in source:
            return "partial"
        if len(classes) >= 1:
            return "implemented"
        return "partial"

    def _as_dict(self, record: AgentRecord) -> dict[str, Any]:
        return {
            "name": record.name,
            "path": record.path,
            "classes": record.classes,
            "functions": record.functions,
            "has_main_class": record.has_main_class,
            "status": record.status,
        }


def build_default_auditor(root: str | Path) -> AgentAuditStandalone:
    return AgentAuditStandalone(root)

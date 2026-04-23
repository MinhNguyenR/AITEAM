# Agent Audit Skill Summary

## Purpose

This skill inspects the `agents/` package and reports implementation coverage and registry consistency.

## Capabilities

- scans all top-level agent modules in `agents/`
- extracts classes and top-level functions using Python AST
- classifies each module as `implemented`, `partial`, or `placeholder`
- compares discovered modules against `agents/__init__.py` exports
- exports a markdown summary for review

## Main Files

- _(removed)_ former `agent_audit_standalone` package
- `docs/skills_admin/AgentAudit/README.md`

## Example Commands

```bash
_(CLI removed — see AgentAudit README.)_
```

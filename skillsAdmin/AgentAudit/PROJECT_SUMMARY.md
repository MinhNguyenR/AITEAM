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

- `agent_audit_standalone/__init__.py`
- `agent_audit_standalone/__main__.py`
- `agent_audit_standalone/cli.py`
- `agent_audit_standalone/indexer.py`
- `skillsAdmin/AgentAudit/README.md`

## Example Commands

```bash
python -m agent_audit_standalone --root . inspect
python -m agent_audit_standalone --root . summary
python -m agent_audit_standalone --root . summary --output skillsAdmin/AgentAudit/AGENT_AUDIT.md
```

"""CLI for the standalone agent audit utility."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_audit_standalone.indexer import build_default_auditor


def _print_json(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent_audit_standalone",
        description="Inspect agent implementation coverage and registry consistency",
    )
    parser.add_argument("--root", default=str(Path.cwd()), help="Repository root to inspect")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("inspect", help="Inspect agent coverage and registry consistency")

    summary = sub.add_parser("summary", help="Print or export markdown summary")
    summary.add_argument("--output", default=None, help="Write markdown summary to a file")

    args = parser.parse_args()
    auditor = build_default_auditor(args.root)

    if args.command == "inspect":
        _print_json(auditor.inspect())
    elif args.command == "summary":
        if args.output:
            out = auditor.export_summary_markdown(args.output)
            _print_json({"written": str(out), "summary": auditor.inspect()})
        else:
            print(auditor.summary_markdown())


if __name__ == "__main__":
    main()

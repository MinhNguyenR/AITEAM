from __future__ import annotations

import argparse
import sys
import webbrowser

from .server import make_server
from ..traces import TraceStore


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    load_dotenv()


def main(argv: list[str] | None = None) -> int:
    _load_env()
    parser = argparse.ArgumentParser(prog="aiteamruntime", description="Run the local aiteamruntime trace viewer.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--trace-root", default=None)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--demo", action="store_true", help="Generate a standalone demo trace before serving.")
    args = parser.parse_args(argv)

    if args.demo:
        from ..demo import run_demo

        run_id = run_demo(trace_root=args.trace_root)
        print(f"demo trace: {run_id}", flush=True)

    server = make_server(args.host, args.port, TraceStore(args.trace_root))
    host, port = server.server_address[:2]
    url = f"http://{host}:{port}"
    print(url, flush=True)
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

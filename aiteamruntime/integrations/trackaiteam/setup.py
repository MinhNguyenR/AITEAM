from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from aiteamruntime.core.runtime import AgentContext


def workspace_snapshot(ctx: AgentContext) -> dict[str, Any]:
    workspace = ctx.runtime.resources.workspace_for(ctx.run_id)
    root = Path(workspace) if workspace else Path.cwd()
    names = []
    for name in ("package.json", "vite.config.js", "vite.config.ts", "src", "app", "pages", "pyproject.toml"):
        try:
            if (root / name).exists():
                names.append(name)
        except OSError:
            pass
    return {"workspace": str(root), "exists": root.exists(), "entries": names}


def safe_setup_commands(ctx: AgentContext, plan: dict[str, Any], raw_commands: Any) -> list[dict[str, Any]]:
    workspace = ctx.runtime.resources.workspace_for(ctx.run_id)
    root = Path(workspace) if workspace else Path.cwd()
    task_blob = json.dumps(plan, ensure_ascii=False).lower()
    has_package = (root / "package.json").exists()
    needs_react = any(token in task_blob for token in ("react", "vite", "frontend", "ui", "web app", "next.js", "nextjs"))
    if has_package:
        return filter_safe_setup_commands(raw_commands)
    if needs_react:
        return [python_vite_react_project_command()]
    return filter_safe_setup_commands(raw_commands)


def filter_safe_setup_commands(raw_commands: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_commands, list):
        return []
    allowed: list[dict[str, Any]] = []
    for command in raw_commands[:3]:
        if not isinstance(command, dict):
            continue
        argv = [str(part) for part in command.get("argv") or []]
        if not argv:
            continue
        executable = Path(argv[0]).name.lower()
        if executable not in {"python", "python.exe", Path(sys.executable).name.lower()}:
            continue
        allowed.append(
            {
                "label": str(command.get("label") or "Secretary setup command"),
                "argv": argv,
                "timeout": float(command.get("timeout") or 60),
            }
        )
    return allowed


def python_vite_react_project_command() -> dict[str, Any]:
    script = (
        "import json\n"
        "import time\n"
        "from pathlib import Path\n"
        "root=Path.cwd()\n"
        "root.mkdir(parents=True, exist_ok=True)\n"
        "src=root/'src'\n"
        "src.mkdir(exist_ok=True)\n"
        "pkg={\n"
        "  'name':'aiteamruntime-vite-react-app',\n"
        "  'private':True,\n"
        "  'version':'0.1.0',\n"
        "  'type':'module',\n"
        "  'scripts':{'dev':'vite --host 127.0.0.1','build':'vite build','preview':'vite preview --host 127.0.0.1'},\n"
        "  'dependencies':{'@vitejs/plugin-react':'latest','vite':'latest','react':'latest','react-dom':'latest'},\n"
        "  'devDependencies':{}\n"
        "}\n"
        "(root/'package.json').write_text(json.dumps(pkg, ensure_ascii=False, indent=2)+'\\n', encoding='utf-8')\n"
        "(root/'index.html').write_text(\"<!doctype html>\\n<html><head><meta charset='UTF-8'/><meta name='viewport' content='width=device-width, initial-scale=1.0'/><title>AI Team Runtime App</title></head><body><div id='root'></div><script type='module' src='/src/main.jsx'></script></body></html>\\n\", encoding='utf-8')\n"
        "(src/'main.jsx').write_text(\"import React from 'react';\\nimport { createRoot } from 'react-dom/client';\\nimport App from './App.jsx';\\nimport './style.css';\\n\\ncreateRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>);\\n\", encoding='utf-8')\n"
        "(src/'App.jsx').write_text(\"export default function App() {\\n  return (\\n    <main className='app-shell'>\\n      <section className='workspace-panel'>\\n        <p className='eyebrow'>AI Team Runtime</p>\\n        <h1>React project scaffold is ready</h1>\\n        <p>Secretary created this Vite-compatible project before workers received assignments.</p>\\n      </section>\\n    </main>\\n  );\\n}\\n\", encoding='utf-8')\n"
        "(src/'style.css').write_text(\":root{font-family:Inter,system-ui,Segoe UI,Arial,sans-serif;color:#20242a;background:#f7f8fb}body{margin:0}.app-shell{min-height:100vh;display:grid;place-items:center;padding:32px}.workspace-panel{max-width:720px;border:1px solid #d9dee7;background:white;border-radius:8px;padding:28px}.eyebrow{font-size:12px;text-transform:uppercase;color:#5c6b7d;letter-spacing:.04em}h1{margin:0 0 12px;font-size:32px}\\n\", encoding='utf-8')\n"
        "manifest={'tool':'Secretary','project':'vite-react','created_at':time.time(),'files':['package.json','index.html','src/main.jsx','src/App.jsx','src/style.css']}\n"
        "(root/'.aiteamruntime_setup.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\\n', encoding='utf-8')\n"
        "print('Secretary created Vite React project scaffold')\n"
        "print(json.dumps(manifest, ensure_ascii=False))\n"
    )
    return {
        "label": "Secretary create Vite React project scaffold",
        "argv": [sys.executable, "-c", script],
        "timeout": 60,
        "creates": ["package.json", "index.html", "src/main.jsx", "src/App.jsx", "src/style.css", ".aiteamruntime_setup.json"],
    }


def format_setup_commands(commands: list[dict[str, Any]]) -> str:
    if not commands:
        return "- No setup required before workers.\n"
    lines = []
    for command in commands:
        label = str(command.get("label") or "setup")
        argv = " ".join(str(part) for part in command.get("argv") or [])
        lines.append(f"- {label}: `{argv}`")
    return "\n".join(lines) + "\n"


def command_payload(command: Any, stage: str) -> dict[str, Any]:
    if isinstance(command, dict):
        argv = [str(part) for part in command.get("argv") or []]
        label = str(command.get("label") or " ".join(argv))
        timeout = float(command.get("timeout") or 30)
    else:
        argv = []
        label = str(command)
        timeout = 30.0
    return {"command": label, "argv": argv, "cwd": ".", "stage": stage, "timeout": timeout}

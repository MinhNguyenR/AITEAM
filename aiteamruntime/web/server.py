from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import threading
import time
from urllib.parse import parse_qs, unquote, urlparse

from ..core.runtime import AgentRuntime
from ..tracing.store import TraceStore
from aiteamruntime.integrations.trackaiteam import (
    model_name,
    model_readiness,
    register_default_agents,
    registry_model_summary,
)
from .directory_browser import browse_directories as _browse_directories
from .directory_browser import pick_directory as _pick_directory
from .pipelines import PipelineRegistry
from .summaries import (
    filter_events as _filter_events,
    new_run_id as _new_run_id,
    next_pipeline_run_number as _next_pipeline_run_number,
    summarize_agents as _summarize_agents,
    summarize_assignments as _summarize_assignments,
    summarize_events as _summarize_events,
    summarize_resources as _summarize_resources,
)

ASSET_DIR = Path(__file__).with_name("assets")

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>AI Team Trace</title>
  <style>
    :root{color-scheme:dark;--bg:#101214;--panel:#181b1f;--line:#2c3238;--text:#edf1f5;--muted:#97a2ad;--accent:#78a6ff;--err:#ff7b7b;--term:#d6b365;--file:#80d4a8;--reason:#b9a0ff}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 ui-sans-serif,system-ui,Segoe UI,Arial}
    header{min-height:56px;display:flex;align-items:center;gap:10px;padding:9px 14px;border-bottom:1px solid var(--line);background:#13161a;position:sticky;top:0;z-index:2;flex-wrap:wrap}
    h1{font-size:16px;margin:0;font-weight:650}.spacer{flex:1}
    select,input,button{background:#0f1215;color:var(--text);border:1px solid var(--line);border-radius:6px;padding:7px 9px;min-height:34px}
    button{cursor:pointer}main{display:grid;grid-template-columns:minmax(520px,1.35fr) minmax(340px,.65fr);gap:12px;padding:12px;min-height:calc(100vh - 56px)}
    section{background:var(--panel);border:1px solid var(--line);border-radius:8px;min-width:0;overflow:hidden}
    .title{padding:10px 12px;border-bottom:1px solid var(--line);color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em;display:flex;align-items:center;justify-content:space-between}
    .summary{display:grid;grid-template-columns:repeat(5,minmax(80px,1fr));gap:8px;padding:10px;border-bottom:1px solid var(--line)}
    .stat{background:#101419;border:1px solid #242b32;border-radius:6px;padding:8px}.stat b{display:block;font-size:18px}.stat span{color:var(--muted);font-size:11px;text-transform:uppercase}
    .lanes{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px;padding:10px;border-bottom:1px solid var(--line)}
    .lane{background:#101419;border:1px solid #242b32;border-radius:7px;min-height:96px;overflow:hidden}.lane h3{font-size:12px;margin:0;padding:7px 8px;border-bottom:1px solid #242b32;color:#cfd7df}.lane-body{padding:7px;display:grid;gap:6px}
    .timeline{padding:10px;display:grid;gap:8px;max-height:calc(100vh - 116px);overflow:auto}
    .event{border-left:3px solid var(--accent);background:#12161a;border-radius:6px;padding:8px 10px}
    .event.mini{padding:6px 7px}.event.error{border-color:var(--err)}.event.abort{border-color:var(--err)}.event.reasoning{border-color:var(--reason)}.event.terminal_requested,.event.terminal_running,.event.terminal_result{border-color:var(--term)}.event.file_update,.event.file_create{border-color:var(--file)}
    .meta{display:flex;gap:8px;flex-wrap:wrap;color:var(--muted);font-size:12px;margin-bottom:4px}.kind{color:var(--text);font-weight:650}
    pre{white-space:pre-wrap;overflow-wrap:anywhere;margin:0;color:#cbd5df;font:12px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace}
    .side{display:grid;grid-template-rows:1fr 1fr 1fr;gap:12px}.pane{max-height:calc((100vh - 88px)/3);overflow:auto;padding:10px;display:grid;gap:8px;align-content:start}
    .empty{color:var(--muted);padding:8px}
    @media (max-width:900px){main{grid-template-columns:1fr}.side{grid-template-rows:auto}.pane,.timeline{max-height:none}}
  </style>
</head>
<body>
  <header>
    <h1>AI Team Trace</h1>
    <select id="run"></select>
    <input id="agent" placeholder="agent filter">
    <input id="kind" placeholder="kind filter">
    <button id="refresh">Refresh</button>
    <button id="pause">Pause</button>
    <span id="status" class="spacer"></span>
  </header>
  <main>
    <section>
      <div class="title">Trace Overview <span id="live"></span></div>
      <div id="summary" class="summary"></div>
      <div id="lanes" class="lanes"></div>
      <div class="title">Timeline</div>
      <div id="timeline" class="timeline"></div>
    </section>
    <div class="side">
      <section><div class="title">Model Stream</div><div id="model" class="pane"></div></section>
      <section><div class="title">Terminal</div><div id="terminal" class="pane"></div></section>
      <section><div class="title">Files</div><div id="files" class="pane"></div></section>
    </div>
  </main>
  <script>
    const els={run:document.querySelector('#run'),agent:document.querySelector('#agent'),kind:document.querySelector('#kind'),summary:document.querySelector('#summary'),lanes:document.querySelector('#lanes'),timeline:document.querySelector('#timeline'),model:document.querySelector('#model'),terminal:document.querySelector('#terminal'),files:document.querySelector('#files'),pause:document.querySelector('#pause'),refresh:document.querySelector('#refresh'),status:document.querySelector('#status'),live:document.querySelector('#live')};
    let events=[], paused=false, source=null;
    const laneNames=['Ambassador','Leader','Worker A','Worker B','Worker C','Worker D','Worker E','Secretary','Tool Curator','Explainer'];
    const termKinds=new Set(['terminal_requested','terminal_running','terminal_result']);
    const fileKinds=new Set(['file_update','file_create']);
    const modelKinds=new Set(['reasoning','writing','reading','classifying','question']);
    function fmtTs(ts){return new Date((ts||0)*1000).toLocaleTimeString();}
    function matches(e){return (!els.agent.value||e.agent_id.toLowerCase().includes(els.agent.value.toLowerCase()))&&(!els.kind.value||e.kind.toLowerCase().includes(els.kind.value.toLowerCase()));}
    function card(e,mini=false){const p=e.payload||{};const preview=p.content||p.command||p.file||p.path||p.summary||p.reason||JSON.stringify(p);return `<div class="event ${mini?'mini ':''}${e.kind}"><div class="meta"><span>${fmtTs(e.ts)}</span><span>${escapeHtml(e.agent_id)}</span><span class="kind">${escapeHtml(e.kind)}</span><span>${escapeHtml(e.status||'')}</span></div>${mini?`<pre>${escapeHtml(String(preview).slice(0,140))}</pre>`:`<pre>${escapeHtml(JSON.stringify(p,null,2))}</pre>`}</div>`}
    function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
    function summary(events){const agents=new Set(events.map(e=>e.agent_id));const errors=events.filter(e=>e.kind==='error'||e.kind==='abort').length;const terminals=events.filter(e=>termKinds.has(e.kind)).length;const files=events.filter(e=>fileKinds.has(e.kind)).length;const latest=events.length?fmtTs(events[events.length-1].ts):'-';return [['Events',events.length],['Agents',agents.size],['Terminal',terminals],['Files',files],['Errors',errors],['Latest',latest]].map(([k,v])=>`<div class="stat"><b>${escapeHtml(v)}</b><span>${k}</span></div>`).join('')}
    function renderLanes(vis){els.lanes.innerHTML=laneNames.map(name=>{const mine=vis.filter(e=>e.agent_id===name).slice(-4);return `<div class="lane"><h3>${name}</h3><div class="lane-body">${mine.map(e=>card(e,true)).join('')||'<div class="empty">idle</div>'}</div></div>`}).join('')}
    function render(){const vis=events.filter(matches);els.summary.innerHTML=summary(vis);renderLanes(vis);els.timeline.innerHTML=vis.map(e=>card(e)).join('')||'<div class="empty">No events.</div>';els.model.innerHTML=vis.filter(e=>modelKinds.has(e.kind)).map(e=>card(e)).join('')||'<div class="empty">No model events.</div>';els.terminal.innerHTML=vis.filter(e=>termKinds.has(e.kind)).map(e=>card(e)).join('')||'<div class="empty">No terminal events.</div>';els.files.innerHTML=vis.filter(e=>fileKinds.has(e.kind)).map(e=>card(e)).join('')||'<div class="empty">No file events.</div>';els.live.textContent=paused?'paused':'live'}
    async function loadRuns(){const current=els.run.value;const runs=await fetch('/runs').then(r=>r.json());els.run.innerHTML=['<option value="">Live / all runs</option>'].concat(runs.map(r=>{const meta=r.metadata&&r.metadata.prompt?` - ${String(r.metadata.prompt).slice(0,40)}`:'';return `<option value="${escapeHtml(r.run_id)}">${escapeHtml(r.run_id)} (${r.events||0})${escapeHtml(meta)}</option>`})).join('');if(current)els.run.value=current;}
    async function loadRun(){const id=els.run.value;if(!id){events=[];connect();return}events=await fetch(`/runs/${encodeURIComponent(id)}/events`).then(r=>r.json());render();connect();}
    function connect(){if(source)source.close();if(paused)return;const qs=els.run.value?`?run_id=${encodeURIComponent(els.run.value)}`:'';source=new EventSource('/events'+qs);source.onopen=()=>els.status.textContent='live';source.onerror=()=>els.status.textContent='disconnected';source.onmessage=ev=>{const e=JSON.parse(ev.data);if(!els.run.value||e.run_id===els.run.value){events.push(e);events=events.slice(-1000);render();}}}
    els.pause.onclick=()=>{paused=!paused;els.pause.textContent=paused?'Resume':'Pause';if(paused&&source)source.close();else connect();render();}
    els.refresh.onclick=()=>loadRuns().then(loadRun);
    els.run.onchange=loadRun;els.agent.oninput=render;els.kind.oninput=render;
    loadRuns().then(()=>{connect();render();});
  </script>
</body>
</html>"""


class TraceRequestHandler(BaseHTTPRequestHandler):
    server: "TraceHTTPServer"

    def log_message(self, fmt: str, *args) -> None:
        return

    def _send_json(self, data, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_asset(self, name: str) -> bool:
        safe = name.strip("/").replace("\\", "/")
        if not safe or ".." in safe:
            return False
        path = (ASSET_DIR / safe).resolve()
        try:
            path.relative_to(ASSET_DIR.resolve())
        except ValueError:
            return False
        if not path.is_file():
            return False
        ctype = "text/plain; charset=utf-8"
        if path.suffix == ".html":
            ctype = "text/html; charset=utf-8"
        elif path.suffix == ".css":
            ctype = "text/css; charset=utf-8"
        elif path.suffix == ".js":
            ctype = "application/javascript; charset=utf-8"
        self._send_bytes(path.read_bytes(), ctype)
        return True

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/":
            if not self._send_asset("index.html"):
                self._send_bytes(INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path.startswith("/assets/"):
            if not self._send_asset(path[len("/assets/") :]):
                self._send_json({"error": "not found"}, status=404)
            return
        if path == "/health":
            store_health = self.server.store.health() if hasattr(self.server.store, "health") else {"backend": "unknown"}
            readiness = model_readiness()
            self._send_json(
                {
                    "ok": True,
                    "store": store_health,
                    "runtime_active": self.server.runtime is not None,
                    "model": {
                        **readiness,
                        "model": model_name("AMBASSADOR") if readiness.get("enabled") else "",
                        "registry": registry_model_summary(),
                    },
                    "secretary_alive": bool(
                        self.server.runtime is not None
                        and self.server.runtime._secretary is not None
                        and self.server.runtime._secretary.is_alive()
                    ),
                }
            )
            return
        if path == "/runs":
            self._send_json(self.server.store.list_runs())
            return
        if path == "/pipelines":
            self._send_json(self.server.pipelines.list_pipelines(self.server.store.list_runs()))
            return
        if path == "/fs":
            self._send_json(_browse_directories((parse_qs(parsed.query).get("path") or [""])[0]))
            return
        if path == "/fs/pick":
            self._send_json(_pick_directory((parse_qs(parsed.query).get("initial") or [""])[0]))
            return
        if path.startswith("/pipelines/") and path.endswith("/runs"):
            pipeline_id = unquote(path[len("/pipelines/") : -len("/runs")])
            self._send_json([run for run in self.server.store.list_runs() if (run.get("metadata") or {}).get("pipeline_id") == pipeline_id])
            return
        if path.startswith("/runs/") and path.endswith("/summary"):
            run_id = unquote(path[len("/runs/") : -len("/summary")])
            self._send_json(_summarize_events(self.server.store.read_events(run_id)))
            return
        if path.startswith("/runs/") and path.endswith("/resources"):
            run_id = unquote(path[len("/runs/") : -len("/resources")])
            if self.server.runtime is not None:
                data = self.server.runtime.resource_snapshot(run_id)
                data.update(_summarize_resources(self.server.store.read_events(run_id)))
                self._send_json(data)
            else:
                self._send_json(_summarize_resources(self.server.store.read_events(run_id)))
            return
        if path.startswith("/runs/") and path.endswith("/assignments"):
            run_id = unquote(path[len("/runs/") : -len("/assignments")])
            if self.server.runtime is not None:
                self._send_json(self.server.runtime.assignments_snapshot(run_id))
            else:
                self._send_json(_summarize_assignments(self.server.store.read_events(run_id)))
            return
        if path.startswith("/runs/") and path.endswith("/governor"):
            run_id = unquote(path[len("/runs/") : -len("/governor")])
            self._send_json(self.server.runtime.governor_snapshot(run_id) if self.server.runtime is not None else {})
            return
        if path.startswith("/runs/") and path.endswith("/refs"):
            run_id = unquote(path[len("/runs/") : -len("/refs")])
            self._send_json(self.server.runtime.refs_snapshot(run_id) if self.server.runtime is not None else [])
            return
        if path == "/contracts":
            self._send_json(self.server.runtime.contracts_snapshot() if self.server.runtime is not None else [])
            return
        if path.startswith("/runs/") and path.endswith("/agents"):
            run_id = unquote(path[len("/runs/") : -len("/agents")])
            self._send_json(_summarize_agents(self.server.store.read_events(run_id)))
            return
        if path.startswith("/runs/") and path.endswith("/events"):
            run_id = unquote(path[len("/runs/") : -len("/events")])
            self._send_json(_filter_events(self.server.store.read_events(run_id), parse_qs(parsed.query)))
            return
        if path == "/events":
            query = parse_qs(parsed.query)
            self._send_sse(query.get("run_id", [None])[0], query)
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/pipelines":
            self._create_pipeline()
            return
        if path.startswith("/runs/") and path.endswith("/answers"):
            run_id = unquote(path[len("/runs/") : -len("/answers")])
            self._answer_run(run_id)
            return
        if path != "/runs":
            self._send_json({"error": "not found"}, status=404)
            return
        self._create_run()

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path.startswith("/pipelines/"):
            pipeline_id = unquote(path[len("/pipelines/") :])
            self._update_pipeline(pipeline_id)
            return
        self._send_json({"error": "not found"}, status=404)

    def _read_json_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            length = 0
        try:
            body = json.loads(self.rfile.read(min(length, 1024 * 1024)).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            raise ValueError("invalid json")
        return body

    def _create_pipeline(self) -> None:
        try:
            body = self._read_json_body()
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
            return
        pipeline = self.server.pipelines.create_pipeline(
            name=str(body.get("name") or "Untitled Pipeline"),
            workspace=str(body.get("workspace") or ""),
        )
        self._send_json(pipeline, status=201)

    def _update_pipeline(self, pipeline_id: str) -> None:
        try:
            body = self._read_json_body()
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
            return
        pipeline = self.server.pipelines.update_pipeline(
            pipeline_id,
            name=str(body.get("name") or ""),
            workspace=str(body.get("workspace") or ""),
        )
        if pipeline is None:
            self._send_json({"error": "unknown pipeline"}, status=404)
            return
        self._send_json(pipeline)

    def _create_run(self) -> None:
        try:
            body = self._read_json_body()
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
            return
        task = str(body.get("task") or body.get("prompt") or "").strip()
        if not task:
            self._send_json({"error": "task is required"}, status=400)
            return
        pipeline_id = str(body.get("pipeline_id") or "trackaiteam")
        pipeline = self.server.pipelines.get_pipeline(pipeline_id)
        if pipeline is None:
            self._send_json({"error": "unknown pipeline"}, status=404)
            return
        workspace = str(body.get("workspace") or pipeline.get("workspace") or "").strip()
        if not workspace:
            self._send_json({"error": "workspace is required"}, status=400)
            return
        workspace_path = Path(workspace).expanduser()
        if not workspace_path.exists() or not workspace_path.is_dir():
            self._send_json({"error": "workspace must be an existing directory"}, status=400)
            return
        readiness = model_readiness()
        if not readiness.get("ok"):
            self._send_json({"error": "model provider is not ready", "model": readiness}, status=409)
            return
        workspace = str(workspace_path.resolve())
        self.server.pipelines.update_workspace(pipeline_id, workspace)
        runtime = self.server.runtime
        if runtime is None:
            runtime = AgentRuntime(store=self.server.store)
            register_default_agents(runtime)
            self.server.runtime = runtime
        run_number = _next_pipeline_run_number(self.server.store.list_runs(), pipeline_id)
        run_id = _new_run_id(pipeline_id, run_number)
        run_name = f"{pipeline.get('name') or pipeline_id} #{run_number}"
        handle = runtime.start_run(
            run_id=run_id,
            prompt=task,
            metadata={
                "source": "web",
                "task": task,
                "run_name": run_name,
                "run_number": run_number,
                "pipeline_id": pipeline_id,
                "workspace": workspace,
            },
        )
        self._send_json(
            {"run_id": handle.run_id, "run_name": run_name, "pipeline_id": pipeline_id, "workspace": workspace, "status": "running"},
            status=201,
        )

    def _answer_run(self, run_id: str) -> None:
        try:
            body = self._read_json_body()
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
            return
        answer = str(body.get("answer") or "").strip()
        if not answer:
            self._send_json({"error": "answer is required"}, status=400)
            return
        readiness = model_readiness()
        if not readiness.get("ok"):
            self._send_json({"error": "model provider is not ready", "model": readiness}, status=409)
            return
        runtime = self.server.runtime
        if runtime is None:
            runtime = AgentRuntime(store=self.server.store)
            register_default_agents(runtime)
            self.server.runtime = runtime
        run_record = _find_run(self.server.store.list_runs(), run_id)
        run_metadata = dict((run_record or {}).get("metadata") or {})
        workspace = str(run_metadata.get("workspace") or (run_record or {}).get("workspace") or "")
        if not runtime.resume_run(run_id, metadata={"workspace": workspace}):
            self._send_json({"error": "run could not be resumed"}, status=409)
            return
        events = self.server.store.read_events(run_id)
        pending = _latest_pending_question(events)
        if pending is None:
            self._send_json({"error": "run has no pending question"}, status=409)
            return
        pending_payload = pending.get("payload") or {}
        latest_brief = _latest_ambassador_brief(events)
        first = next((event for event in events if event.get("kind") == "classifying" and event.get("agent_id") == "runtime"), {})
        first_payload = first.get("payload") or {}
        task = str(
            pending_payload.get("task")
            or latest_brief.get("task")
            or run_metadata.get("task")
            or run_metadata.get("prompt")
            or first_payload.get("prompt")
            or ((first_payload.get("metadata") or {}).get("task"))
            or ""
        )
        brief = {**latest_brief, **pending_payload}
        if task and not brief.get("task"):
            brief["task"] = task
        if task and not brief.get("summary"):
            brief["summary"] = task[:180]
        if not brief.get("tier"):
            brief["tier"] = "MEDIUM"
        event = runtime.emit(
            run_id,
            "runtime",
            "answered",
            {
                "answer": answer,
                "task": task,
                "summary": brief.get("summary") or "",
                "brief": brief,
                "question": pending_payload.get("question") or "",
                "question_event_id": pending.get("event_id") or "",
                "question_agent_id": pending.get("agent_id") or "",
                "tier": brief.get("tier") or "MEDIUM",
                "selected_leader": brief.get("selected_leader") or "Leader",
                "selected_leader_role_key": brief.get("selected_leader_role_key") or "",
                "selected_leader_model": brief.get("selected_leader_model") or "",
            },
            stage="clarify",
            role_state="done",
        )
        self._send_json(event.to_dict(), status=201)

    def _send_sse(self, run_id: str | None, query: dict[str, list[str]] | None = None) -> None:
        # Limit concurrent SSE clients so a slow consumer can't pin all
        # request threads. ``acquire(blocking=False)`` returns immediately.
        if not self.server.sse_semaphore.acquire(blocking=False):
            self._send_json({"error": "too many SSE connections"}, status=503)
            return
        try:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self._stream_sse(run_id, query or {})
        except (BrokenPipeError, ConnectionResetError, OSError):
            return
        finally:
            self.server.sse_semaphore.release()

    def _stream_sse(self, run_id: str | None, query: dict[str, list[str]]) -> None:
        """Push events for ``run_id`` (or all) until the client disconnects.

        Subscribes directly to the runtime's ``EventBus`` if available — that
        avoids re-reading the JSONL file every second. Heartbeats every 30s
        keep proxies alive; idle clients are closed after 60s of silence.
        """
        idle_timeout = 60.0
        heartbeat_interval = 30.0
        runtime = self.server.runtime
        last_send = time.time()
        last_heartbeat = time.time()

        # Backfill historical events first so newly-attached clients see context.
        history_seq: dict[str, int] = {}
        for run in self.server.store.list_runs():
            rid = str(run.get("run_id") or "")
            if run_id and rid != run_id:
                continue
            events = _filter_events(self.server.store.read_events(rid), query)
            for event in events:
                self._sse_write(event)
                history_seq[rid] = max(history_seq.get(rid, 0), int(event.get("sequence") or 0))
        last_send = time.time()

        if runtime is not None:
            subscription = runtime.bus.subscribe(replay=False, run_id=run_id, max_queue=512)
        else:
            subscription = None

        try:
            while True:
                event_obj = None
                if subscription is not None:
                    event_obj = subscription.get(timeout=1.0)
                else:
                    time.sleep(1.0)

                now = time.time()
                if event_obj is not None:
                    event_dict = event_obj.to_dict()
                    if _matches_query(event_dict, query):
                        self._sse_write(event_dict)
                        last_send = now
                        last_heartbeat = now

                if now - last_heartbeat >= heartbeat_interval:
                    self._sse_write({"kind": "heartbeat", "ts": now, "agent_id": "runtime", "run_id": run_id or "*"})
                    last_heartbeat = now

                if now - last_send >= idle_timeout:
                    return
        finally:
            if subscription is not None:
                subscription.close()

    def _sse_write(self, event_dict: dict) -> None:
        self.wfile.write(f"data: {json.dumps(event_dict, ensure_ascii=False)}\n\n".encode("utf-8"))
        self.wfile.flush()


class TraceHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address,
        RequestHandlerClass,
        store: TraceStore,
        runtime: AgentRuntime | None = None,
        *,
        max_sse_connections: int = 64,
    ) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.store = store
        self.runtime = runtime
        self.pipelines = store if all(hasattr(store, name) for name in ("list_pipelines", "get_pipeline", "create_pipeline", "update_pipeline", "update_workspace")) else PipelineRegistry(store.root)
        # Semaphore limits concurrent /events SSE streams so a slow consumer
        # can't pin every thread in the ThreadingHTTPServer pool.
        self.sse_semaphore = threading.Semaphore(max(1, int(max_sse_connections)))

    def handle_error(self, request, client_address) -> None:
        exc_type, exc, _tb = __import__("sys").exc_info()
        if exc_type in {ConnectionAbortedError, ConnectionResetError, BrokenPipeError, OSError}:
            return
        super().handle_error(request, client_address)


def _matches_query(event: dict, query: dict[str, list[str]]) -> bool:
    """Apply ``agent``/``kind``/``after`` filters used by /events SSE clients."""
    agent = (query.get("agent") or [""])[0].lower()
    kind = (query.get("kind") or [""])[0].lower()
    try:
        after = int((query.get("after") or ["0"])[0] or 0)
    except ValueError:
        after = 0
    if after and int(event.get("sequence") or 0) <= after:
        return False
    if agent and agent not in str(event.get("agent_id") or "").lower():
        return False
    if kind and kind != str(event.get("kind") or "").lower():
        return False
    return True


def _find_run(runs: list[dict], run_id: str) -> dict | None:
    return next((run for run in runs if str(run.get("run_id") or "") == run_id), None)


def _latest_pending_question(events: list[dict]) -> dict | None:
    answered_questions = {
        str((event.get("payload") or {}).get("question_event_id") or "")
        for event in events
        if event.get("kind") == "answered"
    }
    answered_questions.discard("")
    latest_legacy_answer = max(
        (int(event.get("sequence") or 0) for event in events if event.get("kind") == "answered" and not (event.get("payload") or {}).get("question_event_id")),
        default=0,
    )
    for event in reversed(events):
        if event.get("kind") != "question" or event.get("status") != "waiting":
            continue
        event_id = str(event.get("event_id") or "")
        if event_id in answered_questions:
            continue
        if latest_legacy_answer and latest_legacy_answer > int(event.get("sequence") or 0):
            continue
        return event
    return None


def _latest_ambassador_brief(events: list[dict]) -> dict:
    for event in reversed(events):
        if event.get("agent_id") != "Ambassador":
            continue
        if event.get("kind") not in {"classifying", "question", "done"}:
            continue
        payload = event.get("payload") or {}
        if payload.get("task") or payload.get("summary"):
            return dict(payload)
    return {}


def find_free_port(host: str, start: int) -> int:
    if int(start) <= 0:
        return 0
    port = int(start)
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                port += 1
                continue
        return port
    raise RuntimeError("no free port found")


def make_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    store: TraceStore | None = None,
    runtime: AgentRuntime | None = None,
) -> TraceHTTPServer:
    actual_port = find_free_port(host, port)
    return TraceHTTPServer((host, actual_port), TraceRequestHandler, store or TraceStore(), runtime)

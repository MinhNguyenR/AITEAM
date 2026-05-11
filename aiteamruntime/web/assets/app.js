const $ = (s) => document.querySelector(s);
const els = {
  runList: $("#runList"),
  runTitle: $("#runTitle"),
  runMeta: $("#runMeta"),
  pipelineSelect: $("#pipelineSelect"),
  workspaceInput: $("#workspaceInput"),
  workspaceHint: $("#workspaceHint"),
  chooseWorkspace: $("#chooseWorkspace"),
  taskInput: $("#taskInput"),
  startRun: $("#startRun"),
  newPipeline: $("#newPipeline"),
  statusFilter: $("#statusFilter"),
  agent: $("#agent"),
  kind: $("#kind"),
  errors: $("#errors"),
  summary: $("#summary"),
  timeline: $("#timeline"),
  model: $("#model"),
  terminal: $("#terminal"),
  files: $("#files"),
  assignments: $("#assignments"),
  agents: $("#agents"),
  detail: $("#detail"),
  pause: $("#pause"),
  refresh: $("#refresh"),
  status: $("#status"),
  live: $("#live"),
  questionPanel: $("#questionPanel"),
  questionText: $("#questionText"),
  questionReason: $("#questionReason"),
  answerInput: $("#answerInput"),
  sendAnswer: $("#sendAnswer"),
  workspaceModal: $("#workspaceModal"),
  closeWorkspaceModal: $("#closeWorkspaceModal"),
  fsCurrent: $("#fsCurrent"),
  fsRoots: $("#fsRoots"),
  fsUp: $("#fsUp"),
  fsEntries: $("#fsEntries"),
  useWorkspace: $("#useWorkspace"),
};

let pipelines = [];
let runs = [];
let events = [];
let assignments = [];
let selectedPipeline = "trackaiteam";
let selectedRun = "";
let paused = false;
let source = null;
let lastSequence = 0;
let activeTab = "model";
let fsCurrentPath = "";
let fsParentPath = "";
const expandedPipelines = new Set(["trackaiteam"]);

const termKinds = new Set(["setup_requested", "setup_done", "terminal_requested", "terminal_running", "terminal_result"]);
const fileKinds = new Set(["file_update", "file_create", "blocked"]);
const modelKinds = new Set([
  "reasoning",
  "writing",
  "reading",
  "classifying",
  "routing",
  "model_requested",
  "model_response",
  "question",
  "answered",
  "assigned",
  "reassigned",
  "validated",
  "finalized",
  "worker_failed",
  "error",
]);

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function ts(v) {
  return v ? new Date(v * 1000).toLocaleTimeString() : "-";
}
function preview(e) {
  const p = e.payload || {};
  return p.question || p.answer || p.content || p.command || p.file || p.path || p.summary || p.reason || p.resource_key || p.stage || p.title || JSON.stringify(p);
}
function currentPipeline() {
  return pipelines.find((p) => p.pipeline_id === selectedPipeline);
}
function runState(r) {
  const kind = String(r.last_kind || "");
  if (["error", "abort", "blocked", "worker_failed"].includes(kind)) return "error";
  if (["finalized", "done"].includes(kind)) return "done";
  return "running";
}
function statusChip(e) {
  return `<span class="status ${esc(e.status || e.kind)}">${esc(e.status || "ok")}</span>`;
}
function matches(e) {
  return (
    (!els.agent.value || e.agent_id.toLowerCase().includes(els.agent.value.toLowerCase())) &&
    (!els.kind.value || e.kind.toLowerCase().includes(els.kind.value.toLowerCase())) &&
    (!els.errors.checked || ["error", "abort", "blocked", "worker_failed"].includes(e.kind) || ["error", "aborted", "blocked"].includes(e.status))
  );
}
function runsForPipeline(pipelineId) {
  return runs.filter((r) => {
    const meta = r.metadata || {};
    const rid = meta.pipeline_id || "trackaiteam";
    return rid === pipelineId && (!els.statusFilter.value || runState(r) === els.statusFilter.value);
  });
}
function pipelineWorkspace(p) {
  if (p.pipeline_id === selectedPipeline && els.workspaceInput.value.trim()) return els.workspaceInput.value.trim();
  if (p.workspace) return p.workspace;
  const latest = runs
    .filter((r) => ((r.metadata || {}).pipeline_id || "trackaiteam") === p.pipeline_id && (r.metadata || {}).workspace)
    .sort((a, b) => Number(b.updated_at || 0) - Number(a.updated_at || 0))[0];
  return latest ? latest.metadata.workspace : "";
}
function runLabel(run) {
  const meta = run.metadata || {};
  if (meta.run_name) return meta.run_name;
  const started = run.started_at ? new Date(run.started_at * 1000).toLocaleString() : run.run_id;
  return `${meta.pipeline_id || "trackaiteam"} - ${started}`;
}
function renderPipelineSelect() {
  els.pipelineSelect.innerHTML = pipelines
    .map((p) => `<option value="${esc(p.pipeline_id)}">${esc(p.name || p.pipeline_id)}</option>`)
    .join("");
  els.pipelineSelect.value = selectedPipeline;
}
function renderRunHistory() {
  const html = [];
  for (const p of pipelines) {
    const pipeRuns = runsForPipeline(p.pipeline_id);
    const active = p.pipeline_id === selectedPipeline && !selectedRun;
    const expanded = expandedPipelines.has(p.pipeline_id);
    html.push(
      `<div class="history-group">
        <button class="pipeline-row ${active ? "active" : ""}" data-pipeline="${esc(p.pipeline_id)}">
          <span class="twisty">${expanded ? "v" : ">"}</span>
          <span class="pipeline-name">${esc(p.name || p.pipeline_id)}</span>
          <span class="pipeline-count">${pipeRuns.length}</span>
          <span class="pipeline-workspace">${esc(pipelineWorkspace(p) || "workspace not selected")}</span>
        </button>
        <div class="run-children ${expanded ? "" : "collapsed"}">
          ${
            pipeRuns
              .map(
                (r) =>
                  `<button class="run-item ${r.run_id === selectedRun ? "active" : ""}" data-run="${esc(r.run_id)}">
                    <div class="run-name">${esc(runLabel(r))}</div>
                    <div class="run-sub">${esc((r.metadata && (r.metadata.task || r.metadata.prompt)) || r.run_id)} - ${esc(r.events || 0)} events - ${esc(r.last_kind || "new")}</div>
                    <span class="run-chip ${runState(r)}">${runState(r)}</span>
                  </button>`
              )
              .join("") || '<div class="empty compact">No runs yet.</div>'
          }
        </div>
      </div>`
    );
  }
  els.runList.innerHTML = html.join("") || '<div class="empty">No pipelines.</div>';
  document.querySelectorAll("[data-pipeline]").forEach((button) => {
    button.onclick = () => {
      const id = button.dataset.pipeline || "";
      if (selectedPipeline === id && !selectedRun) {
        if (expandedPipelines.has(id)) expandedPipelines.delete(id);
        else expandedPipelines.add(id);
        render();
        return;
      }
      expandedPipelines.add(id);
      selectPipeline(id);
    };
  });
  document.querySelectorAll("[data-run]").forEach((button) => (button.onclick = () => selectRun(button.dataset.run || "")));
}
function metrics(vis) {
  const agents = new Set(vis.map((e) => e.agent_id));
  const errors = vis.filter((e) => ["error", "abort", "blocked", "worker_failed"].includes(e.kind)).length;
  const terminals = vis.filter((e) => termKinds.has(e.kind)).length;
  const files = vis.filter((e) => fileKinds.has(e.kind)).length;
  const latest = vis.length ? ts(vis[vis.length - 1].ts) : "-";
  return [
    ["Events", vis.length],
    ["Agents", agents.size],
    ["Terminal", terminals],
    ["Files/Locks", files],
    ["Problems", errors],
    ["Latest", latest],
  ]
    .map(([k, v]) => `<div class="metric"><b>${esc(v)}</b><span>${k}</span></div>`)
    .join("");
}
function spanRow(e) {
  return `<div class="span-row event-line stage-${esc(e.stage || "none")}" data-id="${esc(e.event_id)}">
    <div class="span-agent"><span>${esc(e.stage || "runtime")}</span>${esc(e.agent_id)}</div>
    <div class="span-body">
      <div class="span-head">${statusChip(e)}<span class="span-kind">${esc(e.kind)}</span>${e.duration_ms ? `<span class="duration">${esc(e.duration_ms)}ms</span>` : ""}</div>
      <div class="span-preview">${esc(preview(e))}</div>
    </div>
    <div class="span-time">#${esc(e.sequence)}<br>${ts(e.ts)}</div>
  </div>`;
}
function terminalState(e) {
  const p = e.payload || {};
  if (e.kind === "terminal_running") return ["running", "Running"];
  if (["terminal_requested", "setup_requested"].includes(e.kind)) return ["waiting", "Queued"];
  if (["terminal_result", "setup_done"].includes(e.kind)) return [Number(p.exit_code || 0) === 0 ? "ok" : "bad", "Ran"];
  return ["waiting", e.kind];
}
function terminalBlock(e) {
  const p = e.payload || {};
  const [cls, label] = terminalState(e);
  const out = String(p.output || "").trim();
  const body = ["terminal_result", "setup_done"].includes(e.kind) ? out || "(no output)" : p.cwd ? `cwd: ${p.cwd}` : "waiting for Secretary";
  return `<div class="terminal-card ${cls}" data-id="${esc(e.event_id)}">
    <div class="terminal-head"><span>${label}</span><b>${esc(p.exit_code !== undefined ? "exit " + p.exit_code : "")}</b></div>
    <pre class="cmd">${esc(p.command || "")}</pre>
    <pre class="output">${esc(body)}</pre>
  </div>`;
}
function fileBlock(e) {
  const p = e.payload || {};
  return `<div class="file-card" data-id="${esc(e.event_id)}"><b>${esc(e.kind)}</b> ${statusChip(e)}<pre>${esc(p.absolute_path || p.path || p.file || p.resource_key || JSON.stringify(p, null, 2))}</pre></div>`;
}
function assignmentRows() {
  return (
    assignments
      .map(
        (a) =>
          `<div class="agent-card"><b>${esc(a.id)}</b> <span class="status ${esc(a.status || "assigned")}">${esc(a.status || "assigned")}</span><div class="run-sub">${esc(
            a.assigned_worker || "unassigned"
          )} - attempt ${esc(a.attempt || 0)}</div><pre>${esc((a.allowed_paths || []).join("\n"))}</pre></div>`
      )
      .join("") || '<div class="empty">No assignments.</div>'
  );
}
function agentRows(vis) {
  const map = new Map();
  vis.forEach((e) => map.set(e.agent_id, e));
  return (
    Array.from(map.values())
      .sort((a, b) => a.agent_id.localeCompare(b.agent_id))
      .map((e) => `<div class="agent-card" data-id="${esc(e.event_id)}"><b>${esc(e.agent_id)}</b> ${statusChip(e)}<div class="run-sub">${esc(e.kind)} - ${ts(e.ts)}</div></div>`)
      .join("") || '<div class="empty">No agents.</div>'
  );
}
function pendingQuestion() {
  const answeredQuestions = new Set();
  let latestLegacyAnswer = 0;
  events.forEach((e) => {
    if (e.kind !== "answered") return;
    const id = (e.payload || {}).question_event_id || "";
    if (id) answeredQuestions.add(id);
    else latestLegacyAnswer = Math.max(latestLegacyAnswer, Number(e.sequence || 0));
  });
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (e.kind === "question" && e.status === "waiting") {
      if (answeredQuestions.has(e.event_id)) continue;
      if (latestLegacyAnswer > Number(e.sequence || 0)) continue;
      return e;
    }
  }
  return null;
}
function renderQuestion() {
  const q = pendingQuestion();
  els.questionPanel.classList.toggle("hidden", !q || !selectedRun);
  if (!q) return;
  const p = q.payload || {};
  els.questionText.textContent = p.question || "Clarification required";
  els.questionReason.textContent = p.reason || "";
}
function detail(e) {
  if (!e) {
    els.detail.innerHTML = '<div class="empty">Select an event.</div>';
    return;
  }
  const p = e.payload || {};
  els.detail.innerHTML = `<h2>${esc(e.agent_id)} - ${esc(e.kind)}</h2>
    <div class="kv">
      <span>Status</span><b>${esc(e.status || "ok")}</b>
      <span>Stage</span><b>${esc(e.stage || "-")}</b>
      <span>Work item</span><b>${esc(e.work_item_id || "-")}</b>
      <span>Sequence</span><b>#${esc(e.sequence)}</b>
      <span>Time</span><b>${ts(e.ts)}</b>
      <span>Event</span><b>${esc(e.event_id)}</b>
    </div>
    ${termKinds.has(e.kind) ? terminalBlock(e) : ""}
    <pre class="json">${esc(JSON.stringify(p, null, 2))}</pre>`;
}
function bindEventClicks() {
  document.querySelectorAll("[data-id]").forEach((n) => (n.onclick = () => detail(events.find((e) => e.event_id === n.dataset.id))));
}
function render() {
  const vis = events.filter(matches);
  const current = runs.find((r) => r.run_id === selectedRun);
  const pipe = currentPipeline();
  renderPipelineSelect();
  renderRunHistory();
  els.runTitle.textContent = selectedRun || (pipe ? pipe.name || pipe.pipeline_id : "Run History");
  els.runMeta.textContent = selectedRun
    ? current?.metadata?.prompt || current?.metadata?.task || `${vis.length} visible events`
    : pipe
      ? `${pipelineWorkspace(pipe) || "No workspace selected"}`
      : "Create or select a pipeline.";
  els.summary.innerHTML = metrics(vis);
  els.timeline.innerHTML = vis.map(spanRow).join("") || '<div class="empty">No trace events.</div>';
  els.model.innerHTML = vis.filter((e) => modelKinds.has(e.kind)).map(spanRow).join("") || '<div class="empty">No model events.</div>';
  els.terminal.innerHTML = vis.filter((e) => termKinds.has(e.kind)).map(terminalBlock).join("") || '<div class="empty">No terminal events.</div>';
  els.files.innerHTML = vis.filter((e) => fileKinds.has(e.kind)).map(fileBlock).join("") || '<div class="empty">No file or lock events.</div>';
  els.assignments.innerHTML = assignmentRows();
  els.agents.innerHTML = agentRows(vis);
  els.live.textContent = paused ? "paused" : "live";
  renderQuestion();
  bindEventClicks();
}
async function loadPipelines() {
  pipelines = await fetch("/pipelines").then((r) => r.json());
  if (!pipelines.find((p) => p.pipeline_id === selectedPipeline)) selectedPipeline = pipelines[0]?.pipeline_id || "";
  const pipe = currentPipeline();
  if (pipe && !els.workspaceInput.value) els.workspaceInput.value = pipe.workspace || "";
}
async function loadRuns() {
  runs = await fetch("/runs").then((r) => r.json());
}
async function refreshAll() {
  const keepRun = selectedRun;
  await loadPipelines();
  await loadRuns();
  if (keepRun && runs.some((r) => r.run_id === keepRun)) {
    await selectRun(keepRun, { skipRefresh: true });
  } else {
    selectedRun = "";
    events = [];
    assignments = [];
    lastSequence = 0;
    render();
  }
}
async function selectPipeline(id) {
  selectedPipeline = id;
  selectedRun = "";
  events = [];
  assignments = [];
  lastSequence = 0;
  const pipe = currentPipeline();
  els.workspaceInput.value = pipe?.workspace || "";
  els.pipelineSelect.value = id;
  connect();
  render();
}
async function selectRun(id, opts = {}) {
  selectedRun = id;
  events = [];
  assignments = [];
  lastSequence = 0;
  const run = runs.find((r) => r.run_id === id);
  const meta = run?.metadata || {};
  selectedPipeline = meta.pipeline_id || "trackaiteam";
  if (meta.workspace) els.workspaceInput.value = meta.workspace;
  if (id) {
    events = await fetch(`/runs/${encodeURIComponent(id)}/events`).then((r) => r.json());
    assignments = await fetch(`/runs/${encodeURIComponent(id)}/assignments`)
      .then((r) => r.json())
      .catch(() => []);
    lastSequence = Math.max(0, ...events.map((e) => Number(e.sequence || 0)));
  }
  if (!opts.skipRefresh) connect();
  render();
}
function connect() {
  if (source) source.close();
  if (paused || !selectedRun) {
    els.status.textContent = selectedRun ? "paused" : "select a run";
    return;
  }
  const qs = [];
  qs.push(`run_id=${encodeURIComponent(selectedRun)}`);
  if (lastSequence) qs.push(`after=${lastSequence}`);
  source = new EventSource("/events" + (qs.length ? "?" + qs.join("&") : ""));
  source.onopen = () => (els.status.textContent = "connected");
  source.onerror = () => (els.status.textContent = "disconnected");
  source.onmessage = (ev) => {
    const e = JSON.parse(ev.data);
    if (e.run_id === selectedRun) {
      events.push(e);
      lastSequence = Math.max(lastSequence, Number(e.sequence || 0));
      events = events.slice(-2000);
      loadRuns().then(render);
    }
  };
}
async function createPipeline() {
  const res = await fetch("/pipelines", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: "Untitled Pipeline", workspace: "" }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "failed to create pipeline");
  await loadPipelines();
  await loadRuns();
  expandedPipelines.add(data.pipeline_id);
  await selectPipeline(data.pipeline_id);
}
async function savePipelineWorkspace() {
  const pipe = currentPipeline();
  const workspace = els.workspaceInput.value.trim();
  if (!pipe || !workspace) {
    render();
    return;
  }
  pipe.workspace = workspace;
  renderRunHistory();
  try {
    const res = await fetch(`/pipelines/${encodeURIComponent(pipe.pipeline_id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace }),
    });
    if (res.ok) {
      const updated = await res.json();
      const index = pipelines.findIndex((p) => p.pipeline_id === updated.pipeline_id);
      if (index >= 0) pipelines[index] = updated;
      render();
    }
  } catch (err) {
    els.status.textContent = err.message || String(err);
  }
}
async function loadWorkspaceBrowser(path = "") {
  const qs = path ? `?path=${encodeURIComponent(path)}` : "";
  els.fsCurrent.textContent = "Loading folders...";
  els.fsEntries.innerHTML = '<div class="empty">Loading accessible folders...</div>';
  els.useWorkspace.disabled = true;
  const res = await fetch(`/fs${qs}`);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `folder browser failed with HTTP ${res.status}`);
  }
  fsCurrentPath = data.current || "";
  fsParentPath = data.parent || "";
  els.fsCurrent.textContent = fsCurrentPath || "No folder selected";
  els.useWorkspace.disabled = !fsCurrentPath;
  els.fsUp.disabled = !fsParentPath;
  els.fsRoots.innerHTML = (data.roots || [])
    .map((root) => `<button type="button" data-fs-path="${esc(root.path)}">${esc(root.name)}</button>`)
    .join("");
  els.fsEntries.innerHTML =
    (data.entries || [])
      .map((entry) => `<button type="button" class="fs-entry" data-fs-path="${esc(entry.path)}"><span>${esc(entry.name)}</span><small>${esc(entry.path)}</small></button>`)
      .join("") || '<div class="empty">No accessible folders.</div>';
  document.querySelectorAll("#workspaceModal [data-fs-path]").forEach((button) => {
    button.onclick = () => loadWorkspaceBrowser(button.dataset.fsPath || "");
  });
}
async function chooseWorkspace() {
  const initial = els.workspaceInput.value.trim();
  els.workspaceModal.classList.remove("hidden");
  els.workspaceHint.textContent = "Browsing real local folders from the trackaiteam server.";
  try {
    await loadWorkspaceBrowser(initial);
  } catch (err) {
    els.fsCurrent.textContent = "Folder browser failed";
    els.fsEntries.innerHTML = `<div class="empty">${esc(err.message || String(err))}</div>`;
    els.workspaceHint.textContent = err.message || String(err);
  }
}
async function useCurrentWorkspace() {
  if (!fsCurrentPath) return;
  els.workspaceInput.value = fsCurrentPath;
  els.workspaceModal.classList.add("hidden");
  els.workspaceHint.textContent = `Selected workspace: ${fsCurrentPath}`;
  await savePipelineWorkspace();
}
async function startRun() {
  const task = els.taskInput.value.trim();
  const workspace = els.workspaceInput.value.trim();
  const pipelineId = els.pipelineSelect.value || selectedPipeline;
  if (!task || !workspace || !pipelineId) {
    els.status.textContent = "task, workspace, and pipeline are required";
    return;
  }
  selectedPipeline = pipelineId;
  els.startRun.disabled = true;
  els.status.textContent = "starting run...";
  try {
    await savePipelineWorkspace();
    els.status.textContent = "sending run request...";
    const res = await fetch("/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task, workspace, pipeline_id: pipelineId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "failed");
    els.status.textContent = `started ${data.run_name || data.run_id}`;
    selectedPipeline = data.pipeline_id;
    expandedPipelines.add(data.pipeline_id);
    await loadPipelines();
    await loadRuns();
    els.status.textContent = "loading run events...";
    await selectRun(data.run_id);
  } catch (err) {
    els.status.textContent = err.message || String(err);
  } finally {
    els.startRun.disabled = false;
  }
}
async function sendAnswer() {
  const answer = els.answerInput.value.trim();
  if (!answer || !selectedRun) return;
  els.sendAnswer.disabled = true;
  els.status.textContent = "sending answer...";
  try {
    const res = await fetch(`/runs/${encodeURIComponent(selectedRun)}/answers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer }),
    });
    const data = await res.json();
    if (!res.ok) {
      els.status.textContent = data.error || "answer failed";
      return;
    }
    if (!events.some((e) => e.event_id === data.event_id)) {
      events.push(data);
      lastSequence = Math.max(lastSequence, Number(data.sequence || 0));
    }
    els.answerInput.value = "";
    els.status.textContent = "answer sent";
    render();
    connect();
    await loadRuns();
    await selectRun(selectedRun, { skipRefresh: true });
  } catch (err) {
    els.status.textContent = err.message || String(err);
  } finally {
    els.sendAnswer.disabled = false;
  }
}

document.querySelectorAll(".tab-head button").forEach(
  (b) =>
    (b.onclick = () => {
      activeTab = b.dataset.tab;
      document.querySelectorAll(".tab-head button").forEach((x) => x.classList.toggle("active", x === b));
      document.querySelectorAll(".tab-pane").forEach((p) => p.classList.toggle("active", p.id === activeTab));
    })
);
els.pause.onclick = () => {
  paused = !paused;
  els.pause.textContent = paused ? "Resume" : "Pause";
  if (paused && source) source.close();
  else connect();
  render();
};
els.refresh.onclick = () => refreshAll().catch((err) => (els.status.textContent = err.message || String(err)));
els.newPipeline.onclick = () => createPipeline().catch((err) => (els.status.textContent = err.message || String(err)));
els.chooseWorkspace.onclick = chooseWorkspace;
els.closeWorkspaceModal.onclick = () => els.workspaceModal.classList.add("hidden");
els.fsUp.onclick = () => fsParentPath && loadWorkspaceBrowser(fsParentPath);
els.useWorkspace.onclick = () => useCurrentWorkspace().catch((err) => (els.status.textContent = err.message || String(err)));
els.startRun.onclick = startRun;
els.sendAnswer.onclick = sendAnswer;
els.pipelineSelect.onchange = () => selectPipeline(els.pipelineSelect.value);
els.workspaceInput.onchange = savePipelineWorkspace;
els.workspaceInput.oninput = () => {
  const pipe = currentPipeline();
  if (pipe) pipe.workspace = els.workspaceInput.value.trim();
  renderRunHistory();
};
els.statusFilter.onchange = renderRunHistory;
els.agent.oninput = render;
els.kind.oninput = render;
els.errors.onchange = render;
refreshAll().then(() => {
  render();
});

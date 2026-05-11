from __future__ import annotations

from .core.runtime import AgentRuntime
from .test.workflows import register_default_agents
from .tracing.store import TraceStore


def run_demo(
    *,
    trace_root: str | None = None,
    run_id: str = "demo-run",
    prompt: str = "Demo AI Team event-driven trace",
    timeout: float = 10.0,
) -> str:
    runtime = AgentRuntime(store=TraceStore(trace_root))
    register_default_agents(runtime)
    handle = runtime.start_run(run_id=run_id, prompt=prompt, metadata={"source": "demo"})
    handle.wait(timeout=timeout)
    runtime.shutdown()
    return handle.run_id

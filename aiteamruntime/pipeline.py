from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Callable, Iterable

from .core.contracts import AgentContract
from .core.events import AgentEvent
from .core.runtime import AgentContext, AgentRuntime, AgentSpec

TriggerPredicate = Callable[[AgentEvent], bool]
AgentHandler = Callable[[AgentContext, AgentEvent], object]


def _tag_kinds(predicate: TriggerPredicate, kinds: Iterable[str]) -> TriggerPredicate:
    """Attach ``_triggers_kinds`` so the runtime can index this predicate."""
    setattr(predicate, "_triggers_kinds", frozenset(kinds))
    return predicate


def kinds_of(predicate: TriggerPredicate) -> frozenset[str]:
    """Return the kind whitelist this predicate is known to match (empty = catch-all)."""
    return getattr(predicate, "_triggers_kinds", None) or frozenset()


def on_runtime_start(stage: str = "classify") -> TriggerPredicate:
    return _tag_kinds(
        lambda event: event.agent_id == "runtime" and event.kind == "classifying" and event.stage in {"", stage},
        {"classifying"},
    )


def after_done(agent_id: str, stage: str) -> TriggerPredicate:
    def _trigger(event: AgentEvent) -> bool:
        return event.agent_id == agent_id and event.kind == "done" and (
            event.stage == stage or str((event.payload or {}).get("stage") or "") == stage
        )

    return _tag_kinds(_trigger, {"done"})


def node_agent_id(node_id: str) -> str:
    return f"node:{node_id}"


def node_start_stage(node_id: str) -> str:
    return f"node:{node_id}:start"


def node_role_stage(node_id: str, agent_id: str) -> str:
    return f"node:{node_id}:role:{agent_id}"


def node_done_stage(node_id: str) -> str:
    return f"node:{node_id}:done"


def after_node(node_id: str) -> TriggerPredicate:
    return after_done(node_agent_id(node_id), node_done_stage(node_id))


def on_event(kind: str, *, agent_id: str = "", stage: str = "") -> TriggerPredicate:
    def _trigger(event: AgentEvent) -> bool:
        if event.kind != kind:
            return False
        if agent_id and event.agent_id != agent_id:
            return False
        if stage and event.stage != stage and str((event.payload or {}).get("stage") or "") != stage:
            return False
        return True

    return _tag_kinds(_trigger, {kind})


def assigned_to(agent_id: str) -> TriggerPredicate:
    return _tag_kinds(
        lambda event: event.kind in {"assigned", "reassigned"} and str((event.payload or {}).get("assigned_worker") or "") == agent_id,
        {"assigned", "reassigned"},
    )


def any_of(*predicates: TriggerPredicate) -> TriggerPredicate:
    """Logical OR of predicates. Result is indexable iff every input is indexable."""
    combined: TriggerPredicate = lambda event: any(p(event) for p in predicates)
    kinds: set[str] = set()
    for pred in predicates:
        ks = kinds_of(pred)
        if not ks:
            return combined  # one input is catch-all → fall back to catch-all
        kinds.update(ks)
    return _tag_kinds(combined, kinds)


@dataclass(frozen=True)
class RoleDefinition:
    agent_id: str
    handler: AgentHandler
    trigger: TriggerPredicate
    label: str = ""
    lane: str = ""
    contract: AgentContract | None = None

    def to_spec(self) -> AgentSpec:
        return AgentSpec(
            agent_id=self.agent_id,
            handler=self.handler,
            trigger=self.trigger,
            label=self.label,
            lane=self.lane or self.agent_id,
            triggers_kinds=kinds_of(self.trigger),
            contract=self.contract,
        )


@dataclass(frozen=True)
class NodeDefinition:
    node_id: str
    trigger: TriggerPredicate
    roles: tuple[RoleDefinition, ...]
    mode: str = "sequential"
    label: str = ""
    lane: str = ""
    requires_resources: frozenset[str] = frozenset()
    """Resources this node needs exclusively. Empty = no lock acquired."""
    depends_on: tuple[str, ...] = ()
    """Other node_ids that must finish first. Currently advisory metadata."""
    lock_timeout: float = 30.0
    priority: int = 0
    """Higher priority makes the node less likely to be a deadlock victim."""

    def register(self, runtime: AgentRuntime) -> AgentRuntime:
        if self.mode not in {"sequential", "parallel"}:
            raise ValueError("node mode must be 'sequential' or 'parallel'")
        if not self.roles:
            return runtime

        node_agent = node_agent_id(self.node_id)
        start_stage = node_start_stage(self.node_id)
        done_stage = node_done_stage(self.node_id)
        role_stages = {role.agent_id: node_role_stage(self.node_id, role.agent_id) for role in self.roles}
        pending_runs: set[str] = set()
        started_runs: set[str] = set()
        gate_lock = threading.RLock()

        def _is_dependency_done(run_id: str, dep: str) -> bool:
            dep_stage = node_done_stage(dep)
            dep_agent = node_agent_id(dep)
            return any(
                event.get("agent_id") == dep_agent and event.get("kind") == "done" and event.get("stage") == dep_stage
                for event in runtime.store.read_events(run_id)
            )

        def _dependencies_done(run_id: str) -> bool:
            return all(_is_dependency_done(run_id, dep) for dep in self.depends_on)

        def _is_dependency_event(event: AgentEvent) -> bool:
            return any(after_node(dep)(event) for dep in self.depends_on)

        start_trigger = _tag_kinds(
            lambda event: self.trigger(event) or (bool(self.depends_on) and _is_dependency_event(event)),
            (set(kinds_of(self.trigger)) | ({"done"} if self.depends_on else set())) or {"done"},
        )

        def _start_node(ctx: AgentContext, event: AgentEvent) -> None:
            original_trigger = self.trigger(event)
            with gate_lock:
                if ctx.run_id in started_runs:
                    return
                if original_trigger:
                    pending_runs.add(ctx.run_id)
                elif ctx.run_id not in pending_runs:
                    return
                if not _dependencies_done(ctx.run_id):
                    ctx.emit(
                        "node_blocked",
                        {
                            "node": self.node_id,
                            "reason": "waiting for dependencies",
                            "depends_on": list(self.depends_on),
                        },
                        status="waiting",
                        stage=start_stage,
                        role_state="waiting",
                    )
                    return
                pending_runs.discard(ctx.run_id)
                started_runs.add(ctx.run_id)
            # If this node declared exclusive resources, acquire the lock now.
            # The handler thread blocks until the lock is granted or rejected.
            if self.requires_resources:
                from .resources.locks import LockBlocked, LockRequest

                request = LockRequest(
                    run_id=ctx.run_id,
                    node_id=self.node_id,
                    resources=self.requires_resources,
                    timeout=self.lock_timeout,
                    priority=self.priority,
                    depends_on=frozenset(self.depends_on),
                )
                try:
                    handle = ctx.runtime.locks.acquire(request)
                except LockBlocked as exc:
                    ctx.emit(
                        "node_blocked",
                        {
                            "node": self.node_id,
                            "reason": exc.reason,
                            "owner_node_id": exc.owner_node_id,
                            "wait_for_resources": sorted(exc.contested),
                        },
                        status="deadlock" if exc.reason == "deadlock" else ("timeout" if exc.reason == "timeout" else "blocked"),
                        stage=start_stage,
                        role_state="blocked",
                    )
                    return
                ctx.emit(
                    "node_locked",
                    {"node": self.node_id, "resources": sorted(self.requires_resources)},
                    stage=start_stage,
                    role_state="running",
                )
            ctx.emit(
                "done",
                {"node": self.node_id, "stage": start_stage, "mode": self.mode},
                stage=start_stage,
                role_state="done",
            )

        runtime.register(
            AgentSpec(
                node_agent,
                _start_node,
                start_trigger,
                label=self.label or f"{self.node_id} node start",
                lane=self.lane or self.node_id,
                triggers_kinds=kinds_of(start_trigger),
            )
        )

        for index, role in enumerate(self.roles):
            trigger = self._role_trigger(index)
            runtime.register(self._role_spec(role, trigger, role_stages[role.agent_id]))

        join_trigger = _tag_kinds(
            lambda event, _stages=set(role_stages.values()): event.kind == "done" and event.stage in _stages,
            {"done"},
        )
        runtime.register(
            AgentSpec(
                node_agent,
                self._join_handler(tuple(role.agent_id for role in self.roles), done_stage),
                join_trigger,
                label=self.label or f"{self.node_id} node join",
                lane=self.lane or self.node_id,
                triggers_kinds={"done"},
            )
        )
        return runtime

    def _role_trigger(self, index: int) -> TriggerPredicate:
        if self.mode == "parallel" or index == 0:
            return after_done(node_agent_id(self.node_id), node_start_stage(self.node_id))
        previous = self.roles[index - 1]
        return after_done(previous.agent_id, node_role_stage(self.node_id, previous.agent_id))

    def _role_spec(self, role: RoleDefinition, trigger: TriggerPredicate, completion_stage: str) -> AgentSpec:
        def _handler(ctx: AgentContext, event: AgentEvent) -> object:
            result = role.handler(ctx, event)
            ctx.emit(
                "done",
                {"node": self.node_id, "role": role.agent_id, "stage": completion_stage},
                stage=completion_stage,
                role_state="done",
            )
            return result

        return AgentSpec(
            agent_id=role.agent_id,
            handler=_handler,
            trigger=trigger,
            label=role.label,
            lane=role.lane or role.agent_id,
            triggers_kinds=kinds_of(trigger),
            contract=role.contract,
        )

    def _join_handler(self, role_ids: tuple[str, ...], done_stage: str) -> AgentHandler:
        join_lock = threading.RLock()
        completed_by_run: dict[str, set[str]] = {}
        required = set(role_ids)
        node_id = self.node_id
        requires_resources = self.requires_resources

        def _release_lock(ctx: AgentContext, *, status: str) -> None:
            """Release the node's resource lock, if it acquired one. Idempotent."""
            if not requires_resources:
                return
            if ctx.runtime.locks.release_node(ctx.run_id, node_id):
                ctx.emit(
                    "node_released",
                    {"node": node_id, "resources": sorted(requires_resources), "status": status},
                    status=status if status in {"done", "error", "timeout", "deadlock"} else "done",
                    stage=done_stage,
                    role_state="done",
                )

        def _handler(ctx: AgentContext, event: AgentEvent) -> None:
            role_id = str((event.payload or {}).get("role") or event.agent_id)
            if role_id not in required:
                return
            with join_lock:
                completed = completed_by_run.setdefault(ctx.run_id, set())
                completed.add(role_id)
                if completed != required:
                    return
                completed_by_run.pop(ctx.run_id, None)
            # All roles done — release the node's lock (if any) and signal join.
            _release_lock(ctx, status="done")
            ctx.emit(
                "done",
                {"node": node_id, "stage": done_stage, "roles": list(role_ids)},
                stage=done_stage,
                role_state="done",
            )

        return _handler


@dataclass(frozen=True)
class PipelineDefinition:
    roles: tuple[RoleDefinition, ...]
    nodes: tuple[NodeDefinition, ...] = ()

    def register(self, runtime: AgentRuntime) -> AgentRuntime:
        for role in self.roles:
            runtime.register(role.to_spec())
        for node in self.nodes:
            node.register(runtime)
        return runtime


class NodeBuilder:
    def __init__(
        self,
        parent: "PipelineBuilder",
        node_id: str,
        trigger: TriggerPredicate,
        *,
        mode: str = "sequential",
        label: str = "",
        lane: str = "",
        requires_resources: Iterable[str] = (),
        depends_on: Iterable[str] = (),
        lock_timeout: float = 30.0,
        priority: int = 0,
    ) -> None:
        self._parent = parent
        self._node_id = node_id
        self._trigger = trigger
        self._mode = mode
        self._label = label
        self._lane = lane
        self._requires_resources = frozenset(str(item) for item in requires_resources)
        self._depends_on = tuple(str(item) for item in depends_on)
        self._lock_timeout = float(lock_timeout)
        self._priority = int(priority)
        self._roles: list[RoleDefinition] = []

    def role(
        self,
        agent_id: str,
        handler: AgentHandler,
        *,
        label: str = "",
        lane: str = "",
        contract: AgentContract | None = None,
    ) -> "NodeBuilder":
        self._roles.append(
            RoleDefinition(
                agent_id=agent_id,
                handler=handler,
                trigger=lambda _event: False,
                label=label,
                lane=lane,
                contract=contract,
            )
        )
        return self

    def end(self) -> "PipelineBuilder":
        self._parent._nodes.append(
            NodeDefinition(
                node_id=self._node_id,
                trigger=self._trigger,
                roles=tuple(self._roles),
                mode=self._mode,
                label=self._label,
                lane=self._lane,
                requires_resources=self._requires_resources,
                depends_on=self._depends_on,
                lock_timeout=self._lock_timeout,
                priority=self._priority,
            )
        )
        return self._parent


class PipelineBuilder:
    """Small declarative builder for user-defined runtime pipelines."""

    def __init__(self) -> None:
        self._roles: list[RoleDefinition] = []
        self._nodes: list[NodeDefinition] = []

    def role(
        self,
        agent_id: str,
        handler: AgentHandler,
        trigger: TriggerPredicate,
        *,
        label: str = "",
        lane: str = "",
        contract: AgentContract | None = None,
    ) -> "PipelineBuilder":
        self._roles.append(
            RoleDefinition(
                agent_id=agent_id,
                handler=handler,
                trigger=trigger,
                label=label,
                lane=lane,
                contract=contract,
            )
        )
        return self

    def on_start(
        self,
        agent_id: str,
        handler: AgentHandler,
        *,
        stage: str = "classify",
        label: str = "",
        lane: str = "",
        contract: AgentContract | None = None,
    ) -> "PipelineBuilder":
        return self.role(agent_id, handler, on_runtime_start(stage), label=label, lane=lane, contract=contract)

    def after_done(
        self,
        agent_id: str,
        handler: AgentHandler,
        *,
        after_agent_id: str,
        after_stage: str,
        label: str = "",
        lane: str = "",
        contract: AgentContract | None = None,
    ) -> "PipelineBuilder":
        return self.role(
            agent_id,
            handler,
            after_done(after_agent_id, after_stage),
            label=label,
            lane=lane,
            contract=contract,
        )

    def assigned_worker(
        self,
        agent_id: str,
        handler: AgentHandler,
        *,
        label: str = "",
        lane: str = "",
        contract: AgentContract | None = None,
    ) -> "PipelineBuilder":
        return self.role(agent_id, handler, assigned_to(agent_id), label=label, lane=lane, contract=contract)

    def node(
        self,
        node_id: str,
        trigger: TriggerPredicate,
        *,
        mode: str = "sequential",
        label: str = "",
        lane: str = "",
        requires_resources: Iterable[str] = (),
        depends_on: Iterable[str] = (),
        lock_timeout: float = 30.0,
        priority: int = 0,
    ) -> NodeBuilder:
        return NodeBuilder(
            self,
            node_id,
            trigger,
            mode=mode,
            label=label,
            lane=lane,
            requires_resources=requires_resources,
            depends_on=depends_on,
            lock_timeout=lock_timeout,
            priority=priority,
        )

    def after_node(
        self,
        agent_id: str,
        handler: AgentHandler,
        *,
        node_id: str,
        label: str = "",
        lane: str = "",
        contract: AgentContract | None = None,
    ) -> "PipelineBuilder":
        return self.role(agent_id, handler, after_node(node_id), label=label, lane=lane, contract=contract)

    def build(self) -> PipelineDefinition:
        return PipelineDefinition(tuple(self._roles), tuple(self._nodes))

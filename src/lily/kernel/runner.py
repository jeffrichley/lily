"""Layer 2: Graph execution runner."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lily.kernel.artifact_store import ArtifactStore
from lily.kernel.env_snapshot import (
    ENVIRONMENT_SNAPSHOT_SCHEMA_ID,
    capture_environment_snapshot,
    register_observability_schemas,
)
from lily.kernel.executors.local_command import ExecResult, run_local_command
from lily.kernel.gate_engine import GateExecuteOptions, execute_gate
from lily.kernel.gate_models import register_gate_schemas
from lily.kernel.graph_models import (
    ExecutorSpec,
    GraphSpec,
    StepSpec,
    topological_order,
)
from lily.kernel.paths import LOGS_DIR
from lily.kernel.policy_models import (
    POLICY_VIOLATION_SCHEMA_ID,
    PolicyViolationPayload,
    SafetyPolicy,
    register_policy_schemas,
)
from lily.kernel.routing_models import (
    RoutingAction,
    RoutingActionType,
    RoutingContext,
    RoutingEngine,
)
from lily.kernel.run import KERNEL_VERSION
from lily.kernel.run_state import (
    RunState,
    RunStatus,
    StepRunRecord,
    StepStatus,
    create_initial_run_state,
    load_run_state,
    save_run_state_atomic,
)
from lily.kernel.schema_registry import SchemaRegistry
from lily.kernel.write_path_enforcement import (
    check_write_paths,
    get_modified_paths,
    snapshot_mtimes,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _workspace_root_from_run_root(run_root: Path) -> Path:
    """Derive workspace root from run_root (.iris/runs/<run_id> -> workspace).

    Args:
        run_root: Run directory path (.iris/runs/<run_id>).

    Returns:
        Workspace root (parent of .iris).
    """
    return run_root.resolve().parent.parent.parent


def _artifact_hashes_for_ids(
    store: ArtifactStore, artifact_ids: list[str]
) -> dict[str, str]:
    """Build artifact_id -> sha256 map for IDs that exist in the store.

    Args:
        store: Artifact store to look up refs.
        artifact_ids: List of artifact IDs.

    Returns:
        Map of artifact_id to sha256 for those present in store.
    """
    out: dict[str, str] = {}
    for aid in artifact_ids:
        ref = store.get_ref(aid)
        if ref is not None:
            out[aid] = ref.sha256
    return out


def _duration_ms(started_at: str | None, finished_at: str | None) -> int | None:
    """Compute duration in ms from ISO timestamps. None if either missing.

    Args:
        started_at: ISO start timestamp.
        finished_at: ISO finish timestamp.

    Returns:
        Duration in milliseconds or None if either timestamp missing/invalid.
    """
    if not started_at or not finished_at:
        return None
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
        delta = end - start
        return int(delta.total_seconds() * 1000)
    except (ValueError, TypeError):
        return None


class _ApplyRoutingContext:
    """Bundled arguments for _apply_routing_action (keeps param count ≤5)."""

    def __init__(
        self,
        state: RunState,
        run_root: Path,
        step_id: str,
        rec: StepRunRecord,
        step: StepSpec,
    ) -> None:
        self.state = state
        self.run_root = run_root
        self.step_id = step_id
        self.rec = rec
        self.step = step


def _ensure_initial_run_state(run_root: Path, graph: GraphSpec) -> RunState:
    """Load or create initial RunState. Capture env snapshot for new runs.

    Args:
        run_root: Run directory root.
        graph: Graph spec for initial step records.

    Returns:
        RunState (loaded or newly created and persisted).
    """
    state = load_run_state(run_root)
    if state is not None:
        return state
    state = create_initial_run_state(str(run_root.name), graph)
    run_id = str(run_root.name)
    workspace_root = _workspace_root_from_run_root(run_root)
    store = ArtifactStore(run_root, run_id)
    registry = SchemaRegistry()
    register_gate_schemas(registry)
    register_policy_schemas(registry)
    register_observability_schemas(registry)
    payload = capture_environment_snapshot(
        workspace_root, kernel_version=KERNEL_VERSION
    )
    ref = store.put_envelope(
        ENVIRONMENT_SNAPSHOT_SCHEMA_ID,
        payload,
        meta_fields={
            "producer_id": "kernel",
            "producer_kind": "system",
            "inputs": [],
        },
        artifact_name="environment_snapshot",
    )
    state.environment_snapshot_ref = ref.artifact_id
    save_run_state_atomic(run_root, state)
    return state


def _run_dry_run_gates(
    run_root: Path,
    state: RunState,
    step_by_id: dict[str, StepSpec],
    topo: list[str],
) -> RunState:
    """Run gates only, no step execution. Mutates state, saves, returns it.

    Args:
        run_root: Run directory root.
        state: Current run state.
        step_by_id: Step ID to StepSpec map.
        topo: Topological order of step IDs.

    Returns:
        Updated RunState (mutated and persisted).
    """
    run_id = str(run_root.name)
    store = ArtifactStore(run_root, run_id)
    registry = SchemaRegistry()
    register_gate_schemas(registry)
    for sid in topo:
        step = step_by_id[sid]
        if not step.gates:
            continue
        step_rec = state.step_records.get(sid)
        for gate in step.gates:
            execute_gate(
                gate,
                run_root,
                store,
                registry,
                options=GateExecuteOptions(
                    attempt=step_rec.attempts if step_rec else 1,
                ),
            )
    state.updated_at = _now_iso()
    save_run_state_atomic(run_root, state)
    return state


def _run_final_run_gates(
    run_root: Path, graph: GraphSpec, state: RunState
) -> RunState | None:
    """Run run_gates; if a required gate fails, apply routing and return state.

    Args:
        run_root: Run directory.
        graph: Graph spec (run_gates).
        state: Current run state.

    Returns:
        Updated state if required gate failed, else None.
    """
    run_gates = graph.run_gates
    if not run_gates:
        return None
    run_id = str(run_root.name)
    store = ArtifactStore(run_root, run_id)
    registry = SchemaRegistry()
    register_gate_schemas(registry)
    required_failed = False
    for gate in run_gates:
        _, gate_ok = execute_gate(
            gate,
            run_root,
            store,
            registry,
            options=GateExecuteOptions(attempt=1),
        )
        if gate.required and not gate_ok:
            required_failed = True
            break
    if not required_failed:
        return None
    return _apply_run_gate_failure_state(run_root, graph, state, run_gates)


def _apply_run_gate_failure_state(
    run_root: Path,
    graph: GraphSpec,
    state: RunState,
    run_gates: list,
) -> RunState:
    """Apply routing for run-gate failure and persist state.

    Args:
        run_root: Run directory.
        graph: Graph spec (routing_rules).
        state: Current run state (mutated).
        run_gates: List of run gate specs.

    Returns:
        Updated state (failed/blocked).
    """
    failed_run_gate = next((g for g in run_gates if g.required), None)
    context = RoutingContext(
        step_status="succeeded",
        gate_status="failed",
        gate_id=failed_run_gate.gate_id if failed_run_gate else None,
    )
    action = RoutingEngine.evaluate(context, graph.routing_rules)
    state.status = RunStatus.FAILED
    if action.type == RoutingActionType.ESCALATE:
        state.status = RunStatus.BLOCKED
        state.escalation_reason = action.reason or "run gate failed"
        state.escalation_step_id = None
    state.current_step_id = None
    state.updated_at = _now_iso()
    save_run_state_atomic(run_root, state)
    return state


def _finalize_when_no_eligible(
    run_root: Path, graph: GraphSpec, state: RunState
) -> RunState:
    """Determine final status when no eligible steps; run gates if all succeeded.

    Args:
        run_root: Run directory root.
        graph: Graph spec (run_gates).
        state: Current run state.

    Returns:
        Updated RunState with final status (SUCCEEDED/FAILED/BLOCKED).
    """
    all_succeeded = all(
        r.status == StepStatus.SUCCEEDED for r in state.step_records.values()
    )
    any_failed = any(r.status == StepStatus.FAILED for r in state.step_records.values())
    if all_succeeded and graph.run_gates:
        early = _run_final_run_gates(run_root, graph, state)
        if early is not None:
            return early
    if all_succeeded:
        state.status = RunStatus.SUCCEEDED
    elif any_failed:
        state.status = RunStatus.FAILED
    else:
        state.status = RunStatus.BLOCKED
    state.current_step_id = None
    state.updated_at = _now_iso()
    save_run_state_atomic(run_root, state)
    return state


class _StepExecutionContext:
    """Bundled args for step-execution helpers (keeps param count ≤5)."""

    def __init__(
        self,
        run_root: Path,
        state: RunState,
        step_id: str,
        rec: StepRunRecord,
        step: StepSpec,
    ) -> None:
        self.run_root = run_root
        self.state = state
        self.step_id = step_id
        self.rec = rec
        self.step = step


def _fail_tool_not_allowed(
    ctx: _StepExecutionContext,
    store: ArtifactStore,
) -> RunState:
    """Record tool_not_allowed violation, fail step and run. Mutates state, saves.

    Args:
        ctx: Step execution context.
        store: Artifact store for violation envelope.

    Returns:
        Updated state (failed).
    """
    registry = SchemaRegistry()
    register_gate_schemas(registry)
    register_policy_schemas(registry)
    violation_payload = PolicyViolationPayload(
        step_id=ctx.step_id,
        violation_type="tool_not_allowed",
        details=f"executor kind {ctx.step.executor.kind!r} not in allowed_tools",
        timestamp=datetime.now(UTC),
    )
    ref = store.put_envelope(
        POLICY_VIOLATION_SCHEMA_ID,
        violation_payload,
        meta_fields={
            "producer_id": "kernel",
            "producer_kind": "system",
            "inputs": [],
        },
        artifact_name=f"policy_violation_{ctx.step_id}",
    )
    ctx.rec.policy_violation_ids.append(ref.artifact_id)
    context = RoutingContext(policy_violation=True, step_id=ctx.step_id)
    RoutingEngine.evaluate(context, [])
    ctx.rec.status = StepStatus.FAILED
    ctx.rec.finished_at = _now_iso()
    ctx.rec.last_error = (
        f"Policy violation: tool {ctx.step.executor.kind!r} not in allowed_tools"
    )
    ctx.state.current_step_id = None
    ctx.state.status = RunStatus.FAILED
    ctx.state.updated_at = _now_iso()
    save_run_state_atomic(ctx.run_root, ctx.state)
    return ctx.state


def _fail_unsupported_executor(
    run_root: Path, state: RunState, rec: StepRunRecord, step: StepSpec
) -> RunState:
    """Fail step for unsupported executor. Mutates state, saves.

    Args:
        run_root: Run directory.
        state: Run state (mutated).
        rec: Step run record (mutated).
        step: Step spec.

    Returns:
        Updated state (failed).
    """
    rec.status = StepStatus.FAILED
    rec.finished_at = _now_iso()
    rec.last_error = f"Unsupported executor: {step.executor}"
    state.current_step_id = None
    state.status = RunStatus.FAILED
    state.updated_at = _now_iso()
    save_run_state_atomic(run_root, state)
    return state


def _check_write_violation_and_fail(
    ctx: _StepExecutionContext,
    store: ArtifactStore,
    mtime_before: dict[str, float],
    policy: SafetyPolicy,
) -> RunState | None:
    """Check write paths; if violation, record and fail.

    Returns state if failed, None if ok.

    Args:
        ctx: Step execution context.
        store: Artifact store for violation envelope.
        mtime_before: Snapshot before step.
        policy: Safety policy for write paths.

    Returns:
        RunState if violation (failed), None if ok.
    """
    mtime_after = snapshot_mtimes(ctx.run_root)
    modified = get_modified_paths(mtime_before, mtime_after)
    ok, violation_details = check_write_paths(
        modified,
        ctx.run_root,
        policy.allow_write_paths,
        policy.deny_write_paths,
        exclude_prefixes=[LOGS_DIR],
    )
    if ok or not violation_details:
        return None
    run_id = str(ctx.run_root.name)
    store = ArtifactStore(ctx.run_root, run_id)
    registry = SchemaRegistry()
    register_gate_schemas(registry)
    register_policy_schemas(registry)
    violation_payload = PolicyViolationPayload(
        step_id=ctx.step_id,
        violation_type="write_denied",
        details=violation_details,
        timestamp=datetime.now(UTC),
    )
    ref = store.put_envelope(
        POLICY_VIOLATION_SCHEMA_ID,
        violation_payload,
        meta_fields={
            "producer_id": "kernel",
            "producer_kind": "system",
            "inputs": [],
        },
        artifact_name=f"policy_violation_{ctx.step_id}",
    )
    ctx.rec.policy_violation_ids.append(ref.artifact_id)
    context = RoutingContext(policy_violation=True, step_id=ctx.step_id)
    RoutingEngine.evaluate(context, [])
    ctx.rec.status = StepStatus.FAILED
    ctx.rec.last_error = f"Policy violation: {violation_details}"
    ctx.state.current_step_id = None
    ctx.state.status = RunStatus.FAILED
    ctx.state.updated_at = _now_iso()
    save_run_state_atomic(ctx.run_root, ctx.state)
    return ctx.state


def _apply_routing_action(ctx: _ApplyRoutingContext, action: RoutingAction) -> bool:
    """Apply RoutingAction to state. True = continue loop, False = return.

    Mutates state and rec.

    Args:
        ctx: Bundled context (state, run_root, step_id, rec, step).
        action: Routing action to apply.

    Returns:
        True to continue loop, False to return from loop.
    """
    state, run_root, step_id, rec = ctx.state, ctx.run_root, ctx.step_id, ctx.rec
    action_type = action.type
    target_step_id = action.target_step_id
    reason = action.reason
    if action_type == RoutingActionType.RETRY_STEP:
        rec.status = StepStatus.PENDING
        state.current_step_id = None
        state.forced_next_step_id = None
        state.updated_at = _now_iso()
        save_run_state_atomic(run_root, state)
        return True
    if action_type == RoutingActionType.GOTO_STEP and target_step_id:
        rec.status = (
            StepStatus.FAILED
            if rec.status != StepStatus.SUCCEEDED
            else StepStatus.SUCCEEDED
        )
        state.current_step_id = None
        state.forced_next_step_id = target_step_id
        state.updated_at = _now_iso()
        save_run_state_atomic(run_root, state)
        return True
    if action_type == RoutingActionType.ESCALATE:
        rec.status = (
            StepStatus.FAILED if rec.status != StepStatus.SUCCEEDED else rec.status
        )
        state.status = RunStatus.BLOCKED
        state.escalation_reason = reason or "escalated"
        state.escalation_step_id = step_id
        state.current_step_id = None
        state.forced_next_step_id = None
        state.updated_at = _now_iso()
        save_run_state_atomic(run_root, state)
        return False
    if action_type == RoutingActionType.ABORT_RUN:
        rec.status = StepStatus.FAILED
        state.status = RunStatus.FAILED
        state.current_step_id = None
        state.forced_next_step_id = None
        state.updated_at = _now_iso()
        save_run_state_atomic(run_root, state)
        return False
    # continue
    return True


class _RunLoopContext:
    """Bundled args for run loop helpers."""

    def __init__(
        self,
        run_root: Path,
        graph: GraphSpec,
        state: RunState,
        step_by_id: dict[str, StepSpec],
        safety_policy: SafetyPolicy | None,
    ) -> None:
        self.run_root = run_root
        self.graph = graph
        self.state = state
        self.step_by_id = step_by_id
        self.safety_policy = safety_policy or SafetyPolicy.default_policy()


def _compute_eligible(
    state: RunState, topo: list[str], step_by_id: dict[str, StepSpec]
) -> list[str]:
    """Return step IDs that are PENDING and have all deps succeeded.

    Args:
        state: Current run state.
        topo: Topological order of step IDs.
        step_by_id: Step ID to StepSpec map.

    Returns:
        List of eligible step IDs.
    """
    eligible = []
    for sid in topo:
        step_rec = state.step_records.get(sid)
        if not step_rec or step_rec.status != StepStatus.PENDING:
            continue
        step = step_by_id[sid]
        deps_ok = all(
            state.step_records.get(d, StepRunRecord(step_id=d)).status
            == StepStatus.SUCCEEDED
            for d in step.depends_on
        )
        if deps_ok:
            eligible.append(sid)
    return eligible


def _run_step_gates_and_apply_routing(
    step_ctx: _StepExecutionContext,
    graph: GraphSpec,
) -> bool:
    """Run step gates; if required gate fails, apply routing.

    Args:
        step_ctx: Step execution context.
        graph: Graph spec (routing_rules).

    Returns:
        False if loop should exit, True to continue.
    """
    run_root, state, step_id, rec, step = (
        step_ctx.run_root,
        step_ctx.state,
        step_ctx.step_id,
        step_ctx.rec,
        step_ctx.step,
    )
    store = ArtifactStore(run_root, str(run_root.name))
    registry = SchemaRegistry()
    register_gate_schemas(registry)
    required_failed = False
    failed_gate_id: str | None = None
    failed_reason: str | None = None
    for gate in step.gates:
        artifact_id, gate_ok = execute_gate(
            gate,
            run_root,
            store,
            registry,
            options=GateExecuteOptions(attempt=rec.attempts),
        )
        rec.gate_results.append(artifact_id)
        rec.gate_result_ids.append(artifact_id)
        if gate.required and not gate_ok:
            required_failed = True
            failed_gate_id = gate.gate_id
            failed_reason = failed_reason or f"gate failed: {gate.gate_id}"
    if not required_failed:
        return True
    rec.last_error = failed_reason
    context = RoutingContext(
        step_status="succeeded",
        gate_status="failed",
        step_id=step_id,
        gate_id=failed_gate_id,
    )
    action = RoutingEngine.evaluate(context, graph.routing_rules)
    action_with_reason = action.model_copy(
        update={"reason": failed_reason or action.reason}
    )
    apply_ctx = _ApplyRoutingContext(state, run_root, step_id, rec, step)
    return _apply_routing_action(apply_ctx, action_with_reason)


def _check_executor_policy(
    step_ctx: _StepExecutionContext,
    policy: SafetyPolicy,
    store: ArtifactStore,
) -> RunState | None:
    """Check tool allowlist and executor support. Returns failed state or None.

    Args:
        step_ctx: Step execution context.
        policy: Safety policy (allowed_tools).
        store: Artifact store.

    Returns:
        RunState if policy/executor failure, None if ok.
    """
    step = step_ctx.step
    if step.executor.kind not in policy.allowed_tools:
        return _fail_tool_not_allowed(step_ctx, store)
    if (
        not isinstance(step.executor, ExecutorSpec)
        or step.executor.kind != "local_command"
    ):
        return _fail_unsupported_executor(
            step_ctx.run_root, step_ctx.state, step_ctx.rec, step
        )
    return None


def _handle_step_failure(
    step_ctx: _StepExecutionContext,
    graph: GraphSpec,
    result: ExecResult,
) -> RunState | None:
    """Handle failed step: record error, increment attempts, apply routing.

    Args:
        step_ctx: Step execution context.
        graph: Graph spec (routing_rules).
        result: Executor result (failure).

    Returns:
        RunState if loop should exit, None to continue.
    """
    rec = step_ctx.rec
    step = step_ctx.step
    rec.last_error = result.error_message or f"exit code {result.returncode}"
    rec.attempts += 1
    max_retries = step.retry_policy.max_retries if step.retry_policy else 0
    retry_exhausted = rec.attempts > max_retries
    context = RoutingContext(
        step_status="failed",
        retry_exhausted=retry_exhausted,
        step_id=step_ctx.step_id,
    )
    action = RoutingEngine.evaluate(context, graph.routing_rules)
    apply_ctx = _ApplyRoutingContext(
        step_ctx.state, step_ctx.run_root, step_ctx.step_id, rec, step
    )
    if _apply_routing_action(apply_ctx, action):
        return None
    return step_ctx.state


def _complete_step_success(
    step_ctx: _StepExecutionContext,
    graph: GraphSpec,
    store: ArtifactStore,
    mtime_before: dict[str, float] | None,
    safety_policy: SafetyPolicy,
) -> RunState | None:
    """Record step success, check write policy, run step gates.

    Returns state to exit loop or None to continue.

    Args:
        step_ctx: Step execution context.
        graph: Graph spec.
        store: Artifact store.
        mtime_before: Snapshot before step (None to skip write check).
        safety_policy: Safety policy for write paths.

    Returns:
        RunState if loop should exit, None to continue.
    """
    if mtime_before is not None:
        failed_state = _check_write_violation_and_fail(
            step_ctx, store, mtime_before, safety_policy
        )
        if failed_state is not None:
            return failed_state
    rec = step_ctx.rec
    rec.status = StepStatus.SUCCEEDED
    step_ctx.state.current_step_id = None
    step_ctx.state.updated_at = _now_iso()
    save_run_state_atomic(step_ctx.run_root, step_ctx.state)
    if step_ctx.step.gates:
        should_continue = _run_step_gates_and_apply_routing(step_ctx, graph)
        if not should_continue:
            return step_ctx.state
    step_ctx.state.updated_at = _now_iso()
    save_run_state_atomic(step_ctx.run_root, step_ctx.state)
    return None


def _execute_one_step(ctx: _RunLoopContext, step_id: str) -> RunState | None:
    """Execute one pending step. Returns state if loop should exit, None to continue.

    Args:
        ctx: Run loop context.
        step_id: Step to execute.

    Returns:
        RunState if loop should exit, None to continue.
    """
    run_root, graph, state, step_by_id = (
        ctx.run_root,
        ctx.graph,
        ctx.state,
        ctx.step_by_id,
    )
    step = step_by_id[step_id]
    rec = state.step_records[step_id]
    store = ArtifactStore(run_root, str(run_root.name))

    input_ids: list[str] = list(step.input_artifact_ids)
    for dep in step.depends_on:
        dep_rec = state.step_records.get(dep)
        if dep_rec:
            input_ids.extend(dep_rec.produced_artifact_ids)
    rec.input_artifact_hashes = _artifact_hashes_for_ids(store, input_ids)

    rec.status = StepStatus.RUNNING
    rec.started_at = _now_iso()
    state.current_step_id = step_id
    state.updated_at = _now_iso()
    save_run_state_atomic(run_root, state)

    step_ctx = _StepExecutionContext(run_root, state, step_id, rec, step)
    policy_fail = _check_executor_policy(step_ctx, ctx.safety_policy, store)
    if policy_fail is not None:
        return policy_fail

    mtime_before: dict[str, float] | None = None
    if ctx.safety_policy.allow_write_paths or ctx.safety_policy.deny_write_paths:
        mtime_before = snapshot_mtimes(run_root)

    timeout_s = step.timeout_policy.timeout_s if step.timeout_policy else None
    result = run_local_command(
        step.executor,
        run_root=run_root,
        step_id=step_id,
        attempt=rec.attempts,
        timeout_s=timeout_s,
    )

    rec.finished_at = _now_iso()
    rec.log_paths = result.log_paths
    rec.duration_ms = _duration_ms(rec.started_at, rec.finished_at)
    rec.executor_summary = {
        "argv": step.executor.argv,
        "cwd": step.executor.cwd,
        "env": step.executor.env,
    }
    rec.output_artifact_hashes = _artifact_hashes_for_ids(
        store, rec.produced_artifact_ids
    )

    if result.success:
        return _complete_step_success(
            step_ctx, graph, store, mtime_before, ctx.safety_policy
        )
    return _handle_step_failure(step_ctx, graph, result)


def run_graph(
    run_root: Path,
    graph: GraphSpec,
    *,
    safety_policy: SafetyPolicy | None = None,
    dry_run_gates: bool = False,
) -> RunState:
    """Execute a validated DAG. Load/create RunState, run steps in dependency order.

    Atomic RunState writes; bounded retries. dry_run_gates: gates only, no steps.

    Args:
        run_root: Run directory.
        graph: Validated graph spec.
        safety_policy: Optional safety policy (default used if None).
        dry_run_gates: If True, run step gates only, no step execution.

    Returns:
        Final RunState (running/succeeded/failed/blocked).
    """
    state = _ensure_initial_run_state(run_root, graph)

    for rec in state.step_records.values():
        if rec.status == StepStatus.RUNNING:
            rec.status = StepStatus.FAILED
            rec.last_error = "interrupted"
            rec.finished_at = _now_iso()
    state.current_step_id = None
    state.status = RunStatus.RUNNING
    save_run_state_atomic(run_root, state)

    step_by_id = {s.step_id: s for s in graph.steps}
    topo = topological_order(graph)

    if dry_run_gates:
        return _run_dry_run_gates(run_root, state, step_by_id, topo)

    loop_ctx = _RunLoopContext(run_root, graph, state, step_by_id, safety_policy)
    while True:
        eligible = _compute_eligible(state, topo, step_by_id)
        if state.forced_next_step_id:
            if state.forced_next_step_id in eligible:
                eligible = [state.forced_next_step_id]
            else:
                state.forced_next_step_id = None

        if not eligible:
            return _finalize_when_no_eligible(run_root, graph, state)

        result = _execute_one_step(loop_ctx, eligible[0])
        if result is not None:
            return result

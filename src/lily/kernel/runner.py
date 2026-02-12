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
from lily.kernel.executors.local_command import run_local_command
from lily.kernel.gate_engine import execute_gate
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
from lily.kernel.run_state import (
    RunState,
    RunStatus,
    StepRunRecord,
    StepStatus,
    create_initial_run_state,
    load_run_state,
    save_run_state_atomic,
)
from lily.kernel.routing_models import (
    RoutingActionType,
    RoutingContext,
    RoutingEngine,
)
from lily.kernel.run import KERNEL_VERSION
from lily.kernel.schema_registry import SchemaRegistry
from lily.kernel.write_path_enforcement import (
    check_write_paths,
    get_modified_paths,
    snapshot_mtimes,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _workspace_root_from_run_root(run_root: Path) -> Path:
    """Derive workspace root from run_root (.iris/runs/<run_id> -> workspace)."""
    return run_root.resolve().parent.parent.parent


def _artifact_hashes_for_ids(
    store: ArtifactStore, artifact_ids: list[str]
) -> dict[str, str]:
    """Build artifact_id -> sha256 map for IDs that exist in the store."""
    out: dict[str, str] = {}
    for aid in artifact_ids:
        ref = store.get_ref(aid)
        if ref is not None:
            out[aid] = ref.sha256
    return out


def _duration_ms(started_at: str | None, finished_at: str | None) -> int | None:
    """Compute duration in milliseconds from ISO timestamps. Returns None if either missing."""
    if not started_at or not finished_at:
        return None
    from datetime import datetime

    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
        delta = end - start
        return int(delta.total_seconds() * 1000)
    except (ValueError, TypeError):
        return None


def _apply_routing_action(
    action_type: str,
    state: RunState,
    step_id: str,
    rec: StepRunRecord,
    step: StepSpec,
    run_root: Path,
    reason: str | None = None,
    target_step_id: str | None = None,
) -> bool:
    """
    Apply RoutingAction to state. Returns True if loop should continue, False to return.
    Mutates state and rec.
    """
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


def run_graph(
    run_root: Path,
    graph: GraphSpec,
    *,
    safety_policy: SafetyPolicy | None = None,
    dry_run_gates: bool = False,
) -> RunState:
    """
    Execute a validated DAG. Loads or creates RunState, runs steps in dependency order.
    Uses atomic writes for RunState. Supports bounded retries.
    When dry_run_gates=True, only runs gates (no step execution); does not mutate step status.
    """
    state = load_run_state(run_root)
    if state is None:
        state = create_initial_run_state(str(run_root.name), graph)
        # Layer 5: capture environment snapshot and store envelope before first persist
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

    # Resume: any running step -> failed with reason interrupted
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
        # Layer 5: run gates only; do not execute steps or mutate step status.
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
                    attempt=step_rec.attempts if step_rec else 1,
                )
        state.updated_at = _now_iso()
        save_run_state_atomic(run_root, state)
        return state

    while True:
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

        if state.forced_next_step_id:
            if state.forced_next_step_id in eligible:
                eligible = [state.forced_next_step_id]
            else:
                state.forced_next_step_id = None

        if not eligible:
            # No more work: check if all succeeded or some failed
            all_succeeded = all(
                r.status == StepStatus.SUCCEEDED for r in state.step_records.values()
            )
            any_failed = any(
                r.status == StepStatus.FAILED for r in state.step_records.values()
            )
            if all_succeeded:
                # Run-level gates (optional)
                if graph.run_gates:
                    run_id = str(run_root.name)
                    store = ArtifactStore(run_root, run_id)
                    registry = SchemaRegistry()
                    register_gate_schemas(registry)
                    required_failed = False
                    for gate in graph.run_gates:
                        _, gate_ok = execute_gate(
                            gate,
                            run_root,
                            store,
                            registry,
                            attempt=1,
                        )
                        if gate.required and not gate_ok:
                            required_failed = True
                            break
                    if required_failed:
                        failed_run_gate = next(
                            (g for g in (graph.run_gates or []) if g.required),
                            None,
                        )
                        context = RoutingContext(
                            step_status="succeeded",
                            gate_status="failed",
                            gate_id=failed_run_gate.gate_id
                            if failed_run_gate
                            else None,
                        )
                        action = RoutingEngine.evaluate(context, graph.routing_rules)
                        state.status = RunStatus.FAILED
                        state.current_step_id = None
                        state.updated_at = _now_iso()
                        if action.type == RoutingActionType.ESCALATE:
                            state.status = RunStatus.BLOCKED
                            state.escalation_reason = action.reason or "run gate failed"
                            state.escalation_step_id = None
                        save_run_state_atomic(run_root, state)
                        return state
                state.status = RunStatus.SUCCEEDED
            elif any_failed:
                state.status = RunStatus.FAILED
            else:
                state.status = RunStatus.BLOCKED
            state.current_step_id = None
            state.updated_at = _now_iso()
            save_run_state_atomic(run_root, state)
            return state

        # Pick first eligible by topological order (already sorted)
        step_id = eligible[0]
        step = step_by_id[step_id]
        rec = state.step_records[step_id]
        run_id = str(run_root.name)
        store = ArtifactStore(run_root, run_id)

        # Layer 5: input artifact hashes from deps and step inputs
        input_ids: list[str] = list(step.input_artifact_ids)
        for dep in step.depends_on:
            dep_rec = state.step_records.get(dep)
            if dep_rec:
                input_ids.extend(dep_rec.produced_artifact_ids)
        rec.input_artifact_hashes = _artifact_hashes_for_ids(store, input_ids)

        # Mark running
        rec.status = StepStatus.RUNNING
        rec.started_at = _now_iso()
        state.current_step_id = step_id
        state.updated_at = _now_iso()
        save_run_state_atomic(run_root, state)

        # Tool allowlist check (Layer 4)
        policy = safety_policy or SafetyPolicy.default_policy()
        if step.executor.kind not in policy.allowed_tools:
            registry = SchemaRegistry()
            register_gate_schemas(registry)
            register_policy_schemas(registry)
            violation_payload = PolicyViolationPayload(
                step_id=step_id,
                violation_type="tool_not_allowed",
                details=f"executor kind {step.executor.kind!r} not in allowed_tools",
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
                artifact_name=f"policy_violation_{step_id}",
            )
            rec.policy_violation_ids.append(ref.artifact_id)
            context = RoutingContext(policy_violation=True, step_id=step_id)
            action = RoutingEngine.evaluate(context, [])
            rec.status = StepStatus.FAILED
            rec.finished_at = _now_iso()
            rec.last_error = (
                f"Policy violation: tool {step.executor.kind!r} not in allowed_tools"
            )
            state.current_step_id = None
            state.status = RunStatus.FAILED
            state.updated_at = _now_iso()
            save_run_state_atomic(run_root, state)
            return state

        # Execute (only local_command for now)
        if (
            not isinstance(step.executor, ExecutorSpec)
            or step.executor.kind != "local_command"
        ):
            rec.status = StepStatus.FAILED
            rec.finished_at = _now_iso()
            rec.last_error = f"Unsupported executor: {step.executor}"
            state.current_step_id = None
            state.status = RunStatus.FAILED
            state.updated_at = _now_iso()
            save_run_state_atomic(run_root, state)
            return state

        # Write path snapshot (before step) if policy enforces
        mtime_before: dict[str, float] | None = None
        if policy.allow_write_paths or policy.deny_write_paths:
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
            # Write path enforcement (after step)
            if mtime_before is not None:
                mtime_after = snapshot_mtimes(run_root)
                modified = get_modified_paths(mtime_before, mtime_after)
                ok, violation_details = check_write_paths(
                    modified,
                    run_root,
                    policy.allow_write_paths,
                    policy.deny_write_paths,
                    exclude_prefixes=[LOGS_DIR],
                )
                if not ok and violation_details:
                    run_id = str(run_root.name)
                    store = ArtifactStore(run_root, run_id)
                    registry = SchemaRegistry()
                    register_gate_schemas(registry)
                    register_policy_schemas(registry)
                    violation_payload = PolicyViolationPayload(
                        step_id=step_id,
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
                        artifact_name=f"policy_violation_{step_id}",
                    )
                    rec.policy_violation_ids.append(ref.artifact_id)
                    context = RoutingContext(policy_violation=True, step_id=step_id)
                    RoutingEngine.evaluate(context, [])
                    rec.status = StepStatus.FAILED
                    rec.last_error = f"Policy violation: {violation_details}"
                    state.current_step_id = None
                    state.status = RunStatus.FAILED
                    state.updated_at = _now_iso()
                    save_run_state_atomic(run_root, state)
                    return state
            rec.status = StepStatus.SUCCEEDED
            state.current_step_id = None
            state.updated_at = _now_iso()
            save_run_state_atomic(run_root, state)

            # Run gates after step success
            if step.gates:
                run_id = str(run_root.name)
                store = ArtifactStore(run_root, run_id)
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
                        attempt=rec.attempts,
                    )
                    rec.gate_results.append(artifact_id)
                    rec.gate_result_ids.append(artifact_id)
                    if gate.required and not gate_ok:
                        required_failed = True
                        failed_gate_id = gate.gate_id
                        failed_reason = failed_reason or f"gate failed: {gate.gate_id}"
                if required_failed:
                    rec.last_error = failed_reason
                    context = RoutingContext(
                        step_status="succeeded",
                        gate_status="failed",
                        step_id=step_id,
                        gate_id=failed_gate_id,
                    )
                    action = RoutingEngine.evaluate(context, graph.routing_rules)
                    should_continue = _apply_routing_action(
                        action.type,
                        state,
                        step_id,
                        rec,
                        step,
                        run_root,
                        reason=failed_reason,
                        target_step_id=action.target_step_id,
                    )
                    if not should_continue:
                        return state
                state.updated_at = _now_iso()
                save_run_state_atomic(run_root, state)
            continue

        # Failure: increment attempts, then route
        rec.last_error = result.error_message or f"exit code {result.returncode}"
        rec.attempts += 1
        max_retries = step.retry_policy.max_retries if step.retry_policy else 0
        retry_exhausted = rec.attempts > max_retries
        context = RoutingContext(
            step_status="failed",
            retry_exhausted=retry_exhausted,
            step_id=step_id,
        )
        action = RoutingEngine.evaluate(context, graph.routing_rules)
        should_continue = _apply_routing_action(
            action.type,
            state,
            step_id,
            rec,
            step,
            run_root,
            reason=action.reason,
            target_step_id=action.target_step_id,
        )
        if should_continue:
            continue
        return state

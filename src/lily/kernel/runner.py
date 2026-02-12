"""Layer 2: Graph execution runner."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lily.kernel.executors.local_command import run_local_command
from lily.kernel.graph_models import ExecutorSpec, GraphSpec, topological_order
from lily.kernel.run_state import (
    RunState,
    RunStatus,
    StepRunRecord,
    StepStatus,
    create_initial_run_state,
    load_run_state,
    save_run_state_atomic,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def run_graph(run_root: Path, graph: GraphSpec) -> RunState:
    """
    Execute a validated DAG. Loads or creates RunState, runs steps in dependency order.
    Uses atomic writes for RunState. Supports bounded retries.
    """
    state = load_run_state(run_root)
    if state is None:
        state = create_initial_run_state(str(run_root.name), graph)
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

    while True:
        eligible = []
        for sid in topo:
            rec = state.step_records.get(sid)
            if not rec or rec.status != StepStatus.PENDING:
                continue
            step = step_by_id[sid]
            deps_ok = all(
                state.step_records.get(d, StepRunRecord(step_id=d)).status
                == StepStatus.SUCCEEDED
                for d in step.depends_on
            )
            if deps_ok:
                eligible.append(sid)

        if not eligible:
            # No more work: check if all succeeded or some failed
            all_succeeded = all(
                r.status == StepStatus.SUCCEEDED for r in state.step_records.values()
            )
            any_failed = any(
                r.status == StepStatus.FAILED for r in state.step_records.values()
            )
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

        # Pick first eligible by topological order (already sorted)
        step_id = eligible[0]
        step = step_by_id[step_id]
        rec = state.step_records[step_id]

        # Mark running
        rec.status = StepStatus.RUNNING
        rec.started_at = _now_iso()
        state.current_step_id = step_id
        state.updated_at = _now_iso()
        save_run_state_atomic(run_root, state)

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

        if result.success:
            rec.status = StepStatus.SUCCEEDED
            state.current_step_id = None
            state.updated_at = _now_iso()
            save_run_state_atomic(run_root, state)
            continue

        # Failure: increment attempts then check retry
        rec.last_error = result.error_message or f"exit code {result.returncode}"
        rec.attempts += 1
        max_retries = step.retry_policy.max_retries if step.retry_policy else 0
        if rec.attempts <= max_retries:
            rec.status = StepStatus.PENDING
            state.current_step_id = None
            state.updated_at = _now_iso()
            save_run_state_atomic(run_root, state)
            # Loop again to retry
        else:
            rec.status = StepStatus.FAILED
            state.current_step_id = None
            state.status = RunStatus.FAILED
            state.updated_at = _now_iso()
            save_run_state_atomic(run_root, state)
            return state

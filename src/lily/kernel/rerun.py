"""Layer 2: Replay API - rerun from step."""

from __future__ import annotations

from datetime import UTC, datetime

from lily.kernel.graph_models import GraphSpec
from lily.kernel.run_state import RunState, RunStatus, StepRunRecord, StepStatus


def _downstream_step_ids(graph: GraphSpec, step_id: str) -> set[str]:
    """Return step_id and all steps that depend on it (directly or indirectly).

    Args:
        graph: Graph spec.
        step_id: Starting step id.

    Returns:
        Set of step_id and all downstream step ids.
    """
    step_by_id = {s.step_id: s for s in graph.steps}
    if step_id not in step_by_id:
        return set()
    # Reverse deps: who depends on step_id?
    dependents: dict[str, set[str]] = {sid: set() for sid in step_by_id}
    for s in graph.steps:
        for dep in s.depends_on:
            dependents[dep].add(s.step_id)
    result = {step_id}
    stack = [step_id]
    while stack:
        n = stack.pop()
        for d in dependents[n]:
            if d not in result:
                result.add(d)
                stack.append(d)
    return result


def _reset_step_record(rec: StepRunRecord) -> None:
    """Mark step pending and clear provenance; preserve log_paths.

    Args:
        rec: Step run record to reset (mutated in place).
    """
    rec.status = StepStatus.PENDING
    rec.attempts = 0
    rec.started_at = None
    rec.finished_at = None
    rec.last_error = None
    rec.produced_artifact_ids = []
    rec.input_artifact_hashes = {}
    rec.output_artifact_hashes = {}
    rec.duration_ms = None
    rec.executor_summary = {}
    rec.gate_result_ids = []
    rec.policy_violation_ids = []


def rerun_from(state: RunState, graph: GraphSpec, step_id: str) -> RunState:
    """Mark target and downstream steps pending; clear produced_artifact_ids/provenance.

    Preserves log_paths. Does not delete artifacts. New RunState (caller persists).

    Args:
        state: Current run state (mutated).
        graph: Graph spec for downstream resolution.
        step_id: Step from which to rerun (and all downstream).

    Returns:
        Updated RunState (caller should persist).
    """
    to_reset = _downstream_step_ids(graph, step_id)
    for sid in to_reset:
        rec = state.step_records.get(sid)
        if rec:
            _reset_step_record(rec)
    state.current_step_id = None
    state.status = RunStatus.RUNNING
    state.updated_at = datetime.now(UTC).isoformat()
    return state

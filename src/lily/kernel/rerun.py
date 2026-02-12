"""Layer 2: Replay API - rerun from step."""

from __future__ import annotations

from datetime import UTC, datetime

from lily.kernel.graph_models import GraphSpec
from lily.kernel.run_state import RunState, RunStatus, StepStatus


def _downstream_step_ids(graph: GraphSpec, step_id: str) -> set[str]:
    """Return step_id and all steps that depend on it (directly or indirectly)."""
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


def rerun_from(state: RunState, graph: GraphSpec, step_id: str) -> RunState:
    """
    Mark target step and all downstream steps as pending; clear produced_artifact_ids.
    Does not delete artifacts on disk. Returns a new RunState (caller should persist).
    """
    to_reset = _downstream_step_ids(graph, step_id)
    for sid in to_reset:
        rec = state.step_records.get(sid)
        if rec:
            rec.status = StepStatus.PENDING
            rec.attempts = 0
            rec.started_at = None
            rec.finished_at = None
            rec.last_error = None
            rec.produced_artifact_ids = []
            rec.log_paths = {}
    state.current_step_id = None
    state.status = RunStatus.RUNNING
    state.updated_at = datetime.now(UTC).isoformat()
    return state

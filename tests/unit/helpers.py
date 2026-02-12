"""Test-only helpers for unit tests. Not part of the kernel API."""

from __future__ import annotations

from pathlib import Path

from lily.kernel.graph_models import GraphSpec
from lily.kernel.run_state import (
    RunState,
    create_initial_run_state,
    save_run_state_atomic,
)


def build_run_state_with_step_overrides(
    run_id: str,
    run_root: Path,
    graph: GraphSpec,
    step_overrides: dict[str, dict],
    *,
    save: bool = True,
) -> RunState:
    """Build RunState with step status/artifact overrides (test-only seam).

    step_overrides maps step_id -> dict of StepRunRecord fields to set, e.g.:
        {"a": {"status": StepStatus.SUCCEEDED, "produced_artifact_ids": ["old_1"]}}
    Steps not in step_overrides stay at create_initial_run_state defaults
    (PENDING, empty lists).
    """
    state = create_initial_run_state(run_id, graph)
    new_records = dict(state.step_records)
    for step_id, overrides in step_overrides.items():
        if step_id in new_records:
            new_records[step_id] = new_records[step_id].model_copy(update=overrides)
    state = state.model_copy(update={"step_records": new_records})
    if save:
        save_run_state_atomic(run_root, state)
    return state

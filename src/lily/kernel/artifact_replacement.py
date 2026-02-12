"""Layer 5: Artifact replacement — substitute artifact ID, trigger downstream reset."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lily.kernel.artifact_store import ArtifactStore
from lily.kernel.env_snapshot import (
    ARTIFACT_REPLACEMENT_SCHEMA_ID,
    ArtifactReplacementPayload,
)
from lily.kernel.graph_models import GraphSpec
from lily.kernel.rerun import rerun_from
from lily.kernel.run_state import RunState, save_run_state_atomic


def _replace_in_produced_ids(state: RunState, old_id: str, new_id: str) -> str | None:
    """Replace old_id with new_id in produced_artifact_ids.

    Args:
        state: Current run state to mutate.
        old_id: Artifact ID to replace.
        new_id: New artifact ID.

    Returns:
        Producer step_id if exactly one step had old_id, else None.
    """
    producer_step_id: str | None = None
    for sid, rec in state.step_records.items():
        if old_id in rec.produced_artifact_ids:
            if producer_step_id is None:
                producer_step_id = sid
            rec.produced_artifact_ids = [
                new_id if aid == old_id else aid for aid in rec.produced_artifact_ids
            ]
    return producer_step_id


@dataclass(frozen=True)
class ReplacementSpec:
    """Spec for a single artifact replacement (old_id -> new_id)."""

    old_id: str
    new_id: str
    reason: str


def replace_artifact(
    run_root: Path,
    state: RunState,
    graph: GraphSpec,
    replacement: ReplacementSpec,
) -> RunState:
    """Record an artifact replacement (old_id -> new_id), update RunState references.

    Reset downstream steps so the next run re-executes from the producer step.
    Does not delete artifacts. Caller should persist the returned state.

    Args:
        run_root: Run directory.
        state: Current run state.
        graph: Graph spec for rerun_from.
        replacement: Old ID, new ID, and reason for the replacement.

    Returns:
        Updated RunState (caller should persist).
    """
    run_id = str(run_root.name)
    store = ArtifactStore(run_root, run_id)
    payload = ArtifactReplacementPayload(
        original_artifact_id=replacement.old_id,
        replacement_artifact_id=replacement.new_id,
        reason=replacement.reason,
        timestamp=datetime.now(UTC),
    )
    store.put_envelope(
        ARTIFACT_REPLACEMENT_SCHEMA_ID,
        payload,
        meta_fields={
            "producer_id": "kernel",
            "producer_kind": "system",
            "inputs": [replacement.old_id],
        },
        artifact_name=f"replacement_{replacement.old_id}_to_{replacement.new_id}",
    )

    producer_step_id = _replace_in_produced_ids(
        state, replacement.old_id, replacement.new_id
    )
    if producer_step_id is not None:
        state = rerun_from(state, graph, producer_step_id)

    save_run_state_atomic(run_root, state)
    return state

"""Layer 5: Artifact replacement — substitute artifact ID and trigger downstream reset."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lily.kernel.artifact_store import ArtifactStore
from lily.kernel.env_snapshot import (
    ARTIFACT_REPLACEMENT_SCHEMA_ID,
    ArtifactReplacementPayload,
)
from lily.kernel.graph_models import GraphSpec
from lily.kernel.run_state import RunState, save_run_state_atomic
from lily.kernel.rerun import rerun_from


def replace_artifact(
    run_root: Path,
    state: RunState,
    graph: GraphSpec,
    old_id: str,
    new_id: str,
    reason: str,
) -> RunState:
    """
    Record an artifact replacement (old_id -> new_id), update RunState references,
    and reset downstream steps so the next run re-executes from the producer step.
    Does not delete artifacts. Caller should persist the returned state.
    """
    run_id = str(run_root.name)
    store = ArtifactStore(run_root, run_id)
    payload = ArtifactReplacementPayload(
        original_artifact_id=old_id,
        replacement_artifact_id=new_id,
        reason=reason,
        timestamp=datetime.now(UTC),
    )
    store.put_envelope(
        ARTIFACT_REPLACEMENT_SCHEMA_ID,
        payload,
        meta_fields={
            "producer_id": "kernel",
            "producer_kind": "system",
            "inputs": [old_id],
        },
        artifact_name=f"replacement_{old_id}_to_{new_id}",
    )

    # Update RunState: replace old_id with new_id in produced_artifact_ids
    producer_step_id: str | None = None
    for sid, rec in state.step_records.items():
        if old_id in rec.produced_artifact_ids:
            if producer_step_id is None:
                producer_step_id = sid
            rec.produced_artifact_ids = [
                new_id if aid == old_id else aid for aid in rec.produced_artifact_ids
            ]

    if producer_step_id is not None:
        state = rerun_from(state, graph, producer_step_id)

    save_run_state_atomic(run_root, state)
    return state

"""Layer 2: RunState models and atomic persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic.types import JsonValue

from lily.kernel.atomic_write import atomic_write_json_at
from lily.kernel.graph_models import GraphSpec
from lily.kernel.paths import get_run_state_path


class StepStatus:
    """Step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunStatus:
    """Run-level status."""

    CREATED = "created"
    RUNNING = "running"
    BLOCKED = "blocked"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


class StepRunRecord(BaseModel):
    """Per-step execution record."""

    step_id: str
    status: str = StepStatus.PENDING
    attempts: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    last_error: str | None = None
    produced_artifact_ids: list[str] = Field(default_factory=list)
    log_paths: dict[str, str] = Field(default_factory=dict)
    gate_results: list[str] = Field(default_factory=list)
    # Layer 5 provenance
    input_artifact_hashes: dict[str, str] = Field(
        default_factory=dict
    )  # artifact_id -> sha256
    output_artifact_hashes: dict[str, str] = Field(default_factory=dict)
    duration_ms: int | None = None
    executor_summary: dict[str, Any] = Field(default_factory=dict)
    gate_result_ids: list[str] = Field(default_factory=list)
    policy_violation_ids: list[str] = Field(default_factory=list)


class RunState(BaseModel):
    """Runtime state for a run. Stored at .iris/runs/<run_id>/run_state.json."""

    run_id: str
    status: str = RunStatus.CREATED
    graph_id: str
    current_step_id: str | None = None
    step_records: dict[str, StepRunRecord] = Field(default_factory=dict)
    updated_at: str = ""
    escalation_reason: str | None = None
    escalation_step_id: str | None = None
    forced_next_step_id: str | None = None  # for goto_step routing
    environment_snapshot_ref: str | None = (
        None  # Layer 5: artifact_id of environment_snapshot.v1
    )

    def to_file_dict(self) -> dict[str, JsonValue]:
        """Serialize for JSON file.

        Returns:
            JSON-serializable dict.
        """
        return self.model_dump(mode="json")

    @classmethod
    def from_file_dict(cls, d: dict[str, JsonValue]) -> RunState:
        """Deserialize from JSON file.

        Args:
            d: JSON-compatible dict (e.g. from file).

        Returns:
            RunState instance.
        """
        return cls.model_validate(d)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_initial_run_state(run_id: str, graph: GraphSpec) -> RunState:
    """Create empty RunState for a graph. All steps start as pending.

    Args:
        run_id: Run identifier.
        graph: Graph spec; one step record per step.

    Returns:
        RunState with all steps pending.
    """
    step_records = {s.step_id: StepRunRecord(step_id=s.step_id) for s in graph.steps}
    now = _now_iso()
    return RunState(
        run_id=run_id,
        status=RunStatus.CREATED,
        graph_id=graph.graph_id,
        current_step_id=None,
        step_records=step_records,
        updated_at=now,
    )


def load_run_state(run_root: Path) -> RunState | None:
    """Load RunState from run_root. Returns None if file does not exist.

    Args:
        run_root: Run directory root.

    Returns:
        RunState or None if run_state.json does not exist.
    """
    path = get_run_state_path(run_root)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    return RunState.from_file_dict(data)


def save_run_state_atomic(run_root: Path, state: RunState) -> None:
    """Write RunState atomically: temp -> fsync -> rename -> fsync dir.

    Args:
        run_root: Run directory root.
        state: RunState to persist.
    """
    atomic_write_json_at(
        run_root,
        get_run_state_path(run_root),
        state.to_file_dict(),
        "run_state",
    )

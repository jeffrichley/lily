"""Layer 2: RunState models and atomic persistence."""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

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

    def to_file_dict(self) -> dict[str, Any]:
        """Serialize for JSON file."""
        return self.model_dump(mode="json")

    @classmethod
    def from_file_dict(cls, d: dict[str, Any]) -> RunState:
        """Deserialize from JSON file."""
        return cls.model_validate(d)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_initial_run_state(run_id: str, graph: GraphSpec) -> RunState:
    """Create empty RunState for a graph. All steps start as pending."""
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
    """Load RunState from run_root. Returns None if file does not exist."""
    path = get_run_state_path(run_root)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    return RunState.from_file_dict(data)


def save_run_state_atomic(run_root: Path, state: RunState) -> None:
    """
    Write RunState atomically: write temp -> fsync temp -> rename.
    Same pattern as write_manifest_atomic.
    """
    run_state_path = get_run_state_path(run_root)
    temp_path = run_root / f".run_state.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    content = json.dumps(state.to_file_dict(), indent=2)
    content_bytes = content.encode("utf-8")
    try:
        fd = os.open(
            str(temp_path),
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o644,
        )
        try:
            os.write(fd, content_bytes)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(temp_path, run_state_path)
        try:
            dir_fd = os.open(str(run_root), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)

"""Run manifest schema and read/write. Layer 0."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from lily.kernel.atomic_write import atomic_write_json_at
from lily.kernel.paths import get_manifest_path


# Minimal ref for manifest work_order_ref (full ArtifactRef from artifact store).
class WorkOrderRef(BaseModel):
    """Work order artifact ref (run_id + artifact_id, Phase A)."""

    run_id: str
    artifact_id: str


class RunStatus:
    """Manifest status values."""

    CREATED = "created"
    RUNNING = "running"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


class RunManifest(BaseModel):
    """Authoritative run record. Written atomically under run lock."""

    run_id: str
    created_at: str  # ISO 8601
    updated_at: str
    kernel_version: str
    status: str  # RunStatus.*
    work_order_ref: WorkOrderRef | None = None
    workspace_snapshot: dict[str, Any] | None = None

    def to_file_dict(self) -> dict[str, Any]:
        """Serialize for JSON file (work_order_ref as dict or null).

        Returns:
            Dict suitable for JSON serialization.
        """
        d = self.model_dump(mode="json")
        return d

    @classmethod
    def from_file_dict(cls, d: dict[str, Any]) -> RunManifest:
        """Deserialize from JSON file.

        Args:
            d: Dict loaded from JSON.

        Returns:
            Validated RunManifest.
        """
        return cls.model_validate(d)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_initial_manifest(
    run_id: str,
    kernel_version: str,
    work_order_ref: WorkOrderRef | None = None,
    workspace_snapshot: dict[str, Any] | None = None,
) -> RunManifest:
    """Build manifest for a new run (status=created).

    Args:
        run_id: Run identifier.
        kernel_version: Kernel version string.
        work_order_ref: Optional work order artifact ref.
        workspace_snapshot: Optional workspace snapshot dict.

    Returns:
        RunManifest with status=created.
    """
    now = _now_iso()
    return RunManifest(
        run_id=run_id,
        created_at=now,
        updated_at=now,
        kernel_version=kernel_version,
        status=RunStatus.CREATED,
        work_order_ref=work_order_ref,
        workspace_snapshot=workspace_snapshot,
    )


def read_manifest(run_root: Path) -> RunManifest:
    """Load and parse run_manifest.json. For resume/audit.

    Args:
        run_root: Run directory containing run_manifest.json.

    Returns:
        Parsed RunManifest.

    Raises:
        FileNotFoundError: If manifest file does not exist.
    """
    path = get_manifest_path(run_root)
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    return RunManifest.from_file_dict(data)


def write_manifest_atomic(run_root: Path, manifest: RunManifest) -> None:
    """Write manifest atomically: temp -> fsync -> rename -> fsync dir.

    Caller must hold run lock. Used for manifest only (index is SQLite later).

    Args:
        run_root: Run directory to write manifest into.
        manifest: Manifest to write.
    """
    atomic_write_json_at(
        run_root,
        get_manifest_path(run_root),
        manifest.to_file_dict(),
        "run_manifest",
    )

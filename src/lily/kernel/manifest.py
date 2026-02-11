"""Run manifest schema and read/write. Layer 0."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel


# Minimal ref for manifest's work_order_ref (full ArtifactRef comes with artifact store).
class WorkOrderRef(BaseModel):
    """Reference to a work order artifact. run_id + artifact_id only for Phase A."""

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
        """Serialize for JSON file (work_order_ref as dict or null)."""
        d = self.model_dump(mode="json")
        return d

    @classmethod
    def from_file_dict(cls, d: dict[str, Any]) -> RunManifest:
        """Deserialize from JSON file."""
        return cls.model_validate(d)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_initial_manifest(
    run_id: str,
    kernel_version: str,
    work_order_ref: WorkOrderRef | None = None,
    workspace_snapshot: dict[str, Any] | None = None,
) -> RunManifest:
    """Build manifest for a new run (status=created)."""
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
    """Load and parse run_manifest.json. For resume/audit."""
    from lily.kernel.paths import get_manifest_path

    path = get_manifest_path(run_root)
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    text = path.read_text(encoding="utf-8")
    import json

    data = json.loads(text)
    return RunManifest.from_file_dict(data)


def write_manifest_atomic(run_root: Path, manifest: RunManifest) -> None:
    """
    Write manifest atomically: write temp -> fsync temp -> rename -> fsync dir.
    Caller must hold run lock. Used for manifest only (index is SQLite later).
    """
    import json
    import os
    import uuid

    from lily.kernel.paths import get_manifest_path

    manifest_path = get_manifest_path(run_root)
    # Temp file in same directory so rename is atomic; unique name for concurrent safety
    temp_path = run_root / f".run_manifest.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    content = json.dumps(manifest.to_file_dict(), indent=2)
    content_bytes = content.encode("utf-8")
    try:
        # Open for write, write, fsync (Windows needs write handle for fsync)
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
        # rename to final name (replace so overwrite works on Windows)
        os.replace(temp_path, manifest_path)
        # fsync directory (recommended for durability; skip on Windows - permission denied on dir open)
        try:
            dir_fd = os.open(str(run_root), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass  # e.g. Windows: directory fsync best-effort
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)

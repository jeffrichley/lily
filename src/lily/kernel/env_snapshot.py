"""Layer 5: Observability envelopes — environment snapshot and artifact replacement."""

from __future__ import annotations

import hashlib
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from lily.kernel.schema_registry import SchemaRegistry

ENVIRONMENT_SNAPSHOT_SCHEMA_ID = "environment_snapshot.v1"
ARTIFACT_REPLACEMENT_SCHEMA_ID = "artifact_replacement.v1"


class EnvironmentSnapshotPayload(BaseModel):
    """Payload for environment_snapshot.v1 envelope. Captured at run start."""

    model_config = {"extra": "forbid"}

    python_version: str
    platform: str
    kernel_version: str
    uv_lock_hash: str | None = None
    timestamp: datetime


class ArtifactReplacementPayload(BaseModel):
    """Payload for artifact_replacement.v1 envelope. Records artifact substitution."""

    model_config = {"extra": "forbid"}

    original_artifact_id: str
    replacement_artifact_id: str
    reason: str
    timestamp: datetime


def register_observability_schemas(registry: SchemaRegistry) -> None:
    """Register Layer 5 observability schema(s) on the given registry.

    Args:
        registry: Schema registry to register observability schemas on.
    """
    registry.register(ENVIRONMENT_SNAPSHOT_SCHEMA_ID, EnvironmentSnapshotPayload)
    registry.register(ARTIFACT_REPLACEMENT_SCHEMA_ID, ArtifactReplacementPayload)


def capture_environment_snapshot(
    workspace_root: Path,
    *,
    kernel_version: str,
) -> EnvironmentSnapshotPayload:
    """Collect reproducibility metadata: Python version, platform, kernel version.

    Optional uv.lock hash. Does not perform I/O beyond reading uv.lock if present.

    Args:
        workspace_root: Workspace root (for uv.lock path).
        kernel_version: Kernel version string to record.

    Returns:
        EnvironmentSnapshotPayload with captured metadata.
    """
    uv_lock_hash: str | None = None
    uv_lock_path = workspace_root / "uv.lock"
    if uv_lock_path.is_file():
        h = hashlib.sha256()
        with open(uv_lock_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        uv_lock_hash = h.hexdigest()

    return EnvironmentSnapshotPayload(
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        kernel_version=kernel_version,
        uv_lock_hash=uv_lock_hash,
        timestamp=datetime.now(UTC),
    )

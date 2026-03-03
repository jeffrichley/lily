"""Session persistence and reload helpers."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from lily.session.models import Session

# Persisted session schema v1 is the current and only supported version today.
# Keep `SESSION_SCHEMA_VERSION` as the canonical source for payload envelopes.
SESSION_SCHEMA_VERSION = 1
MIN_SUPPORTED_SESSION_SCHEMA_VERSION = 1

MigrationStep = Callable[[dict[str, object]], dict[str, object]]


class SessionStoreError(RuntimeError):
    """Base persistence error for session store operations."""


class SessionSchemaVersionError(SessionStoreError):
    """Raised when persisted payload schema version is unsupported."""


class SessionDecodeError(SessionStoreError):
    """Raised when persisted payload cannot be decoded/validated."""


class PersistedSessionV1(BaseModel):
    """Versioned persisted session payload."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = SESSION_SCHEMA_VERSION
    session: Session


def save_session(session: Session, path: Path) -> None:
    """Persist full session payload atomically.

    Args:
        session: Session payload to persist.
        path: Target file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = PersistedSessionV1(session=session)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(
        payload.model_dump_json(indent=2, by_alias=True),
        encoding="utf-8",
    )
    temp_path.replace(path)


def load_session(path: Path) -> Session:
    """Load persisted session payload from disk.

    Args:
        path: Session file path.

    Returns:
        Loaded session model.

    Raises:
        SessionDecodeError: If JSON decode or payload validation fails.
    """
    raw = path.read_text(encoding="utf-8")
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SessionDecodeError(f"Invalid session JSON: {exc}") from exc

    migrated = _migrate_payload(decoded)
    try:
        payload = PersistedSessionV1.model_validate(migrated)
    except ValidationError as exc:
        raise SessionDecodeError(f"Invalid session payload: {exc}") from exc
    return payload.session


def recover_corrupt_session(path: Path) -> Path | None:
    """Move unreadable/invalid session aside and return backup path.

    Args:
        path: Session file path.

    Returns:
        Backup path when source exists, else None.
    """
    if not path.exists():
        return None
    timestamp = int(time.time())
    backup = path.with_name(f"{path.name}.corrupt-{timestamp}")
    path.replace(backup)
    return backup


def _migrate_payload(payload: object) -> dict[str, object]:
    """Migrate persisted payload into latest schema.

    Contract:
    - migration always happens before Pydantic model validation
    - payloads outside supported version range fail explicitly
    - new versions should add `vN -> vN+1` entries in `_MIGRATION_STEPS`

    Args:
        payload: Decoded JSON payload object.

    Returns:
        Migrated payload matching latest schema.

    Raises:
        SessionDecodeError: If payload is not a JSON object.
        SessionSchemaVersionError: If schema version is unsupported.
    """
    if not isinstance(payload, dict):
        raise SessionDecodeError("Invalid session payload: expected JSON object.")

    version = _read_schema_version(payload)
    if version == SESSION_SCHEMA_VERSION:
        migrated = _clone_payload(payload)
        _migrate_v1_session_defaults(migrated)
        return migrated

    if (
        version < MIN_SUPPORTED_SESSION_SCHEMA_VERSION
        or version > SESSION_SCHEMA_VERSION
    ):
        raise SessionSchemaVersionError(
            f"Unsupported session schema version: {version!r}. "
            f"Expected {SESSION_SCHEMA_VERSION}."
        )

    migrated = _clone_payload(payload)
    for source_version in range(version, SESSION_SCHEMA_VERSION):
        migrate = _MIGRATION_STEPS.get(source_version)
        if migrate is None:
            raise SessionSchemaVersionError(
                f"Unsupported session schema version: {version!r}. "
                f"No migration path from v{source_version} to "
                f"v{source_version + 1}."
            )
        migrated = migrate(migrated)

    migrated["schema_version"] = SESSION_SCHEMA_VERSION
    _migrate_v1_session_defaults(migrated)
    return migrated


def _read_schema_version(payload: dict[str, object]) -> int:
    """Read and validate persisted schema version field.

    Args:
        payload: Decoded persisted payload envelope.

    Returns:
        Integer schema version value from the payload envelope.

    Raises:
        SessionSchemaVersionError: If schema version is missing or not an integer.
    """
    version_raw = payload.get("schema_version")
    if not isinstance(version_raw, int) or isinstance(version_raw, bool):
        raise SessionSchemaVersionError(
            f"Unsupported session schema version: {version_raw!r}. "
            f"Expected {SESSION_SCHEMA_VERSION}."
        )
    return version_raw


def _clone_payload(payload: dict[str, object]) -> dict[str, object]:
    """Clone top-level payload and session object to isolate migration edits.

    Args:
        payload: Decoded persisted payload envelope.

    Returns:
        Shallow-cloned payload with cloned nested `session` dict when present.
    """
    migrated = dict(payload)
    session_raw = migrated.get("session")
    if isinstance(session_raw, dict):
        migrated["session"] = dict(session_raw)
    return migrated


def _migrate_v1_session_defaults(payload: dict[str, object]) -> None:
    """Fill missing V1 session fields with deterministic explicit defaults.

    Args:
        payload: Decoded V1 payload object mutated in place.
    """
    session_raw = payload.get("session")
    if not isinstance(session_raw, dict):
        return
    session_raw.setdefault("active_persona", "default")


# Migration registry keyed by source schema version.
# Example when v2 exists: `{1: _migrate_v1_to_v2}`.
_MIGRATION_STEPS: dict[int, MigrationStep] = {}

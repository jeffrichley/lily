"""Session persistence and reload helpers."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from lily.session.models import Session

SESSION_SCHEMA_VERSION = 1


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
    """Persist full session payload atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = PersistedSessionV1(session=session)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(
        payload.model_dump_json(indent=2, by_alias=True),
        encoding="utf-8",
    )
    temp_path.replace(path)


def load_session(path: Path) -> Session:
    """Load persisted session payload from disk."""
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
    """Move unreadable/invalid session aside and return backup path."""
    if not path.exists():
        return None
    timestamp = int(time.time())
    backup = path.with_name(f"{path.name}.corrupt-{timestamp}")
    path.replace(backup)
    return backup


def _migrate_payload(payload: Any) -> dict[str, Any]:
    """Migrate persisted payload into latest schema.

    Migration stubs for future versions belong here.
    """
    if not isinstance(payload, dict):
        raise SessionDecodeError("Invalid session payload: expected JSON object.")
    version = payload.get("schema_version")
    if version == SESSION_SCHEMA_VERSION:
        return payload
    raise SessionSchemaVersionError(
        f"Unsupported session schema version: {version!r}. "
        f"Expected {SESSION_SCHEMA_VERSION}."
    )


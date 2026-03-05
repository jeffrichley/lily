"""Shared helpers for deterministic MemoryRecord creation/update payloads."""

from __future__ import annotations

from datetime import datetime

from lily.memory.models import MemoryRecord, MemoryStore, MemoryWriteRequest


def memory_update_fields(
    *,
    request: MemoryWriteRequest,
    updated_at: datetime,
) -> dict[str, object]:
    """Build common update fields for remember upsert paths.

    Args:
        request: Memory write payload.
        updated_at: Timestamp to stamp on updated record.

    Returns:
        Dictionary of model update fields.
    """
    return {
        "source": request.source,
        "confidence": request.confidence,
        "tags": request.tags,
        "updated_at": updated_at,
        "preference_type": request.preference_type,
        "stability": request.stability,
        "task_id": request.task_id,
        "session_id": request.session_id,
        "status": request.status,
        "expires_at": request.expires_at,
        "last_verified": request.last_verified,
        "conflict_group": request.conflict_group,
    }


def create_memory_record(  # noqa: PLR0913
    *,
    store: MemoryStore,
    namespace: str,
    content: str,
    request: MemoryWriteRequest,
    now: datetime,
    record_id: str | None = None,
) -> MemoryRecord:
    """Create deterministic MemoryRecord from one write request.

    Args:
        store: Target memory store domain.
        namespace: Logical namespace token.
        content: Normalized memory content.
        request: Memory write request payload.
        now: Timestamp used for created/updated fields.
        record_id: Optional explicit memory id override.

    Returns:
        New MemoryRecord instance.
    """
    payload: dict[str, object] = {
        "schema_version": 1,
        "store": store,
        "namespace": namespace,
        "content": content,
        "source": request.source,
        "confidence": request.confidence,
        "tags": request.tags,
        "created_at": now,
        "updated_at": now,
        "preference_type": request.preference_type,
        "stability": request.stability,
        "task_id": request.task_id,
        "session_id": request.session_id,
        "status": request.status,
        "expires_at": request.expires_at,
        "last_verified": request.last_verified,
        "conflict_group": request.conflict_group,
    }
    if record_id is not None:
        payload["id"] = record_id
    return MemoryRecord(**payload)

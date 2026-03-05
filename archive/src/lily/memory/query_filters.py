"""Shared deterministic query-filter helpers for memory repositories."""

from __future__ import annotations

from datetime import UTC, datetime

from lily.memory.models import MemoryQuery, MemoryRecord


def namespace_matches(*, namespace: str | None, record: MemoryRecord) -> bool:
    """Check namespace constraint.

    Args:
        namespace: Optional required namespace.
        record: Candidate memory record.

    Returns:
        ``True`` when namespace constraint is satisfied.
    """
    if namespace is None:
        return True
    return record.namespace == namespace


def confidence_matches(*, query: MemoryQuery, record: MemoryRecord) -> bool:
    """Check confidence threshold constraint.

    Args:
        query: Memory query payload.
        record: Candidate memory record.

    Returns:
        ``True`` when confidence threshold is satisfied.
    """
    if query.min_confidence is None:
        return True
    return record.confidence >= query.min_confidence


def status_visible(*, query: MemoryQuery, record: MemoryRecord) -> bool:
    """Check status/expiry visibility filters.

    Args:
        query: Memory query payload.
        record: Candidate memory record.

    Returns:
        ``True`` when status/expiry filters allow this record.
    """
    if not query.include_archived and record.status == "archived":
        return False
    if not query.include_conflicted and record.status == "conflicted":
        return False
    return not (
        not query.include_expired
        and record.expires_at is not None
        and record.expires_at <= datetime.now(UTC)
    )


def content_matches(*, query: MemoryQuery, record: MemoryRecord) -> bool:
    """Check text query match.

    Args:
        query: Memory query payload.
        record: Candidate memory record.

    Returns:
        ``True`` when text query matches content.
    """
    needle = query.query.strip().lower()
    if needle == "*":
        return True
    return needle in record.content.lower()

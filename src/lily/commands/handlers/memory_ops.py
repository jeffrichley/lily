"""Shared query/render helpers for `/memory` command handlers."""

from __future__ import annotations

from typing import Any

from lily.commands.handlers._memory_support import resolve_store_file
from lily.commands.types import CommandResult
from lily.memory import (
    ConsolidationResult,
    MemoryError,
    MemoryQuery,
    MemoryRecord,
    PersonalityMemoryRepository,
    TaskMemoryRepository,
)
from lily.memory.langmem_tools import LangMemToolingAdapter
from lily.observability import memory_metrics
from lily.session.models import Session


def build_langmem_adapter(
    session: Session,
) -> tuple[LangMemToolingAdapter | None, CommandResult | None]:
    """Build LangMem adapter from session memory storage roots.

    Args:
        session: Active session context.

    Returns:
        Adapter or deterministic error result.
    """
    store_file = resolve_store_file(session)
    if store_file is None:
        return None, CommandResult.error(
            "Error: memory tooling is unavailable for this session.",
            code="memory_unavailable",
        )
    return LangMemToolingAdapter(store_file=store_file), None


def query_personality(  # noqa: PLR0913
    *,
    repository: PersonalityMemoryRepository,
    namespace: str,
    query: str,
    include_archived: bool = False,
    include_expired: bool = False,
    include_conflicted: bool = False,
    limit: int = 10,
) -> tuple[tuple[MemoryRecord, ...] | None, CommandResult | None]:
    """Query one personality namespace with deterministic error mapping.

    Args:
        repository: Personality repository.
        namespace: Target namespace token.
        query: Query text.
        include_archived: Whether archived records should be included.
        include_expired: Whether expired records should be included.
        include_conflicted: Whether conflicted records should be included.
        limit: Maximum number of records to return.

    Returns:
        Tuple of records-or-none and error-or-none.
    """
    try:
        records = repository.query(
            MemoryQuery(
                query=query,
                namespace=namespace,
                limit=limit,
                include_archived=include_archived,
                include_expired=include_expired,
                include_conflicted=include_conflicted,
            )
        )
    except MemoryError as exc:
        return None, CommandResult.error(f"Error: {exc}", code=exc.code.value)
    return records, None


def query_task(  # noqa: PLR0913
    *,
    repository: TaskMemoryRepository,
    namespace: str,
    query: str,
    include_archived: bool = False,
    include_expired: bool = False,
    include_conflicted: bool = False,
    limit: int = 10,
) -> tuple[tuple[MemoryRecord, ...] | None, CommandResult | None]:
    """Query task namespace with deterministic error mapping.

    Args:
        repository: Task repository.
        namespace: Target task namespace.
        query: Query text.
        include_archived: Whether archived records should be included.
        include_expired: Whether expired records should be included.
        include_conflicted: Whether conflicted records should be included.
        limit: Maximum number of records to return.

    Returns:
        Tuple of records-or-none and error-or-none.
    """
    try:
        records = repository.query(
            MemoryQuery(
                query=query,
                namespace=namespace,
                limit=limit,
                include_archived=include_archived,
                include_expired=include_expired,
                include_conflicted=include_conflicted,
            )
        )
    except MemoryError as exc:
        return None, CommandResult.error(f"Error: {exc}", code=exc.code.value)
    return records, None


def find_personality_record(
    *,
    repository: PersonalityMemoryRepository,
    namespace: str,
    memory_id: str,
) -> tuple[MemoryRecord | None, CommandResult | None]:
    """Find one personality record by id.

    Args:
        repository: Personality repository.
        namespace: Namespace path.
        memory_id: Target record id.

    Returns:
        Record and optional error tuple.
    """
    records, query_error = query_personality(
        repository=repository,
        namespace=namespace,
        query="*",
        include_archived=True,
        include_expired=True,
        include_conflicted=True,
        limit=20,
    )
    if query_error is not None:
        return None, query_error
    assert records is not None
    target = next((record for record in records if record.id == memory_id), None)
    if target is None:
        return None, CommandResult.error(
            f"Error: Memory record '{memory_id}' was not found.",
            code="memory_not_found",
        )
    return target, None


def render_records(
    *,
    query: str,
    records: tuple[MemoryRecord, ...],
    empty_message: str,
) -> CommandResult:
    """Render query results into deterministic command envelope.

    Args:
        query: Query text.
        records: Memory records tuple.
        empty_message: Message used when no records are present.

    Returns:
        Deterministic command result.
    """
    if not records:
        return CommandResult.ok(
            empty_message,
            code="memory_empty",
            data={"count": 0, "query": query},
        )
    for record in records:
        memory_metrics.record_last_verified(last_verified=record.last_verified)
    lines = [f"- {record.id}: {record.content}" for record in records]
    return CommandResult.ok(
        "\n".join(lines),
        code="memory_listed",
        data={
            "count": len(records),
            "query": query,
            "records": [
                {
                    "id": record.id,
                    "namespace": record.namespace,
                    "content": record.content,
                    "updated_at": record.updated_at.isoformat(),
                    "status": record.status,
                    "last_verified": (
                        record.last_verified.isoformat()
                        if record.last_verified is not None
                        else None
                    ),
                    "conflict_group": record.conflict_group,
                    "expires_at": (
                        record.expires_at.isoformat()
                        if record.expires_at is not None
                        else None
                    ),
                }
                for record in records
            ],
        },
    )


def render_tool_rows(
    *,
    query: str,
    rows: tuple[dict[str, Any], ...],
    route: str,
) -> CommandResult:
    """Render LangMem tool search rows with deterministic envelope.

    Args:
        query: Query text.
        rows: Tool-result rows.
        route: Stable route identifier.

    Returns:
        Deterministic command result.
    """
    if not rows:
        return CommandResult.ok(
            "No memory records found.",
            code="memory_empty",
            data={"count": 0, "query": query, "route": route},
        )
    normalized: list[dict[str, object]] = []
    lines: list[str] = []
    for row in rows:
        key = str(row.get("key", "")).strip()
        value = row.get("value", {})
        content = ""
        if isinstance(value, dict):
            content = str(value.get("content", "")).strip()
        if not content:
            continue
        lines.append(f"- {key}: {content}")
        normalized.append(
            {
                "id": key,
                "namespace": row.get("namespace"),
                "content": content,
                "updated_at": row.get("updated_at"),
            }
        )
    if not normalized:
        return CommandResult.ok(
            "No memory records found.",
            code="memory_empty",
            data={"count": 0, "query": query, "route": route},
        )
    return CommandResult.ok(
        "\n".join(lines),
        code="memory_langmem_listed",
        data={
            "count": len(normalized),
            "query": query,
            "route": route,
            "records": normalized,
        },
    )


def render_consolidation_result(result: ConsolidationResult) -> CommandResult:
    """Render consolidation engine result into command envelope.

    Args:
        result: Consolidation result object.

    Returns:
        Deterministic command output.
    """
    status = result.status
    backend = result.backend.value
    proposed = result.proposed
    written = result.written
    skipped = result.skipped
    notes = result.notes
    records = result.records
    memory_metrics.record_consolidation(
        proposed=proposed,
        written=written,
        skipped=skipped,
    )
    if status == "disabled":
        return CommandResult.error(
            "Error: consolidation is disabled by config.",
            code="memory_consolidation_disabled",
            data={"backend": backend},
        )
    summary = (
        f"Consolidation [{backend}] status={status} "
        f"proposed={proposed} written={written} skipped={skipped}"
    )
    return CommandResult.ok(
        summary,
        code="memory_consolidation_ran",
        data={
            "backend": backend,
            "status": status,
            "proposed": proposed,
            "written": written,
            "skipped": skipped,
            "notes": notes,
            "records": records,
        },
    )

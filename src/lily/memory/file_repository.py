"""File-backed implementations for split Lily memory repositories."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from pydantic import ValidationError

from lily.memory.models import (
    MemoryError,
    MemoryErrorCode,
    MemoryQuery,
    MemoryRecord,
    MemoryStore,
    MemoryWriteRequest,
)
from lily.memory.query_filters import (
    confidence_matches,
    content_matches,
    namespace_matches,
    status_visible,
)
from lily.memory.record_factory import create_memory_record, memory_update_fields
from lily.memory.repository import PersonalityMemoryRepository, TaskMemoryRepository
from lily.observability import memory_metrics
from lily.policy import evaluate_memory_write

_PERSONALITY_FILE = "personality_memory.json"
_TASK_FILE = "task_memory.json"


class _FileMemoryStore:
    """Internal JSON-file storage helper for one deterministic memory store."""

    def __init__(self, *, root_dir: Path, store: MemoryStore) -> None:
        """Create file store for one memory domain.

        Args:
            root_dir: Storage root directory.
            store: Target memory store identifier.
        """
        self._root_dir = root_dir
        self._store = store
        self._path = root_dir / (
            _PERSONALITY_FILE if store == MemoryStore.PERSONALITY else _TASK_FILE
        )

    def remember(self, request: MemoryWriteRequest) -> MemoryRecord:
        """Create or upsert memory record by namespace/content hash.

        Args:
            request: Memory write payload.

        Returns:
            Stored memory record.

        Raises:
            MemoryError: If input is invalid or persistence fails.
        """
        normalized_namespace = request.namespace.strip()
        normalized_content = request.content.strip()
        if not normalized_namespace or not normalized_content:
            raise MemoryError(
                MemoryErrorCode.INVALID_INPUT,
                "Invalid memory write input.",
            )
        decision = evaluate_memory_write(normalized_content)
        if not decision.allowed:
            memory_metrics.record_denied_write(namespace=normalized_namespace)
            raise MemoryError(
                MemoryErrorCode.POLICY_DENIED,
                decision.reason,
            )
        records = self._load_records()
        fingerprint = _fingerprint(normalized_namespace, normalized_content)
        now = datetime.now(UTC)
        for index, record in enumerate(records):
            existing_fingerprint = _fingerprint(record.namespace, record.content)
            if existing_fingerprint != fingerprint:
                continue
            updated = record.model_copy(
                update=memory_update_fields(request=request, updated_at=now)
            )
            records[index] = updated
            self._save_records(records)
            memory_metrics.record_write(namespace=normalized_namespace)
            return updated

        created = create_memory_record(
            store=self._store,
            namespace=normalized_namespace,
            content=normalized_content,
            request=request,
            now=now,
        )
        records.append(created)
        self._save_records(records)
        memory_metrics.record_write(namespace=normalized_namespace)
        return created

    def forget(self, memory_id: str) -> None:
        """Delete one memory record by id.

        Args:
            memory_id: Stable memory record id.

        Raises:
            MemoryError: If id is invalid, missing, or persistence fails.
        """
        normalized = memory_id.strip()
        if not normalized:
            raise MemoryError(
                MemoryErrorCode.INVALID_INPUT,
                "Memory id is required.",
            )
        records = self._load_records()
        filtered = [record for record in records if record.id != normalized]
        if len(filtered) == len(records):
            raise MemoryError(
                MemoryErrorCode.NOT_FOUND,
                f"Memory record '{normalized}' was not found.",
            )
        self._save_records(filtered)

    def query(self, query: MemoryQuery) -> tuple[MemoryRecord, ...]:
        """Run deterministic substring query for this store.

        Args:
            query: Query payload.

        Returns:
            Ordered matching memory records.
        """
        records = self._load_records()
        namespace = query.namespace.strip() if query.namespace is not None else None
        matches = [
            record
            for record in records
            if _record_visible(
                query=query,
                record=record,
                namespace=namespace,
            )
        ]
        ordered = sorted(matches, key=lambda record: record.updated_at, reverse=True)
        selected = tuple(ordered[: query.limit])
        memory_metrics.record_read(
            namespace=namespace or "unknown",
            hit_count=len(selected),
        )
        return selected

    def _load_records(self) -> list[MemoryRecord]:
        """Load and validate memory records from backing file.

        Returns:
            Parsed memory records list.

        Raises:
            MemoryError: If store payload is unreadable or invalid.
        """
        if not self._path.exists():
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MemoryError(
                MemoryErrorCode.STORE_UNAVAILABLE,
                f"Memory store '{self._store.value}' is unreadable.",
            ) from exc
        if not isinstance(raw, list):
            raise MemoryError(
                MemoryErrorCode.SCHEMA_MISMATCH,
                f"Memory store '{self._store.value}' payload must be a list.",
            )
        records: list[MemoryRecord] = []
        for item in raw:
            try:
                record = MemoryRecord.model_validate(item)
            except ValidationError as exc:
                raise MemoryError(
                    MemoryErrorCode.SCHEMA_MISMATCH,
                    f"Memory store '{self._store.value}' contains invalid records.",
                ) from exc
            if record.store != self._store:
                raise MemoryError(
                    MemoryErrorCode.SCHEMA_MISMATCH,
                    f"Memory record store mismatch in '{self._store.value}'.",
                )
            records.append(record)
        return records

    def _save_records(self, records: list[MemoryRecord]) -> None:
        """Persist records atomically to backing store.

        Args:
            records: Records to persist.

        Raises:
            MemoryError: If filesystem persistence fails.
        """
        try:
            self._root_dir.mkdir(parents=True, exist_ok=True)
            payload = [record.model_dump(mode="json") for record in records]
            temp_path = self._path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            temp_path.replace(self._path)
        except OSError as exc:
            raise MemoryError(
                MemoryErrorCode.STORE_UNAVAILABLE,
                f"Memory store '{self._store.value}' is unavailable.",
            ) from exc


class FileBackedPersonalityMemoryRepository(PersonalityMemoryRepository):
    """File-backed personality memory repository."""

    def __init__(self, *, root_dir: Path) -> None:
        """Create personality memory repository.

        Args:
            root_dir: Store root directory.
        """
        self._store = _FileMemoryStore(root_dir=root_dir, store=MemoryStore.PERSONALITY)

    def remember(self, request: MemoryWriteRequest) -> MemoryRecord:
        """Create or upsert one personality memory record.

        Args:
            request: Memory write payload.

        Returns:
            Stored record.
        """
        return self._store.remember(request)

    def forget(self, memory_id: str) -> None:
        """Delete one personality memory record.

        Args:
            memory_id: Stable memory id.
        """
        self._store.forget(memory_id)

    def query(self, query: MemoryQuery) -> tuple[MemoryRecord, ...]:
        """Query personality memory records.

        Args:
            query: Query payload.

        Returns:
            Matching personality memory records.
        """
        return self._store.query(query)


class FileBackedTaskMemoryRepository(TaskMemoryRepository):
    """File-backed task memory repository with required namespace queries."""

    def __init__(self, *, root_dir: Path) -> None:
        """Create task memory repository.

        Args:
            root_dir: Store root directory.
        """
        self._store = _FileMemoryStore(root_dir=root_dir, store=MemoryStore.TASK)

    def remember(self, request: MemoryWriteRequest) -> MemoryRecord:
        """Create or upsert one task memory record.

        Args:
            request: Memory write payload.

        Returns:
            Stored task memory record.
        """
        return self._store.remember(request)

    def forget(self, memory_id: str) -> None:
        """Delete one task memory record.

        Args:
            memory_id: Stable memory id.
        """
        self._store.forget(memory_id)

    def query(self, query: MemoryQuery) -> tuple[MemoryRecord, ...]:
        """Query task memory records with required namespace isolation.

        Args:
            query: Query payload.

        Returns:
            Matching task memory records.

        Raises:
            MemoryError: If namespace is missing.
        """
        namespace = query.namespace.strip() if query.namespace is not None else ""
        if not namespace:
            raise MemoryError(
                MemoryErrorCode.NAMESPACE_REQUIRED,
                "Task memory query requires namespace.",
            )
        return self._store.query(query)


def _fingerprint(namespace: str, content: str) -> str:
    """Build deterministic dedup fingerprint.

    Args:
        namespace: Memory namespace.
        content: Memory content.

    Returns:
        Stable hash digest.
    """
    value = f"{namespace.strip().lower()}::{content.strip().lower()}".encode()
    return sha256(value).hexdigest()


def _record_visible(
    *,
    query: MemoryQuery,
    record: MemoryRecord,
    namespace: str | None,
) -> bool:
    """Check whether one record passes deterministic visibility filters.

    Args:
        query: Memory query payload.
        record: Candidate memory record.
        namespace: Optional required namespace filter.

    Returns:
        ``True`` when record is visible and matches query.
    """
    return all(
        (
            namespace_matches(namespace=namespace, record=record),
            confidence_matches(query=query, record=record),
            status_visible(query=query, record=record),
            content_matches(query=query, record=record),
        )
    )

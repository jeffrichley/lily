"""LangGraph Store-backed implementations for split Lily memory repositories."""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from langgraph.store.base import SearchItem
from langgraph.store.sqlite import SqliteStore
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

if TYPE_CHECKING:
    from collections.abc import Iterator

_SEARCH_PAGE_SIZE = 500
_NAMESPACE_PAGE_SIZE = 200


class _SqliteStoreBackedRepository:
    """Internal store adapter for one deterministic memory domain."""

    def __init__(self, *, store_file: Path, store: MemoryStore) -> None:
        """Create one store-backed memory adapter.

        Args:
            store_file: Sqlite store file path.
            store: Target memory domain identifier.
        """
        self._store_file = store_file
        self._store = store

    def remember(self, request: MemoryWriteRequest) -> MemoryRecord:
        """Create or upsert memory record by deterministic fingerprint key.

        Args:
            request: Memory write payload.

        Returns:
            Stored memory record.

        Raises:
            MemoryError: If input is invalid, denied by policy, or store fails.
        """
        namespace = request.namespace.strip()
        content = request.content.strip()
        if not namespace or not content:
            raise MemoryError(
                MemoryErrorCode.INVALID_INPUT,
                "Invalid memory write input.",
            )
        decision = evaluate_memory_write(content)
        if not decision.allowed:
            memory_metrics.record_denied_write(namespace=namespace)
            raise MemoryError(MemoryErrorCode.POLICY_DENIED, decision.reason)

        key = _fingerprint(namespace, content)
        ns_path = _namespace_path(self._store, namespace)
        now = datetime.now(UTC)
        try:
            with self._open_store() as store:
                existing = store.get(ns_path, key)
                if existing is not None:
                    existing_record = self._to_record(existing.value)
                    updated = existing_record.model_copy(
                        update=memory_update_fields(request=request, updated_at=now)
                    )
                    store.put(
                        ns_path, key, updated.model_dump(mode="json"), index=False
                    )
                    memory_metrics.record_write(namespace=namespace)
                    return updated

                created = create_memory_record(
                    store=self._store,
                    namespace=namespace,
                    content=content,
                    request=request,
                    now=now,
                    record_id=f"mem_{uuid4().hex}",
                )
                store.put(ns_path, key, created.model_dump(mode="json"), index=False)
                memory_metrics.record_write(namespace=namespace)
                return created
        except MemoryError:
            raise
        except Exception as exc:  # pragma: no cover - backend defensive
            raise MemoryError(
                MemoryErrorCode.STORE_UNAVAILABLE,
                f"Memory store '{self._store.value}' is unavailable.",
            ) from exc

    def forget(self, memory_id: str) -> None:
        """Delete one memory record by id.

        Args:
            memory_id: Stable memory id.

        Raises:
            MemoryError: If id is invalid, missing, or store fails.
        """
        normalized = memory_id.strip()
        if not normalized:
            raise MemoryError(MemoryErrorCode.INVALID_INPUT, "Memory id is required.")
        try:
            with self._open_store() as store:
                for namespace in _list_all_namespaces(
                    store=store,
                    prefix=_domain_prefix(self._store),
                ):
                    for item in _search_all(store=store, namespace=namespace):
                        record = self._to_record(item.value)
                        if record.id != normalized:
                            continue
                        store.delete(namespace, item.key)
                        return
        except MemoryError:
            raise
        except Exception as exc:  # pragma: no cover - backend defensive
            raise MemoryError(
                MemoryErrorCode.STORE_UNAVAILABLE,
                f"Memory store '{self._store.value}' is unavailable.",
            ) from exc
        raise MemoryError(
            MemoryErrorCode.NOT_FOUND,
            f"Memory record '{normalized}' was not found.",
        )

    def query(self, query: MemoryQuery) -> tuple[MemoryRecord, ...]:
        """Query one memory domain using deterministic filtering/sorting.

        Args:
            query: Query payload.

        Returns:
            Ordered matching memory records.

        Raises:
            MemoryError: If backend query execution fails.
        """
        namespace = query.namespace.strip() if query.namespace is not None else None
        try:
            matches = self._load_matches(namespace=namespace)
        except MemoryError:
            raise
        except Exception as exc:  # pragma: no cover - backend defensive
            raise MemoryError(
                MemoryErrorCode.STORE_UNAVAILABLE,
                f"Memory store '{self._store.value}' is unavailable.",
            ) from exc
        records = [self._to_record(item.value) for item in matches]
        filtered = [
            record
            for record in records
            if _record_matches(query=query, namespace=namespace, record=record)
        ]
        ordered = sorted(filtered, key=lambda item: item.updated_at, reverse=True)
        selected = tuple(ordered[: query.limit])
        memory_metrics.record_read(
            namespace=namespace or "unknown",
            hit_count=len(selected),
        )
        return selected

    def _load_matches(self, *, namespace: str | None) -> tuple[SearchItem, ...]:
        """Load raw store items for one namespace or full domain prefix.

        Args:
            namespace: Optional namespace token.

        Returns:
            Raw matching store items.
        """
        with self._open_store() as store:
            if namespace is None:
                return _scan_prefix(store=store, prefix=_domain_prefix(self._store))
            return _search_all(
                store=store,
                namespace=_namespace_path(self._store, namespace),
            )

    @contextmanager
    def _open_store(self) -> Iterator[SqliteStore]:
        """Open SqliteStore for one repository operation.

        Yields:
            Open store instance.

        Raises:
            MemoryError: If store backend cannot be opened.
        """
        try:
            self._store_file.parent.mkdir(parents=True, exist_ok=True)
            with SqliteStore.from_conn_string(str(self._store_file)) as store:
                yield store
        except OSError as exc:
            raise MemoryError(
                MemoryErrorCode.STORE_UNAVAILABLE,
                f"Memory store '{self._store.value}' is unavailable.",
            ) from exc

    def _to_record(self, payload: dict[str, object]) -> MemoryRecord:
        """Convert raw store payload into validated MemoryRecord.

        Args:
            payload: Raw stored payload.

        Returns:
            Parsed memory record.

        Raises:
            MemoryError: If payload cannot be validated or has store mismatch.
        """
        try:
            record = MemoryRecord.model_validate(payload)
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
        return record


class StoreBackedPersonalityMemoryRepository(PersonalityMemoryRepository):
    """Store-backed personality memory repository."""

    def __init__(self, *, store_file: Path) -> None:
        """Create personality store-backed repository.

        Args:
            store_file: Sqlite store file path.
        """
        self._store = _SqliteStoreBackedRepository(
            store_file=store_file,
            store=MemoryStore.PERSONALITY,
        )

    def remember(self, request: MemoryWriteRequest) -> MemoryRecord:
        """Create or update one personality memory record.

        Args:
            request: Memory write payload.

        Returns:
            Stored memory record.
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


class StoreBackedTaskMemoryRepository(TaskMemoryRepository):
    """Store-backed task memory repository with required namespace queries."""

    def __init__(self, *, store_file: Path) -> None:
        """Create task store-backed repository.

        Args:
            store_file: Sqlite store file path.
        """
        self._store = _SqliteStoreBackedRepository(
            store_file=store_file,
            store=MemoryStore.TASK,
        )

    def remember(self, request: MemoryWriteRequest) -> MemoryRecord:
        """Create or update one task memory record.

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
        """Query task memory records with namespace requirement.

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


def _scan_prefix(
    *,
    store: SqliteStore,
    prefix: tuple[str, ...],
) -> tuple[SearchItem, ...]:
    """Scan all namespaces under one domain prefix.

    Args:
        store: Open sqlite store.
        prefix: Namespace prefix.

    Returns:
        Flat tuple of search items under prefix.
    """
    items: list[SearchItem] = []
    for namespace in _list_all_namespaces(store=store, prefix=prefix):
        items.extend(_search_all(store=store, namespace=namespace))
    return tuple(items)


def _record_matches(
    *,
    query: MemoryQuery,
    namespace: str | None,
    record: MemoryRecord,
) -> bool:
    """Apply deterministic query filters to one record.

    Args:
        query: Query payload.
        namespace: Optional required namespace.
        record: Candidate record.

    Returns:
        Whether record matches query filter criteria.
    """
    return all(
        (
            namespace_matches(namespace=namespace, record=record),
            confidence_matches(query=query, record=record),
            status_visible(query=query, record=record),
            content_matches(query=query, record=record),
        )
    )


def _domain_prefix(store: MemoryStore) -> tuple[str, ...]:
    """Build store-domain prefix.

    Args:
        store: Memory store identifier.

    Returns:
        Namespace prefix tuple.
    """
    if store == MemoryStore.PERSONALITY:
        return ("memory", "personality")
    return ("memory", "task")


def _namespace_path(store: MemoryStore, namespace: str) -> tuple[str, ...]:
    """Build full namespace path tuple from store + namespace token.

    Args:
        store: Memory store identifier.
        namespace: Logical namespace token.

    Returns:
        Full namespace tuple.
    """
    segments = tuple(segment for segment in namespace.strip().split("/") if segment)
    cleaned = segments or ("default",)
    if store == MemoryStore.PERSONALITY:
        return ("memory", "personality", *cleaned)
    return ("memory", "task", *cleaned)


def _fingerprint(namespace: str, content: str) -> str:
    """Build deterministic dedup fingerprint key.

    Args:
        namespace: Logical namespace.
        content: Memory content.

    Returns:
        Stable hash digest.
    """
    value = f"{namespace.strip().lower()}::{content.strip().lower()}".encode()
    return hashlib.sha256(value).hexdigest()


def _list_all_namespaces(
    *,
    store: SqliteStore,
    prefix: tuple[str, ...],
) -> tuple[tuple[str, ...], ...]:
    """List all namespaces under prefix with deterministic pagination.

    Args:
        store: Open sqlite store.
        prefix: Namespace prefix.

    Returns:
        All matching namespaces.
    """
    offset = 0
    namespaces: list[tuple[str, ...]] = []
    while True:
        page = store.list_namespaces(
            prefix=prefix,
            limit=_NAMESPACE_PAGE_SIZE,
            offset=offset,
        )
        if not page:
            return tuple(namespaces)
        namespaces.extend(page)
        if len(page) < _NAMESPACE_PAGE_SIZE:
            return tuple(namespaces)
        offset += _NAMESPACE_PAGE_SIZE


def _search_all(
    *,
    store: SqliteStore,
    namespace: tuple[str, ...],
) -> tuple[SearchItem, ...]:
    """Search full namespace with deterministic pagination.

    Args:
        store: Open sqlite store.
        namespace: Concrete namespace path.

    Returns:
        All records found in namespace.
    """
    offset = 0
    items: list[SearchItem] = []
    while True:
        page = store.search(
            namespace,
            query=None,
            limit=_SEARCH_PAGE_SIZE,
            offset=offset,
        )
        if not page:
            return tuple(items)
        items.extend(page)
        if len(page) < _SEARCH_PAGE_SIZE:
            return tuple(items)
        offset += _SEARCH_PAGE_SIZE

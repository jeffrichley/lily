"""LangMem-based memory search/manage adapter with deterministic output mapping."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langgraph.store.sqlite import SqliteStore
from langmem import create_manage_memory_tool, create_search_memory_tool

from lily.memory.models import MemoryError, MemoryErrorCode
from lily.policy import evaluate_memory_write

if TYPE_CHECKING:
    from collections.abc import Iterator


class LangMemToolingAdapter:
    """Adapter that runs LangMem tools against Lily's sqlite memory store."""

    def __init__(self, *, store_file: Path) -> None:
        """Create adapter.

        Args:
            store_file: Sqlite store backing file.
        """
        self._store_file = store_file

    def search(
        self,
        *,
        namespace: str,
        query: str,
        tool_name: str,
    ) -> tuple[dict[str, Any], ...]:
        """Search memory via LangMem search tool.

        Args:
            namespace: Logical namespace string.
            query: Query string.
            tool_name: Stable tool name.

        Returns:
            Deterministic tuple of result dicts.

        Raises:
            MemoryError: If tool execution fails.
        """
        if not query.strip():
            raise MemoryError(
                MemoryErrorCode.INVALID_INPUT, "Memory query is required."
            )
        with self._open_store() as store:
            tool = create_search_memory_tool(
                namespace=_namespace_tuple(namespace),
                store=store,
                name=tool_name,
            )
            payload = tool.invoke({"query": query})
        return _normalize_search_payload(payload)

    def remember(
        self,
        *,
        namespace: str,
        content: str,
        tool_name: str,
    ) -> str:
        """Write memory via LangMem manage tool with policy interception.

        Args:
            namespace: Logical namespace string.
            content: Memory content to persist.
            tool_name: Stable tool name.

        Returns:
            Created/updated memory key string.

        Raises:
            MemoryError: If policy denies or tool execution fails.
        """
        normalized = content.strip()
        if not normalized:
            raise MemoryError(
                MemoryErrorCode.INVALID_INPUT,
                "Memory content is required.",
            )
        decision = evaluate_memory_write(normalized)
        if not decision.allowed:
            raise MemoryError(MemoryErrorCode.POLICY_DENIED, decision.reason)
        with self._open_store() as store:
            tool = create_manage_memory_tool(
                namespace=_namespace_tuple(namespace),
                store=store,
                name=tool_name,
            )
            payload = tool.invoke({"content": normalized})
        return _extract_memory_key(payload)

    @contextmanager
    def _open_store(self) -> Iterator[SqliteStore]:
        """Open sqlite store context.

        Yields:
            Open store instance.
        """
        self._store_file.parent.mkdir(parents=True, exist_ok=True)
        with SqliteStore.from_conn_string(str(self._store_file)) as store:
            yield store


def _namespace_tuple(namespace: str) -> tuple[str, ...]:
    """Convert slash namespace string to tuple path.

    Args:
        namespace: Slash-delimited namespace payload.

    Returns:
        Full tuple namespace with domain prefix.
    """
    segments = tuple(segment for segment in namespace.strip().split("/") if segment)
    if segments and segments[0] == "task_memory":
        return ("memory", "task", *segments)
    return ("memory", "personality", *segments)


def _normalize_search_payload(payload: object) -> tuple[dict[str, Any], ...]:
    """Normalize LangMem search payload into deterministic tuple.

    Args:
        payload: Tool payload object.

    Returns:
        Tuple of normalized search records.
    """
    if isinstance(payload, str):
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return ()
        if not isinstance(decoded, list):
            return ()
        return tuple(item for item in decoded if isinstance(item, dict))
    if isinstance(payload, list):
        return tuple(item for item in payload if isinstance(item, dict))
    return ()


def _extract_memory_key(payload: object) -> str:
    """Extract memory key from LangMem manage payload string.

    Args:
        payload: Tool payload object.

    Returns:
        Parsed key when present, otherwise empty string.
    """
    text = str(payload).strip()
    if not text:
        return ""
    tokens = text.split()
    return tokens[-1] if tokens else ""

"""Repository protocols for split personality/task memory stores."""

from __future__ import annotations

from typing import Protocol

from lily.memory.models import MemoryQuery, MemoryRecord, MemoryWriteRequest


class PersonalityMemoryRepository(Protocol):
    """Repository contract for personality memory operations."""

    def remember(self, request: MemoryWriteRequest) -> MemoryRecord:
        """Create or update one personality memory record.

        Args:
            request: Memory write payload.
        """

    def forget(self, memory_id: str) -> None:
        """Delete one personality memory record by id.

        Args:
            memory_id: Stable memory record id.
        """

    def query(self, query: MemoryQuery) -> tuple[MemoryRecord, ...]:
        """Query personality memory records.

        Args:
            query: Query payload.
        """


class TaskMemoryRepository(Protocol):
    """Repository contract for task memory operations."""

    def remember(self, request: MemoryWriteRequest) -> MemoryRecord:
        """Create or update one task memory record.

        Args:
            request: Memory write payload.
        """

    def forget(self, memory_id: str) -> None:
        """Delete one task memory record by id.

        Args:
            memory_id: Stable memory record id.
        """

    def query(self, query: MemoryQuery) -> tuple[MemoryRecord, ...]:
        """Query task memory records.

        Args:
            query: Query payload.
        """

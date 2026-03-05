"""Memory domain models and deterministic error contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class MemoryStore(StrEnum):
    """Supported memory stores."""

    PERSONALITY = "personality_memory"
    TASK = "task_memory"


class MemorySource(StrEnum):
    """Supported memory sources."""

    COMMAND = "command"
    INFERENCE = "inference"
    IMPORT = "import"
    SYSTEM = "system"


class MemoryErrorCode(StrEnum):
    """Stable memory operation error codes."""

    INVALID_INPUT = "memory_invalid_input"
    NOT_FOUND = "memory_not_found"
    POLICY_DENIED = "memory_policy_denied"
    STORE_UNAVAILABLE = "memory_store_unavailable"
    NAMESPACE_REQUIRED = "memory_namespace_required"
    SCHEMA_MISMATCH = "memory_schema_mismatch"


class MemoryError(RuntimeError):
    """Memory operation failure with stable code."""

    def __init__(self, code: MemoryErrorCode, message: str) -> None:
        """Create deterministic memory error.

        Args:
            code: Stable memory error code.
            message: Human-readable error message.
        """
        super().__init__(message)
        self.code = code


class MemoryRecord(BaseModel):
    """Stored memory record shared across stores."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"mem_{uuid4().hex}")
    schema_version: int = 1
    store: MemoryStore
    namespace: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source: MemorySource = MemorySource.COMMAND
    confidence: float = 1.0
    tags: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    preference_type: str | None = None
    stability: str | None = None
    task_id: str | None = None
    session_id: str | None = None
    status: str | None = None
    expires_at: datetime | None = None
    last_verified: datetime | None = None
    conflict_group: str | None = None


class MemoryWriteRequest(BaseModel):
    """Input contract for create/update memory operations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    namespace: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source: MemorySource = MemorySource.COMMAND
    confidence: float = 1.0
    tags: tuple[str, ...] = ()
    preference_type: str | None = None
    stability: str | None = None
    task_id: str | None = None
    session_id: str | None = None
    status: str | None = None
    expires_at: datetime | None = None
    last_verified: datetime | None = None
    conflict_group: str | None = None


class MemoryQuery(BaseModel):
    """Input contract for deterministic store query operations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query: str = Field(min_length=1)
    namespace: str | None = None
    limit: int = Field(default=5, ge=1, le=20)
    min_confidence: float | None = None
    include_archived: bool = False
    include_expired: bool = False
    include_conflicted: bool = False

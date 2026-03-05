"""Canonical executable envelope models for orchestration runtime."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExecutableKind(StrEnum):
    """Supported executable target kinds."""

    AGENT = "agent"
    BLUEPRINT = "blueprint"
    SKILL = "skill"
    TOOL = "tool"
    JOB = "job"
    WORKFLOW = "workflow"


class ExecutableRef(BaseModel):
    """Stable executable target identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    executable_id: str = Field(min_length=1)
    executable_kind: ExecutableKind | None = None
    version: str | None = None


class CallerContext(BaseModel):
    """Authority context carried in executable requests."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    supervisor_id: str = Field(min_length=1)
    active_agent: str = Field(min_length=1)


class ExecutionConstraints(BaseModel):
    """Execution boundary settings for one step request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    timeout_ms: int | None = Field(default=None, ge=1)
    retry_budget: int | None = Field(default=None, ge=0)
    cost_budget: float | None = Field(default=None, ge=0)


class ExecutionContext(BaseModel):
    """Execution context references and constraints."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_refs: tuple[str, ...]
    artifact_refs: tuple[str, ...]
    constraints: ExecutionConstraints


class ExecutionMetadata(BaseModel):
    """Trace metadata carried with a request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trace_tags: dict[str, object]
    created_at_utc: str = Field(min_length=1)


class ExecutableRequest(BaseModel):
    """Canonical request envelope for executable dispatch."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    parent_step_id: str | None = None
    caller: CallerContext
    target: ExecutableRef
    objective: str = Field(min_length=1)
    input: dict[str, object]
    context: ExecutionContext
    metadata: ExecutionMetadata


class ExecutableStatus(StrEnum):
    """Canonical execution status values."""

    OK = "ok"
    ERROR = "error"
    DEFERRED = "deferred"


class ExecutableError(BaseModel):
    """Structured deterministic error payload for executable result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool
    data: dict[str, object]


class ExecutionMetrics(BaseModel):
    """Execution metrics attached to result envelopes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    duration_ms: int = Field(ge=0)


class ExecutableResult(BaseModel):
    """Canonical result envelope returned by executable handlers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    status: ExecutableStatus
    output: dict[str, object]
    references: tuple[str, ...]
    artifacts: tuple[str, ...]
    metrics: ExecutionMetrics
    error: ExecutableError | None = None

    @model_validator(mode="after")
    def _validate_error_presence(self) -> ExecutableResult:
        """Enforce explicit error payload semantics by status."""
        if self.status == ExecutableStatus.OK and self.error is not None:
            raise ValueError("error must be null when status is 'ok'.")
        if self.status != ExecutableStatus.OK and self.error is None:
            raise ValueError("error is required when status is not 'ok'.")
        return self


class GateOutcome(StrEnum):
    """Deterministic policy gate outcomes."""

    OK = "ok"
    RETRY = "retry"
    FALLBACK = "fallback"
    ESCALATE = "escalate"
    ABORT = "abort"


class GateDecision(BaseModel):
    """Policy gate decision envelope for one executable step."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    outcome: GateOutcome
    reason_code: str = Field(min_length=1)
    reason_message: str = Field(min_length=1)
    next_step_hint: str | None = None

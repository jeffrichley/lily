"""Job spec and run models."""

from __future__ import annotations

from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobTriggerType(StrEnum):
    """Supported job trigger types for V0."""

    MANUAL = "manual"
    CRON = "cron"


class JobTargetKind(StrEnum):
    """Supported runnable target kinds for V0."""

    BLUEPRINT = "blueprint"


class JobTargetSpec(BaseModel):
    """Runnable target reference for one job."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: JobTargetKind
    id: str = Field(min_length=1)
    input: dict[str, object] = {}


class JobTriggerSpec(BaseModel):
    """Trigger configuration for one job."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: JobTriggerType
    cron: str | None = None
    timezone: str | None = None

    @model_validator(mode="after")
    def _validate_trigger(self) -> JobTriggerSpec:
        """Validate trigger semantics for V0.

        Returns:
            Validated trigger model.

        Raises:
            ValueError: If trigger payload is invalid.
        """
        if self.type == JobTriggerType.MANUAL:
            if self.cron is not None or self.timezone is not None:
                raise ValueError(
                    "manual trigger must not define cron or timezone fields."
                )
            return self

        if not self.cron:
            raise ValueError("cron trigger must declare cron expression.")
        if not self.timezone:
            raise ValueError("cron trigger must declare IANA timezone.")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("cron trigger timezone is invalid.") from exc
        return self


class JobRuntimeSpec(BaseModel):
    """Execution limits for one job."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    timeout_seconds: int = Field(default=300, ge=1, le=86_400)
    retry_max: int = Field(default=0, ge=0, le=10)
    max_parallel_runs: int = Field(default=1, ge=1, le=8)


class JobOutputSpec(BaseModel):
    """Output rendering and artifact settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    summary_format: str = "markdown"


class JobSpec(BaseModel):
    """Validated executable job spec loaded from yaml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    target: JobTargetSpec
    bindings: dict[str, object] = {}
    trigger: JobTriggerSpec = Field(
        default_factory=lambda: JobTriggerSpec(type=JobTriggerType.MANUAL)
    )
    runtime: JobRuntimeSpec = Field(default_factory=JobRuntimeSpec)
    output: JobOutputSpec = Field(default_factory=JobOutputSpec)


class JobDiagnostic(BaseModel):
    """Non-fatal repository scan diagnostic for one job spec file."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    code: str
    message: str


class JobRepositoryScan(BaseModel):
    """Repository listing payload for jobs + scan diagnostics."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    jobs: tuple[JobSpec, ...] = ()
    diagnostics: tuple[JobDiagnostic, ...] = ()


class JobRunEnvelope(BaseModel):
    """Shared envelope returned by job execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    job_id: str
    status: str
    started_at: str
    ended_at: str
    target: dict[str, object]
    artifacts: tuple[str, ...]
    approvals_requested: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    payload: dict[str, object] = {}


class JobTailResult(BaseModel):
    """Recent event tail payload for one job."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    job_id: str
    run_id: str | None = None
    lines: tuple[str, ...] = ()

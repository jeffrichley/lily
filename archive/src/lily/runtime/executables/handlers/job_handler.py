"""Executable adapter for jobs execution runtime."""

from __future__ import annotations

from typing import Protocol

from lily.jobs.errors import JobError
from lily.jobs.models import JobRunEnvelope
from lily.runtime.executables.handlers._common import (
    elapsed_ms,
    error_result,
    started_timer,
)
from lily.runtime.executables.handlers.base import BaseExecutableHandler
from lily.runtime.executables.models import (
    ExecutableError,
    ExecutableKind,
    ExecutableRequest,
    ExecutableResult,
    ExecutableStatus,
    ExecutionMetrics,
)


class JobExecutorPort(Protocol):
    """Protocol for job executor dependency used by adapter."""

    def run(self, job_id: str) -> JobRunEnvelope:
        """Execute one job by id."""


class JobExecutableHandler(BaseExecutableHandler):
    """Adapter handler for job execution through `JobExecutor`."""

    kind = ExecutableKind.JOB

    def __init__(self, executor: JobExecutorPort) -> None:
        """Store job executor dependency.

        Args:
            executor: Jobs execution backend.
        """
        self._executor = executor

    def handle(self, request: ExecutableRequest) -> ExecutableResult:
        """Execute one job run request via canonical envelope."""
        started = started_timer()
        try:
            job_id = str(
                request.input.get("job_id") or request.target.executable_id
            ).strip()
            if not job_id:
                raise ValueError("Missing required input field 'job_id'.")
        except ValueError as exc:
            return error_result(
                request=request,
                error=ExecutableError(
                    code="adapter_input_invalid",
                    message=f"Error: job adapter input is invalid: {exc}",
                    retryable=False,
                    data={"target_id": request.target.executable_id},
                ),
                duration_ms=elapsed_ms(started),
            )

        try:
            run = self._executor.run(job_id)
        except JobError as exc:
            return error_result(
                request=request,
                error=ExecutableError(
                    code=exc.code.value,
                    message=str(exc),
                    retryable=False,
                    data=exc.data,
                ),
                duration_ms=elapsed_ms(started),
            )

        status = ExecutableStatus.OK if run.status == "ok" else ExecutableStatus.ERROR
        return ExecutableResult(
            run_id=request.run_id,
            step_id=request.step_id,
            status=status,
            output={
                "job_id": run.job_id,
                "run_id": run.run_id,
                "status": run.status,
                "payload": run.payload,
            },
            references=run.references,
            artifacts=run.artifacts,
            metrics=ExecutionMetrics(duration_ms=elapsed_ms(started)),
            error=(
                None
                if status == ExecutableStatus.OK
                else ExecutableError(
                    code="job_execution_failed",
                    message="Error: job runtime returned error status.",
                    retryable=False,
                    data={"job_id": job_id},
                )
            ),
        )

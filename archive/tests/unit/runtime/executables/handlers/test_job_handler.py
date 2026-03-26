"""Unit tests for job executable adapter handler."""

from __future__ import annotations

import pytest

from lily.jobs.errors import JobError, JobErrorCode
from lily.jobs.models import JobRunEnvelope
from lily.runtime.executables.handlers.job_handler import JobExecutableHandler
from lily.runtime.executables.models import (
    CallerContext,
    ExecutableKind,
    ExecutableRef,
    ExecutableRequest,
    ExecutableStatus,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionMetadata,
)


class _JobExecutorFixture:
    """Job executor fixture used to test adapter behavior."""

    def __init__(self, *, should_fail: bool = False) -> None:
        """Store deterministic failure mode toggle."""
        self._should_fail = should_fail

    def run(self, job_id: str) -> JobRunEnvelope:
        """Return deterministic run envelope or raise deterministic job error."""
        if self._should_fail:
            raise JobError(
                JobErrorCode.NOT_FOUND,
                f"Error: job '{job_id}' was not found.",
                data={"job_id": job_id},
            )
        return JobRunEnvelope(
            run_id="run_20260304T200000Z_abcd1234",
            job_id=job_id,
            status="ok",
            started_at="2026-03-04T20:00:00Z",
            ended_at="2026-03-04T20:00:02Z",
            target={"kind": "blueprint", "id": "nightly_security_council"},
            artifacts=("run_receipt.json", "summary.md", "events.jsonl"),
            references=("ref://job-run",),
            payload={"attempt_count": 1},
        )


def _request(*, job_id: str = "nightly-job") -> ExecutableRequest:
    """Create job executable request fixture."""
    return ExecutableRequest(
        run_id="run-001",
        step_id="step-001",
        caller=CallerContext(supervisor_id="supervisor.v1", active_agent="default"),
        target=ExecutableRef(executable_id=job_id, executable_kind=ExecutableKind.JOB),
        objective="Run nightly job.",
        input={"job_id": job_id},
        context=ExecutionContext(
            memory_refs=(),
            artifact_refs=(),
            constraints=ExecutionConstraints(),
        ),
        metadata=ExecutionMetadata(
            trace_tags={}, created_at_utc="2026-03-04T20:00:00Z"
        ),
    )


@pytest.mark.unit
def test_job_handler_maps_successful_job_run_to_ok_result() -> None:
    """Job handler should normalize successful run envelope into executable result."""
    # Arrange - create job handler with successful executor fixture.
    handler = JobExecutableHandler(executor=_JobExecutorFixture())
    request = _request(job_id="nightly-job")

    # Act - execute job request via adapter.
    result = handler.handle(request)

    # Assert - result maps run envelope to canonical executable success payload.
    assert result.status == ExecutableStatus.OK
    assert result.error is None
    assert result.output["job_id"] == "nightly-job"
    assert result.output["status"] == "ok"
    assert result.references == ("ref://job-run",)


@pytest.mark.unit
def test_job_handler_maps_job_error_to_deterministic_envelope() -> None:
    """Job handler should map job runtime failures to deterministic error envelope."""
    # Arrange - create handler with failing executor fixture.
    handler = JobExecutableHandler(executor=_JobExecutorFixture(should_fail=True))
    request = _request(job_id="missing-job")

    # Act - execute job request with deterministic not-found failure.
    result = handler.handle(request)

    # Assert - adapter returns error envelope preserving job error code and payload.
    assert result.status == ExecutableStatus.ERROR
    assert result.error is not None
    assert result.error.code == JobErrorCode.NOT_FOUND.value
    assert result.error.data["job_id"] == "missing-job"

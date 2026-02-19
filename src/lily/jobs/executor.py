"""Manual job execution against blueprint targets."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn, Protocol, cast
from uuid import uuid4

from lily.blueprints import (
    BlueprintError,
    BlueprintErrorCode,
    BlueprintRegistry,
    BlueprintRunEnvelope,
)
from lily.jobs.errors import JobError, JobErrorCode
from lily.jobs.models import (
    JobRepositoryScan,
    JobRunEnvelope,
    JobSpec,
    JobTailResult,
    JobTargetKind,
)
from lily.jobs.repository import JobRepository

_MANDATORY_ARTIFACTS = ("run_receipt.json", "summary.md", "events.jsonl")


class _JobAttemptTimeoutError(RuntimeError):
    """Raised when one job attempt exceeds configured timeout."""


@dataclass(frozen=True)
class _AttemptFailure:
    """Structured failure metadata for one attempt."""

    code: str
    message: str
    retryable: bool
    exc: Exception


@dataclass(frozen=True)
class _FinalizeFailureRequest:
    """Input payload for final failure artifact persistence."""

    spec: JobSpec
    run_id: str
    run_dir: Path
    started_at: str
    attempts: tuple[dict[str, object], ...]
    failure: _AttemptFailure


class _CompiledBlueprintRunnable(Protocol):
    """Protocol for compiled blueprint runnables."""

    def invoke(self, raw_input: dict[str, object]) -> BlueprintRunEnvelope:
        """Execute one compiled blueprint run with validated input.

        Args:
            raw_input: Execution input payload.
        """


class JobExecutor:
    """Execute validated jobs and persist required run artifacts."""

    def __init__(
        self,
        *,
        repository: JobRepository,
        blueprint_registry: BlueprintRegistry,
        runs_root: Path,
    ) -> None:
        """Store execution dependencies.

        Args:
            repository: Job repository.
            blueprint_registry: Blueprint runtime registry.
            runs_root: Root directory for persisted run artifacts.
        """
        self._repository = repository
        self._blueprint_registry = blueprint_registry
        self._runs_root = runs_root

    def list_jobs(self) -> JobRepositoryScan:
        """List repository jobs with diagnostics.

        Returns:
            Repository scan with valid jobs and diagnostics.
        """
        return self._repository.list_jobs()

    def run(self, job_id: str) -> JobRunEnvelope:
        """Execute one job by id.

        Args:
            job_id: Target job id.

        Returns:
            Deterministic job run envelope.

        Raises:
            JobError: For deterministic job failures.
        """
        spec = self._repository.load(job_id)
        if spec.target.kind != JobTargetKind.BLUEPRINT:
            raise JobError(
                JobErrorCode.TARGET_UNRESOLVED,
                "Error: unsupported job target kind.",
                data={
                    "job_id": spec.id,
                    "target_kind": spec.target.kind.value,
                },
            )

        started_at = _utc_now()
        run_id = (
            f"run_{datetime.now(tz=UTC).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"
        )
        run_dir = self._create_run_dir(spec.id, run_id)
        self._append_event(
            run_dir,
            {
                "timestamp": started_at,
                "event": "job_started",
                "job_id": spec.id,
                "run_id": run_id,
                "target": spec.target.model_dump(mode="json"),
            },
        )

        return self._run_with_retry_policy(
            spec=spec,
            run_id=run_id,
            run_dir=run_dir,
            started_at=started_at,
        )

    def tail(self, job_id: str, *, limit: int = 50) -> JobTailResult:
        """Return recent event lines from latest run for a job.

        Args:
            job_id: Target job identifier.
            limit: Maximum number of trailing lines.

        Returns:
            Tail result payload.
        """
        spec = self._repository.load(job_id)
        job_runs_root = self._runs_root / spec.id
        if not job_runs_root.exists():
            return JobTailResult(job_id=spec.id, run_id=None, lines=())
        run_dirs = sorted(
            (
                path
                for path in job_runs_root.iterdir()
                if path.is_dir() and path.name.startswith("run_")
            ),
            key=lambda path: path.name,
        )
        if not run_dirs:
            return JobTailResult(job_id=spec.id, run_id=None, lines=())

        latest = run_dirs[-1]
        events_file = latest / "events.jsonl"
        if not events_file.exists():
            return JobTailResult(job_id=spec.id, run_id=latest.name, lines=())
        lines = events_file.read_text(encoding="utf-8").splitlines()
        trimmed = tuple(lines[-max(1, limit) :])
        return JobTailResult(job_id=spec.id, run_id=latest.name, lines=trimmed)

    def _execute_blueprint_target(
        self,
        *,
        spec: JobSpec,
        run_id: str,
        started_at: str,
    ) -> JobRunEnvelope:
        """Execute blueprint target and normalize to job envelope.

        Args:
            spec: Validated job spec.
            run_id: Run identifier.
            started_at: Start timestamp in UTC ISO-8601.

        Returns:
            Job run envelope.
        """
        run = self._invoke_blueprint_with_timeout(spec=spec)
        ended_at = _utc_now()
        artifacts = (*_MANDATORY_ARTIFACTS, *run.artifacts)
        return JobRunEnvelope(
            run_id=run_id,
            job_id=spec.id,
            status=run.status.value,
            started_at=started_at,
            ended_at=ended_at,
            target=spec.target.model_dump(mode="json"),
            artifacts=tuple(dict.fromkeys(artifacts)),
            approvals_requested=tuple(run.approvals_requested),
            references=tuple(run.references),
            payload=run.payload,
        )

    def _run_with_retry_policy(
        self,
        *,
        spec: JobSpec,
        run_id: str,
        run_dir: Path,
        started_at: str,
    ) -> JobRunEnvelope:
        """Execute job attempts with bounded retries and timeout handling.

        Args:
            spec: Validated job specification.
            run_id: Stable run id.
            run_dir: Run artifact directory.
            started_at: Run start timestamp.

        Returns:
            Final successful run envelope.

        Raises:
            JobError: When run fails after retry/timeout policy.
        """
        attempts: list[dict[str, object]] = []
        max_attempts = max(1, spec.runtime.retry_max + 1)
        for attempt in range(1, max_attempts + 1):
            attempt_started = _utc_now()
            self._append_event(
                run_dir,
                {
                    "timestamp": attempt_started,
                    "event": "job_attempt_started",
                    "job_id": spec.id,
                    "run_id": run_id,
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                },
            )
            try:
                attempt_result = self._execute_blueprint_target(
                    spec=spec,
                    run_id=run_id,
                    started_at=started_at,
                )
            except (BlueprintError, JobError, _JobAttemptTimeoutError) as exc:
                failure = self._resolve_attempt_failure(
                    spec=spec, run_id=run_id, exc=exc
                )
                attempt_ended = _utc_now()
                will_retry = failure.retryable and attempt < max_attempts
                attempts.append(
                    {
                        "attempt": attempt,
                        "status": "error",
                        "started_at": attempt_started,
                        "ended_at": attempt_ended,
                        "error_code": failure.code,
                        "error_message": failure.message,
                        "retryable": failure.retryable,
                        "will_retry": will_retry,
                    }
                )
                self._append_event(
                    run_dir,
                    {
                        "timestamp": attempt_ended,
                        "event": "job_attempt_failed",
                        "job_id": spec.id,
                        "run_id": run_id,
                        "attempt": attempt,
                        "error_code": failure.code,
                        "retryable": failure.retryable,
                        "will_retry": will_retry,
                    },
                )
                if will_retry:
                    continue
                return self._finalize_failure(
                    _FinalizeFailureRequest(
                        spec=spec,
                        run_id=run_id,
                        run_dir=run_dir,
                        started_at=started_at,
                        attempts=tuple(attempts),
                        failure=failure,
                    )
                )
            attempt_ended = _utc_now()
            attempts.append(
                {
                    "attempt": attempt,
                    "status": "ok",
                    "started_at": attempt_started,
                    "ended_at": attempt_ended,
                }
            )
            result_with_attempts = attempt_result.model_copy(
                update={
                    "payload": {
                        **attempt_result.payload,
                        "attempt_count": attempt,
                        "attempts": tuple(attempts),
                    }
                }
            )
            self._write_success_artifacts(
                run_dir=run_dir, envelope=result_with_attempts
            )
            self._append_event(
                run_dir,
                {
                    "timestamp": result_with_attempts.ended_at,
                    "event": "job_attempt_succeeded",
                    "job_id": spec.id,
                    "run_id": run_id,
                    "attempt": attempt,
                },
            )
            self._append_event(
                run_dir,
                {
                    "timestamp": result_with_attempts.ended_at,
                    "event": "job_completed",
                    "job_id": spec.id,
                    "run_id": run_id,
                    "status": result_with_attempts.status,
                    "attempt_count": attempt,
                },
            )
            return result_with_attempts
        raise JobError(  # pragma: no cover - loop always returns or finalizes failure
            JobErrorCode.EXECUTION_FAILED,
            f"Error: job '{spec.id}' execution failed.",
            data={"job_id": spec.id, "run_id": run_id},
        )

    def _finalize_failure(self, request: _FinalizeFailureRequest) -> NoReturn:
        """Persist failure artifacts and re-raise deterministic error.

        Args:
            request: Final failure request payload.
        """
        ended_at = _utc_now()
        envelope = JobRunEnvelope(
            run_id=request.run_id,
            job_id=request.spec.id,
            status="error",
            started_at=request.started_at,
            ended_at=ended_at,
            target=request.spec.target.model_dump(mode="json"),
            artifacts=_MANDATORY_ARTIFACTS,
            approvals_requested=(),
            references=(),
            payload={
                "attempt_count": len(request.attempts),
                "attempts": request.attempts,
                "error_code": request.failure.code,
                "error_message": request.failure.message,
            },
        )
        self._write_failure_artifacts(
            run_dir=request.run_dir,
            envelope=envelope,
            error=request.failure.exc,
        )
        self._append_event(
            request.run_dir,
            {
                "timestamp": ended_at,
                "event": "job_failed",
                "job_id": request.spec.id,
                "run_id": request.run_id,
                "error_code": request.failure.code,
                "attempt_count": len(request.attempts),
            },
        )
        self._raise_failure_exception(
            request.failure.exc, spec=request.spec, run_id=request.run_id
        )

    def _invoke_blueprint_with_timeout(self, *, spec: JobSpec) -> BlueprintRunEnvelope:
        """Execute blueprint invocation with timeout boundary.

        Args:
            spec: Validated job spec.

        Returns:
            Blueprint run envelope.

        Raises:
            _JobAttemptTimeoutError: If invocation exceeds configured timeout.
        """
        timeout_seconds = spec.runtime.timeout_seconds
        pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lily-job-attempt")
        future = pool.submit(self._invoke_blueprint_once, spec)
        timed_out = False
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            timed_out = True
            future.cancel()
            raise _JobAttemptTimeoutError(
                f"Error: job '{spec.id}' attempt timed out after {timeout_seconds}s."
            ) from exc
        finally:
            pool.shutdown(wait=not timed_out, cancel_futures=timed_out)

    def _invoke_blueprint_once(self, spec: JobSpec) -> BlueprintRunEnvelope:
        """Invoke blueprint path once without timeout/retry orchestration.

        Args:
            spec: Validated job specification.

        Returns:
            Blueprint run envelope.
        """
        blueprint = self._blueprint_registry.resolve(spec.target.id)
        bindings = self._blueprint_registry.validate_bindings(
            blueprint_id=blueprint.id,
            raw_bindings=spec.bindings,
        )
        compiled = cast(_CompiledBlueprintRunnable, blueprint.compile(bindings))
        return compiled.invoke(spec.target.input)

    @staticmethod
    def _resolve_attempt_failure(
        *, spec: JobSpec, run_id: str, exc: Exception
    ) -> _AttemptFailure:
        """Map one attempt exception to deterministic failure metadata.

        Args:
            spec: Job specification.
            run_id: Stable run id.
            exc: Raised attempt exception.

        Returns:
            Structured failure metadata.
        """
        if isinstance(exc, _JobAttemptTimeoutError):
            timeout_error = JobError(
                JobErrorCode.EXECUTION_FAILED,
                str(exc),
                data={
                    "job_id": spec.id,
                    "run_id": run_id,
                    "reason": "timeout",
                },
            )
            return _AttemptFailure(
                code=JobErrorCode.EXECUTION_FAILED.value,
                message=str(timeout_error),
                retryable=True,
                exc=timeout_error,
            )
        if isinstance(exc, BlueprintError):
            mapped_code = _map_blueprint_error_to_job_code(exc.code)
            mapped = JobError(
                mapped_code,
                f"Error: job '{spec.id}' failed during blueprint execution.",
                data={
                    "job_id": spec.id,
                    "run_id": run_id,
                    "blueprint_error_code": exc.code.value,
                    "blueprint_error_message": str(exc),
                },
            )
            return _AttemptFailure(
                code=mapped.code.value,
                message=str(mapped),
                retryable=mapped.code == JobErrorCode.EXECUTION_FAILED,
                exc=mapped,
            )
        if isinstance(exc, JobError):
            return _AttemptFailure(
                code=exc.code.value,
                message=str(exc),
                retryable=exc.code == JobErrorCode.EXECUTION_FAILED,
                exc=exc,
            )
        wrapped = JobError(
            JobErrorCode.EXECUTION_FAILED,
            f"Error: job '{spec.id}' execution failed.",
            data={"job_id": spec.id, "run_id": run_id},
        )
        return _AttemptFailure(
            code=JobErrorCode.EXECUTION_FAILED.value,
            message=str(wrapped),
            retryable=True,
            exc=wrapped,
        )

    @staticmethod
    def _raise_failure_exception(
        exc: Exception,
        *,
        spec: JobSpec,
        run_id: str,
    ) -> NoReturn:
        """Raise deterministic final failure exception.

        Args:
            exc: Final failure exception.
            spec: Job specification.
            run_id: Stable run identifier.

        Raises:
            JobError: For deterministic job-level failures.
        """
        if isinstance(exc, JobError):
            raise JobError(exc.code, str(exc), data=exc.data) from exc
        raise JobError(
            JobErrorCode.EXECUTION_FAILED,
            f"Error: job '{spec.id}' execution failed.",
            data={"job_id": spec.id, "run_id": run_id},
        ) from exc

    def _create_run_dir(self, job_id: str, run_id: str) -> Path:
        """Create deterministic run directory for one job execution.

        Args:
            job_id: Job identifier.
            run_id: Run identifier.

        Returns:
            Created run directory path.
        """
        run_dir = self._runs_root / job_id / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    @staticmethod
    def _append_event(run_dir: Path, event: dict[str, object]) -> None:
        """Append one json event line to required event stream file.

        Args:
            run_dir: Run artifact directory.
            event: Event payload.
        """
        path = run_dir / "events.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True))
            handle.write("\n")

    @staticmethod
    def _write_success_artifacts(*, run_dir: Path, envelope: JobRunEnvelope) -> None:
        """Write mandatory success artifact files.

        Args:
            run_dir: Run artifact directory.
            envelope: Final run envelope.
        """
        (run_dir / "run_receipt.json").write_text(
            json.dumps(envelope.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        attempt_count = envelope.payload.get("attempt_count")
        attempt_line = (
            f"- attempt_count: `{attempt_count}`\n"
            if isinstance(attempt_count, int)
            else ""
        )
        summary = (
            f"# Job Run Summary\n\n"
            f"- job_id: `{envelope.job_id}`\n"
            f"- run_id: `{envelope.run_id}`\n"
            f"- status: `{envelope.status}`\n"
            f"- target: `{envelope.target.get('id', '')}`\n"
            f"- started_at: `{envelope.started_at}`\n"
            f"- ended_at: `{envelope.ended_at}`\n"
            f"{attempt_line}"
        )
        (run_dir / "summary.md").write_text(summary, encoding="utf-8")

    @staticmethod
    def _write_failure_artifacts(
        *,
        run_dir: Path,
        envelope: JobRunEnvelope,
        error: Exception,
    ) -> None:
        """Write mandatory failure artifact files.

        Args:
            run_dir: Run artifact directory.
            envelope: Failure run envelope.
            error: Raised execution error.
        """
        (run_dir / "run_receipt.json").write_text(
            json.dumps(envelope.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        summary = (
            f"# Job Run Summary\n\n"
            f"- job_id: `{envelope.job_id}`\n"
            f"- run_id: `{envelope.run_id}`\n"
            f"- status: `{envelope.status}`\n"
            f"- started_at: `{envelope.started_at}`\n"
            f"- ended_at: `{envelope.ended_at}`\n"
            f"- attempt_count: `{envelope.payload.get('attempt_count', 0)}`\n"
            f"- error: `{error}`\n"
        )
        (run_dir / "summary.md").write_text(summary, encoding="utf-8")


def _map_blueprint_error_to_job_code(code: BlueprintErrorCode) -> JobErrorCode:
    """Map blueprint failure code to job-level deterministic failure code.

    Args:
        code: Blueprint error code.

    Returns:
        Job-level deterministic error code.
    """
    mapping = {
        BlueprintErrorCode.NOT_FOUND: JobErrorCode.TARGET_UNRESOLVED,
        BlueprintErrorCode.BINDINGS_INVALID: JobErrorCode.BINDINGS_INVALID,
        BlueprintErrorCode.COMPILE_FAILED: JobErrorCode.EXECUTION_FAILED,
        BlueprintErrorCode.EXECUTION_FAILED: JobErrorCode.EXECUTION_FAILED,
        BlueprintErrorCode.CONTRACT_INVALID: JobErrorCode.EXECUTION_FAILED,
    }
    return mapping[code]


def _utc_now() -> str:
    """Return UTC timestamp in stable RFC3339-like format.

    Returns:
        UTC timestamp string.
    """
    return (
        datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )

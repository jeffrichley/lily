"""Manual job execution against blueprint targets."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast
from uuid import uuid4

from lily.blueprints import BlueprintError, BlueprintRegistry, BlueprintRunEnvelope
from lily.jobs.errors import JobError, JobErrorCode
from lily.jobs.models import JobRepositoryScan, JobRunEnvelope, JobSpec, JobTargetKind
from lily.jobs.repository import JobRepository


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
            BlueprintError: For blueprint-layer failures.
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

        try:
            result = self._execute_blueprint_target(
                spec=spec, run_id=run_id, started_at=started_at
            )
            self._write_success_artifacts(run_dir=run_dir, envelope=result)
            self._append_event(
                run_dir,
                {
                    "timestamp": result.ended_at,
                    "event": "job_completed",
                    "job_id": spec.id,
                    "run_id": run_id,
                    "status": result.status,
                },
            )
            return result
        except BlueprintError as exc:
            ended_at = _utc_now()
            failure = JobRunEnvelope(
                run_id=run_id,
                job_id=spec.id,
                status="error",
                started_at=started_at,
                ended_at=ended_at,
                target=spec.target.model_dump(mode="json"),
                artifacts=("run_receipt.json", "summary.md", "events.jsonl"),
                approvals_requested=(),
                references=(),
                payload={
                    "error_code": exc.code.value,
                    "error_message": str(exc),
                },
            )
            self._write_failure_artifacts(run_dir=run_dir, envelope=failure, error=exc)
            self._append_event(
                run_dir,
                {
                    "timestamp": ended_at,
                    "event": "job_failed",
                    "job_id": spec.id,
                    "run_id": run_id,
                    "error_code": exc.code.value,
                },
            )
            raise
        except Exception as exc:  # pragma: no cover - defensive path
            ended_at = _utc_now()
            failure = JobRunEnvelope(
                run_id=run_id,
                job_id=spec.id,
                status="error",
                started_at=started_at,
                ended_at=ended_at,
                target=spec.target.model_dump(mode="json"),
                artifacts=("run_receipt.json", "summary.md", "events.jsonl"),
                approvals_requested=(),
                references=(),
                payload={
                    "error_code": JobErrorCode.EXECUTION_FAILED.value,
                    "error_message": str(exc),
                },
            )
            self._write_failure_artifacts(run_dir=run_dir, envelope=failure, error=exc)
            self._append_event(
                run_dir,
                {
                    "timestamp": ended_at,
                    "event": "job_failed",
                    "job_id": spec.id,
                    "run_id": run_id,
                    "error_code": JobErrorCode.EXECUTION_FAILED.value,
                },
            )
            raise JobError(
                JobErrorCode.EXECUTION_FAILED,
                f"Error: job '{spec.id}' execution failed.",
                data={"job_id": spec.id, "run_id": run_id},
            ) from exc

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
        blueprint = self._blueprint_registry.resolve(spec.target.id)
        bindings = self._blueprint_registry.validate_bindings(
            blueprint_id=blueprint.id,
            raw_bindings=spec.bindings,
        )
        compiled = cast(_CompiledBlueprintRunnable, blueprint.compile(bindings))
        run = compiled.invoke(spec.target.input)
        ended_at = _utc_now()
        artifacts = ("run_receipt.json", "summary.md", "events.jsonl", *run.artifacts)
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
        summary = (
            f"# Job Run Summary\n\n"
            f"- job_id: `{envelope.job_id}`\n"
            f"- run_id: `{envelope.run_id}`\n"
            f"- status: `{envelope.status}`\n"
            f"- target: `{envelope.target.get('id', '')}`\n"
            f"- started_at: `{envelope.started_at}`\n"
            f"- ended_at: `{envelope.ended_at}`\n"
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
            f"- error: `{error}`\n"
        )
        (run_dir / "summary.md").write_text(summary, encoding="utf-8")


def _utc_now() -> str:
    """Return UTC timestamp in stable RFC3339-like format.

    Returns:
        UTC timestamp string.
    """
    return (
        datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )

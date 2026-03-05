"""Filesystem-backed job repository."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import yaml
from pydantic import ValidationError

from lily.jobs.errors import JobError, JobErrorCode
from lily.jobs.models import JobDiagnostic, JobRepositoryScan, JobSpec


class JobRepository:
    """Load and validate jobs from `.lily/jobs/*.job.yaml` files."""

    def __init__(self, *, jobs_dir: Path) -> None:
        """Store repository location.

        Args:
            jobs_dir: Jobs directory root.
        """
        self._jobs_dir = jobs_dir

    def list_jobs(self) -> JobRepositoryScan:
        """List valid jobs with deterministic diagnostics for invalid files.

        Returns:
            Repository scan result.
        """
        jobs: list[JobSpec] = []
        diagnostics: list[JobDiagnostic] = []
        for path in self._iter_job_files():
            try:
                jobs.append(self._parse_job_file(path))
            except JobError as exc:
                diagnostics.append(
                    JobDiagnostic(path=str(path), code=exc.code.value, message=str(exc))
                )
        jobs_sorted = tuple(sorted(jobs, key=lambda item: item.id))
        diagnostics_sorted = tuple(
            sorted(diagnostics, key=lambda item: (item.path, item.code))
        )
        return JobRepositoryScan(jobs=jobs_sorted, diagnostics=diagnostics_sorted)

    def load(self, job_id: str) -> JobSpec:
        """Load one job by id.

        Args:
            job_id: Requested job id.

        Returns:
            Validated job spec.

        Raises:
            JobError: If job is missing or invalid.
        """
        normalized = job_id.strip()
        for path in self._iter_job_files():
            try:
                spec = self._parse_job_file(path)
            except JobError:
                if (
                    path.stem == f"{normalized}.job"
                    or self._peek_job_id(path) == normalized
                ):
                    raise
                continue
            if spec.id == normalized:
                return spec
        raise JobError(
            JobErrorCode.NOT_FOUND,
            f"Error: job '{normalized}' not found.",
            data={"job_id": normalized},
        )

    def _iter_job_files(self) -> tuple[Path, ...]:
        """Return deterministic ordered job spec files.

        Returns:
            Ordered job file list.
        """
        if not self._jobs_dir.exists():
            return ()
        files = list(self._jobs_dir.glob("*.job.yaml"))
        files.extend(self._jobs_dir.glob("*.job.yml"))
        return tuple(sorted(files))

    def _parse_job_file(self, path: Path) -> JobSpec:
        """Parse one job spec file and validate schema.

        Args:
            path: Job file path.

        Returns:
            Validated job spec.

        Raises:
            JobError: If spec is malformed/invalid.
        """
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise JobError(
                JobErrorCode.INVALID_SPEC,
                f"Error: invalid job spec in '{path.name}'.",
                data={"path": str(path), "reason": str(exc)},
            ) from exc
        if not isinstance(payload, dict):
            raise JobError(
                JobErrorCode.INVALID_SPEC,
                f"Error: invalid job spec in '{path.name}'.",
                data={"path": str(path), "reason": "expected mapping payload"},
            )
        try:
            return JobSpec.model_validate(payload)
        except ValidationError as exc:
            code = _resolve_validation_code(exc.errors())
            message = (
                f"Error: invalid trigger for job spec '{path.name}'."
                if code == JobErrorCode.TRIGGER_INVALID
                else f"Error: invalid job spec in '{path.name}'."
            )
            raise JobError(
                code,
                message,
                data={"path": str(path), "validation_errors": exc.errors()},
            ) from exc

    @staticmethod
    def _peek_job_id(path: Path) -> str | None:
        """Best-effort read of raw job id field for invalid spec matching.

        Args:
            path: Job spec file path.

        Returns:
            Raw `id` string if readable, otherwise ``None``.
        """
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            return None
        if not isinstance(payload, dict):
            return None
        raw = payload.get("id")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None


def _resolve_validation_code(errors: Sequence[object]) -> JobErrorCode:
    """Map pydantic errors to deterministic job error code.

    Args:
        errors: Validation error payload list.

    Returns:
        Stable error code.
    """
    for item in errors:
        if not isinstance(item, dict):
            continue
        loc = item.get("loc")
        if isinstance(loc, tuple) and loc and loc[0] == "trigger":
            return JobErrorCode.TRIGGER_INVALID
    return JobErrorCode.INVALID_SPEC

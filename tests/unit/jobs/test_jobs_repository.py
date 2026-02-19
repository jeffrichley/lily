"""Unit tests for job repository loading and validation."""

from __future__ import annotations

from pathlib import Path

from lily.jobs import JobError, JobErrorCode, JobRepository


def _write(path: Path, content: str) -> None:
    """Write utf-8 file content for tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_job_repository_loads_valid_manual_job(tmp_path: Path) -> None:
    """Repository should load a valid manual job spec."""
    jobs_dir = tmp_path / ".lily" / "jobs"
    _write(
        jobs_dir / "nightly.job.yaml",
        (
            "id: nightly_security_council\n"
            "title: Nightly security council\n"
            "target:\n"
            "  kind: blueprint\n"
            "  id: council.v1\n"
            "  input:\n"
            "    topic: perimeter\n"
            "bindings:\n"
            "  specialists: [security.v1, operations.v1]\n"
            "  synthesizer: default.v1\n"
            "  synth_strategy: deterministic\n"
            "  max_findings: 5\n"
            "trigger:\n"
            "  type: manual\n"
        ),
    )
    repository = JobRepository(jobs_dir=jobs_dir)

    loaded = repository.load("nightly_security_council")

    assert loaded.id == "nightly_security_council"
    assert loaded.target.id == "council.v1"
    assert loaded.trigger.type.value == "manual"


def test_job_repository_invalid_spec_maps_to_job_invalid_spec(tmp_path: Path) -> None:
    """Malformed spec should fail with deterministic invalid spec code."""
    jobs_dir = tmp_path / ".lily" / "jobs"
    _write(
        jobs_dir / "broken.job.yaml",
        ("id: broken\ntarget:\n  kind: blueprint\n  id: council.v1\n"),
    )
    repository = JobRepository(jobs_dir=jobs_dir)

    try:
        repository.load("broken")
    except JobError as exc:
        assert exc.code == JobErrorCode.INVALID_SPEC
        assert "invalid job spec" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected invalid spec failure.")


def test_job_repository_invalid_cron_timezone_maps_trigger_invalid(
    tmp_path: Path,
) -> None:
    """Invalid cron timezone should map to deterministic trigger-invalid code."""
    jobs_dir = tmp_path / ".lily" / "jobs"
    _write(
        jobs_dir / "cron.job.yaml",
        (
            "id: cron_job\n"
            "title: cron\n"
            "target:\n"
            "  kind: blueprint\n"
            "  id: council.v1\n"
            "bindings:\n"
            "  specialists: [security.v1, operations.v1]\n"
            "  synthesizer: default.v1\n"
            "  synth_strategy: deterministic\n"
            "trigger:\n"
            "  type: cron\n"
            '  cron: "0 * * * *"\n'
            "  timezone: Not/AZone\n"
        ),
    )
    repository = JobRepository(jobs_dir=jobs_dir)

    try:
        repository.load("cron_job")
    except JobError as exc:
        assert exc.code == JobErrorCode.TRIGGER_INVALID
        assert "invalid trigger" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected trigger invalid failure.")

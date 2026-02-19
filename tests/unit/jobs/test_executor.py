"""Unit tests for manual job execution and artifact persistence."""

from __future__ import annotations

import json
from pathlib import Path

from lily.blueprints import BlueprintError, build_default_blueprint_registry
from lily.jobs import JobError, JobErrorCode, JobExecutor, JobRepository


def _write(path: Path, content: str) -> None:
    """Write utf-8 file content for tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_job_executor_run_writes_required_artifacts(tmp_path: Path) -> None:
    """Successful run should write run receipt, summary, and events."""
    jobs_dir = tmp_path / ".lily" / "jobs"
    runs_root = tmp_path / ".lily" / "runs"
    _write(
        jobs_dir / "nightly.job.yaml",
        (
            "id: nightly_security_council\n"
            "title: Nightly security council\n"
            "target:\n"
            "  kind: blueprint\n"
            "  id: council.v1\n"
            "  input:\n"
            "    topic: service perimeter\n"
            "bindings:\n"
            "  specialists: [security.v1, operations.v1]\n"
            "  synthesizer: default.v1\n"
            "  synth_strategy: deterministic\n"
            "  max_findings: 5\n"
            "trigger:\n"
            "  type: manual\n"
        ),
    )
    executor = JobExecutor(
        repository=JobRepository(jobs_dir=jobs_dir),
        blueprint_registry=build_default_blueprint_registry(),
        runs_root=runs_root,
    )

    run = executor.run("nightly_security_council")

    run_dir = runs_root / run.job_id / run.run_id
    assert run.status == "ok"
    assert (run_dir / "run_receipt.json").exists()
    assert (run_dir / "summary.md").exists()
    assert (run_dir / "events.jsonl").exists()
    receipt = json.loads((run_dir / "run_receipt.json").read_text(encoding="utf-8"))
    assert receipt["job_id"] == "nightly_security_council"
    assert receipt["status"] == "ok"


def test_job_executor_missing_job_maps_to_job_not_found(tmp_path: Path) -> None:
    """Unknown job should fail with deterministic not-found code."""
    executor = JobExecutor(
        repository=JobRepository(jobs_dir=tmp_path / ".lily" / "jobs"),
        blueprint_registry=build_default_blueprint_registry(),
        runs_root=tmp_path / ".lily" / "runs",
    )

    try:
        executor.run("missing")
    except JobError as exc:
        assert exc.code == JobErrorCode.NOT_FOUND
        assert "not found" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected missing job failure.")


def test_job_executor_blueprint_bindings_error_is_propagated(tmp_path: Path) -> None:
    """Invalid bindings should propagate blueprint contract error code."""
    jobs_dir = tmp_path / ".lily" / "jobs"
    _write(
        jobs_dir / "broken_bindings.job.yaml",
        (
            "id: broken_bindings\n"
            "title: Broken bindings\n"
            "target:\n"
            "  kind: blueprint\n"
            "  id: council.v1\n"
            "  input:\n"
            "    topic: service perimeter\n"
            "bindings:\n"
            "  specialists: [security.v1]\n"
            "  synthesizer: default.v1\n"
            "  synth_strategy: deterministic\n"
            "  max_findings: 5\n"
            "trigger:\n"
            "  type: manual\n"
        ),
    )
    executor = JobExecutor(
        repository=JobRepository(jobs_dir=jobs_dir),
        blueprint_registry=build_default_blueprint_registry(),
        runs_root=tmp_path / ".lily" / "runs",
    )

    try:
        executor.run("broken_bindings")
    except BlueprintError as exc:
        assert exc.code.value == "blueprint_bindings_invalid"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected blueprint bindings error.")

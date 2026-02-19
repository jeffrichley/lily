"""Unit tests for manual job execution and artifact persistence."""

from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from lily.blueprints import (
    BlueprintError,
    BlueprintErrorCode,
    BlueprintRegistry,
    BlueprintRunEnvelope,
    BlueprintRunStatus,
    build_default_blueprint_registry,
)
from lily.jobs import JobError, JobErrorCode, JobExecutor, JobRepository


def _write(path: Path, content: str) -> None:
    """Write utf-8 file content for tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class _TestBindings(BaseModel):
    """Simple bindings schema for executor retry/timeout tests."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: str = "ok"


class _TestInput(BaseModel):
    """Simple input schema for executor retry/timeout tests."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    topic: str = Field(min_length=1)


class _TestOutput(BaseModel):
    """Simple output schema for executor retry/timeout tests."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    message: str


class _RetryThenSuccessRunnable:
    """Runnable fixture that fails once, then succeeds."""

    def __init__(self, state: dict[str, int]) -> None:
        """Store mutable invocation state."""
        self._state = state

    def invoke(self, raw_input: dict[str, object]) -> BlueprintRunEnvelope:
        """Raise first call, then return success envelope."""
        del raw_input
        self._state["calls"] += 1
        if self._state["calls"] == 1:
            raise BlueprintError(
                BlueprintErrorCode.EXECUTION_FAILED,
                "Error: transient failure.",
            )
        return BlueprintRunEnvelope(
            status=BlueprintRunStatus.OK,
            artifacts=("summary.md",),
            payload={"message": "ok"},
        )


class _AlwaysSleepRunnable:
    """Runnable fixture that exceeds timeout boundary."""

    def __init__(self, delay_seconds: float) -> None:
        """Store deterministic sleep delay."""
        self._delay_seconds = delay_seconds

    def invoke(self, raw_input: dict[str, object]) -> BlueprintRunEnvelope:
        """Sleep and return success payload (usually too late)."""
        del raw_input
        time.sleep(self._delay_seconds)
        return BlueprintRunEnvelope(
            status=BlueprintRunStatus.OK,
            artifacts=("summary.md",),
            payload={"message": "late"},
        )


class _RetryThenSuccessBlueprint:
    """Blueprint fixture with one transient execution failure."""

    id = "retry_then_success.v1"
    version = "1.0.0"
    summary = "Retry test blueprint."
    bindings_schema = _TestBindings
    input_schema = _TestInput
    output_schema = _TestOutput

    def __init__(self) -> None:
        """Initialize mutable run-call state."""
        self._state = {"calls": 0}

    def compile(self, bindings: BaseModel) -> _RetryThenSuccessRunnable:
        """Compile runnable with shared call state."""
        del bindings
        return _RetryThenSuccessRunnable(self._state)


class _AlwaysSleepBlueprint:
    """Blueprint fixture that always times out."""

    id = "always_sleep.v1"
    version = "1.0.0"
    summary = "Timeout test blueprint."
    bindings_schema = _TestBindings
    input_schema = _TestInput
    output_schema = _TestOutput

    def compile(self, bindings: BaseModel) -> _AlwaysSleepRunnable:
        """Compile runnable with deterministic sleep delay."""
        del bindings
        return _AlwaysSleepRunnable(delay_seconds=1.3)


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
    """Invalid bindings should map to deterministic job bindings-invalid code."""
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
    except JobError as exc:
        assert exc.code == JobErrorCode.BINDINGS_INVALID
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected job bindings-invalid failure.")


def test_job_executor_tail_reads_latest_events(tmp_path: Path) -> None:
    """Tail should read latest run events for a job."""
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

    tail = executor.tail("nightly_security_council", limit=10)

    assert tail.job_id == "nightly_security_council"
    assert tail.run_id == run.run_id
    assert tail.lines
    assert "job_completed" in tail.lines[-1]


def test_job_executor_retries_and_succeeds_with_attempt_lineage(tmp_path: Path) -> None:
    """Executor should retry transient failure and persist attempt lineage."""
    jobs_dir = tmp_path / ".lily" / "jobs"
    runs_root = tmp_path / ".lily" / "runs"
    _write(
        jobs_dir / "retry.job.yaml",
        (
            "id: retry_job\n"
            "title: Retry job\n"
            "target:\n"
            "  kind: blueprint\n"
            "  id: retry_then_success.v1\n"
            "  input:\n"
            "    topic: test\n"
            "bindings:\n"
            "  mode: ok\n"
            "trigger:\n"
            "  type: manual\n"
            "runtime:\n"
            "  timeout_seconds: 5\n"
            "  retry_max: 1\n"
            "  max_parallel_runs: 1\n"
        ),
    )
    blueprint = _RetryThenSuccessBlueprint()
    registry = BlueprintRegistry(blueprints=(blueprint,))
    executor = JobExecutor(
        repository=JobRepository(jobs_dir=jobs_dir),
        blueprint_registry=registry,
        runs_root=runs_root,
    )

    run = executor.run("retry_job")

    assert run.status == "ok"
    assert run.payload["attempt_count"] == 2
    attempts = run.payload["attempts"]
    assert isinstance(attempts, tuple)
    assert attempts[0]["status"] == "error"
    assert attempts[1]["status"] == "ok"


def test_job_executor_timeout_maps_to_execution_failed_and_attempts(
    tmp_path: Path,
) -> None:
    """Timeout should fail deterministically with attempt lineage in artifacts."""
    jobs_dir = tmp_path / ".lily" / "jobs"
    runs_root = tmp_path / ".lily" / "runs"
    _write(
        jobs_dir / "timeout.job.yaml",
        (
            "id: timeout_job\n"
            "title: Timeout job\n"
            "target:\n"
            "  kind: blueprint\n"
            "  id: always_sleep.v1\n"
            "  input:\n"
            "    topic: test\n"
            "bindings:\n"
            "  mode: ok\n"
            "trigger:\n"
            "  type: manual\n"
            "runtime:\n"
            "  timeout_seconds: 1\n"
            "  retry_max: 1\n"
            "  max_parallel_runs: 1\n"
        ),
    )
    registry = BlueprintRegistry(blueprints=(_AlwaysSleepBlueprint(),))
    executor = JobExecutor(
        repository=JobRepository(jobs_dir=jobs_dir),
        blueprint_registry=registry,
        runs_root=runs_root,
    )

    try:
        executor.run("timeout_job")
    except JobError as exc:
        assert exc.code == JobErrorCode.EXECUTION_FAILED
        assert "timed out" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected timeout failure.")

    run_root = runs_root / "timeout_job"
    run_dirs = sorted(path for path in run_root.iterdir() if path.is_dir())
    assert run_dirs
    receipt = json.loads(
        (run_dirs[-1] / "run_receipt.json").read_text(encoding="utf-8")
    )
    assert receipt["status"] == "error"
    assert receipt["payload"]["attempt_count"] == 2
    assert receipt["payload"]["error_code"] == "job_execution_failed"


def test_job_executor_retain_all_policy_keeps_prior_runs(tmp_path: Path) -> None:
    """Retain-all policy should preserve prior run artifact directories."""
    jobs_dir = tmp_path / ".lily" / "jobs"
    runs_root = tmp_path / ".lily" / "runs"
    _write(
        jobs_dir / "retain_all.job.yaml",
        (
            "id: retain_all\n"
            "title: Retain all test\n"
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

    first = executor.run("retain_all")
    second = executor.run("retain_all")

    run_root = runs_root / "retain_all"
    run_dirs = sorted(path for path in run_root.iterdir() if path.is_dir())
    assert len(run_dirs) == 2
    assert {path.name for path in run_dirs} == {first.run_id, second.run_id}
    assert all((path / "run_receipt.json").exists() for path in run_dirs)


def test_job_executor_history_returns_newest_first(tmp_path: Path) -> None:
    """History should return deterministically ordered entries."""
    jobs_dir = tmp_path / ".lily" / "jobs"
    runs_root = tmp_path / ".lily" / "runs"
    _write(
        jobs_dir / "history.job.yaml",
        (
            "id: history_job\n"
            "title: History job\n"
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
    first = executor.run("history_job")
    second = executor.run("history_job")

    history = executor.history("history_job", limit=10)

    assert history.job_id == "history_job"
    assert len(history.entries) == 2
    run_ids = {entry.run_id for entry in history.entries}
    assert run_ids == {first.run_id, second.run_id}
    assert list(history.entries) == sorted(
        history.entries,
        key=lambda item: (item.started_at, item.ended_at, item.run_id),
        reverse=True,
    )
    assert history.entries[0].attempt_count >= 1

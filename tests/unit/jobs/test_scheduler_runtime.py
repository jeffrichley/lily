"""Unit tests for APScheduler-backed jobs runtime service."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobExecutionEvent
from apscheduler.triggers.interval import IntervalTrigger

from lily.jobs import JobRepository, JobSchedulerRuntime


def _write(path: Path, content: str) -> None:
    """Write utf-8 file content for tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_runtime(workspace_root: Path) -> JobSchedulerRuntime:
    """Build scheduler runtime fixture."""
    repository = JobRepository(jobs_dir=workspace_root / "jobs")
    return JobSchedulerRuntime(
        repository=repository,
        jobs_dir=workspace_root / "jobs",
        runs_root=workspace_root / "runs",
        sqlite_path=workspace_root / "db" / "jobs_scheduler.sqlite3",
    )


@pytest.mark.unit
def test_scheduler_refresh_registers_cron_job_with_defaults(tmp_path: Path) -> None:
    """Refresh should register cron jobs with stable id and APS defaults."""
    # Arrange - workspace with cron job yaml and runtime
    workspace = tmp_path / ".lily"
    _write(
        workspace / "jobs" / "nightly.job.yaml",
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
            "  type: cron\n"
            '  cron: "*/5 * * * *"\n'
            "  timezone: UTC\n"
        ),
    )
    runtime = _build_runtime(workspace)

    # Act - start runtime
    runtime.start()
    try:
        # Assert - job registered with expected defaults
        job = runtime._scheduler.get_job("job:nightly_security_council")
        assert job is not None
        assert job.coalesce is True
        assert job.max_instances == 1
        assert job.misfire_grace_time == 30
    finally:
        runtime.shutdown()


@pytest.mark.unit
def test_scheduler_listener_writes_execution_event_payload(tmp_path: Path) -> None:
    """Scheduler listener should append executed-event payload to jsonl stream."""
    # Arrange - workspace, runtime, and executed event
    workspace = tmp_path / ".lily"
    runtime = _build_runtime(workspace)
    event = JobExecutionEvent(
        code=EVENT_JOB_EXECUTED,
        job_id="job:nightly_security_council",
        jobstore="default",
        scheduled_run_time=datetime(2026, 2, 19, 10, 15, tzinfo=UTC),
        retval="run_abc123",
    )

    # Act - handle event
    runtime._handle_event(event)
    stream = workspace / "runs" / "nightly_security_council" / "scheduler_events.jsonl"

    # Assert - stream has event row with expected fields
    assert stream.exists()
    row = json.loads(stream.read_text(encoding="utf-8").splitlines()[-1])
    assert row["event_code"] == "EVENT_JOB_EXECUTED"
    assert row["job_id"] == "nightly_security_council"
    assert row["run_id"] == "run_abc123"


@pytest.mark.unit
def test_scheduler_listener_writes_error_event_payload(tmp_path: Path) -> None:
    """Scheduler listener should append error event with exception message."""
    # Arrange - workspace, runtime, error event
    workspace = tmp_path / ".lily"
    runtime = _build_runtime(workspace)
    event = JobExecutionEvent(
        code=EVENT_JOB_ERROR,
        job_id="job:nightly_security_council",
        jobstore="default",
        scheduled_run_time=datetime(2026, 2, 19, 10, 20, tzinfo=UTC),
        exception=RuntimeError("boom"),
    )

    # Act - handle error event
    runtime._handle_event(event)
    stream = workspace / "runs" / "nightly_security_council" / "scheduler_events.jsonl"
    row = json.loads(stream.read_text(encoding="utf-8").splitlines()[-1])

    # Assert - error event row
    assert row["event_code"] == "EVENT_JOB_ERROR"
    assert row["exception"] == "boom"


@pytest.mark.unit
def test_scheduler_executes_registered_job_via_aps_runtime(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Scheduler should execute registered callback through APS runtime loop."""
    # Arrange - workspace with cron job, runtime, interval trigger monkeypatch
    workspace = tmp_path / ".lily"
    _write(
        workspace / "jobs" / "nightly.job.yaml",
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
            "  type: cron\n"
            '  cron: "*/5 * * * *"\n'
            "  timezone: UTC\n"
        ),
    )
    runtime = _build_runtime(workspace)
    monkeypatch.setattr(
        "lily.jobs.scheduler_runtime.CronTrigger.from_crontab",
        lambda *_args, **_kwargs: IntervalTrigger(seconds=0.2),
    )

    # Act - start and wait for interval trigger
    runtime.start()
    try:
        time.sleep(0.6)
    finally:
        runtime.shutdown()

    # Assert - run dirs created
    runs_root = workspace / "runs" / "nightly_security_council"
    run_dirs = (
        [path for path in runs_root.iterdir() if path.is_dir()]
        if runs_root.exists()
        else []
    )
    assert run_dirs


@pytest.mark.unit
def test_scheduler_pause_resume_disable_persist_state(tmp_path: Path) -> None:
    """Lifecycle controls should persist state and apply to APS jobs."""
    # Arrange - workspace with cron job and runtime
    workspace = tmp_path / ".lily"
    _write(
        workspace / "jobs" / "nightly.job.yaml",
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
            "  type: cron\n"
            '  cron: "*/5 * * * *"\n'
            "  timezone: UTC\n"
        ),
    )
    runtime = _build_runtime(workspace)

    # Act - start then pause resume disable
    runtime.start()
    try:
        runtime.pause_job("nightly_security_council")
        paused = runtime._scheduler.get_job("job:nightly_security_council")
        # Assert - paused state
        assert paused is not None
        assert paused.next_run_time is None

        runtime.resume_job("nightly_security_council")
        resumed = runtime._scheduler.get_job("job:nightly_security_council")
        assert resumed is not None
        assert resumed.next_run_time is not None

        runtime.disable_job("nightly_security_council")
        assert runtime._scheduler.get_job("job:nightly_security_council") is None
        status = runtime.status()
        states = status["states"]
        assert isinstance(states, list)
        assert states
        first = states[0]
        assert isinstance(first, dict)
        assert first["state"] == "disabled"
    finally:
        runtime.shutdown()


@pytest.mark.unit
def test_scheduler_persisted_pause_state_survives_restart(tmp_path: Path) -> None:
    """Paused scheduler state should persist and be re-applied on restart."""
    # Arrange - workspace with cron job, runtime, start and pause then shutdown
    workspace = tmp_path / ".lily"
    _write(
        workspace / "jobs" / "nightly.job.yaml",
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
            "  type: cron\n"
            '  cron: "*/5 * * * *"\n'
            "  timezone: UTC\n"
        ),
    )
    runtime = _build_runtime(workspace)
    runtime.start()
    runtime.pause_job("nightly_security_council")
    runtime.shutdown()

    # Act - restart runtime
    restarted = _build_runtime(workspace)
    restarted.start()
    try:
        # Assert - job still paused after restart
        paused = restarted._scheduler.get_job("job:nightly_security_council")
        assert paused is not None
        assert paused.next_run_time is None
        status = restarted.status()
        states = status["states"]
        assert isinstance(states, list)
        assert states
        row = states[0]
        assert isinstance(row, dict)
        assert row["state"] == "paused"
    finally:
        restarted.shutdown()

"""Unit tests for `/jobs` command handler behavior."""

from __future__ import annotations

from pathlib import Path

from lily.blueprints import build_default_blueprint_registry
from lily.commands.handlers.jobs import JobsCommand
from lily.commands.parser import CommandCall
from lily.jobs import JobExecutor, JobRepository
from lily.session.models import ModelConfig, Session
from lily.skills.types import SkillSnapshot


def _session() -> Session:
    """Create minimal empty-snapshot session fixture."""
    return Session(
        session_id="session-jobs",
        active_agent="default",
        skill_snapshot=SkillSnapshot(version="v-test", skills=()),
        model_config=ModelConfig(),
    )


def _write(path: Path, content: str) -> None:
    """Write utf-8 file content for tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_command(workspace_root: Path) -> JobsCommand:
    """Build jobs command with real repository/executor wiring."""
    executor = JobExecutor(
        repository=JobRepository(jobs_dir=workspace_root / "jobs"),
        blueprint_registry=build_default_blueprint_registry(),
        runs_root=workspace_root / "runs",
    )
    return JobsCommand(
        executor,
        runs_root=workspace_root / "runs",
    )


class _StubSchedulerControl:
    """Minimal scheduler control stub for jobs command tests."""

    def __init__(self) -> None:
        self.actions: list[tuple[str, str]] = []

    def pause_job(self, job_id: str) -> None:
        self.actions.append(("pause", job_id))

    def resume_job(self, job_id: str) -> None:
        self.actions.append(("resume", job_id))

    def disable_job(self, job_id: str) -> None:
        self.actions.append(("disable", job_id))

    def status(self) -> dict[str, object]:
        return {
            "started": True,
            "sqlite_path": ".lily/db/jobs_scheduler.sqlite3",
            "registered_jobs": 1,
            "state_rows": 1,
            "states": [
                {
                    "job_id": "nightly_security_council",
                    "state": "active",
                    "spec_hash": "abc",
                    "updated_at": "2026-02-19T23:00:00Z",
                }
            ],
        }


def test_jobs_list_and_run_paths_work_in_handler(tmp_path: Path) -> None:
    """`/jobs list` and `/jobs run` should succeed for valid job spec."""
    workspace_root = tmp_path / ".lily"
    _write(
        workspace_root / "jobs" / "nightly.job.yaml",
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
    command = _build_command(workspace_root)
    session = _session()

    listed = command.execute(
        CommandCall(name="jobs", args=("list",), raw="/jobs list"),
        session,
    )
    ran = command.execute(
        CommandCall(
            name="jobs",
            args=("run", "nightly_security_council"),
            raw="/jobs run nightly_security_council",
        ),
        session,
    )

    assert listed.status.value == "ok"
    assert listed.code == "jobs_listed"
    assert "nightly_security_council - Nightly security council" in listed.message
    assert ran.status.value == "ok"
    assert ran.code == "job_run_completed"
    assert ran.data is not None
    run_path = Path(str(ran.data["run_path"]))
    assert (run_path / "run_receipt.json").exists()
    assert (run_path / "summary.md").exists()
    assert (run_path / "events.jsonl").exists()


def test_jobs_run_missing_job_maps_to_job_not_found(tmp_path: Path) -> None:
    """Missing job id should return deterministic `job_not_found` error."""
    command = _build_command(tmp_path / ".lily")
    session = _session()

    result = command.execute(
        CommandCall(name="jobs", args=("run", "missing_job"), raw="/jobs run missing"),
        session,
    )

    assert result.status.value == "error"
    assert result.code == "job_not_found"


def test_jobs_tail_returns_latest_events(tmp_path: Path) -> None:
    """`/jobs tail` should return latest run events for existing job."""
    workspace_root = tmp_path / ".lily"
    _write(
        workspace_root / "jobs" / "nightly.job.yaml",
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
    command = _build_command(workspace_root)
    session = _session()
    _ = command.execute(
        CommandCall(
            name="jobs",
            args=("run", "nightly_security_council"),
            raw="/jobs run nightly_security_council",
        ),
        session,
    )

    tailed = command.execute(
        CommandCall(
            name="jobs",
            args=("tail", "nightly_security_council"),
            raw="/jobs tail nightly_security_council",
        ),
        session,
    )

    assert tailed.status.value == "ok"
    assert tailed.code == "jobs_tailed"
    assert tailed.data is not None
    assert tailed.data["job_id"] == "nightly_security_council"
    assert tailed.data["run_id"]
    assert tailed.data["line_count"] >= 1


def test_jobs_history_returns_run_entries(tmp_path: Path) -> None:
    """`/jobs history` should return newest-first history payload."""
    workspace_root = tmp_path / ".lily"
    _write(
        workspace_root / "jobs" / "nightly.job.yaml",
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
    command = _build_command(workspace_root)
    session = _session()
    _ = command.execute(
        CommandCall(
            name="jobs",
            args=("run", "nightly_security_council"),
            raw="/jobs run nightly_security_council",
        ),
        session,
    )

    result = command.execute(
        CommandCall(
            name="jobs",
            args=("history", "nightly_security_council", "--limit", "1"),
            raw="/jobs history nightly_security_council --limit 1",
        ),
        session,
    )

    assert result.status.value == "ok"
    assert result.code == "jobs_history"
    assert result.data is not None
    entries = result.data["entries"]
    assert isinstance(entries, list)
    assert entries
    assert len(entries) == 1


def test_jobs_scheduler_controls_and_status(tmp_path: Path) -> None:
    """Scheduler control subcommands should route to control port."""
    workspace_root = tmp_path / ".lily"
    scheduler_control = _StubSchedulerControl()
    executor = JobExecutor(
        repository=JobRepository(jobs_dir=workspace_root / "jobs"),
        blueprint_registry=build_default_blueprint_registry(),
        runs_root=workspace_root / "runs",
    )
    command = JobsCommand(
        executor,
        runs_root=workspace_root / "runs",
        scheduler_control=scheduler_control,
    )
    session = _session()

    paused = command.execute(
        CommandCall(
            name="jobs",
            args=("pause", "nightly_security_council"),
            raw="/jobs pause nightly_security_council",
        ),
        session,
    )
    resumed = command.execute(
        CommandCall(
            name="jobs",
            args=("resume", "nightly_security_council"),
            raw="/jobs resume nightly_security_council",
        ),
        session,
    )
    disabled = command.execute(
        CommandCall(
            name="jobs",
            args=("disable", "nightly_security_council"),
            raw="/jobs disable nightly_security_council",
        ),
        session,
    )
    status = command.execute(
        CommandCall(name="jobs", args=("status",), raw="/jobs status"),
        session,
    )

    assert paused.code == "jobs_paused"
    assert resumed.code == "jobs_resumed"
    assert disabled.code == "jobs_disabled"
    assert status.code == "jobs_scheduler_status"
    assert scheduler_control.actions == [
        ("pause", "nightly_security_council"),
        ("resume", "nightly_security_council"),
        ("disable", "nightly_security_council"),
    ]

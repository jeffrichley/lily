"""Unit tests for `/jobs` command routing through runtime facade."""

from __future__ import annotations

from pathlib import Path

from lily.runtime.facade import RuntimeFacade
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


def test_jobs_list_and_run_paths_work_in_runtime(tmp_path: Path) -> None:
    """`/jobs list` and `/jobs run` should succeed for valid J0 job spec."""
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
    runtime = RuntimeFacade(workspace_root=workspace_root)
    session = _session()

    listed = runtime.handle_input("/jobs list", session)
    ran = runtime.handle_input("/jobs run nightly_security_council", session)

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
    runtime = RuntimeFacade(workspace_root=tmp_path / ".lily")
    session = _session()

    result = runtime.handle_input("/jobs run missing_job", session)

    assert result.status.value == "error"
    assert result.code == "job_not_found"

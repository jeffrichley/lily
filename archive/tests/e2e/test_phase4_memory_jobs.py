"""Phase 4 e2e tests for memory and jobs flows."""

from __future__ import annotations

from pathlib import Path

import pytest


def _write_job_spec(workspace_root: Path, *, trigger_type: str = "manual") -> None:
    """Write minimal job spec for jobs command e2e flows."""
    trigger_block = "trigger:\n  type: manual\n"
    if trigger_type == "cron":
        trigger_block = 'trigger:\n  type: cron\n  cron: "0 2 * * *"\n  timezone: UTC\n'
    job_path = workspace_root / "jobs" / "nightly.job.yaml"
    job_path.parent.mkdir(parents=True, exist_ok=True)
    job_path.write_text(
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
            "  max_findings: 5\n" + trigger_block
        ),
        encoding="utf-8",
    )


@pytest.mark.e2e
def test_memory_long_and_evidence_e2e(e2e_env: object) -> None:
    """Memory show/evidence ingest/evidence show should work end-to-end."""
    # Arrange - initialized workspace and evidence source text file
    env = e2e_env
    env.init()
    notes = env.root / "notes.txt"
    notes.write_text(
        "User preference: favorite color is dark royal purple.\n",
        encoding="utf-8",
    )

    # Act - remember, show memory, ingest evidence, and query evidence
    remembered = env.run("/remember favorite color is dark royal purple")
    shown = env.run("/memory show")
    ingested = env.run(f"/memory evidence ingest {notes}")
    evidence = env.run("/memory evidence show dark royal purple")

    # Assert - all commands succeed and expected content is visible
    assert remembered.exit_code == 0
    assert shown.exit_code == 0
    assert ingested.exit_code == 0
    assert evidence.exit_code == 0
    assert "dark royal" in shown.stdout.lower()
    assert "purple" in shown.stdout.lower()
    assert "Semantic Evidence" in evidence.stdout


@pytest.mark.e2e
def test_jobs_lifecycle_and_artifacts_e2e(e2e_env: object) -> None:
    """Jobs list/run/tail/history should execute and emit artifacts."""
    # Arrange - initialized workspace with one manual job spec
    env = e2e_env
    _write_job_spec(env.workspace_dir.parent)
    env.init()

    # Act - execute jobs lifecycle commands
    listed = env.run("/jobs list")
    ran = env.run("/jobs run nightly_security_council")
    tailed = env.run("/jobs tail nightly_security_council")
    history = env.run("/jobs history nightly_security_council --limit 1")

    # Assert - command success and required run artifacts present
    assert listed.exit_code == 0
    assert ran.exit_code == 0
    assert tailed.exit_code == 0
    assert history.exit_code == 0

    runs_root = env.workspace_dir.parent / "runs" / "nightly_security_council"
    run_dirs = sorted(path for path in runs_root.iterdir() if path.is_dir())
    assert run_dirs
    latest = run_dirs[-1]
    assert (latest / "run_receipt.json").exists()
    assert (latest / "summary.md").exists()
    assert (latest / "events.jsonl").exists()


@pytest.mark.e2e
def test_scheduler_controls_e2e(e2e_env: object) -> None:
    """Scheduler status/pause/resume/disable flows should run end-to-end."""
    # Arrange - initialized workspace with one cron job spec
    env = e2e_env
    _write_job_spec(env.workspace_dir.parent, trigger_type="cron")
    env.init()

    # Act - execute scheduler control commands
    status = env.run("/jobs status")
    paused = env.run("/jobs pause nightly_security_council")
    resumed = env.run("/jobs resume nightly_security_council")
    disabled = env.run("/jobs disable nightly_security_council")

    # Assert - scheduler commands succeed
    assert status.exit_code == 0
    assert paused.exit_code == 0
    assert resumed.exit_code == 0
    assert disabled.exit_code == 0

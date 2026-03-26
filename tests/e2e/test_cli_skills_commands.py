"""End-to-end tests for ``lily skills`` CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from lily.cli import app

pytestmark = pytest.mark.e2e

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SKILLS_FIXTURE_AGENT = _REPO_ROOT / "tests/fixtures/config/skills_retrieval/agent.toml"


def _minimal_agent_no_skills(path: Path) -> None:
    """Write a valid runtime config without a ``[skills]`` section."""
    path.write_text(
        "schema_version = 1\n"
        "[agent]\n"
        'name = "t"\n'
        'system_prompt = "x"\n'
        "[models.profiles.default]\n"
        'provider = "openai"\n'
        'model = "m"\n'
        "temperature = 0.1\n"
        "timeout_seconds = 30\n"
        "[models.profiles.long_context]\n"
        'provider = "openai"\n'
        'model = "m2"\n'
        "temperature = 0.1\n"
        "timeout_seconds = 30\n"
        "[models.routing]\n"
        "enabled = false\n"
        'default_profile = "default"\n'
        'long_context_profile = "long_context"\n'
        "complexity_threshold = 8000\n"
        "[tools]\n"
        'allowlist = ["echo_tool"]\n'
        "[policies]\n"
        "max_iterations = 10\n"
        "max_model_calls = 10\n"
        "max_tool_calls = 10\n"
        "[logging]\n"
        'level = "INFO"\n',
        encoding="utf-8",
    )


def test_cli_skills_list_shows_index_table_and_fixture_row() -> None:
    """List command prints Rich table headers and the fixture skill key."""
    # Arrange - fixture config with one skill under tests/fixtures/...
    runner = CliRunner()
    # Act - run list against the checked-in skills fixture
    result = runner.invoke(
        app,
        ["skills", "list", "--config", str(_SKILLS_FIXTURE_AGENT)],
    )
    # Assert - table title and fixture canonical key appear in stdout
    assert result.exit_code == 0
    assert "Skills index" in result.stdout
    assert "Key" in result.stdout
    assert "fixture-skill" in result.stdout


def test_cli_skills_inspect_shows_metadata_and_policy_columns() -> None:
    """Inspect command prints canonical key and policy lines."""
    # Arrange - CLI runner for invoking Typer app
    runner = CliRunner()
    # Act - inspect the fixture skill by canonical key
    result = runner.invoke(
        app,
        [
            "skills",
            "inspect",
            "fixture-skill",
            "--config",
            str(_SKILLS_FIXTURE_AGENT),
        ],
    )
    # Assert - structured panel includes policy and tool intersection lines
    assert result.exit_code == 0
    assert "Canonical key" in result.stdout
    assert "Policy (retrieval)" in result.stdout
    assert "Effective tools" in result.stdout


def test_cli_skills_inspect_not_found_exits_nonzero() -> None:
    """Missing skill name yields a clear error panel and exit code 1."""
    # Arrange - CLI runner
    runner = CliRunner()
    # Act - request a skill id that does not exist in the fixture index
    result = runner.invoke(
        app,
        [
            "skills",
            "inspect",
            "no-such-skill-xyz",
            "--config",
            str(_SKILLS_FIXTURE_AGENT),
        ],
    )
    # Assert - non-zero exit and operator-facing not-found title
    assert result.exit_code == 1
    assert "Not found" in result.stdout


def test_cli_skills_doctor_shows_summary_table() -> None:
    """Doctor command prints summary and diagnostics tables."""
    # Arrange - use fixture agent so discovery runs
    runner = CliRunner()
    # Act - run doctor on the fixture skills config
    result = runner.invoke(
        app,
        ["skills", "doctor", "--config", str(_SKILLS_FIXTURE_AGENT)],
    )
    # Assert - summary and diagnostics sections render
    assert result.exit_code == 0
    assert "Summary" in result.stdout
    assert "Diagnostics" in result.stdout
    assert "Candidates parsed" in result.stdout


def test_cli_skills_list_disabled_skills_shows_notice(tmp_path: Path) -> None:
    """When no skills section exists, list explains skills are disabled."""
    # Arrange - minimal config without skills
    agent = tmp_path / "agent.toml"
    _minimal_agent_no_skills(agent)
    runner = CliRunner()
    # Act - list skills when subsystem is not configured
    result = runner.invoke(app, ["skills", "list", "--config", str(agent)])
    # Assert - user-facing notice instead of an index table
    assert result.exit_code == 0
    assert (
        "disabled" in result.stdout.lower() or "not configured" in result.stdout.lower()
    )

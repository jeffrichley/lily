"""End-to-end smoke tests for the Lily CLI run command."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import ClassVar
from uuid import UUID

import pytest
from typer.testing import CliRunner

from lily.cli import app
from lily.runtime.agent_runtime import AgentRunResult

pytestmark = pytest.mark.e2e

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SKILLS_FIXTURE_AGENT = _REPO_ROOT / "tests/fixtures/config/skills_retrieval/agent.toml"


class _FakeSupervisor:
    """Test double supervisor used to avoid external model calls in e2e tests."""

    captured_conversation_ids: ClassVar[list[str | None]] = []

    @classmethod
    def from_config_paths(
        cls,
        config_path: str | Path,
        override_config_path: str | Path | None = None,
        *,
        skill_telemetry_echo: bool = False,
    ) -> _FakeSupervisor:
        """Build fake supervisor from config paths for command smoke tests."""
        _ = (config_path, override_config_path, skill_telemetry_echo)
        return cls()

    def run_prompt(
        self,
        prompt: str,
        conversation_id: str | None = None,
    ) -> AgentRunResult:
        """Return deterministic response payload for CLI assertions."""
        self.captured_conversation_ids.append(conversation_id)
        return AgentRunResult(
            final_output=f"fake: {prompt}",
            message_count=2,
            conversation_id=conversation_id,
        )


def test_cli_run_command_smoke_with_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Runs CLI command with config and verifies visible output contract."""
    # Arrange - substitute runtime supervisor to avoid real provider calls.
    monkeypatch.setattr("lily.cli.LilySupervisor", _FakeSupervisor)
    config_file = tmp_path / "agent.yaml"
    config_file.write_text("schema_version: 1\n", encoding="utf-8")
    _FakeSupervisor.captured_conversation_ids = []
    runner = CliRunner()

    # Act - invoke CLI run command using baseline config path.
    with monkeypatch.context() as context:
        context.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "--prompt",
                "hello from e2e",
            ],
        )

    # Assert - command exits and reports generated conversation id.
    assert result.exit_code == 0
    assert "fake: hello from e2e" in result.stdout
    assert "Conversation ID" in result.stdout
    assert "Active conversation id:" in result.stdout
    assert len(_FakeSupervisor.captured_conversation_ids) == 1


def test_cli_run_smoke_with_skills_fixture_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CLI run accepts the checked-in skills fixture config (fake supervisor)."""
    # Arrange - fake supervisor and isolated temp fixture copy.
    monkeypatch.setattr("lily.cli.LilySupervisor", _FakeSupervisor)
    _FakeSupervisor.captured_conversation_ids = []
    runner = CliRunner()
    fixture_dir = _SKILLS_FIXTURE_AGENT.parent
    temp_fixture_dir = tmp_path / "skills_retrieval"
    temp_fixture_dir.mkdir(parents=True)
    shutil.copy2(fixture_dir / "agent.toml", temp_fixture_dir / "agent.toml")
    shutil.copy2(fixture_dir / "tools.toml", temp_fixture_dir / "tools.toml")
    shutil.copytree(fixture_dir / "skills", temp_fixture_dir / "skills")
    temp_fixture_agent = temp_fixture_dir / "agent.toml"

    # Act - invoke run with skills-enabled agent.toml
    with monkeypatch.context() as context:
        context.chdir(temp_fixture_dir)
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(temp_fixture_agent),
                "--prompt",
                "skills fixture e2e prompt",
            ],
        )
    # Assert - same visible contract as baseline smoke
    assert result.exit_code == 0
    assert "fake: skills fixture e2e prompt" in result.stdout
    assert "Conversation ID" in result.stdout
    generated_id = _FakeSupervisor.captured_conversation_ids[0]
    assert generated_id is not None
    UUID(generated_id)


def test_cli_run_command_attach_explicit_and_last(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Supports explicit attach and attach-last resolution modes."""
    # Arrange - patch fake supervisor and isolate cwd session DB.
    monkeypatch.setattr("lily.cli.LilySupervisor", _FakeSupervisor)
    _FakeSupervisor.captured_conversation_ids = []
    config_file = tmp_path / "agent.yaml"
    config_file.write_text("schema_version: 1\n", encoding="utf-8")
    runner = CliRunner()
    explicit_id = "00000000-0000-0000-0000-000000000001"

    # Act - seed one conversation, then attach explicit and attach-last.
    with monkeypatch.context() as context:
        context.chdir(tmp_path)
        seed_result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "--prompt",
                "seed conversation",
            ],
        )
        explicit_result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "--conversation-id",
                _FakeSupervisor.captured_conversation_ids[0] or "",
                "--prompt",
                "explicit attach",
            ],
        )
        last_result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "--last-conversation",
                "--prompt",
                "last attach",
            ],
        )
        bad_explicit_result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "--conversation-id",
                explicit_id,
                "--prompt",
                "bad explicit",
            ],
        )

    # Assert - explicit + last pass and use expected ids, invalid explicit fails.
    assert seed_result.exit_code == 0
    assert explicit_result.exit_code == 0
    assert last_result.exit_code == 0
    assert bad_explicit_result.exit_code == 1
    assert "Unknown conversation id for attach" in bad_explicit_result.stdout
    assert len(_FakeSupervisor.captured_conversation_ids) == 3
    seeded_id = _FakeSupervisor.captured_conversation_ids[0]
    assert _FakeSupervisor.captured_conversation_ids[1] == seeded_id
    assert _FakeSupervisor.captured_conversation_ids[2] == seeded_id


def test_cli_run_command_rejects_ambiguous_attach_flags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Rejects simultaneous explicit and last attach mode flags."""
    # Arrange - patch fake supervisor and isolate cwd session DB.
    monkeypatch.setattr("lily.cli.LilySupervisor", _FakeSupervisor)
    _FakeSupervisor.captured_conversation_ids = []
    config_file = tmp_path / "agent.yaml"
    config_file.write_text("schema_version: 1\n", encoding="utf-8")
    runner = CliRunner()

    # Act - invoke run with mutually-exclusive attach flags.
    with monkeypatch.context() as context:
        context.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "--conversation-id",
                "id-1",
                "--last-conversation",
                "--prompt",
                "ambiguous",
            ],
        )

    # Assert - command fails with deterministic user-visible error.
    assert result.exit_code == 1
    assert "Choose only one attach mode" in result.stdout
    assert _FakeSupervisor.captured_conversation_ids == []

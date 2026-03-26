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


def _create_named_agent_workspace(root: Path, name: str) -> Path:
    """Create minimal valid named-agent workspace for CLI tests."""
    agent_dir = root / ".lily" / "agents" / name
    agent_dir.mkdir(parents=True)
    (agent_dir / "agent.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (agent_dir / "tools.toml").write_text("[[definitions]]\n", encoding="utf-8")
    for filename in ("AGENTS.md", "IDENTITY.md", "SOUL.md", "USER.md", "TOOLS.md"):
        (agent_dir / filename).write_text(f"# {filename}\n", encoding="utf-8")
    (agent_dir / "skills").mkdir()
    (agent_dir / "memory").mkdir()
    return agent_dir


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
        agent_workspace_dir: str | Path | None = None,
    ) -> _FakeSupervisor:
        """Build fake supervisor from config paths for command smoke tests."""
        _ = (
            config_path,
            override_config_path,
            skill_telemetry_echo,
            agent_workspace_dir,
        )
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


def test_cli_run_command_defaults_to_named_default_agent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Uses `.lily/agents/default` when no --config/--agent is provided."""
    # Arrange - create default agent workspace and patch fake supervisor.
    monkeypatch.setattr("lily.cli.LilySupervisor", _FakeSupervisor)
    _FakeSupervisor.captured_conversation_ids = []
    _create_named_agent_workspace(tmp_path, "default")
    runner = CliRunner()

    # Act - invoke command with no explicit config/agent selection.
    with monkeypatch.context() as context:
        context.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "run",
                "--prompt",
                "default agent mode",
            ],
        )

    # Assert - run succeeds and fake supervisor receives one conversation id.
    assert result.exit_code == 0
    assert "fake: default agent mode" in result.stdout
    assert len(_FakeSupervisor.captured_conversation_ids) == 1


def test_cli_run_command_accepts_named_agent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Resolves selected named-agent workspace via --agent flag."""
    # Arrange - create two named-agent workspaces and patch fake supervisor.
    monkeypatch.setattr("lily.cli.LilySupervisor", _FakeSupervisor)
    _FakeSupervisor.captured_conversation_ids = []
    _create_named_agent_workspace(tmp_path, "default")
    _create_named_agent_workspace(tmp_path, "pepper-potts")
    runner = CliRunner()

    # Act - invoke run command with explicit named-agent selector.
    with monkeypatch.context() as context:
        context.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "run",
                "--agent",
                "pepper-potts",
                "--prompt",
                "named agent mode",
            ],
        )

    # Assert - run succeeds and emits expected visible output.
    assert result.exit_code == 0
    assert "fake: named agent mode" in result.stdout
    assert len(_FakeSupervisor.captured_conversation_ids) == 1


def test_cli_run_command_rejects_unknown_named_agent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Fails deterministically when --agent directory is missing."""
    # Arrange - patch fake supervisor and create only default workspace.
    monkeypatch.setattr("lily.cli.LilySupervisor", _FakeSupervisor)
    _create_named_agent_workspace(tmp_path, "default")
    runner = CliRunner()

    # Act - invoke with non-existent named agent.
    with monkeypatch.context() as context:
        context.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "run",
                "--agent",
                "missing-agent",
                "--prompt",
                "should fail",
            ],
        )

    # Assert - command fails with deterministic error payload.
    assert result.exit_code == 1
    assert "Unknown agent 'missing-agent'" in result.stdout


def test_cli_run_command_rejects_ambiguous_agent_and_config_modes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Rejects simultaneous --agent and --config runtime modes."""
    # Arrange - patch fake supervisor and create valid local config + workspace.
    monkeypatch.setattr("lily.cli.LilySupervisor", _FakeSupervisor)
    config_file = tmp_path / "agent.yaml"
    config_file.write_text("schema_version: 1\n", encoding="utf-8")
    _create_named_agent_workspace(tmp_path, "default")
    runner = CliRunner()

    # Act - invoke with both explicit runtime mode selectors.
    with monkeypatch.context() as context:
        context.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "run",
                "--agent",
                "default",
                "--config",
                str(config_file),
                "--prompt",
                "ambiguous mode",
            ],
        )

    # Assert - command fails with deterministic mode conflict error.
    assert result.exit_code == 1
    assert "Choose only one runtime mode" in result.stdout


def test_cli_run_attach_last_is_isolated_per_agent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Ensures attach-last resolves within selected agent session scope only."""
    # Arrange - create two named workspaces and patch fake supervisor.
    monkeypatch.setattr("lily.cli.LilySupervisor", _FakeSupervisor)
    _FakeSupervisor.captured_conversation_ids = []
    _create_named_agent_workspace(tmp_path, "default")
    _create_named_agent_workspace(tmp_path, "pepper-potts")
    runner = CliRunner()

    # Act - seed one conversation per agent, then attach-last on each.
    with monkeypatch.context() as context:
        context.chdir(tmp_path)
        seed_default = runner.invoke(
            app,
            ["run", "--agent", "default", "--prompt", "seed default"],
        )
        default_seed_id = _FakeSupervisor.captured_conversation_ids[-1]
        seed_pepper = runner.invoke(
            app,
            ["run", "--agent", "pepper-potts", "--prompt", "seed pepper"],
        )
        pepper_seed_id = _FakeSupervisor.captured_conversation_ids[-1]
        attach_default_last = runner.invoke(
            app,
            ["run", "--agent", "default", "--last-conversation", "--prompt", "d last"],
        )
        default_last_id = _FakeSupervisor.captured_conversation_ids[-1]
        attach_pepper_last = runner.invoke(
            app,
            [
                "run",
                "--agent",
                "pepper-potts",
                "--last-conversation",
                "--prompt",
                "p last",
            ],
        )
        pepper_last_id = _FakeSupervisor.captured_conversation_ids[-1]

    # Assert - each agent resolves its own last conversation id.
    assert seed_default.exit_code == 0
    assert seed_pepper.exit_code == 0
    assert attach_default_last.exit_code == 0
    assert attach_pepper_last.exit_code == 0
    assert default_seed_id is not None
    assert pepper_seed_id is not None
    assert default_last_id == default_seed_id
    assert pepper_last_id == pepper_seed_id
    assert default_seed_id != pepper_seed_id

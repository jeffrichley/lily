"""End-to-end smoke tests for the Lily CLI run command."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from lily.cli import app
from lily.runtime.agent_runtime import AgentRunResult

pytestmark = pytest.mark.e2e


class _FakeSupervisor:
    """Test double supervisor used to avoid external model calls in e2e tests."""

    @classmethod
    def from_config_paths(
        cls,
        config_path: str | Path,
        override_config_path: str | Path | None = None,
    ) -> _FakeSupervisor:
        """Build fake supervisor from config paths for command smoke tests."""
        _ = (config_path, override_config_path)
        return cls()

    def run_prompt(self, prompt: str) -> AgentRunResult:
        """Return deterministic response payload for CLI assertions."""
        return AgentRunResult(final_output=f"fake: {prompt}", message_count=2)


def test_cli_run_command_smoke_with_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Runs CLI command with config and verifies visible output contract."""
    # Arrange - substitute runtime supervisor to avoid real provider calls.
    monkeypatch.setattr("lily.cli.LilySupervisor", _FakeSupervisor)
    config_file = tmp_path / "agent.yaml"
    config_file.write_text("schema_version: 1\n", encoding="utf-8")
    runner = CliRunner()

    # Act - invoke CLI run command using baseline config path.
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

    # Assert - command exits successfully and prints the fake final output.
    assert result.exit_code == 0
    assert "fake: hello from e2e" in result.stdout

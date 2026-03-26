"""End-to-end smoke tests for Lily Textual TUI."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import anyio
import pytest
from textual.widgets import Input
from typer.testing import CliRunner

from lily.cli import app
from lily.runtime.agent_runtime import AgentRunResult
from lily.ui.app import LilyTuiApp
from lily.ui.widgets.transcript import TranscriptLog

pytestmark = pytest.mark.e2e


class _FakeSupervisor:
    """Test double supervisor for TUI smoke tests."""

    def run_prompt(
        self,
        prompt: str,
        conversation_id: str | None = None,
    ) -> AgentRunResult:
        """Return deterministic response for prompt assertions.

        Args:
            prompt: Prompt text entered in TUI.
            conversation_id: Optional active conversation id for runtime thread.

        Returns:
            Deterministic response payload.
        """
        return AgentRunResult(
            final_output=f"fake: {prompt}",
            message_count=2,
            conversation_id=conversation_id,
        )


def _fake_supervisor_factory(
    config_path: Path,
    override_config_path: Path | None,
    skill_telemetry_echo: bool = False,
) -> _FakeSupervisor:
    """Build fake supervisor while validating config arguments are plumbed.

    Args:
        config_path: Base config path from app startup.
        override_config_path: Optional override path.
        skill_telemetry_echo: Echo flag from TUI (unused by fake).

    Returns:
        Fake supervisor instance.
    """
    _ = (config_path, override_config_path, skill_telemetry_echo)
    return _FakeSupervisor()


def test_textual_tui_startup_and_prompt_cycle(tmp_path: Path) -> None:
    """Starts TUI, submits a prompt, and verifies transcript entries.

    Args:
        tmp_path: Temporary path fixture for isolated config file.
    """
    # Arrange - create app with fake supervisor factory for deterministic responses.
    config_file = tmp_path / "agent.yaml"
    config_file.write_text("schema_version: 1\n", encoding="utf-8")
    app = LilyTuiApp(
        config_path=config_file,
        conversation_id="conv-tui-1",
        supervisor_factory=_fake_supervisor_factory,
    )

    async def _exercise_ui() -> list[str]:
        """Execute interactive test steps against Textual test pilot."""
        # Act - run app test pilot and submit one prompt via input widget.
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#prompt_input")
            pilot.app.screen.query_one("#prompt_input", Input).value = "hello tui"
            await pilot.press("enter")
            await pilot.pause()
            transcript = pilot.app.screen.query_one("#transcript", TranscriptLog)
            return list(transcript.history)

    history = anyio.run(_exercise_ui)

    # Assert - transcript contains startup, conversation id, user, and assistant.
    assert any("Lily TUI ready" in line for line in history)
    assert any("Active conversation id: conv-tui-1" in line for line in history)
    assert any(line == "[you] hello tui" for line in history)
    assert any(line == "[lily] fake: hello tui" for line in history)


class _FakeTuiApp:
    """Fake TUI app class used to validate CLI tui command wiring."""

    created_conversation_ids: ClassVar[list[str | None]] = []

    def __init__(
        self,
        config_path: Path,
        override_config_path: Path | None = None,
        conversation_id: str | None = None,
        supervisor_factory: object | None = None,
        skill_telemetry_echo: bool = False,
    ) -> None:
        """Capture constructor arguments for assertions."""
        _ = (
            config_path,
            override_config_path,
            supervisor_factory,
            skill_telemetry_echo,
        )
        self._conversation_id = conversation_id
        self.created_conversation_ids.append(conversation_id)

    def run(self) -> None:
        """No-op fake run method used by command test."""


def test_cli_tui_command_supports_default_explicit_and_last_attach(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verifies attach-mode resolution and exit output for `lily tui`."""
    # Arrange - patch TUI app class and isolate cwd for session DB.
    monkeypatch.setattr("lily.cli.LilyTuiApp", _FakeTuiApp)
    _FakeTuiApp.created_conversation_ids = []
    config_file = tmp_path / "agent.yaml"
    config_file.write_text("schema_version: 1\n", encoding="utf-8")
    runner = CliRunner()

    # Act - run default/new, explicit attach, then last attach.
    with monkeypatch.context() as context:
        context.chdir(tmp_path)
        default_result = runner.invoke(
            app,
            ["tui", "--config", str(config_file)],
        )
        seeded_id = _FakeTuiApp.created_conversation_ids[0]
        explicit_result = runner.invoke(
            app,
            [
                "tui",
                "--config",
                str(config_file),
                "--conversation-id",
                seeded_id or "",
            ],
        )
        last_result = runner.invoke(
            app,
            [
                "tui",
                "--config",
                str(config_file),
                "--last-conversation",
            ],
        )
        ambiguous_result = runner.invoke(
            app,
            [
                "tui",
                "--config",
                str(config_file),
                "--conversation-id",
                "id-1",
                "--last-conversation",
            ],
        )

    # Assert - modes resolve and emit deterministic conversation-id output.
    assert default_result.exit_code == 0
    assert explicit_result.exit_code == 0
    assert last_result.exit_code == 0
    assert ambiguous_result.exit_code == 1
    assert "Active conversation id:" in default_result.stdout
    assert "Active conversation id:" in explicit_result.stdout
    assert "Active conversation id:" in last_result.stdout
    assert "Choose only one attach mode" in ambiguous_result.stdout
    assert len(_FakeTuiApp.created_conversation_ids) == 3
    assert _FakeTuiApp.created_conversation_ids[1] == seeded_id
    assert _FakeTuiApp.created_conversation_ids[2] == seeded_id

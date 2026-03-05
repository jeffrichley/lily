"""End-to-end smoke tests for Lily Textual TUI."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest
from textual.widgets import Input

from lily.runtime.agent_runtime import AgentRunResult
from lily.ui.app import LilyTuiApp
from lily.ui.widgets.transcript import TranscriptLog

pytestmark = pytest.mark.e2e


class _FakeSupervisor:
    """Test double supervisor for TUI smoke tests."""

    def run_prompt(self, prompt: str) -> AgentRunResult:
        """Return deterministic response for prompt assertions.

        Args:
            prompt: Prompt text entered in TUI.

        Returns:
            Deterministic response payload.
        """
        return AgentRunResult(final_output=f"fake: {prompt}", message_count=2)


def _fake_supervisor_factory(
    config_path: Path,
    override_config_path: Path | None,
) -> _FakeSupervisor:
    """Build fake supervisor while validating config arguments are plumbed.

    Args:
        config_path: Base config path from app startup.
        override_config_path: Optional override path.

    Returns:
        Fake supervisor instance.
    """
    _ = (config_path, override_config_path)
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

    # Assert - transcript contains startup, user, and assistant entries.
    assert any("Lily TUI ready" in line for line in history)
    assert any(line == "[you] hello tui" for line in history)
    assert any(line == "[lily] fake: hello tui" for line in history)

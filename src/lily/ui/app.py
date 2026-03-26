"""Top-level Textual application for Lily interactive sessions."""
# ruff: noqa: PLR0913

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import ClassVar, Protocol

from textual.app import App
from textual.binding import Binding

from lily.agents.lily_supervisor import LilySupervisor
from lily.runtime.agent_runtime import AgentRunResult
from lily.ui.screens.chat import ChatScreen


class _SupervisorProtocol(Protocol):
    """Protocol for supervisor prompt execution used by the TUI."""

    def run_prompt(
        self,
        prompt: str,
        conversation_id: str | None = None,
    ) -> AgentRunResult:
        """Run one prompt through supervisor runtime.

        Args:
            prompt: Prompt text to execute.
            conversation_id: Optional conversation/thread id for resume continuity.
        """


type SupervisorFactory = Callable[
    [Path, Path | None, bool, Path | None], _SupervisorProtocol
]


def _default_supervisor_factory(
    config_path: Path,
    override_config_path: Path | None,
    skill_telemetry_echo: bool = False,
    agent_workspace_dir: Path | None = None,
) -> _SupervisorProtocol:
    """Build default supervisor from config paths.

    Args:
        config_path: Base runtime config path.
        override_config_path: Optional runtime override config path.
        skill_telemetry_echo: Mirror skill telemetry JSON to stderr when true.
        agent_workspace_dir: Optional named-agent workspace directory used to load
            middleware-injected identity context.

    Returns:
        Configured Lily supervisor instance.
    """
    return LilySupervisor.from_config_paths(
        config_path,
        override_config_path,
        skill_telemetry_echo=skill_telemetry_echo,
        agent_workspace_dir=agent_workspace_dir,
    )


class LilyTuiApp(App[None]):
    """Minimal chat TUI that uses existing supervisor runtime path."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("ctrl+q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
    ]
    CSS_PATH = "styles/app.tcss"
    TITLE = "Lily"
    SUB_TITLE = "Textual Interface"

    def __init__(
        self,
        config_path: Path,
        override_config_path: Path | None = None,
        conversation_id: str | None = None,
        supervisor_factory: SupervisorFactory = _default_supervisor_factory,
        skill_telemetry_echo: bool = False,
        agent_workspace_dir: Path | None = None,
    ) -> None:
        """Initialize TUI app with config-driven supervisor factory.

        Args:
            config_path: Base runtime config path.
            override_config_path: Optional runtime override config path.
            conversation_id: Active conversation id for this TUI process.
            supervisor_factory: Factory building supervisor runtime object.
            skill_telemetry_echo: Passed through when constructing the supervisor.
            agent_workspace_dir: Optional named-agent workspace directory used for
                identity context middleware injection.
        """
        super().__init__()
        self._config_path = config_path
        self._override_config_path = override_config_path
        self._conversation_id = conversation_id
        self._supervisor_factory = supervisor_factory
        self._skill_telemetry_echo = skill_telemetry_echo
        self._agent_workspace_dir = agent_workspace_dir
        self._supervisor: _SupervisorProtocol | None = None

    def on_mount(self) -> None:
        """Push the chat screen on startup."""
        self.push_screen(ChatScreen(conversation_id=self._conversation_id))

    def _get_supervisor(self) -> _SupervisorProtocol:
        """Lazily construct and return supervisor runtime object.

        Returns:
            Supervisor instance used for prompt execution.
        """
        if self._supervisor is None:
            self._supervisor = self._supervisor_factory(
                self._config_path,
                self._override_config_path,
                self._skill_telemetry_echo,
                self._agent_workspace_dir,
            )
        return self._supervisor

    def run_prompt_for_ui(self, prompt: str) -> str:
        """Execute prompt through same supervisor path used by CLI.

        Args:
            prompt: Prompt text from UI input.

        Returns:
            Final assistant output text.
        """
        result = self._get_supervisor().run_prompt(
            prompt,
            conversation_id=self._conversation_id,
        )
        return result.final_output

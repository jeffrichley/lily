"""CLI entrypoint for Lily supervisor runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lily.agents.lily_supervisor import LilySupervisor
from lily.runtime.agent_runtime import AgentRuntimeError
from lily.runtime.config_loader import ConfigLoadError
from lily.runtime.conversation_sessions import (
    ConversationSessionStore,
    ConversationSessionStoreError,
    default_sessions_db_path,
)
from lily.runtime.model_factory import ModelFactoryError
from lily.runtime.tool_registry import ToolRegistryError
from lily.ui.app import LilyTuiApp

app = typer.Typer(no_args_is_help=True)
_console = Console()
PromptOption = Annotated[
    str,
    typer.Option(..., "--prompt", help="Prompt text to send to Lily."),
]
ConfigOption = Annotated[
    Path,
    typer.Option(
        "--config",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Path to base runtime YAML config.",
    ),
]
OverrideOption = Annotated[
    Path | None,
    typer.Option(
        "--override",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Optional path to YAML override config.",
    ),
]
ConversationIdOption = Annotated[
    str | None,
    typer.Option(
        "--conversation-id",
        help="Attach to a specific conversation id.",
    ),
]
LastConversationOption = Annotated[
    bool,
    typer.Option(
        "--last-conversation",
        help="Attach to the most recently used conversation id.",
    ),
]


class ConversationResolutionError(ValueError):
    """Raised when attach mode selection or resolution fails."""


def _resolve_conversation_id(
    conversation_id: str | None,
    last_conversation: bool,
) -> str:
    """Resolve conversation mode to one active conversation id.

    Args:
        conversation_id: Explicit conversation id from CLI options.
        last_conversation: Whether to attach to most-recent conversation id.

    Returns:
        Resolved active conversation id for this process run.

    Raises:
        ConversationResolutionError: If attach mode flags are ambiguous.
    """
    if conversation_id is not None and last_conversation:
        msg = "Choose only one attach mode: --conversation-id or --last-conversation."
        raise ConversationResolutionError(msg)

    store = ConversationSessionStore(default_sessions_db_path(Path.cwd()))
    try:
        if conversation_id is not None:
            return store.attach(conversation_id)
        if last_conversation:
            return store.attach_last()
        return store.start_new()
    except ConversationSessionStoreError as exc:
        raise ConversationResolutionError(str(exc)) from exc


def _print_success_panel(
    final_output: str,
    message_count: int,
    conversation_id: str,
) -> None:
    """Render successful CLI output with rich primitives.

    Args:
        final_output: Final assistant text output.
        message_count: Number of messages in the runtime transcript.
        conversation_id: Active conversation id used for this run.
    """
    _console.print(Panel.fit(final_output, title="Lily", border_style="green"))

    table = Table(title="Run Summary")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Messages", str(message_count))
    table.add_row("Conversation ID", conversation_id)
    _console.print(table)
    _console.print(f"Active conversation id: {conversation_id}")


@app.callback()
def app_callback() -> None:
    """Root callback to keep explicit subcommand invocation (`lily run`)."""


@app.command("run")
def run_command(
    prompt: PromptOption,
    config: ConfigOption = Path(".lily/config/agent.yaml"),
    override: OverrideOption = None,
    conversation_id: ConversationIdOption = None,
    last_conversation: LastConversationOption = False,
) -> None:
    """Run a single prompt using YAML-configured Lily supervisor runtime.

    Args:
        prompt: Prompt text to execute.
        config: Base YAML config path.
        override: Optional override YAML config path.
        conversation_id: Optional explicit conversation id attach target.
        last_conversation: Whether to attach to most-recent conversation.

    Raises:
        Exit: Raised with non-zero code when runtime/config fails.
    """
    try:
        resolved_conversation_id = _resolve_conversation_id(
            conversation_id=conversation_id,
            last_conversation=last_conversation,
        )
        supervisor = LilySupervisor.from_config_paths(config, override)
        result = supervisor.run_prompt(
            prompt,
            conversation_id=resolved_conversation_id,
        )
    except (
        ConfigLoadError,
        ConversationResolutionError,
        ConversationSessionStoreError,
        ToolRegistryError,
        ModelFactoryError,
        AgentRuntimeError,
    ) as exc:
        _console.print(Panel.fit(str(exc), title="Lily Error", border_style="red"))
        raise typer.Exit(code=1) from exc

    _print_success_panel(
        final_output=result.final_output,
        message_count=result.message_count,
        conversation_id=resolved_conversation_id,
    )


@app.command("tui")
def tui_command(
    config: ConfigOption = Path(".lily/config/agent.yaml"),
    override: OverrideOption = None,
    conversation_id: ConversationIdOption = None,
    last_conversation: LastConversationOption = False,
) -> None:
    """Launch Textual TUI using YAML-configured Lily supervisor runtime.

    Args:
        config: Base YAML config path.
        override: Optional override YAML config path.
        conversation_id: Optional explicit conversation id attach target.
        last_conversation: Whether to attach to most-recent conversation.

    Raises:
        Exit: Raised with non-zero code when runtime/config fails.
    """
    try:
        resolved_conversation_id = _resolve_conversation_id(
            conversation_id=conversation_id,
            last_conversation=last_conversation,
        )
        app = LilyTuiApp(
            config_path=config,
            override_config_path=override,
            conversation_id=resolved_conversation_id,
        )
        app.run()
    except (
        ConfigLoadError,
        ConversationResolutionError,
        ConversationSessionStoreError,
        ToolRegistryError,
        ModelFactoryError,
        AgentRuntimeError,
    ) as exc:
        _console.print(Panel.fit(str(exc), title="Lily Error", border_style="red"))
        raise typer.Exit(code=1) from exc

    _console.print(f"Active conversation id: {resolved_conversation_id}")

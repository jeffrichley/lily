"""CLI entrypoint for Lily supervisor runtime."""
# ruff: noqa: PLR0913

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lily.agents.lily_supervisor import LilySupervisor
from lily.cli_options import OverrideOption
from lily.cli_skills import skills_app
from lily.runtime.agent_locator import AgentLocatorError, resolve_agent_workspace
from lily.runtime.agent_runtime import AgentRuntimeError
from lily.runtime.config_loader import ConfigLoadError
from lily.runtime.conversation_sessions import (
    ConversationSessionStore,
    ConversationSessionStoreError,
    default_sessions_db_path,
)
from lily.runtime.model_factory import ModelFactoryError
from lily.runtime.tool_catalog import ToolCatalogLoadError
from lily.runtime.tool_registry import ToolRegistryError
from lily.runtime.tool_resolvers import ToolResolverError
from lily.ui.app import LilyTuiApp

app = typer.Typer(no_args_is_help=True)
app.add_typer(skills_app, name="skills")
_console = Console()
PromptOption = Annotated[
    str,
    typer.Option(..., "--prompt", help="Prompt text to send to Lily."),
]
AgentOption = Annotated[
    str | None,
    typer.Option(
        "--agent",
        help="Named agent directory under .lily/agents (defaults to 'default').",
    ),
]
RunConfigOption = Annotated[
    Path | None,
    typer.Option(
        "--config",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help=(
            "Optional explicit base runtime config (.yaml/.yml/.toml). "
            "Cannot be used with --agent."
        ),
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
ShowSkillTelemetryOption = Annotated[
    bool,
    typer.Option(
        "--show-skill-telemetry",
        help=(
            "Print skill telemetry JSON to stderr; default is file-only "
            "(see [logging].skill_telemetry_log / .lily/logs/skill-telemetry.jsonl)."
        ),
    ),
]


class ConversationResolutionError(ValueError):
    """Raised when attach mode selection or resolution fails."""


def _resolve_conversation_id(
    conversation_id: str | None,
    last_conversation: bool,
    *,
    workspace_root: Path,
) -> str:
    """Resolve conversation mode to one active conversation id.

    Args:
        conversation_id: Explicit conversation id from CLI options.
        last_conversation: Whether to attach to most-recent conversation id.
        workspace_root: Workspace root path used for session store scoping.

    Returns:
        Resolved active conversation id for this process run.

    Raises:
        ConversationResolutionError: If attach mode flags are ambiguous.
    """
    if conversation_id is not None and last_conversation:
        msg = "Choose only one attach mode: --conversation-id or --last-conversation."
        raise ConversationResolutionError(msg)

    store = ConversationSessionStore(default_sessions_db_path(workspace_root))
    try:
        if conversation_id is not None:
            return store.attach(conversation_id)
        if last_conversation:
            return store.attach_last()
        return store.start_new()
    except ConversationSessionStoreError as exc:
        raise ConversationResolutionError(str(exc)) from exc


def _resolve_runtime_paths(
    *,
    agent: str | None,
    config: Path | None,
) -> tuple[Path, Path, Path | None]:
    """Resolve runtime config path and session workspace root.

    Args:
        agent: Optional named-agent identifier.
        config: Optional explicit runtime config path.

    Returns:
        Tuple of `(config_path, session_workspace_root, agent_workspace_dir)`.

    Raises:
        ConversationResolutionError: If option selection is ambiguous.
        AgentLocatorError: If named-agent workspace cannot be resolved.
    """
    if config is not None and agent is not None:
        msg = "Choose only one runtime mode: --config or --agent."
        raise ConversationResolutionError(msg)
    if config is not None:
        return config, Path.cwd(), None
    try:
        workspace = resolve_agent_workspace(agent_name=agent)
    except AgentLocatorError as exc:
        # Re-raise explicitly so runtime-mode resolution has deterministic error type.
        raise AgentLocatorError(str(exc)) from exc
    return workspace.config_path, workspace.agent_dir, workspace.agent_dir


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
    config: RunConfigOption = None,
    agent: AgentOption = None,
    override: OverrideOption = None,
    conversation_id: ConversationIdOption = None,
    last_conversation: LastConversationOption = False,
    show_skill_telemetry: ShowSkillTelemetryOption = False,
) -> None:
    """Run a single prompt using config-driven Lily supervisor runtime.

    Args:
        prompt: Prompt text to execute.
        config: Optional explicit base runtime config path.
        agent: Optional named-agent identifier under `.lily/agents/`.
        override: Optional override runtime config path.
        conversation_id: Optional explicit conversation id attach target.
        last_conversation: Whether to attach to most-recent conversation.
        show_skill_telemetry: Mirror skill F7 JSON telemetry to stderr.

    Raises:
        Exit: Raised with non-zero code when runtime/config fails.
    """
    try:
        (
            resolved_config_path,
            session_workspace_root,
            agent_workspace_dir,
        ) = _resolve_runtime_paths(
            agent=agent,
            config=config,
        )
        resolved_conversation_id = _resolve_conversation_id(
            conversation_id=conversation_id,
            last_conversation=last_conversation,
            workspace_root=session_workspace_root,
        )
        supervisor = LilySupervisor.from_config_paths(
            resolved_config_path,
            override,
            skill_telemetry_echo=show_skill_telemetry,
            agent_workspace_dir=agent_workspace_dir,
        )
        result = supervisor.run_prompt(
            prompt,
            conversation_id=resolved_conversation_id,
        )
    except (
        ConfigLoadError,
        AgentLocatorError,
        ConversationResolutionError,
        ConversationSessionStoreError,
        ToolRegistryError,
        ToolCatalogLoadError,
        ToolResolverError,
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
    config: RunConfigOption = None,
    agent: AgentOption = None,
    override: OverrideOption = None,
    conversation_id: ConversationIdOption = None,
    last_conversation: LastConversationOption = False,
    show_skill_telemetry: ShowSkillTelemetryOption = False,
) -> None:
    """Launch Textual TUI using config-driven Lily supervisor runtime.

    Args:
        config: Optional explicit base runtime config path.
        agent: Optional named-agent identifier under `.lily/agents/`.
        override: Optional override runtime config path.
        conversation_id: Optional explicit conversation id attach target.
        last_conversation: Whether to attach to most-recent conversation.
        show_skill_telemetry: Mirror skill F7 JSON telemetry to stderr.

    Raises:
        Exit: Raised with non-zero code when runtime/config fails.
    """
    try:
        (
            resolved_config_path,
            session_workspace_root,
            agent_workspace_dir,
        ) = _resolve_runtime_paths(
            agent=agent,
            config=config,
        )
        resolved_conversation_id = _resolve_conversation_id(
            conversation_id=conversation_id,
            last_conversation=last_conversation,
            workspace_root=session_workspace_root,
        )
        app = LilyTuiApp(
            config_path=resolved_config_path,
            override_config_path=override,
            conversation_id=resolved_conversation_id,
            skill_telemetry_echo=show_skill_telemetry,
            agent_workspace_dir=agent_workspace_dir,
        )
        app.run()
    except (
        ConfigLoadError,
        AgentLocatorError,
        ConversationResolutionError,
        ConversationSessionStoreError,
        ToolRegistryError,
        ToolCatalogLoadError,
        ToolResolverError,
        ModelFactoryError,
        AgentRuntimeError,
    ) as exc:
        _console.print(Panel.fit(str(exc), title="Lily Error", border_style="red"))
        raise typer.Exit(code=1) from exc

    _console.print(f"Active conversation id: {resolved_conversation_id}")

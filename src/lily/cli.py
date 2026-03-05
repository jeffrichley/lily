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


def _print_success_panel(final_output: str, message_count: int) -> None:
    """Render successful CLI output with rich primitives.

    Args:
        final_output: Final assistant text output.
        message_count: Number of messages in the runtime transcript.
    """
    _console.print(Panel.fit(final_output, title="Lily", border_style="green"))

    table = Table(title="Run Summary")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Messages", str(message_count))
    _console.print(table)


@app.callback()
def app_callback() -> None:
    """Root callback to keep explicit subcommand invocation (`lily run`)."""


@app.command("run")
def run_command(
    prompt: PromptOption,
    config: ConfigOption = Path(".lily/config/agent.yaml"),
    override: OverrideOption = None,
) -> None:
    """Run a single prompt using YAML-configured Lily supervisor runtime.

    Args:
        prompt: Prompt text to execute.
        config: Base YAML config path.
        override: Optional override YAML config path.

    Raises:
        Exit: Raised with non-zero code when runtime/config fails.
    """
    try:
        supervisor = LilySupervisor.from_config_paths(config, override)
        result = supervisor.run_prompt(prompt)
    except (
        ConfigLoadError,
        ToolRegistryError,
        ModelFactoryError,
        AgentRuntimeError,
    ) as exc:
        _console.print(Panel.fit(str(exc), title="Lily Error", border_style="red"))
        raise typer.Exit(code=1) from exc

    _print_success_panel(
        final_output=result.final_output,
        message_count=result.message_count,
    )


@app.command("tui")
def tui_command(
    config: ConfigOption = Path(".lily/config/agent.yaml"),
    override: OverrideOption = None,
) -> None:
    """Launch Textual TUI using YAML-configured Lily supervisor runtime.

    Args:
        config: Base YAML config path.
        override: Optional override YAML config path.
    """
    app = LilyTuiApp(config_path=config, override_config_path=override)
    app.run()

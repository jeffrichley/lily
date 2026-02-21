"""Typer CLI entrypoint for Lily."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import click
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lily.cli.bootstrap import (
    bootstrap_workspace as _bootstrap_workspace,
)
from lily.cli.bootstrap import (
    build_runtime_for_workspace as _build_runtime_for_workspace_impl,
)
from lily.cli.bootstrap import (
    build_session as _build_session,
)
from lily.cli.bootstrap import (
    configure_logging as _configure_logging,
)
from lily.cli.bootstrap import (
    default_bundled_dir as _default_bundled_dir,
)
from lily.cli.bootstrap import (
    default_session_file as _default_session_file,
)
from lily.cli.bootstrap import (
    default_workspace_dir as _default_workspace_dir,
)
from lily.cli.bootstrap import (
    persist_session as _persist_session_impl,
)
from lily.cli.rendering import CliRenderer
from lily.commands.types import CommandResult, CommandStatus
from lily.runtime.checkpointing import CheckpointerBuildError
from lily.runtime.client_facade import ClientRuntimeFacade
from lily.runtime.facade import RuntimeFacade
from lily.session.models import Session

app = typer.Typer(help="Lily CLI")
_CONSOLE = Console()
_RENDERER = CliRenderer(console=_CONSOLE)


def _build_runtime_for_workspace(
    *,
    workspace_dir: Path,
    config_file: Path | None,
) -> RuntimeFacade:
    """Compatibility wrapper for tests and CLI runtime construction.

    Args:
        workspace_dir: Workspace skills directory path.
        config_file: Optional global config file path.

    Returns:
        Configured runtime facade.
    """
    return _build_runtime_for_workspace_impl(
        workspace_dir=workspace_dir,
        config_file=config_file,
        console=_CONSOLE,
    )


def _persist_session(session: Session, session_file: Path) -> None:
    """Compatibility wrapper for tests and CLI session persistence.

    Args:
        session: Session to persist.
        session_file: Persistence target path.
    """
    _persist_session_impl(session, session_file, console=_CONSOLE)


def _render_result(result: CommandResult) -> None:
    """Render command result with Rich styles.

    Args:
        result: Structured command result envelope.
    """
    _RENDERER.render(result)


def _execute_once(  # noqa: PLR0913
    *,
    text: str,
    bundled_dir: Path,
    workspace_dir: Path,
    model_name: str,
    session_file: Path,
    config_file: Path | None,
) -> int:
    """Execute one input line through runtime facade.

    Args:
        text: Raw input line.
        bundled_dir: Bundled skills root.
        workspace_dir: Workspace skills root.
        model_name: Session model name.
        session_file: Session persistence file path.
        config_file: Optional global config file path.

    Returns:
        Process exit code.
    """
    facade = ClientRuntimeFacade(
        session_builder=lambda: _build_session(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            model_name=model_name,
            session_file=session_file,
            console=_CONSOLE,
        ),
        runtime_builder=lambda: _build_runtime_for_workspace(
            workspace_dir=workspace_dir,
            config_file=config_file,
        ),
        session_persistor=lambda session: _persist_session(session, session_file),
    )
    try:
        result = facade.run_input(text)
        _render_result(result)
        return 0 if result.status == CommandStatus.OK else 1
    except CheckpointerBuildError as exc:
        _CONSOLE.print(f"[bold red]Failed to initialize checkpointer: {exc}[/bold red]")
        return 1
    finally:
        facade.close()


@app.command("init")
def init_command(
    workspace_dir: Annotated[
        Path | None,
        typer.Option(file_okay=False, dir_okay=True, help="Workspace skills root."),
    ] = None,
    config_file: Annotated[
        Path | None,
        typer.Option(
            file_okay=True,
            dir_okay=False,
            help="Path to global Lily config YAML/JSON file.",
        ),
    ] = None,
    overwrite_config: Annotated[
        bool,
        typer.Option(
            "--overwrite-config",
            help="Overwrite existing config file with default template.",
        ),
    ] = False,
) -> None:
    """Initialize Lily workspace files and directories.

    Args:
        workspace_dir: Optional workspace skills root override.
        config_file: Optional global config path override.
        overwrite_config: Whether to overwrite existing config.
    """
    _configure_logging()
    effective_workspace_dir = workspace_dir or _default_workspace_dir()
    _, effective_config_file, actions = _bootstrap_workspace(
        workspace_dir=effective_workspace_dir,
        config_file=config_file,
        overwrite_config=overwrite_config,
    )
    table = Table(title="Lily Init", show_header=True, header_style="bold cyan")
    table.add_column("Resource", style="bold")
    table.add_column("Status", style="green")
    for resource, status in actions:
        table.add_row(resource, status)
    _CONSOLE.print(table)
    _CONSOLE.print(
        Panel(
            (f"Workspace: {effective_workspace_dir}\nConfig: {effective_config_file}"),
            title="Initialized",
            border_style="green",
            expand=True,
        )
    )


@app.command("run")
def run_command(  # noqa: PLR0913
    text: Annotated[str, typer.Argument(help="Single input line to execute.")],
    bundled_dir: Annotated[
        Path | None,
        typer.Option(file_okay=False, dir_okay=True, help="Bundled skills root."),
    ] = None,
    workspace_dir: Annotated[
        Path | None,
        typer.Option(file_okay=False, dir_okay=True, help="Workspace skills root."),
    ] = None,
    model_name: Annotated[
        str,
        typer.Option(help="Model identifier used by llm_orchestration."),
    ] = "ollama:llama3.2",
    session_file: Annotated[
        Path | None,
        typer.Option(
            file_okay=True,
            dir_okay=False,
            help="Path to persisted session JSON file.",
        ),
    ] = None,
    config_file: Annotated[
        Path | None,
        typer.Option(
            file_okay=True,
            dir_okay=False,
            help="Path to global Lily config YAML/JSON file.",
        ),
    ] = None,
) -> None:
    """Execute one input line and print deterministic result.

    Args:
        text: Raw input line.
        bundled_dir: Optional bundled skills root override.
        workspace_dir: Optional workspace skills root override.
        model_name: Model identifier for execution.
        session_file: Optional session file path override.
        config_file: Optional global config file path override.

    Raises:
        Exit: Raised with process-style exit code.
    """
    _configure_logging()
    effective_bundled_dir = bundled_dir or _default_bundled_dir()
    effective_workspace_dir = workspace_dir or _default_workspace_dir()
    effective_session_file = session_file or _default_session_file(
        effective_workspace_dir
    )
    exit_code = _execute_once(
        text=text,
        bundled_dir=effective_bundled_dir,
        workspace_dir=effective_workspace_dir,
        model_name=model_name,
        session_file=effective_session_file,
        config_file=config_file,
    )
    raise typer.Exit(code=exit_code)


@app.command("repl")
def repl_command(
    bundled_dir: Annotated[
        Path | None,
        typer.Option(file_okay=False, dir_okay=True, help="Bundled skills root."),
    ] = None,
    workspace_dir: Annotated[
        Path | None,
        typer.Option(file_okay=False, dir_okay=True, help="Workspace skills root."),
    ] = None,
    model_name: Annotated[
        str,
        typer.Option(help="Model identifier used by llm_orchestration."),
    ] = "ollama:llama3.2",
    session_file: Annotated[
        Path | None,
        typer.Option(
            file_okay=True,
            dir_okay=False,
            help="Path to persisted session JSON file.",
        ),
    ] = None,
    config_file: Annotated[
        Path | None,
        typer.Option(
            file_okay=True,
            dir_okay=False,
            help="Path to global Lily config YAML/JSON file.",
        ),
    ] = None,
) -> None:
    """Run interactive REPL for slash-command testing.

    Args:
        bundled_dir: Optional bundled skills root override.
        workspace_dir: Optional workspace skills root override.
        model_name: Model identifier for execution.
        session_file: Optional session file path override.
        config_file: Optional global config file path override.

    Raises:
        Exit: Raised when runtime initialization fails.
    """
    _configure_logging()
    _CONSOLE.print(
        "Lily REPL. Type /skills, /skill <name> ..., or 'exit'.", style="cyan"
    )
    effective_bundled_dir = bundled_dir or _default_bundled_dir()
    effective_workspace_dir = workspace_dir or _default_workspace_dir()
    effective_session_file = session_file or _default_session_file(
        effective_workspace_dir
    )
    facade = ClientRuntimeFacade(
        session_builder=lambda: _build_session(
            bundled_dir=effective_bundled_dir,
            workspace_dir=effective_workspace_dir,
            model_name=model_name,
            session_file=effective_session_file,
            console=_CONSOLE,
        ),
        runtime_builder=lambda: _build_runtime_for_workspace(
            workspace_dir=effective_workspace_dir,
            config_file=config_file,
        ),
        session_persistor=lambda session: _persist_session(
            session,
            effective_session_file,
        ),
    )
    try:
        facade.start()
        while True:
            try:
                raw = typer.prompt("lily")
            except (EOFError, KeyboardInterrupt, click.Abort):
                _CONSOLE.print("\nbye", style="yellow")
                break

            text = raw.strip()
            if text.lower() in {"exit", "quit", "exit()", "quit()"}:
                _CONSOLE.print("bye", style="yellow")
                break
            if not text:
                continue

            result = facade.run_input(text)
            _render_result(result)
    except CheckpointerBuildError as exc:
        _CONSOLE.print(f"[bold red]Failed to initialize checkpointer: {exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    finally:
        facade.close()

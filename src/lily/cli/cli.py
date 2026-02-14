"""Typer CLI entrypoint for Lily."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import click
import typer
from rich.console import Console
from rich.logging import RichHandler

from lily.commands.types import CommandStatus
from lily.runtime.facade import RuntimeFacade
from lily.session.factory import SessionFactory, SessionFactoryConfig
from lily.session.models import ModelConfig, Session

app = typer.Typer(help="Lily CLI")
_CONSOLE = Console()
_LOGGING_CONFIGURED = False


def _configure_logging() -> None:
    """Configure Rich-backed logging once for CLI commands."""
    global _LOGGING_CONFIGURED  # noqa: PLW0603
    if _LOGGING_CONFIGURED:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(show_path=False, rich_tracebacks=True)],
    )
    _LOGGING_CONFIGURED = True


def _project_root() -> Path:
    """Resolve project root from this module location.

    Returns:
        Project root path.
    """
    return Path(__file__).resolve().parents[3]


def _default_bundled_dir() -> Path:
    """Return default bundled skills directory.

    Returns:
        Bundled skills path.
    """
    return _project_root() / "skills"


def _default_workspace_dir() -> Path:
    """Return default workspace skills directory.

    Returns:
        Workspace skills path.
    """
    workspace = Path.cwd() / ".lily" / "skills"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _build_session(
    *,
    bundled_dir: Path,
    workspace_dir: Path,
    model_name: str,
) -> Session:
    """Build runtime session for CLI command handling.

    Args:
        bundled_dir: Bundled skills root.
        workspace_dir: Workspace skills root.
        model_name: Session model name.

    Returns:
        Initialized session.
    """
    workspace_dir.mkdir(parents=True, exist_ok=True)
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"skills", "skill"},
        )
    )
    return factory.create(model_config=ModelConfig(model_name=model_name))


def _build_runtime() -> RuntimeFacade:
    """Build default runtime facade.

    Returns:
        Runtime facade with default wiring.
    """
    return RuntimeFacade()


def _render_result(message: str, status: CommandStatus) -> None:
    """Render command result with Rich styles.

    Args:
        message: User-facing command output.
        status: Result status.
    """
    if status == CommandStatus.OK:
        _CONSOLE.print(message, style="green")
        return
    _CONSOLE.print(message, style="bold red")


def _execute_once(
    *,
    text: str,
    bundled_dir: Path,
    workspace_dir: Path,
    model_name: str,
) -> int:
    """Execute one input line through runtime facade.

    Args:
        text: Raw input text.
        bundled_dir: Bundled skills root.
        workspace_dir: Workspace skills root.
        model_name: Model name for session construction.

    Returns:
        Process exit code.
    """
    session = _build_session(
        bundled_dir=bundled_dir,
        workspace_dir=workspace_dir,
        model_name=model_name,
    )
    runtime = _build_runtime()
    result = runtime.handle_input(text, session)
    _render_result(result.message, result.status)
    return 0 if result.status == CommandStatus.OK else 1


@app.command("run")
def run_command(
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
) -> None:
    """Execute one input line and print deterministic result.

    Args:
        text: Raw input line.
        bundled_dir: Optional bundled skills root override.
        workspace_dir: Optional workspace skills root override.
        model_name: Model identifier for session execution.

    Raises:
        Exit: Raised with command status code for shell integration.
    """
    _configure_logging()
    effective_bundled_dir = bundled_dir or _default_bundled_dir()
    effective_workspace_dir = workspace_dir or _default_workspace_dir()
    exit_code = _execute_once(
        text=text,
        bundled_dir=effective_bundled_dir,
        workspace_dir=effective_workspace_dir,
        model_name=model_name,
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
) -> None:
    """Run interactive REPL for slash-command testing.

    Args:
        bundled_dir: Optional bundled skills root override.
        workspace_dir: Optional workspace skills root override.
        model_name: Model identifier for session execution.
    """
    _configure_logging()
    _CONSOLE.print(
        "Lily REPL. Type /skills, /skill <name> ..., or 'exit'.", style="cyan"
    )
    effective_bundled_dir = bundled_dir or _default_bundled_dir()
    effective_workspace_dir = workspace_dir or _default_workspace_dir()
    session = _build_session(
        bundled_dir=effective_bundled_dir,
        workspace_dir=effective_workspace_dir,
        model_name=model_name,
    )
    runtime = _build_runtime()

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

        result = runtime.handle_input(text, session)
        _render_result(result.message, result.status)

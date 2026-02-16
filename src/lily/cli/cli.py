"""Typer CLI entrypoint for Lily."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import click
import typer
from rich.console import Console
from rich.json import JSON
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from lily.commands.types import CommandResult, CommandStatus
from lily.runtime.facade import RuntimeFacade
from lily.session.factory import SessionFactory, SessionFactoryConfig
from lily.session.models import ModelConfig, Session
from lily.session.store import (
    SessionDecodeError,
    SessionSchemaVersionError,
    load_session,
    recover_corrupt_session,
    save_session,
)

app = typer.Typer(help="Lily CLI")
_CONSOLE = Console()
_LOGGING_CONFIGURED = False
_HIDE_DATA_CODES = {
    "persona_listed",
    "persona_set",
    "persona_shown",
    "style_set",
    "memory_listed",
    "memory_empty",
    "memory_saved",
    "memory_deleted",
}


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


def _default_session_file(workspace_dir: Path) -> Path:
    """Return default persisted session file path.

    Args:
        workspace_dir: Workspace skills directory path.

    Returns:
        Session persistence file path.
    """
    workspace_dir.mkdir(parents=True, exist_ok=True)
    return workspace_dir.parent / "session.json"


def _build_session(
    *,
    bundled_dir: Path,
    workspace_dir: Path,
    model_name: str,
    session_file: Path,
) -> Session:
    """Build runtime session for CLI command handling.

    Args:
        bundled_dir: Bundled skills root.
        workspace_dir: Workspace skills root.
        model_name: Session model name.
        session_file: Session persistence file path.

    Returns:
        Initialized session (loaded from disk when possible).
    """
    workspace_dir.mkdir(parents=True, exist_ok=True)
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={
                "skills",
                "skill",
                "help",
                "reload_skills",
                "persona",
                "style",
                "remember",
                "forget",
                "memory",
            },
        )
    )
    try:
        return load_session(session_file)
    except FileNotFoundError:
        session = factory.create(model_config=ModelConfig(model_name=model_name))
        save_session(session, session_file)
        return session
    except (SessionDecodeError, SessionSchemaVersionError) as exc:
        backup = recover_corrupt_session(session_file)
        if backup is not None:
            _CONSOLE.print(
                f"[yellow]Session file was invalid. Moved to {backup}.[/yellow]"
            )
        else:
            _CONSOLE.print(
                "[yellow]Session file was invalid. Creating a new session.[/yellow]"
            )
        _CONSOLE.print(f"[yellow]Reason: {exc}[/yellow]")
        session = factory.create(model_config=ModelConfig(model_name=model_name))
        save_session(session, session_file)
        return session


def _persist_session(session: Session, session_file: Path) -> None:
    """Persist session with best-effort user-visible error reporting.

    Args:
        session: Session to persist.
        session_file: Persistence target path.
    """
    try:
        save_session(session, session_file)
    except OSError as exc:
        _CONSOLE.print(
            f"[bold red]Failed to persist session to {session_file}: {exc}[/bold red]"
        )


def _build_runtime() -> RuntimeFacade:
    """Build default runtime facade.

    Returns:
        Runtime facade with default wiring.
    """
    return RuntimeFacade()


def _render_result(result: CommandResult) -> None:
    """Render command result with Rich styles.

    Args:
        result: Structured command output envelope.
    """
    if result.status == CommandStatus.OK:
        if _render_rich_success(result):
            return
        _CONSOLE.print(
            Panel(
                Markdown(result.message),
                title=f"Lily [{result.code}]",
                border_style="green",
                expand=True,
            )
        )
        if result.data and result.code not in _HIDE_DATA_CODES:
            _CONSOLE.print(
                Panel(
                    JSON.from_data(result.data),
                    title="Data",
                    border_style="cyan",
                    expand=True,
                )
            )
        return
    _CONSOLE.print(
        Panel(
            result.message,
            title=f"Error [{result.code}]",
            border_style="bold red",
            expand=True,
        )
    )
    if result.data:
        _CONSOLE.print(
            Panel(
                JSON.from_data(result.data),
                title="Data",
                border_style="cyan",
                expand=True,
            )
        )


def _render_rich_success(result: CommandResult) -> bool:
    """Render specialized success view for selected command result codes.

    Args:
        result: Command result payload.

    Returns:
        True when a specialized render path handled output.
    """
    if result.code == "persona_listed":
        return _render_persona_list(result)
    if result.code == "persona_set":
        return _render_persona_set(result)
    if result.code == "persona_shown":
        return _render_persona_show(result)
    if result.code == "memory_listed":
        return _render_memory_list(result)
    return False


def _render_persona_list(result: CommandResult) -> bool:
    """Render `/persona list` in table form.

    Args:
        result: Command result payload.

    Returns:
        True when table render succeeded.
    """
    data = result.data if isinstance(result.data, dict) else None
    raw_rows = data.get("personas") if data is not None else None
    if not isinstance(raw_rows, list):
        return False

    table = Table(title="Personas", show_header=True, header_style="bold cyan")
    table.add_column("Active", style="green", no_wrap=True)
    table.add_column("Persona", style="bold")
    table.add_column("Default Style", style="magenta")
    table.add_column("Summary")
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        active = "yes" if bool(row.get("active")) else ""
        table.add_row(
            active,
            str(row.get("persona", "")),
            str(row.get("default_style", "")),
            str(row.get("summary", "")),
        )
    _CONSOLE.print(table)
    return True


def _render_persona_set(result: CommandResult) -> bool:
    """Render `/persona use` confirmation in concise panel.

    Args:
        result: Command result payload.

    Returns:
        True when panel render succeeded.
    """
    data = result.data if isinstance(result.data, dict) else None
    if data is None:
        return False
    persona = str(data.get("persona", "")).strip()
    style = str(data.get("style", "")).strip()
    if not persona or not style:
        return False
    _CONSOLE.print(
        Panel(
            f"Active Persona: [bold]{persona}[/bold]\nStyle: [bold]{style}[/bold]",
            title="Persona Updated",
            border_style="green",
            expand=True,
        )
    )
    return True


def _render_persona_show(result: CommandResult) -> bool:
    """Render `/persona show` details as fields + instructions panel.

    Args:
        result: Command result payload.

    Returns:
        True when rich render succeeded.
    """
    data = result.data if isinstance(result.data, dict) else None
    if data is None:
        return False
    persona = str(data.get("persona", "")).strip()
    summary = str(data.get("summary", "")).strip()
    default_style = str(data.get("default_style", "")).strip()
    effective_style = str(data.get("effective_style", "")).strip()
    instructions = str(data.get("instructions", "")).strip()
    if not persona:
        return False

    details = Table(show_header=False, box=None, expand=True)
    details.add_column("Field", style="bold cyan", no_wrap=True)
    details.add_column("Value")
    details.add_row("Persona", persona)
    details.add_row("Summary", summary)
    details.add_row("Default Style", default_style)
    details.add_row("Effective Style", effective_style)
    _CONSOLE.print(Panel(details, title="Persona", border_style="green", expand=True))
    if instructions:
        _CONSOLE.print(
            Panel(
                instructions,
                title="Instructions",
                border_style="cyan",
                expand=True,
            )
        )
    return True


def _render_memory_list(result: CommandResult) -> bool:
    """Render `/memory show` records in table form.

    Args:
        result: Command result payload.

    Returns:
        True when table render succeeded.
    """
    data = result.data if isinstance(result.data, dict) else None
    raw_records = data.get("records") if data is not None else None
    if not isinstance(raw_records, list):
        return False
    table = Table(
        title=f"Memory ({len(raw_records)} records)",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("ID", style="green")
    table.add_column("Namespace", style="magenta", no_wrap=True)
    table.add_column("Content")
    for record in raw_records:
        if not isinstance(record, dict):
            continue
        table.add_row(
            str(record.get("id", "")),
            str(record.get("namespace", "")),
            str(record.get("content", "")),
        )
    _CONSOLE.print(table)
    return True


def _execute_once(
    *,
    text: str,
    bundled_dir: Path,
    workspace_dir: Path,
    model_name: str,
    session_file: Path,
) -> int:
    """Execute one input line through runtime facade.

    Args:
        text: Raw input text.
        bundled_dir: Bundled skills root.
        workspace_dir: Workspace skills root.
        model_name: Model name for session construction.
        session_file: Session persistence file path.

    Returns:
        Process exit code.
    """
    session = _build_session(
        bundled_dir=bundled_dir,
        workspace_dir=workspace_dir,
        model_name=model_name,
        session_file=session_file,
    )
    runtime = _build_runtime()
    result = runtime.handle_input(text, session)
    _persist_session(session, session_file)
    _render_result(result)
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
    session_file: Annotated[
        Path | None,
        typer.Option(
            file_okay=True,
            dir_okay=False,
            help="Path to persisted session JSON file.",
        ),
    ] = None,
) -> None:
    """Execute one input line and print deterministic result.

    Args:
        text: Raw input line.
        bundled_dir: Optional bundled skills root override.
        workspace_dir: Optional workspace skills root override.
        model_name: Model identifier for session execution.
        session_file: Optional persisted session file path override.

    Raises:
        Exit: Raised with command status code for shell integration.
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
) -> None:
    """Run interactive REPL for slash-command testing.

    Args:
        bundled_dir: Optional bundled skills root override.
        workspace_dir: Optional workspace skills root override.
        model_name: Model identifier for session execution.
        session_file: Optional persisted session file path override.
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
    session = _build_session(
        bundled_dir=effective_bundled_dir,
        workspace_dir=effective_workspace_dir,
        model_name=model_name,
        session_file=effective_session_file,
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
        _persist_session(session, effective_session_file)
        _render_result(result)

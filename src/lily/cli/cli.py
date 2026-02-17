"""Typer CLI entrypoint for Lily."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import click
import typer
import yaml
from rich.console import Console
from rich.json import JSON
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from lily.commands.types import CommandResult, CommandStatus
from lily.config import GlobalConfigError, LilyGlobalConfig, load_global_config
from lily.memory import ConsolidationBackend as MemoryConsolidationBackend
from lily.memory import (
    EvidenceChunkingMode as MemoryEvidenceChunkingMode,
)
from lily.memory import (
    EvidenceChunkingSettings,
)
from lily.runtime.checkpointing import CheckpointerBuildError, build_checkpointer
from lily.runtime.facade import RuntimeFacade
from lily.session.factory import SessionFactory, SessionFactoryConfig
from lily.session.models import HistoryCompactionBackend, ModelConfig, Session
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
    "persona_reloaded",
    "persona_exported",
    "persona_imported",
    "agent_listed",
    "agent_set",
    "agent_shown",
    "style_set",
    "memory_listed",
    "memory_empty",
    "memory_saved",
    "memory_deleted",
    "memory_langmem_saved",
    "memory_langmem_listed",
    "memory_evidence_ingested",
}
_SECURITY_ALERT_CODES = {
    "provider_policy_denied",
    "skill_capability_denied",
    "security_policy_denied",
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


def _default_global_config_file(workspace_dir: Path) -> Path:
    """Return default global config path for current workspace root.

    Args:
        workspace_dir: Workspace skills directory path.

    Returns:
        Global config file path.
    """
    workspace_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = workspace_dir.parent / "config.yaml"
    json_path = workspace_dir.parent / "config.json"
    if yaml_path.exists():
        return yaml_path
    if json_path.exists():
        return json_path
    return yaml_path


def _bootstrap_workspace(
    *,
    workspace_dir: Path,
    config_file: Path | None = None,
    overwrite_config: bool = False,
) -> tuple[Path, Path, tuple[tuple[str, str], ...]]:
    """Bootstrap local Lily workspace artifacts.

    Args:
        workspace_dir: Workspace skills directory path.
        config_file: Optional global config path override.
        overwrite_config: Whether to overwrite existing config payload.

    Returns:
        Effective workspace dir, config file path, and action rows.
    """
    effective_workspace_dir = workspace_dir
    effective_config_file = config_file or _default_global_config_file(
        effective_workspace_dir
    )
    targets = {
        "workspace_skills_dir": effective_workspace_dir,
        "checkpoints_dir": effective_workspace_dir.parent / "checkpoints",
        "memory_dir": effective_workspace_dir.parent / "memory",
    }
    actions: list[tuple[str, str]] = []
    for name, path in targets.items():
        existed = path.exists()
        path.mkdir(parents=True, exist_ok=True)
        actions.append((name, "exists" if existed else "created"))
    config_existed = effective_config_file.exists()
    if not config_existed or overwrite_config:
        effective_config_file.parent.mkdir(parents=True, exist_ok=True)
        payload = LilyGlobalConfig().model_dump(mode="json")
        effective_config_file.write_text(
            yaml.safe_dump(payload, sort_keys=False),
            encoding="utf-8",
        )
        actions.append(
            (
                "config_file",
                "overwritten" if config_existed and overwrite_config else "created",
            )
        )
    else:
        actions.append(("config_file", "exists"))
    return effective_workspace_dir, effective_config_file, tuple(actions)


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
                "reload_persona",
                "agent",
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


def _build_runtime_for_workspace(
    *,
    workspace_dir: Path,
    config_file: Path | None,
) -> RuntimeFacade:
    """Build runtime facade with configured checkpointer backend.

    Args:
        workspace_dir: Workspace skills directory path.
        config_file: Optional global config override path.

    Returns:
        Runtime facade wired with configured checkpointer.
    """
    effective_config_file = config_file or _default_global_config_file(workspace_dir)
    config: LilyGlobalConfig
    try:
        config = load_global_config(effective_config_file)
    except GlobalConfigError as exc:
        _CONSOLE.print(
            f"[yellow]Global config at {effective_config_file} is invalid; "
            "falling back to defaults.[/yellow]"
        )
        _CONSOLE.print(f"[yellow]Reason: {exc}[/yellow]")
        config = LilyGlobalConfig()
    result = build_checkpointer(config.checkpointer)
    return RuntimeFacade(
        conversation_checkpointer=result.saver,
        memory_tooling_enabled=config.memory_tooling.enabled,
        memory_tooling_auto_apply=config.memory_tooling.auto_apply,
        consolidation_enabled=config.consolidation.enabled,
        consolidation_backend=MemoryConsolidationBackend(
            config.consolidation.backend.value
        ),
        consolidation_llm_assisted_enabled=config.consolidation.llm_assisted_enabled,
        consolidation_auto_run_every_n_turns=config.consolidation.auto_run_every_n_turns,
        evidence_chunking=EvidenceChunkingSettings(
            mode=MemoryEvidenceChunkingMode(config.evidence.chunking_mode.value),
            chunk_size=config.evidence.chunk_size,
            chunk_overlap=config.evidence.chunk_overlap,
            token_encoding_name=config.evidence.token_encoding_name,
        ),
        compaction_backend=HistoryCompactionBackend(config.compaction.backend.value),
        compaction_max_tokens=config.compaction.max_tokens,
    )


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
            (
                "[bold white on red] SECURITY ALERT [/bold white on red]\n"
                f"Code: {result.code}\n{result.message}"
            )
            if result.code in _SECURITY_ALERT_CODES
            else result.message,
            title=(
                "SECURITY ALERT"
                if result.code in _SECURITY_ALERT_CODES
                else f"Error [{result.code}]"
            ),
            border_style=(
                "bold bright_red"
                if result.code in _SECURITY_ALERT_CODES
                else "bold red"
            ),
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
    renderers: dict[str, Callable[[CommandResult], bool]] = {
        "persona_listed": _render_persona_list,
        "persona_set": _render_persona_set,
        "persona_shown": _render_persona_show,
        "agent_listed": _render_agent_list,
        "agent_set": _render_agent_set,
        "agent_shown": _render_agent_show,
        "memory_listed": _render_memory_list,
        "memory_langmem_listed": _render_memory_list,
        "memory_evidence_listed": _render_evidence_list,
    }
    renderer = renderers.get(result.code)
    if renderer is None:
        return False
    return renderer(result)


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


def _render_evidence_list(result: CommandResult) -> bool:
    """Render `/memory evidence show` records with citation + score.

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
        title=f"Semantic Evidence ({len(raw_records)} hits)",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Score", style="green", no_wrap=True)
    table.add_column("Citation", style="magenta")
    table.add_column("Snippet")
    for record in raw_records:
        if not isinstance(record, dict):
            continue
        score = float(record.get("score", 0.0))
        table.add_row(
            f"{score:.3f}",
            str(record.get("citation", "")),
            str(record.get("content", "")),
        )
    _CONSOLE.print(table)
    _CONSOLE.print(
        Panel(
            "Evidence results are non-canonical context. "
            "Structured long-term memory remains the source of truth.",
            title="Evidence Policy",
            border_style="yellow",
            expand=True,
        )
    )
    return True


def _render_agent_list(result: CommandResult) -> bool:
    """Render `/agent list` in table form.

    Args:
        result: Command result payload.

    Returns:
        True when table render succeeded.
    """
    data = result.data if isinstance(result.data, dict) else None
    raw_rows = data.get("agents") if data is not None else None
    if not isinstance(raw_rows, list):
        return False
    table = Table(title="Agents", show_header=True, header_style="bold cyan")
    table.add_column("Active", style="green", no_wrap=True)
    table.add_column("Agent", style="bold")
    table.add_column("Summary")
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        table.add_row(
            "yes" if bool(row.get("active")) else "",
            str(row.get("agent", "")),
            str(row.get("summary", "")),
        )
    _CONSOLE.print(table)
    return True


def _render_agent_set(result: CommandResult) -> bool:
    """Render `/agent use` confirmation in concise panel.

    Args:
        result: Command result payload.

    Returns:
        True when panel render succeeded.
    """
    data = result.data if isinstance(result.data, dict) else None
    if data is None:
        return False
    agent = str(data.get("agent", "")).strip()
    if not agent:
        return False
    _CONSOLE.print(
        Panel(
            f"Active Agent: [bold]{agent}[/bold]",
            title="Agent Updated",
            border_style="green",
            expand=True,
        )
    )
    return True


def _render_agent_show(result: CommandResult) -> bool:
    """Render `/agent show` details panel.

    Args:
        result: Command result payload.

    Returns:
        True when panel render succeeded.
    """
    data = result.data if isinstance(result.data, dict) else None
    if data is None:
        return False
    agent = str(data.get("agent", "")).strip()
    summary = str(data.get("summary", "")).strip()
    if not agent:
        return False
    _CONSOLE.print(
        Panel(
            f"Agent: [bold]{agent}[/bold]\nSummary: {summary}",
            title="Agent",
            border_style="green",
            expand=True,
        )
    )
    return True


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
        text: Raw input text.
        bundled_dir: Bundled skills root.
        workspace_dir: Workspace skills root.
        model_name: Model name for session construction.
        session_file: Session persistence file path.
        config_file: Optional global config path.

    Returns:
        Process exit code.
    """
    session = _build_session(
        bundled_dir=bundled_dir,
        workspace_dir=workspace_dir,
        model_name=model_name,
        session_file=session_file,
    )
    try:
        runtime = _build_runtime_for_workspace(
            workspace_dir=workspace_dir,
            config_file=config_file,
        )
    except CheckpointerBuildError as exc:
        _CONSOLE.print(f"[bold red]Failed to initialize checkpointer: {exc}[/bold red]")
        return 1
    try:
        result = runtime.handle_input(text, session)
        _persist_session(session, session_file)
        _render_result(result)
        return 0 if result.status == CommandStatus.OK else 1
    finally:
        maybe_close = getattr(runtime, "close", None)
        if callable(maybe_close):
            maybe_close()


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
        config_file: Optional global config file path override.
        overwrite_config: Whether to overwrite existing config payload.
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
        model_name: Model identifier for session execution.
        session_file: Optional persisted session file path override.
        config_file: Optional global Lily config file path override.

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
        model_name: Model identifier for session execution.
        session_file: Optional persisted session file path override.
        config_file: Optional global Lily config file path override.

    Raises:
        Exit: Raised when configured checkpointer cannot be initialized.
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
    try:
        runtime = _build_runtime_for_workspace(
            workspace_dir=effective_workspace_dir,
            config_file=config_file,
        )
    except CheckpointerBuildError as exc:
        _CONSOLE.print(f"[bold red]Failed to initialize checkpointer: {exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    try:
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
    finally:
        maybe_close = getattr(runtime, "close", None)
        if callable(maybe_close):
            maybe_close()

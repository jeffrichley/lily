"""CLI bootstrap/runtime lifecycle helpers."""

from __future__ import annotations

import logging
from pathlib import Path

import click
import typer
import yaml
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel

from lily.config import GlobalConfigError, LilyGlobalConfig, load_global_config
from lily.memory import ConsolidationBackend as MemoryConsolidationBackend
from lily.memory import (
    EvidenceChunkingMode as MemoryEvidenceChunkingMode,
)
from lily.memory import (
    EvidenceChunkingSettings,
)
from lily.runtime.checkpointing import build_checkpointer
from lily.runtime.facade import RuntimeFacade
from lily.runtime.security import ApprovalDecision, ApprovalRequest, SecurityPrompt
from lily.session.factory import SessionFactory, SessionFactoryConfig
from lily.session.models import HistoryCompactionBackend, ModelConfig, Session
from lily.session.store import (
    SessionDecodeError,
    SessionSchemaVersionError,
    load_session,
    recover_corrupt_session,
    save_session,
)

_LOGGING_CONFIGURED = False


class TerminalSecurityPrompt(SecurityPrompt):
    """Terminal HITL prompt for plugin security approvals."""

    def __init__(self, *, console: Console) -> None:
        """Store console dependency.

        Args:
            console: Rich console used for display.
        """
        self._console = console

    def request_approval(self, request: ApprovalRequest) -> ApprovalDecision | None:
        """Prompt operator for deterministic run_once/always_allow/deny decision.

        Args:
            request: Security approval context.

        Returns:
            Selected approval decision.
        """
        hash_note = "YES" if request.hash_changed else "NO"
        write_note = "YES" if request.write_access else "NO"
        self._console.print(
            Panel(
                (
                    f"Agent: {request.agent_id}\n"
                    f"Skill: {request.skill_name}\n"
                    f"Security Hash: {request.security_hash}\n"
                    f"Hash Changed Since Prior Grant: {hash_note}\n"
                    f"Write Access Requested: {write_note}\n\n"
                    "Choose approval mode: run_once | always_allow | deny"
                ),
                title="Security Approval Required",
                border_style="bold yellow",
                expand=True,
            )
        )
        choice = typer.prompt(
            "approval",
            type=click.Choice(
                ["run_once", "always_allow", "deny"], case_sensitive=False
            ),
        ).strip()
        if choice == "run_once":
            return ApprovalDecision.RUN_ONCE
        if choice == "always_allow":
            return ApprovalDecision.ALWAYS_ALLOW
        return ApprovalDecision.DENY


def configure_logging() -> None:
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


def project_root() -> Path:
    """Resolve project root from this module location.

    Returns:
        Project root path.
    """
    return Path(__file__).resolve().parents[3]


def default_bundled_dir() -> Path:
    """Return default bundled skills directory.

    Returns:
        Bundled skills path.
    """
    return project_root() / "skills"


def default_workspace_dir() -> Path:
    """Return default workspace skills directory.

    Returns:
        Workspace skills path.
    """
    workspace = Path.cwd() / ".lily" / "skills"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def default_session_file(workspace_dir: Path) -> Path:
    """Return default persisted session file path.

    Args:
        workspace_dir: Workspace skills directory path.

    Returns:
        Session file path.
    """
    workspace_dir.mkdir(parents=True, exist_ok=True)
    return workspace_dir.parent / "session.json"


def default_global_config_file(workspace_dir: Path) -> Path:
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


def bootstrap_workspace(
    *,
    workspace_dir: Path,
    config_file: Path | None = None,
    overwrite_config: bool = False,
) -> tuple[Path, Path, tuple[tuple[str, str], ...]]:
    """Bootstrap local Lily workspace artifacts.

    Args:
        workspace_dir: Workspace skills directory path.
        config_file: Optional config path override.
        overwrite_config: Whether to overwrite existing config payload.

    Returns:
        Effective workspace/config paths and action rows.
    """
    effective_workspace_dir = workspace_dir
    effective_config_file = config_file or default_global_config_file(
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


def build_session(
    *,
    bundled_dir: Path,
    workspace_dir: Path,
    model_name: str,
    session_file: Path,
    console: Console,
) -> Session:
    """Build runtime session for CLI command handling.

    Args:
        bundled_dir: Bundled skills root.
        workspace_dir: Workspace skills root.
        model_name: Model name for session.
        session_file: Session persistence file path.
        console: Rich console for recovery messaging.

    Returns:
        Loaded or newly created session.
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
                "jobs",
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
            console.print(
                f"[yellow]Session file was invalid. Moved to {backup}.[/yellow]"
            )
        else:
            console.print(
                "[yellow]Session file was invalid. Creating a new session.[/yellow]"
            )
        console.print(f"[yellow]Reason: {exc}[/yellow]")
        session = factory.create(model_config=ModelConfig(model_name=model_name))
        save_session(session, session_file)
        return session


def persist_session(session: Session, session_file: Path, *, console: Console) -> None:
    """Persist session with best-effort user-visible error reporting.

    Args:
        session: Session to persist.
        session_file: Persistence target path.
        console: Rich console for error rendering.
    """
    try:
        save_session(session, session_file)
    except OSError as exc:
        console.print(
            f"[bold red]Failed to persist session to {session_file}: {exc}[/bold red]"
        )


def build_runtime_for_workspace(
    *,
    workspace_dir: Path,
    config_file: Path | None,
    console: Console,
) -> RuntimeFacade:
    """Build runtime facade with configured checkpointer backend.

    Args:
        workspace_dir: Workspace skills directory path.
        config_file: Optional config file path.
        console: Rich console for config warnings.

    Returns:
        Configured runtime facade.
    """
    effective_config_file = config_file or default_global_config_file(workspace_dir)
    config: LilyGlobalConfig
    try:
        config = load_global_config(effective_config_file)
    except GlobalConfigError as exc:
        console.print(
            f"[yellow]Global config at {effective_config_file} is invalid; "
            "falling back to defaults.[/yellow]"
        )
        console.print(f"[yellow]Reason: {exc}[/yellow]")
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
        security=config.security,
        security_prompt=TerminalSecurityPrompt(console=console),
        project_root=project_root(),
        workspace_root=workspace_dir.parent,
        jobs_scheduler_enabled=True,
    )

"""Checkpointer backend construction for conversation runtime."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from lily.config import CheckpointerBackend, CheckpointerSettings


class CheckpointerBuildError(RuntimeError):
    """Raised when checkpointer backend construction fails."""


@dataclass(frozen=True)
class CheckpointerBuildResult:
    """Constructed checkpointer plus resolved storage path metadata."""

    saver: BaseCheckpointSaver
    resolved_sqlite_path: Path | None


type CheckpointerStrategy = Callable[[CheckpointerSettings], CheckpointerBuildResult]


def _build_memory_backend(settings: CheckpointerSettings) -> CheckpointerBuildResult:
    """Build in-memory checkpointer backend.

    Args:
        settings: Checkpointer settings payload (unused for memory backend).

    Returns:
        In-memory checkpointer result.
    """
    del settings
    return CheckpointerBuildResult(saver=InMemorySaver(), resolved_sqlite_path=None)


def _build_postgres_backend(settings: CheckpointerSettings) -> CheckpointerBuildResult:
    """Raise explicit contract-only error for unimplemented postgres backend.

    Args:
        settings: Checkpointer settings payload (unused for current behavior).

    Raises:
        CheckpointerBuildError: Always, until postgres backend is implemented.
    """
    del settings
    raise CheckpointerBuildError(
        "Checkpointer backend 'postgres' is a configured profile contract but "
        "is not implemented in this build. Supported backends: sqlite, memory."
    )


def _build_sqlite_backend(settings: CheckpointerSettings) -> CheckpointerBuildResult:
    """Build sqlite checkpointer backend with deterministic path resolution.

    Args:
        settings: Checkpointer settings payload.

    Returns:
        SQLite checkpointer result with resolved file path metadata.

    Raises:
        CheckpointerBuildError: If sqlite backend initialization fails.
    """
    sqlite_path = Path(settings.sqlite_path).expanduser()
    if not sqlite_path.is_absolute():
        sqlite_path = Path.cwd() / sqlite_path
    try:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        # `check_same_thread=False` allows lane-serialized usage across worker threads.
        connection = sqlite3.connect(sqlite_path, check_same_thread=False)
        saver = SqliteSaver(connection)
    except (OSError, sqlite3.Error) as exc:
        raise CheckpointerBuildError(
            f"Failed to initialize sqlite checkpointer at '{sqlite_path}': {exc}"
        ) from exc
    return CheckpointerBuildResult(saver=saver, resolved_sqlite_path=sqlite_path)


_STRATEGY_REGISTRY: dict[CheckpointerBackend, CheckpointerStrategy] = {
    CheckpointerBackend.MEMORY: _build_memory_backend,
    CheckpointerBackend.SQLITE: _build_sqlite_backend,
    CheckpointerBackend.POSTGRES: _build_postgres_backend,
}


def build_checkpointer(settings: CheckpointerSettings) -> CheckpointerBuildResult:
    """Build configured checkpointer backend.

    Args:
        settings: Global checkpointer settings.

    Returns:
        Constructed checkpointer and resolved sqlite path when applicable.

    Raises:
        CheckpointerBuildError: If backend cannot be constructed.
    """
    strategy = _STRATEGY_REGISTRY.get(settings.backend)
    if strategy is None:  # pragma: no cover - defensive
        known = ", ".join(sorted(backend.value for backend in _STRATEGY_REGISTRY))
        raise CheckpointerBuildError(
            f"Unsupported checkpointer backend '{settings.backend}'. "
            f"Supported backends: {known}."
        )
    return strategy(settings)

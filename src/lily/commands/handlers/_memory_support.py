"""Shared support helpers for memory command handlers."""

from __future__ import annotations

from pathlib import Path

from lily.memory import (
    FileBackedPersonalityMemoryRepository,
    FileBackedTaskMemoryRepository,
    PersonalityMemoryRepository,
    StoreBackedPersonalityMemoryRepository,
    StoreBackedTaskMemoryRepository,
    TaskMemoryRepository,
)
from lily.session.models import Session


def resolve_memory_root(session: Session) -> Path | None:
    """Resolve deterministic memory root for current session.

    Args:
        session: Active session.

    Returns:
        Memory root path when session can resolve one.
    """
    config = session.skill_snapshot_config
    if config is None:
        return None
    return config.workspace_dir.parent / "memory"


def resolve_store_file(session: Session) -> Path | None:
    """Resolve default store sqlite file path for current session.

    Args:
        session: Active session.

    Returns:
        Store sqlite path when session can resolve one.
    """
    root = resolve_memory_root(session)
    if root is None:
        return None
    return root / "langgraph_store.sqlite"


def build_personality_repository(
    session: Session,
) -> PersonalityMemoryRepository | None:
    """Build personality memory repository with store-first fallback behavior.

    Args:
        session: Active session.

    Returns:
        Personality repository when session can resolve storage.
    """
    root = resolve_memory_root(session)
    if root is None:
        return None
    store_file = resolve_store_file(session)
    if store_file is not None:
        return StoreBackedPersonalityMemoryRepository(store_file=store_file)
    return FileBackedPersonalityMemoryRepository(root_dir=root)


def build_task_repository(session: Session) -> TaskMemoryRepository | None:
    """Build task memory repository with store-first fallback behavior.

    Args:
        session: Active session.

    Returns:
        Task repository when session can resolve storage.
    """
    root = resolve_memory_root(session)
    if root is None:
        return None
    store_file = resolve_store_file(session)
    if store_file is not None:
        return StoreBackedTaskMemoryRepository(store_file=store_file)
    return FileBackedTaskMemoryRepository(root_dir=root)


def build_personality_namespace(*, session: Session, domain: str) -> str:
    """Build deterministic personality namespace from active persona + subdomain.

    Args:
        session: Active session.
        domain: Long-term personality subdomain identifier.

    Returns:
        Deterministic namespace token.
    """
    persona = session.active_agent.strip() or "default"
    return f"{domain}:{persona}"


def build_task_namespace(*, task: str) -> str:
    """Build deterministic task namespace token.

    Args:
        task: Task or project identifier.

    Returns:
        Deterministic namespace token.
    """
    return task.strip()

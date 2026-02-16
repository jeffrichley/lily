"""Shared support helpers for memory command handlers."""

from __future__ import annotations

from pathlib import Path

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

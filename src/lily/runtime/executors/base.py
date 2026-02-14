"""Base interface for skill executors."""

from __future__ import annotations

from typing import Protocol

from lily.commands.types import CommandResult
from lily.session.models import Session
from lily.skills.types import InvocationMode, SkillEntry


class SkillExecutor(Protocol):
    """Protocol for invocation-mode-specific skill execution."""

    mode: InvocationMode

    def execute(
        self, entry: SkillEntry, session: Session, user_text: str
    ) -> CommandResult:
        """Execute one skill entry.

        Args:
            entry: Resolved skill entry from session snapshot.
            session: Active session.
            user_text: Remaining user payload after skill name.
        """

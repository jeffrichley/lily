"""Tool-dispatch skill executor placeholder."""

from __future__ import annotations

from lily.commands.types import CommandResult
from lily.session.models import Session
from lily.skills.types import InvocationMode, SkillEntry


class ToolDispatchExecutor:
    """Placeholder executor for `tool_dispatch` invocation mode."""

    mode = InvocationMode.TOOL_DISPATCH

    def execute(
        self, entry: SkillEntry, session: Session, user_text: str
    ) -> CommandResult:
        """Return explicit deferred message for `tool_dispatch`.

        Args:
            entry: Skill entry selected from snapshot.
            session: Active session.
            user_text: User payload for skill execution.

        Returns:
            Explicit not-yet-implemented command result.
        """
        del session
        del user_text
        return CommandResult.error(
            f"Error: tool_dispatch executor is not implemented for '{entry.name}'."
        )

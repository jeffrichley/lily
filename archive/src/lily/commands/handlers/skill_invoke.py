"""Handler for /skill <name>."""

from __future__ import annotations

from typing import Protocol

from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.session.models import Session
from lily.skills.types import SkillEntry


class SkillInvokerPort(Protocol):
    """Invoker port used by the command layer."""

    def invoke(
        self, entry: SkillEntry, session: Session, user_text: str
    ) -> CommandResult:
        """Invoke a resolved skill entry.

        Args:
            entry: Resolved skill selected from snapshot.
            session: Active session.
            user_text: User payload following skill name.
        """


class SkillInvokeCommand:
    """Deterministic `/skill <name>` command handler."""

    def __init__(self, invoker: SkillInvokerPort) -> None:
        """Create handler with invocation backend.

        Args:
            invoker: Invoker used for skill execution delegation.
        """
        self._invoker = invoker

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Validate target skill and invoke deterministically.

        Args:
            call: Parsed command call.
            session: Session containing immutable skill snapshot.

        Returns:
            Command result with explicit success/failure outcome.
        """
        if not call.args:
            return CommandResult.error(
                "Error: /skill requires a skill name.",
                code="invalid_args",
                data={"command": "skill"},
            )

        skill_name = call.args[0]
        user_text = " ".join(call.args[1:])
        target = self._find_skill(session, skill_name)
        if target is None:
            return CommandResult.error(
                f"Error: skill '{skill_name}' not found in snapshot.",
                code="skill_not_found",
                data={"skill": skill_name},
            )

        return self._invoker.invoke(target, session, user_text)

    @staticmethod
    def _find_skill(session: Session, skill_name: str) -> SkillEntry | None:
        """Look up skill by exact name in session snapshot.

        Args:
            session: Active session.
            skill_name: Requested exact skill name.

        Returns:
            Matching skill entry or ``None`` when not present.
        """
        for entry in session.skill_snapshot.skills:
            if entry.name == skill_name:
                return entry
        return None

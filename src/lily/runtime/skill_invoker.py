"""Skill invoker orchestration service."""

from __future__ import annotations

from lily.commands.types import CommandResult
from lily.runtime.executors.base import SkillExecutor
from lily.session.models import Session
from lily.skills.types import InvocationMode, SkillEntry


class SkillInvoker:
    """Route skill execution to invocation-mode-specific executors."""

    def __init__(self, executors: tuple[SkillExecutor, ...]) -> None:
        """Create invoker with fixed executor map.

        Args:
            executors: Available executors keyed by invocation mode.
        """
        self._executors = {executor.mode: executor for executor in executors}

    def invoke(
        self, entry: SkillEntry, session: Session, user_text: str
    ) -> CommandResult:
        """Invoke a skill entry through its declared invocation mode.

        Args:
            entry: Skill selected from snapshot.
            session: Active session.
            user_text: User payload for skill execution.

        Returns:
            Command result from resolved executor or explicit error.
        """
        executor = self._executors.get(entry.invocation_mode)
        if executor is None:
            return self._unknown_mode_result(entry.invocation_mode, entry.name)
        return executor.execute(entry, session, user_text)

    @staticmethod
    def _unknown_mode_result(mode: InvocationMode, skill_name: str) -> CommandResult:
        """Build explicit unknown-mode error.

        Args:
            mode: Invocation mode missing executor binding.
            skill_name: Skill name for diagnostics.

        Returns:
            Error result.
        """
        return CommandResult.error(
            f"Error: no executor bound for mode '{mode.value}' (skill '{skill_name}')."
        )

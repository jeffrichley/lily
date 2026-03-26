"""Executable adapter for skill invocation runtime."""

from __future__ import annotations

from typing import Protocol

from lily.commands.types import CommandResult
from lily.runtime.executables.handlers._common import (
    ResultArtifacts,
    command_to_result,
    elapsed_ms,
    error_result,
    require_input_value,
    started_timer,
)
from lily.runtime.executables.handlers.base import BaseExecutableHandler
from lily.runtime.executables.models import (
    ExecutableError,
    ExecutableKind,
    ExecutableRequest,
    ExecutableResult,
)
from lily.session.models import Session
from lily.skills.types import SkillEntry


class SkillInvokerPort(Protocol):
    """Protocol for skill invoker dependency used by adapter."""

    def invoke(
        self,
        entry: SkillEntry,
        session: Session,
        user_text: str,
    ) -> CommandResult:
        """Invoke one resolved skill entry."""


class SkillExecutableHandler(BaseExecutableHandler):
    """Adapter handler that executes one skill via `SkillInvoker`."""

    kind = ExecutableKind.SKILL

    def __init__(self, invoker: SkillInvokerPort) -> None:
        """Store skill invoker adapter dependency.

        Args:
            invoker: Runtime skill invoker service.
        """
        self._invoker = invoker

    def handle(self, request: ExecutableRequest) -> ExecutableResult:
        """Execute skill invocation through canonical executable envelope."""
        started = started_timer()
        try:
            session = require_input_value(
                request.input,
                key="session",
                expected_type=Session,
            )
            skill = _resolve_skill_entry(
                session=session,
                skill_name=request.target.executable_id,
            )
            user_text = str(request.input.get("user_text", "")).strip()
        except ValueError as exc:
            return error_result(
                request=request,
                error=ExecutableError(
                    code="adapter_input_invalid",
                    message=f"Error: skill adapter input is invalid: {exc}",
                    retryable=False,
                    data={"target_id": request.target.executable_id},
                ),
                duration_ms=elapsed_ms(started),
            )
        command = self._invoker.invoke(skill, session, user_text)
        return command_to_result(
            request=request,
            command=command,
            duration_ms=elapsed_ms(started),
            links=ResultArtifacts(references=(f"skill://{skill.name}",)),
            output={"message": command.message, "skill": skill.name},
        )


def _resolve_skill_entry(*, session: Session, skill_name: str) -> SkillEntry:
    """Resolve one skill entry by exact name from session snapshot.

    Raises:
        ValueError: If no matching skill entry exists.
    """
    for entry in session.skill_snapshot.skills:
        if entry.name == skill_name:
            return entry
    raise ValueError(f"Skill '{skill_name}' was not found in session snapshot.")

"""Executable adapter for direct tool-dispatch invocation."""

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


class ToolDispatchExecutorPort(Protocol):
    """Protocol for tool dispatch executor dependency used by adapter."""

    def execute(
        self,
        entry: SkillEntry,
        session: Session,
        user_text: str,
    ) -> CommandResult:
        """Execute one tool-dispatch request."""


class ToolExecutableHandler(BaseExecutableHandler):
    """Adapter handler for direct tool execution through tool-dispatch executor."""

    kind = ExecutableKind.TOOL

    def __init__(self, executor: ToolDispatchExecutorPort) -> None:
        """Store tool dispatch executor dependency.

        Args:
            executor: Tool dispatch execution backend.
        """
        self._executor = executor

    def handle(self, request: ExecutableRequest) -> ExecutableResult:
        """Execute one tool dispatch request through canonical envelope."""
        started = started_timer()
        try:
            session = require_input_value(
                request.input,
                key="session",
                expected_type=Session,
            )
            skill = require_input_value(
                request.input,
                key="skill_entry",
                expected_type=SkillEntry,
            )
            user_text = str(request.input.get("user_text", "")).strip()
        except (TypeError, ValueError) as exc:
            return error_result(
                request=request,
                error=ExecutableError(
                    code="adapter_input_invalid",
                    message=f"Error: tool adapter input is invalid: {exc}",
                    retryable=False,
                    data={"target_id": request.target.executable_id},
                ),
                duration_ms=elapsed_ms(started),
            )
        command = self._executor.execute(skill, session, user_text)
        return command_to_result(
            request=request,
            command=command,
            duration_ms=elapsed_ms(started),
            links=ResultArtifacts(
                references=(
                    f"tool://{skill.command_tool_provider}:{skill.command_tool}",
                )
            ),
            output={
                "message": command.message,
                "tool_request": request.target.executable_id,
            },
        )

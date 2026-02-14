"""Tool-dispatch skill executor."""

from __future__ import annotations

import re
from typing import Protocol

from lily.commands.types import CommandResult
from lily.session.models import Session
from lily.skills.types import InvocationMode, SkillEntry


class ToolDispatchTool(Protocol):
    """Protocol for deterministic command-tool implementations."""

    name: str

    def execute(
        self, payload: str, *, session: Session, skill_name: str
    ) -> CommandResult:
        """Execute tool with raw payload."""


class AddTool:
    """Deterministic add tool for simple arithmetic expressions."""

    name = "add"
    _EXPR_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*\+\s*(-?\d+(?:\.\d+)?)\s*$")

    def execute(
        self, payload: str, *, session: Session, skill_name: str
    ) -> CommandResult:
        """Evaluate `<number>+<number>` and return deterministic result."""
        del session
        del skill_name
        text = payload.strip()
        if not text:
            return CommandResult.error(
                "Error: add tool requires an expression like '2+2'."
            )

        match = self._EXPR_RE.fullmatch(text)
        if match is None:
            return CommandResult.error(
                "Error: add tool expects format '<number>+<number>'."
            )

        left = float(match.group(1))
        right = float(match.group(2))
        total = left + right

        if total.is_integer():
            return CommandResult.ok(str(int(total)))
        return CommandResult.ok(str(total))


class ToolDispatchExecutor:
    """Execute `tool_dispatch` skills by direct tool invocation."""

    mode = InvocationMode.TOOL_DISPATCH

    def __init__(self, tools: tuple[ToolDispatchTool, ...]) -> None:
        """Build deterministic tool registry keyed by tool name."""
        self._tools = {tool.name: tool for tool in tools}

    def execute(
        self, entry: SkillEntry, session: Session, user_text: str
    ) -> CommandResult:
        """Dispatch to configured command tool for entry.

        Args:
            entry: Skill entry selected from snapshot.
            session: Active session.
            user_text: User payload for skill execution.

        Returns:
            Deterministic command-tool execution result.
        """
        if not entry.command_tool:
            return CommandResult.error(
                f"Error: skill '{entry.name}' is missing command_tool for tool_dispatch."
            )

        tool = self._tools.get(entry.command_tool)
        if tool is None:
            return CommandResult.error(
                f"Error: command tool '{entry.command_tool}' is not registered for skill '{entry.name}'."
            )

        return tool.execute(user_text, session=session, skill_name=entry.name)

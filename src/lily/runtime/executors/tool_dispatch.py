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
        """Execute tool with raw payload.

        Args:
            payload: Raw user payload.
            session: Active session context.
            skill_name: Calling skill name.
        """


class AddTool:
    """Deterministic add tool for simple arithmetic expressions."""

    name = "add"
    _EXPR_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*\+\s*(-?\d+(?:\.\d+)?)\s*$")

    def execute(
        self, payload: str, *, session: Session, skill_name: str
    ) -> CommandResult:
        """Evaluate `<number>+<number>` and return deterministic result.

        Args:
            payload: Raw user expression payload.
            session: Active session context.
            skill_name: Calling skill name.

        Returns:
            Deterministic add-tool result.
        """
        del session
        del skill_name
        text = payload.strip()
        if not text:
            return CommandResult.error(
                "Error: add tool requires an expression like '2+2'.",
                code="tool_invalid_args",
                data={"tool": self.name},
            )

        match = self._EXPR_RE.fullmatch(text)
        if match is None:
            return CommandResult.error(
                "Error: add tool expects format '<number>+<number>'.",
                code="tool_invalid_args",
                data={"tool": self.name},
            )

        left = float(match.group(1))
        right = float(match.group(2))
        total = left + right

        if total.is_integer():
            return CommandResult.ok(
                str(int(total)),
                code="tool_ok",
                data={"tool": self.name},
            )
        return CommandResult.ok(
            str(total),
            code="tool_ok",
            data={"tool": self.name},
        )


class ToolDispatchExecutor:
    """Execute `tool_dispatch` skills by direct tool invocation."""

    mode = InvocationMode.TOOL_DISPATCH

    def __init__(self, tools: tuple[ToolDispatchTool, ...]) -> None:
        """Build deterministic tool registry keyed by tool name.

        Args:
            tools: Registered dispatch tools.
        """
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
                (
                    f"Error: skill '{entry.name}' is missing command_tool "
                    "for tool_dispatch."
                ),
                code="command_tool_missing",
                data={"skill": entry.name},
            )

        tool = self._tools.get(entry.command_tool)
        if tool is None:
            return CommandResult.error(
                (
                    f"Error: command tool '{entry.command_tool}' is not registered "
                    f"for skill '{entry.name}'."
                ),
                code="command_tool_unregistered",
                data={"skill": entry.name, "tool": entry.command_tool},
            )

        return tool.execute(user_text, session=session, skill_name=entry.name)

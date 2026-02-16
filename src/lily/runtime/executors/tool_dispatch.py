"""Tool-dispatch skill executor with typed input/output contracts."""

from __future__ import annotations

import re
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError

from lily.commands.types import CommandResult
from lily.session.models import Session
from lily.skills.types import InvocationMode, SkillEntry


class ToolContract(Protocol):
    """Typed contract for deterministic command-tool execution."""

    name: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]

    def parse_payload(self, payload: str) -> dict[str, Any]:
        """Convert raw payload string into schema-ready input dictionary.

        Args:
            payload: Raw user payload text.
        """

    def execute_typed(
        self,
        typed_input: BaseModel,
        *,
        session: Session,
        skill_name: str,
    ) -> dict[str, Any]:
        """Execute tool with validated input and return schema-ready output.

        Args:
            typed_input: Validated input payload model.
            session: Active session context.
            skill_name: Calling skill name.
        """

    def render_output(self, typed_output: BaseModel) -> str:
        """Render validated output into deterministic user-facing text.

        Args:
            typed_output: Validated tool output payload model.
        """


class _BinaryExpressionInput(BaseModel):
    """Validated input payload for binary arithmetic tools."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    left: float
    right: float


class _ArithmeticOutput(BaseModel):
    """Validated output payload for arithmetic tools."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: float
    display: str


class _ArithmeticToolBase:
    """Base helper for deterministic binary arithmetic command tools."""

    input_schema = _BinaryExpressionInput
    output_schema = _ArithmeticOutput

    def __init__(self, *, operator_symbol: str, name: str) -> None:
        """Create arithmetic tool.

        Args:
            operator_symbol: Binary operator symbol.
            name: Stable tool name.
        """
        self.name = name
        escaped = re.escape(operator_symbol)
        self._expr_re = re.compile(
            rf"^\s*(-?\d+(?:\.\d+)?)\s*{escaped}\s*(-?\d+(?:\.\d+)?)\s*$"
        )

    def parse_payload(self, payload: str) -> dict[str, Any]:
        """Parse `<number><op><number>` payload into schema input data.

        Args:
            payload: Raw user payload.

        Returns:
            Candidate input dictionary (validated later).
        """
        match = self._expr_re.fullmatch(payload.strip())
        if match is None:
            return {}
        return {"left": float(match.group(1)), "right": float(match.group(2))}

    def render_output(self, typed_output: BaseModel) -> str:
        """Render arithmetic output display string.

        Args:
            typed_output: Validated arithmetic output.

        Returns:
            Deterministic display text.
        """
        output = _ArithmeticOutput.model_validate(typed_output)
        return output.display

    @staticmethod
    def _display(value: float) -> str:
        """Render float with integer simplification where possible.

        Args:
            value: Numeric result value.

        Returns:
            Deterministic display text.
        """
        if value.is_integer():
            return str(int(value))
        return str(value)


class AddTool(_ArithmeticToolBase):
    """Deterministic add tool for `<number>+<number>` expressions."""

    def __init__(self) -> None:
        """Create add tool."""
        super().__init__(operator_symbol="+", name="add")

    def execute_typed(
        self,
        typed_input: BaseModel,
        *,
        session: Session,
        skill_name: str,
    ) -> dict[str, Any]:
        """Execute typed add operation.

        Args:
            typed_input: Validated arithmetic input.
            session: Active session context.
            skill_name: Calling skill name.

        Returns:
            Output dictionary matching output schema.
        """
        del session
        del skill_name
        payload = _BinaryExpressionInput.model_validate(typed_input)
        total = payload.left + payload.right
        return {"value": total, "display": self._display(total)}


class SubtractTool(_ArithmeticToolBase):
    """Deterministic subtract tool for `<number>-<number>` expressions."""

    def __init__(self) -> None:
        """Create subtract tool."""
        super().__init__(operator_symbol="-", name="subtract")

    def execute_typed(
        self,
        typed_input: BaseModel,
        *,
        session: Session,
        skill_name: str,
    ) -> dict[str, Any]:
        """Execute typed subtraction operation.

        Args:
            typed_input: Validated arithmetic input.
            session: Active session context.
            skill_name: Calling skill name.

        Returns:
            Output dictionary matching output schema.
        """
        del session
        del skill_name
        payload = _BinaryExpressionInput.model_validate(typed_input)
        total = payload.left - payload.right
        return {"value": total, "display": self._display(total)}


class MultiplyTool(_ArithmeticToolBase):
    """Deterministic multiply tool for `<number>*<number>` expressions."""

    def __init__(self) -> None:
        """Create multiply tool."""
        super().__init__(operator_symbol="*", name="multiply")

    def execute_typed(
        self,
        typed_input: BaseModel,
        *,
        session: Session,
        skill_name: str,
    ) -> dict[str, Any]:
        """Execute typed multiplication operation.

        Args:
            typed_input: Validated arithmetic input.
            session: Active session context.
            skill_name: Calling skill name.

        Returns:
            Output dictionary matching output schema.
        """
        del session
        del skill_name
        payload = _BinaryExpressionInput.model_validate(typed_input)
        total = payload.left * payload.right
        return {"value": total, "display": self._display(total)}


class ToolDispatchExecutor:
    """Execute `tool_dispatch` skills by typed contract-bound tool invocation."""

    mode = InvocationMode.TOOL_DISPATCH

    def __init__(self, tools: tuple[ToolContract, ...]) -> None:
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

        try:
            raw_input = tool.parse_payload(user_text)
            typed_input = tool.input_schema.model_validate(raw_input)
        except ValidationError as exc:
            return CommandResult.error(
                f"Error: invalid input for tool '{tool.name}'.",
                code="tool_input_invalid",
                data={
                    "skill": entry.name,
                    "tool": tool.name,
                    "validation_errors": exc.errors(),
                },
            )

        try:
            raw_output = tool.execute_typed(
                typed_input,
                session=session,
                skill_name=entry.name,
            )
            typed_output = tool.output_schema.model_validate(raw_output)
        except ValidationError as exc:
            return CommandResult.error(
                f"Error: invalid output from tool '{tool.name}'.",
                code="tool_output_invalid",
                data={
                    "skill": entry.name,
                    "tool": tool.name,
                    "validation_errors": exc.errors(),
                },
            )

        return CommandResult.ok(
            tool.render_output(typed_output),
            code="tool_ok",
            data={
                "skill": entry.name,
                "tool": tool.name,
                "output": typed_output.model_dump(),
            },
        )

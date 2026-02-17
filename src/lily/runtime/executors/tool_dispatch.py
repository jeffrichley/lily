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


class ToolProvider(Protocol):
    """Provider contract for resolving command tools by stable provider id."""

    provider_id: str

    def resolve_tool(
        self,
        tool_name: str,
        *,
        session: Session,
        skill_name: str,
    ) -> ToolContract | None:
        """Resolve tool implementation for one provider-scoped tool id.

        Args:
            tool_name: Provider-scoped tool identifier.
            session: Active session context.
            skill_name: Calling skill name.
        """


class ProviderPolicyDeniedError(RuntimeError):
    """Raised when provider policy denies tool resolution/execution."""


class BuiltinToolProvider:
    """Builtin in-process tool provider."""

    provider_id = "builtin"

    def __init__(self, tools: tuple[ToolContract, ...]) -> None:
        """Build deterministic builtin tool map keyed by tool name.

        Args:
            tools: Registered builtin tools.
        """
        self._tools = {tool.name: tool for tool in tools}

    def resolve_tool(
        self,
        tool_name: str,
        *,
        session: Session,
        skill_name: str,
    ) -> ToolContract | None:
        """Resolve builtin tool by name.

        Args:
            tool_name: Builtin tool identifier.
            session: Active session context.
            skill_name: Calling skill name.

        Returns:
            Matching builtin tool contract, or None when not found.
        """
        del session
        del skill_name
        return self._tools.get(tool_name)


class McpToolResolver(Protocol):
    """Protocol for MCP adapter used by MCP tool provider."""

    def resolve_tool(
        self,
        tool_name: str,
        *,
        session: Session,
        skill_name: str,
    ) -> ToolContract | None:
        """Resolve MCP tool contract for one skill invocation.

        Args:
            tool_name: MCP tool identifier.
            session: Active session context.
            skill_name: Calling skill name.
        """


class _DefaultMcpResolver:
    """Default MCP resolver stub (no MCP tools configured)."""

    def resolve_tool(
        self,
        tool_name: str,
        *,
        session: Session,
        skill_name: str,
    ) -> ToolContract | None:
        """Return no tool by default until MCP tools are configured.

        Args:
            tool_name: MCP tool identifier.
            session: Active session context.
            skill_name: Calling skill name.

        Returns:
            None because default resolver has no MCP tools.
        """
        del tool_name
        del session
        del skill_name
        return None


class McpToolProvider:
    """MCP-backed tool provider adapter."""

    provider_id = "mcp"

    def __init__(self, resolver: McpToolResolver | None = None) -> None:
        """Store MCP resolver adapter.

        Args:
            resolver: Optional MCP resolver implementation.
        """
        self._resolver = resolver or _DefaultMcpResolver()

    def resolve_tool(
        self,
        tool_name: str,
        *,
        session: Session,
        skill_name: str,
    ) -> ToolContract | None:
        """Resolve tool via MCP adapter contract.

        Args:
            tool_name: MCP tool identifier.
            session: Active session context.
            skill_name: Calling skill name.

        Returns:
            MCP tool contract, or None when unavailable.
        """
        return self._resolver.resolve_tool(
            tool_name,
            session=session,
            skill_name=skill_name,
        )


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

    def __init__(self, providers: tuple[ToolProvider, ...]) -> None:
        """Build deterministic provider registry keyed by provider id.

        Args:
            providers: Registered tool providers.
        """
        self._providers = {provider.provider_id: provider for provider in providers}

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
        tool, error = self._resolve_tool(entry, session)
        if error is not None:
            return error
        assert tool is not None

        typed_input, error = self._validate_input(tool, entry, user_text)
        if error is not None:
            return error
        assert typed_input is not None

        typed_output, error = self._validate_output(tool, entry, typed_input, session)
        if error is not None:
            return error
        assert typed_output is not None

        return CommandResult.ok(
            tool.render_output(typed_output),
            code="tool_ok",
            data={
                "skill": entry.name,
                "provider": entry.command_tool_provider,
                "tool": tool.name,
                "output": typed_output.model_dump(),
            },
        )

    def _resolve_tool(
        self,
        entry: SkillEntry,
        session: Session,
    ) -> tuple[ToolContract | None, CommandResult | None]:
        """Resolve provider + tool for one skill invocation.

        Args:
            entry: Skill entry selected from snapshot.
            session: Active session context.

        Returns:
            Tuple of resolved tool and optional error result.
        """
        if not entry.command_tool:
            return None, CommandResult.error(
                (
                    f"Error: skill '{entry.name}' is missing command_tool "
                    "for tool_dispatch."
                ),
                code="command_tool_missing",
                data={"skill": entry.name},
            )
        provider = self._providers.get(entry.command_tool_provider)
        if provider is None:
            return None, CommandResult.error(
                (
                    f"Error: tool provider '{entry.command_tool_provider}' is not "
                    f"registered for skill '{entry.name}'."
                ),
                code="provider_unbound",
                data={"skill": entry.name, "provider": entry.command_tool_provider},
            )
        try:
            tool = provider.resolve_tool(
                entry.command_tool,
                session=session,
                skill_name=entry.name,
            )
        except ProviderPolicyDeniedError as exc:
            return None, CommandResult.error(
                f"Security alert: provider policy denied '{entry.command_tool}'.",
                code="provider_policy_denied",
                data={
                    "skill": entry.name,
                    "provider": entry.command_tool_provider,
                    "tool": entry.command_tool,
                    "reason": str(exc),
                },
            )
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            return None, CommandResult.error(
                f"Error: provider execution failed for '{entry.command_tool}'.",
                code="provider_execution_failed",
                data={
                    "skill": entry.name,
                    "provider": entry.command_tool_provider,
                    "tool": entry.command_tool,
                    "reason": str(exc),
                },
            )
        if tool is None:
            return None, CommandResult.error(
                (
                    f"Error: tool '{entry.command_tool}' is not registered for "
                    f"provider '{entry.command_tool_provider}' "
                    f"(skill '{entry.name}')."
                ),
                code="provider_tool_unregistered",
                data={
                    "skill": entry.name,
                    "provider": entry.command_tool_provider,
                    "tool": entry.command_tool,
                },
            )
        return tool, None

    @staticmethod
    def _validate_input(
        tool: ToolContract,
        entry: SkillEntry,
        user_text: str,
    ) -> tuple[BaseModel | None, CommandResult | None]:
        """Validate tool input payload.

        Args:
            tool: Resolved tool contract.
            entry: Calling skill entry.
            user_text: Raw user payload.

        Returns:
            Tuple of validated input model and optional error result.
        """
        try:
            raw_input = tool.parse_payload(user_text)
            typed_input = tool.input_schema.model_validate(raw_input)
            return typed_input, None
        except ValidationError as exc:
            return None, CommandResult.error(
                f"Error: invalid input for tool '{tool.name}'.",
                code="tool_input_invalid",
                data={
                    "skill": entry.name,
                    "provider": entry.command_tool_provider,
                    "tool": tool.name,
                    "validation_errors": exc.errors(),
                },
            )

    @staticmethod
    def _validate_output(
        tool: ToolContract,
        entry: SkillEntry,
        typed_input: BaseModel,
        session: Session,
    ) -> tuple[BaseModel | None, CommandResult | None]:
        """Validate tool output payload.

        Args:
            tool: Resolved tool contract.
            entry: Calling skill entry.
            typed_input: Validated input payload.
            session: Active session context.

        Returns:
            Tuple of validated output model and optional error result.
        """
        try:
            raw_output = tool.execute_typed(
                typed_input,
                session=session,
                skill_name=entry.name,
            )
            typed_output = tool.output_schema.model_validate(raw_output)
            return typed_output, None
        except ValidationError as exc:
            return None, CommandResult.error(
                f"Error: invalid output from tool '{tool.name}'.",
                code="tool_output_invalid",
                data={
                    "skill": entry.name,
                    "provider": entry.command_tool_provider,
                    "tool": tool.name,
                    "validation_errors": exc.errors(),
                },
            )

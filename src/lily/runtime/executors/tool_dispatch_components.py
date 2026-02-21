"""Tool-dispatch skill executor with typed input/output contracts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Protocol, cast

from pydantic import BaseModel, ConfigDict

from lily.runtime.plugin_runner import DockerPluginRunner, PluginRuntimeError
from lily.runtime.security import (
    SecurityAuthorizationError,
    SecurityGate,
)
from lily.session.models import Session
from lily.skills.types import SkillEntry


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


class ProviderExecutionError(RuntimeError):
    """Provider boundary error with deterministic code mapping."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        data: dict[str, object] | None = None,
    ) -> None:
        """Store deterministic provider error payload.

        Args:
            code: Deterministic machine-readable error code.
            message: Human-readable error message.
            data: Optional structured error payload.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or {}


class ToolExecutionError(RuntimeError):
    """Tool execution error with deterministic code mapping."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        data: dict[str, object] | None = None,
    ) -> None:
        """Store deterministic tool error payload.

        Args:
            code: Deterministic machine-readable error code.
            message: Human-readable error message.
            data: Optional structured error payload.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or {}


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


class _PluginInput(BaseModel):
    """Validated input payload for plugin-backed tools."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    payload: str


class _PluginOutput(BaseModel):
    """Validated output payload for plugin-backed tools."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    display: str
    data: dict[str, Any] | None = None


class _PluginTool:
    """Tool adapter for plugin-backed execution."""

    name: str
    input_schema = _PluginInput
    output_schema = _PluginOutput

    def __init__(
        self,
        *,
        tool_name: str,
        entry: SkillEntry,
        security_gate: SecurityGate,
        runner: DockerPluginRunner,
    ) -> None:
        """Bind one plugin tool adapter to a skill entry.

        Args:
            tool_name: Stable tool identifier.
            entry: Snapshot skill entry.
            security_gate: Security gate coordinator.
            runner: Container runtime adapter.
        """
        self.name = tool_name
        self._entry = entry
        self._security_gate = security_gate
        self._runner = runner

    def parse_payload(self, payload: str) -> dict[str, Any]:
        """Wrap raw payload in plugin input envelope.

        Args:
            payload: Raw user payload string.

        Returns:
            Plugin input envelope mapping.
        """
        return {"payload": payload}

    def execute_typed(
        self,
        typed_input: BaseModel,
        *,
        session: Session,
        skill_name: str,
    ) -> dict[str, Any]:
        """Authorize and execute plugin in sandboxed container.

        Args:
            typed_input: Validated plugin input payload.
            session: Active session context.
            skill_name: Calling skill name.

        Returns:
            Plugin output payload.

        Raises:
            ToolExecutionError: If approval/preflight/runtime fails.
        """
        del skill_name
        payload = _PluginInput.model_validate(typed_input)
        try:
            security_hash, hash_payload = self._security_gate.authorize(
                entry=self._entry,
                agent_id=session.active_agent,
            )
            result = self._runner.run(
                entry=self._entry,
                user_text=payload.payload,
                security_hash=security_hash,
                agent_id=session.active_agent,
                session_id=session.session_id,
            )
            self._security_gate.record_outcome(
                entry=self._entry,
                agent_id=session.active_agent,
                security_hash=security_hash,
                outcome="plugin_ok",
                details={"hash_payload": hash_payload},
            )
            return result
        except SecurityAuthorizationError as exc:
            raise ToolExecutionError(
                code=exc.code,
                message=exc.message,
                data=exc.data,
            ) from exc
        except PluginRuntimeError as exc:
            raise ToolExecutionError(
                code=exc.code,
                message=exc.message,
                data=exc.data,
            ) from exc

    def render_output(self, typed_output: BaseModel) -> str:
        """Render plugin output display string.

        Args:
            typed_output: Validated plugin output payload.

        Returns:
            User-facing display string.
        """
        output = _PluginOutput.model_validate(typed_output)
        return output.display


class PluginToolProvider:
    """Plugin provider using security gate + Docker container runner."""

    provider_id = "plugin"

    def __init__(
        self, *, security_gate: SecurityGate, runner: DockerPluginRunner
    ) -> None:
        """Create plugin provider with deterministic runtime dependencies.

        Args:
            security_gate: Security gate coordinator.
            runner: Container runtime adapter.
        """
        self._security_gate = security_gate
        self._runner = runner

    def resolve_tool(
        self,
        tool_name: str,
        *,
        session: Session,
        skill_name: str,
    ) -> ToolContract | None:
        """Resolve plugin-backed tool adapter for skill entry.

        Args:
            tool_name: Provider-scoped tool identifier.
            session: Active session context.
            skill_name: Calling skill name.

        Returns:
            Plugin-backed tool contract.

        Raises:
            ProviderExecutionError: If plugin contract metadata is invalid.
        """
        entry = _find_skill_entry(session=session, skill_name=skill_name)
        if entry is None:
            raise ProviderExecutionError(
                code="plugin_contract_invalid",
                message=f"Error: plugin skill '{skill_name}' was not found in session.",
                data={"skill": skill_name},
            )
        if entry.plugin.entrypoint is None:
            raise ProviderExecutionError(
                code="plugin_contract_invalid",
                message=(
                    f"Error: skill '{skill_name}' is missing plugin entrypoint "
                    "metadata."
                ),
                data={"skill": skill_name},
            )
        _validate_plugin_paths(entry)
        return cast(
            ToolContract,
            _PluginTool(
                tool_name=tool_name,
                entry=entry,
                security_gate=self._security_gate,
                runner=self._runner,
            ),
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


def _find_skill_entry(*, session: Session, skill_name: str) -> SkillEntry | None:
    """Resolve one skill entry by exact name from session snapshot.

    Args:
        session: Active session context.
        skill_name: Exact skill name to resolve.

    Returns:
        Matching skill entry or ``None``.
    """
    for entry in session.skill_snapshot.skills:
        if entry.name == skill_name:
            return entry
    return None


def _validate_plugin_paths(entry: SkillEntry) -> None:
    """Validate plugin contract relative paths for one entry.

    Args:
        entry: Skill entry under validation.
    """
    _validate_relative_path(entry, entry.plugin.entrypoint or "", field="entrypoint")
    for value in entry.plugin.source_files:
        _validate_relative_path(entry, value, field="source_files")
    for value in entry.plugin.asset_files:
        _validate_relative_path(entry, value, field="asset_files")


def _validate_relative_path(entry: SkillEntry, value: str, *, field: str) -> None:
    """Validate one plugin path as in-root relative filesystem path.

    Args:
        entry: Skill entry under validation.
        value: Raw relative path value.
        field: Metadata field containing this path.

    Raises:
        ProviderExecutionError: If path value is empty, absolute, or escaped.
    """
    normalized = value.strip()
    if not normalized:
        raise ProviderExecutionError(
            code="plugin_contract_invalid",
            message=f"Error: skill '{entry.name}' has empty plugin path value.",
            data={"skill": entry.name, "field": field},
        )
    candidate = Path(normalized)
    if candidate.is_absolute():
        raise ProviderExecutionError(
            code="plugin_contract_invalid",
            message=f"Error: skill '{entry.name}' has absolute plugin path.",
            data={"skill": entry.name, "field": field, "path": normalized},
        )
    if ".." in candidate.parts:
        raise ProviderExecutionError(
            code="plugin_contract_invalid",
            message=f"Error: skill '{entry.name}' plugin path escapes skill root.",
            data={"skill": entry.name, "field": field, "path": normalized},
        )

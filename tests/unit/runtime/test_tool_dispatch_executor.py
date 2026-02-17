"""Unit tests for typed tool-dispatch executor behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from lily.runtime.executors.tool_dispatch import (
    AddTool,
    BuiltinToolProvider,
    McpToolProvider,
    MultiplyTool,
    ProviderPolicyDeniedError,
    SubtractTool,
    ToolContract,
    ToolDispatchExecutor,
)
from lily.session.models import ModelConfig, Session
from lily.skills.types import InvocationMode, SkillEntry, SkillSnapshot, SkillSource


def _session() -> Session:
    """Create minimal session fixture for executor tests."""
    return Session(
        session_id="session-dispatch-test",
        active_agent="default",
        skill_snapshot=SkillSnapshot(version="v-test", skills=()),
        model_config=ModelConfig(),
    )


def _entry(
    *,
    name: str = "add",
    command_tool: str | None = "add",
) -> SkillEntry:
    """Create tool_dispatch skill entry fixture."""
    return SkillEntry(
        name=name,
        source=SkillSource.BUNDLED,
        path=Path(f"/skills/{name}/SKILL.md"),
        invocation_mode=InvocationMode.TOOL_DISPATCH,
        command_tool=command_tool,
    )


def test_tool_dispatch_executes_registered_add_tool() -> None:
    """Registered add command tool should execute with typed contract output."""
    executor = ToolDispatchExecutor(
        providers=(BuiltinToolProvider(tools=(AddTool(),)),)
    )

    result = executor.execute(_entry(), _session(), "2+2")

    assert result.status.value == "ok"
    assert result.message == "4"
    assert result.code == "tool_ok"
    assert result.data is not None
    assert result.data["output"]["value"] == 4.0


def test_tool_dispatch_requires_command_tool() -> None:
    """Executor should fail clearly when entry lacks command_tool."""
    executor = ToolDispatchExecutor(
        providers=(BuiltinToolProvider(tools=(AddTool(),)),)
    )

    result = executor.execute(_entry(command_tool=None), _session(), "2+2")

    assert result.status.value == "error"
    assert (
        result.message
        == "Error: skill 'add' is missing command_tool for tool_dispatch."
    )


def test_tool_dispatch_fails_for_unknown_tool() -> None:
    """Executor should fail clearly for unregistered tool names."""
    executor = ToolDispatchExecutor(
        providers=(BuiltinToolProvider(tools=(AddTool(),)),)
    )

    result = executor.execute(_entry(command_tool="missing_tool"), _session(), "2+2")

    assert result.status.value == "error"
    assert result.message == (
        "Error: tool 'missing_tool' is not registered for provider "
        "'builtin' (skill 'add')."
    )
    assert result.code == "provider_tool_unregistered"


def test_tool_dispatch_returns_input_validation_error_deterministically() -> None:
    """Invalid payload should return schema-based deterministic input error."""
    executor = ToolDispatchExecutor(
        providers=(BuiltinToolProvider(tools=(AddTool(),)),)
    )

    result = executor.execute(_entry(), _session(), "invalid payload")

    assert result.status.value == "error"
    assert result.code == "tool_input_invalid"
    assert result.data is not None
    assert result.data["tool"] == "add"
    assert result.data["validation_errors"]


def test_tool_dispatch_conformance_for_three_tools() -> None:
    """Typed contract conformance should hold for add/subtract/multiply tools."""
    executor = ToolDispatchExecutor(
        providers=(
            BuiltinToolProvider(tools=(AddTool(), SubtractTool(), MultiplyTool())),
        )
    )

    add_result = executor.execute(
        _entry(name="add", command_tool="add"),
        _session(),
        "20+42",
    )
    subtract_result = executor.execute(
        _entry(name="subtract", command_tool="subtract"),
        _session(),
        "50-8",
    )
    multiply_result = executor.execute(
        _entry(name="multiply", command_tool="multiply"),
        _session(),
        "6*7",
    )

    assert add_result.status.value == "ok"
    assert add_result.message == "62"
    assert subtract_result.status.value == "ok"
    assert subtract_result.message == "42"
    assert multiply_result.status.value == "ok"
    assert multiply_result.message == "42"


class _DummyInput(BaseModel):
    """Dummy input schema for output-validation failure test."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: int


class _DummyOutput(BaseModel):
    """Dummy output schema for output-validation failure test."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    expected: str


class _BadOutputTool:
    """Tool fixture that violates output schema."""

    name = "bad_output"
    input_schema = _DummyInput
    output_schema = _DummyOutput

    def parse_payload(self, payload: str) -> dict[str, Any]:
        """Parse payload into valid dummy input."""
        del payload
        return {"value": 1}

    def execute_typed(
        self,
        typed_input: BaseModel,
        *,
        session: Session,
        skill_name: str,
    ) -> dict[str, Any]:
        """Return invalid output payload that fails schema validation."""
        del typed_input
        del session
        del skill_name
        return {"unexpected": "value"}

    def render_output(self, typed_output: BaseModel) -> str:
        """Render output string."""
        del typed_output
        return "unused"


def test_tool_dispatch_returns_output_validation_error_deterministically() -> None:
    """Invalid tool output should produce deterministic schema error envelope."""
    bad_tool: ToolContract = _BadOutputTool()
    executor = ToolDispatchExecutor(providers=(BuiltinToolProvider(tools=(bad_tool,)),))
    entry = _entry(name="bad", command_tool="bad_output")

    result = executor.execute(entry, _session(), "anything")

    assert result.status.value == "error"
    assert result.code == "tool_output_invalid"
    assert result.data is not None
    assert result.data["tool"] == "bad_output"
    assert result.data["validation_errors"]


def test_tool_dispatch_errors_for_unbound_provider() -> None:
    """Missing provider binding should return deterministic provider_unbound error."""
    executor = ToolDispatchExecutor(
        providers=(BuiltinToolProvider(tools=(AddTool(),)),)
    )
    entry = _entry(command_tool="add").model_copy(
        update={"command_tool_provider": "mcp"}
    )

    result = executor.execute(entry, _session(), "2+2")

    assert result.status.value == "error"
    assert result.code == "provider_unbound"


class _McpAddResolver:
    """Resolver that exposes one add-like MCP tool."""

    def __init__(self, tool: ToolContract) -> None:
        self._tool = tool

    def resolve_tool(
        self,
        tool_name: str,
        *,
        session: Session,
        skill_name: str,
    ) -> ToolContract | None:
        del session
        del skill_name
        if tool_name == self._tool.name:
            return self._tool
        return None


def test_tool_dispatch_routes_through_mcp_provider_resolver() -> None:
    """MCP provider contract should support deterministic tool routing."""
    executor = ToolDispatchExecutor(
        providers=(
            BuiltinToolProvider(tools=(AddTool(),)),
            McpToolProvider(resolver=_McpAddResolver(AddTool())),
        )
    )
    entry = _entry(command_tool="add").model_copy(
        update={"command_tool_provider": "mcp"}
    )

    result = executor.execute(entry, _session(), "2+2")

    assert result.status.value == "ok"
    assert result.code == "tool_ok"
    assert result.message == "4"
    assert result.data is not None
    assert result.data["provider"] == "mcp"


class _PolicyDeniedResolver:
    """Resolver that always denies by policy."""

    def resolve_tool(
        self,
        tool_name: str,
        *,
        session: Session,
        skill_name: str,
    ) -> ToolContract | None:
        del tool_name
        del session
        del skill_name
        raise ProviderPolicyDeniedError("blocked for test")


def test_tool_dispatch_maps_mcp_policy_denied_error() -> None:
    """Provider policy denials should map to deterministic security code."""
    executor = ToolDispatchExecutor(
        providers=(McpToolProvider(resolver=_PolicyDeniedResolver()),)
    )
    entry = _entry(command_tool="add").model_copy(
        update={"command_tool_provider": "mcp"}
    )

    result = executor.execute(entry, _session(), "2+2")

    assert result.status.value == "error"
    assert result.code == "provider_policy_denied"

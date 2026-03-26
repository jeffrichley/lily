"""Unit tests for typed tool-dispatch executor behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict

from lily.config import SkillSandboxSettings
from lily.runtime.executors.tool_dispatch import (
    AddTool,
    BuiltinToolProvider,
    McpToolProvider,
    MultiplyTool,
    PluginToolProvider,
    ProviderPolicyDeniedError,
    SubtractTool,
    ToolContract,
    ToolDispatchExecutor,
)
from lily.runtime.plugin_runner import PluginRuntimeError
from lily.runtime.security import (
    ApprovalDecision,
    ApprovalRequest,
    SecurityApprovalStore,
    SecurityGate,
    SecurityHashService,
    SecurityPreflightScanner,
    SecurityPrompt,
)
from lily.session.models import ModelConfig, Session
from lily.skills.types import (
    InvocationMode,
    SkillCapabilitySpec,
    SkillEntry,
    SkillPluginSpec,
    SkillSnapshot,
    SkillSource,
)


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
        capabilities=SkillCapabilitySpec(declared_tools=("builtin:add",)),
    )


@pytest.mark.unit
def test_tool_dispatch_executes_registered_add_tool() -> None:
    """Registered add command tool should execute with typed contract output."""
    # Arrange - executor with builtin add tool, entry and session
    executor = ToolDispatchExecutor(
        providers=(BuiltinToolProvider(tools=(AddTool(),)),)
    )

    # Act - execute add with 2+2
    result = executor.execute(_entry(), _session(), "2+2")

    # Assert - ok and typed output
    assert result.status.value == "ok"
    assert result.message == "4"
    assert result.code == "tool_ok"
    assert result.data is not None
    assert result.data["output"]["value"] == 4.0


@pytest.mark.unit
def test_tool_dispatch_requires_command_tool() -> None:
    """Executor should fail clearly when entry lacks command_tool."""
    # Arrange - executor, entry without command_tool
    executor = ToolDispatchExecutor(
        providers=(BuiltinToolProvider(tools=(AddTool(),)),)
    )

    # Act - execute
    result = executor.execute(_entry(command_tool=None), _session(), "2+2")

    # Assert - error and explicit message
    assert result.status.value == "error"
    assert (
        result.message
        == "Error: skill 'add' is missing command_tool for tool_dispatch."
    )


@pytest.mark.unit
def test_tool_dispatch_fails_for_unknown_tool() -> None:
    """Executor should fail clearly for unregistered tool names."""
    # Arrange - executor with add only, entry requesting missing_tool
    executor = ToolDispatchExecutor(
        providers=(BuiltinToolProvider(tools=(AddTool(),)),)
    )

    # Act - execute with unregistered tool name
    result = executor.execute(_entry(command_tool="missing_tool"), _session(), "2+2")

    # Assert - error and provider_tool_unregistered code
    assert result.status.value == "error"
    assert result.message == (
        "Error: tool 'missing_tool' is not registered for provider "
        "'builtin' (skill 'add')."
    )
    assert result.code == "provider_tool_unregistered"


@pytest.mark.unit
def test_tool_dispatch_returns_input_validation_error_deterministically() -> None:
    """Invalid payload should return schema-based deterministic input error."""
    # Arrange - executor and entry
    executor = ToolDispatchExecutor(
        providers=(BuiltinToolProvider(tools=(AddTool(),)),)
    )

    # Act - execute with invalid payload
    result = executor.execute(_entry(), _session(), "invalid payload")

    # Assert - tool_input_invalid and validation_errors in data
    assert result.status.value == "error"
    assert result.code == "tool_input_invalid"
    assert result.data is not None
    assert result.data["tool"] == "add"
    assert result.data["validation_errors"]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("skill_name", "command_tool", "payload", "expected_message"),
    [
        ("add", "add", "20+42", "62"),
        ("subtract", "subtract", "50-8", "42"),
        ("multiply", "multiply", "6*7", "42"),
    ],
)
def test_tool_dispatch_conformance_for_builtin_tools(
    skill_name: str,
    command_tool: str,
    payload: str,
    expected_message: str,
) -> None:
    """Typed contract conformance should hold for builtin arithmetic tools."""
    # Arrange - executor with add, subtract, and multiply tools.
    executor = ToolDispatchExecutor(
        providers=(
            BuiltinToolProvider(tools=(AddTool(), SubtractTool(), MultiplyTool())),
        )
    )

    # Act - execute the selected builtin tool case.
    result = executor.execute(
        _entry(name=skill_name, command_tool=command_tool),
        _session(),
        payload,
    )
    # Assert - deterministic success envelope and rendered output.
    assert result.status.value == "ok"
    assert result.code == "tool_ok"
    assert result.message == expected_message


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


@pytest.mark.unit
def test_tool_dispatch_returns_output_validation_error_deterministically() -> None:
    """Invalid tool output should produce deterministic schema error envelope."""
    # Arrange - executor with bad-output tool, entry
    bad_tool: ToolContract = _BadOutputTool()
    executor = ToolDispatchExecutor(providers=(BuiltinToolProvider(tools=(bad_tool,)),))
    entry = _entry(name="bad", command_tool="bad_output")

    # Act - execute (tool returns invalid output)
    result = executor.execute(entry, _session(), "anything")

    # Assert - tool_output_invalid and validation_errors
    assert result.status.value == "error"
    assert result.code == "tool_output_invalid"
    assert result.data is not None
    assert result.data["tool"] == "bad_output"
    assert result.data["validation_errors"]


@pytest.mark.unit
def test_tool_dispatch_errors_for_unbound_provider() -> None:
    """Missing provider binding should return deterministic provider_unbound error."""
    # Arrange - executor with builtin only, entry requesting mcp provider
    executor = ToolDispatchExecutor(
        providers=(BuiltinToolProvider(tools=(AddTool(),)),)
    )
    entry = _entry(command_tool="add").model_copy(
        update={"command_tool_provider": "mcp"}
    )

    # Act - execute
    result = executor.execute(entry, _session(), "2+2")

    # Assert - provider_unbound
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


@pytest.mark.unit
def test_tool_dispatch_routes_through_mcp_provider_resolver() -> None:
    """MCP provider contract should support deterministic tool routing."""
    # Arrange - executor with builtin and MCP provider, entry with mcp provider
    executor = ToolDispatchExecutor(
        providers=(
            BuiltinToolProvider(tools=(AddTool(),)),
            McpToolProvider(resolver=_McpAddResolver(AddTool())),
        )
    )
    entry = _entry(command_tool="add").model_copy(
        update={"command_tool_provider": "mcp"}
    )

    # Act - execute add via MCP
    result = executor.execute(entry, _session(), "2+2")

    # Assert - ok and provider mcp in data
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


@pytest.mark.unit
def test_tool_dispatch_maps_mcp_policy_denied_error() -> None:
    """Provider policy denials should map to deterministic security code."""
    # Arrange - executor with policy-denying MCP resolver, entry
    executor = ToolDispatchExecutor(
        providers=(McpToolProvider(resolver=_PolicyDeniedResolver()),)
    )
    entry = _entry(command_tool="add").model_copy(
        update={"command_tool_provider": "mcp"}
    )

    # Act - execute
    result = executor.execute(entry, _session(), "2+2")

    # Assert - provider_policy_denied
    assert result.status.value == "error"
    assert result.code == "provider_policy_denied"


class _ApprovalPromptStub(SecurityPrompt):
    """Prompt stub for plugin provider tests."""

    def request_approval(self, request: ApprovalRequest) -> ApprovalDecision | None:
        del request
        return ApprovalDecision.RUN_ONCE


class _PluginRunnerStub:
    """Runner stub for plugin-provider tests."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def run(
        self,
        *,
        entry: SkillEntry,
        user_text: str,
        security_hash: str,
        agent_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        del entry
        del security_hash
        del agent_id
        del session_id
        if self.fail:
            raise PluginRuntimeError(
                code="plugin_runtime_failed",
                message="Error: plugin container failed.",
            )
        return {"display": user_text.upper(), "data": {"ok": True}}


@pytest.mark.unit
def test_tool_dispatch_routes_through_plugin_provider(tmp_path: Path) -> None:
    """Plugin provider should route through security gate and runner stubs."""
    # Arrange - skill dir, plugin entry, security gate, runner stub, executor
    skill_root = tmp_path / "skills" / "echo_plugin"
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "SKILL.md").write_text("# plugin", encoding="utf-8")
    (skill_root / "plugin.py").write_text(
        "def run(payload, **kwargs):\n    return {'display': payload}\n",
        encoding="utf-8",
    )
    entry = SkillEntry(
        name="echo_plugin",
        source=SkillSource.BUNDLED,
        path=skill_root / "SKILL.md",
        invocation_mode=InvocationMode.TOOL_DISPATCH,
        command_tool_provider="plugin",
        command_tool="execute",
        capabilities=SkillCapabilitySpec(declared_tools=("plugin:execute",)),
        plugin=SkillPluginSpec(entrypoint="plugin.py", source_files=("plugin.py",)),
    )
    providers = (
        PluginToolProvider(
            security_gate=SecurityGate(
                hash_service=SecurityHashService(
                    sandbox=SkillSandboxSettings(),
                    project_root=Path.cwd(),
                ),
                preflight=SecurityPreflightScanner(),
                store=SecurityApprovalStore(sqlite_path=tmp_path / "security.sqlite"),
                prompt=_ApprovalPromptStub(),
                sandbox=SkillSandboxSettings(),
            ),
            runner=_PluginRunnerStub(),
        ),
    )
    executor = ToolDispatchExecutor(providers=providers)
    session = _session().model_copy(
        update={"skill_snapshot": SkillSnapshot(version="v-test", skills=(entry,))}
    )

    # Act - execute via plugin
    result = executor.execute(entry, session, "hello")

    # Assert - ok and uppercased message
    assert result.status.value == "ok"
    assert result.message == "HELLO"
    assert result.code == "tool_ok"


@pytest.mark.unit
def test_tool_dispatch_maps_plugin_runtime_error(tmp_path: Path) -> None:
    """Plugin runtime failures should return deterministic plugin code."""
    # Arrange - skill dir, entry, plugin provider with failing runner
    skill_root = tmp_path / "skills" / "echo_plugin"
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "SKILL.md").write_text("# plugin", encoding="utf-8")
    (skill_root / "plugin.py").write_text(
        "def run(payload, **kwargs):\n    return {'display': payload}\n",
        encoding="utf-8",
    )
    entry = SkillEntry(
        name="echo_plugin",
        source=SkillSource.BUNDLED,
        path=skill_root / "SKILL.md",
        invocation_mode=InvocationMode.TOOL_DISPATCH,
        command_tool_provider="plugin",
        command_tool="execute",
        capabilities=SkillCapabilitySpec(declared_tools=("plugin:execute",)),
        plugin=SkillPluginSpec(entrypoint="plugin.py", source_files=("plugin.py",)),
    )
    providers = (
        PluginToolProvider(
            security_gate=SecurityGate(
                hash_service=SecurityHashService(
                    sandbox=SkillSandboxSettings(),
                    project_root=Path.cwd(),
                ),
                preflight=SecurityPreflightScanner(),
                store=SecurityApprovalStore(sqlite_path=tmp_path / "security.sqlite"),
                prompt=_ApprovalPromptStub(),
                sandbox=SkillSandboxSettings(),
            ),
            runner=_PluginRunnerStub(fail=True),
        ),
    )
    executor = ToolDispatchExecutor(providers=providers)
    session = _session().model_copy(
        update={"skill_snapshot": SkillSnapshot(version="v-test", skills=(entry,))}
    )

    # Act - execute (runner raises)
    result = executor.execute(entry, session, "hello")

    # Assert - plugin_runtime_failed
    assert result.status.value == "error"
    assert result.code == "plugin_runtime_failed"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("source_text", "source_bytes", "expected_signature"),
    [
        ("import os\n", None, "node_import"),
        (None, b"\xff\xfe\x00", "file_decode_error"),
    ],
)
def test_tool_dispatch_maps_language_policy_denials(
    tmp_path: Path,
    source_text: str | None,
    source_bytes: bytes | None,
    expected_signature: str,
) -> None:
    """Language policy denials should map through tool-dispatch deterministically."""
    # Arrange - plugin source violating language policy and provider dependencies.
    skill_root = tmp_path / "skills" / "echo_plugin"
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "SKILL.md").write_text("# plugin", encoding="utf-8")
    plugin_path = skill_root / "plugin.py"
    if source_text is not None:
        plugin_path.write_text(source_text, encoding="utf-8")
    else:
        assert source_bytes is not None
        plugin_path.write_bytes(source_bytes)
    entry = SkillEntry(
        name="echo_plugin",
        source=SkillSource.BUNDLED,
        path=skill_root / "SKILL.md",
        invocation_mode=InvocationMode.TOOL_DISPATCH,
        command_tool_provider="plugin",
        command_tool="execute",
        capabilities=SkillCapabilitySpec(declared_tools=("plugin:execute",)),
        plugin=SkillPluginSpec(entrypoint="plugin.py", source_files=("plugin.py",)),
    )
    providers = (
        PluginToolProvider(
            security_gate=SecurityGate(
                hash_service=SecurityHashService(
                    sandbox=SkillSandboxSettings(),
                    project_root=Path.cwd(),
                ),
                preflight=SecurityPreflightScanner(),
                store=SecurityApprovalStore(sqlite_path=tmp_path / "security.sqlite"),
                prompt=_ApprovalPromptStub(),
                sandbox=SkillSandboxSettings(),
            ),
            runner=_PluginRunnerStub(),
        ),
    )
    executor = ToolDispatchExecutor(providers=providers)
    session = _session().model_copy(
        update={"skill_snapshot": SkillSnapshot(version="v-test", skills=(entry,))}
    )

    # Act - execute plugin-backed tool.
    result = executor.execute(entry, session, "hello")

    # Assert - denial is bridged to deterministic tool error envelope.
    assert result.status.value == "error"
    assert result.code == "security_language_policy_denied"
    assert result.data is not None
    assert result.data["path"] == "plugin.py"
    assert result.data["signature"] == expected_signature


@pytest.mark.unit
def test_tool_dispatch_maps_language_policy_read_denial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plugin file read failures should map through tool-dispatch deterministically."""
    # Arrange - valid plugin source with forced read failure on plugin file path.
    skill_root = tmp_path / "skills" / "echo_plugin"
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "SKILL.md").write_text("# plugin", encoding="utf-8")
    (skill_root / "plugin.py").write_text(
        "def run(payload, **kwargs):\n    return {'display': payload}\n",
        encoding="utf-8",
    )
    plugin_file = (skill_root / "plugin.py").resolve()
    original_read_bytes = Path.read_bytes
    read_counts: dict[Path, int] = {}

    def _read_bytes_raise(path: Path) -> bytes:
        resolved = path.resolve()
        read_counts[resolved] = read_counts.get(resolved, 0) + 1
        # First read is from SecurityHashService.
        # Second read is from language policy scan.
        if resolved == plugin_file and read_counts[resolved] >= 2:
            raise OSError("forced read failure")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", _read_bytes_raise)
    entry = SkillEntry(
        name="echo_plugin",
        source=SkillSource.BUNDLED,
        path=skill_root / "SKILL.md",
        invocation_mode=InvocationMode.TOOL_DISPATCH,
        command_tool_provider="plugin",
        command_tool="execute",
        capabilities=SkillCapabilitySpec(declared_tools=("plugin:execute",)),
        plugin=SkillPluginSpec(entrypoint="plugin.py", source_files=("plugin.py",)),
    )
    providers = (
        PluginToolProvider(
            security_gate=SecurityGate(
                hash_service=SecurityHashService(
                    sandbox=SkillSandboxSettings(),
                    project_root=Path.cwd(),
                ),
                preflight=SecurityPreflightScanner(),
                store=SecurityApprovalStore(sqlite_path=tmp_path / "security.sqlite"),
                prompt=_ApprovalPromptStub(),
                sandbox=SkillSandboxSettings(),
            ),
            runner=_PluginRunnerStub(),
        ),
    )
    executor = ToolDispatchExecutor(providers=providers)
    session = _session().model_copy(
        update={"skill_snapshot": SkillSnapshot(version="v-test", skills=(entry,))}
    )

    # Act - execute plugin-backed tool.
    result = executor.execute(entry, session, "hello")

    # Assert - read denial is bridged to tool error envelope.
    assert result.status.value == "error"
    assert result.code == "security_language_policy_denied"
    assert result.data is not None
    assert result.data["path"] == "plugin.py"
    assert result.data["signature"] == "file_read_error"

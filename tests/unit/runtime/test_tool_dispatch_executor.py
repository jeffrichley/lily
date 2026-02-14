"""Unit tests for tool-dispatch executor behavior."""

from __future__ import annotations

from pathlib import Path

from lily.runtime.executors.tool_dispatch import AddTool, ToolDispatchExecutor
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


def test_tool_dispatch_executes_registered_tool() -> None:
    """Registered command tool should execute and return deterministic result."""
    executor = ToolDispatchExecutor(tools=(AddTool(),))

    result = executor.execute(_entry(), _session(), "2+2")

    assert result.status.value == "ok"
    assert result.message == "4"


def test_tool_dispatch_requires_command_tool() -> None:
    """Executor should fail clearly when entry lacks command_tool."""
    executor = ToolDispatchExecutor(tools=(AddTool(),))

    result = executor.execute(_entry(command_tool=None), _session(), "2+2")

    assert result.status.value == "error"
    assert (
        result.message
        == "Error: skill 'add' is missing command_tool for tool_dispatch."
    )


def test_tool_dispatch_fails_for_unknown_tool() -> None:
    """Executor should fail clearly for unregistered tool names."""
    executor = ToolDispatchExecutor(tools=(AddTool(),))

    result = executor.execute(_entry(command_tool="missing_tool"), _session(), "2+2")

    assert result.status.value == "error"
    assert (
        result.message
        == "Error: command tool 'missing_tool' is not registered for skill 'add'."
    )

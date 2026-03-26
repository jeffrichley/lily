"""Unit tests for tool executable adapter handler."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.commands.types import CommandResult
from lily.runtime.executables.handlers.tool_handler import ToolExecutableHandler
from lily.runtime.executables.models import (
    CallerContext,
    ExecutableKind,
    ExecutableRef,
    ExecutableRequest,
    ExecutableStatus,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionMetadata,
)
from lily.session.models import ModelConfig, Session
from lily.skills.types import (
    InvocationMode,
    SkillCapabilitySpec,
    SkillEntry,
    SkillSnapshot,
    SkillSource,
)


class _ToolExecutorFixture:
    """Tool executor fixture for deterministic adapter tests."""

    def __init__(self, result: CommandResult) -> None:
        """Store predetermined command result."""
        self._result = result

    def execute(
        self, entry: SkillEntry, session: Session, user_text: str
    ) -> CommandResult:
        """Return deterministic tool command result."""
        del entry
        del session
        del user_text
        return self._result


def _session() -> Session:
    """Create basic session fixture."""
    return Session(
        session_id="session-tool-adapter",
        active_agent="default",
        skill_snapshot=SkillSnapshot(version="v-test", skills=()),
        model_config=ModelConfig(),
    )


def _tool_skill_entry() -> SkillEntry:
    """Create one tool-dispatch skill entry fixture."""
    return SkillEntry(
        name="calc_skill",
        source=SkillSource.BUNDLED,
        path=Path("/skills/calc_skill/SKILL.md"),
        invocation_mode=InvocationMode.TOOL_DISPATCH,
        command_tool_provider="builtin",
        command_tool="add",
        capabilities=SkillCapabilitySpec(declared_tools=("builtin:add",)),
    )


def _request(*, payload: dict[str, object]) -> ExecutableRequest:
    """Create tool executable request fixture."""
    return ExecutableRequest(
        run_id="run-001",
        step_id="step-001",
        caller=CallerContext(supervisor_id="supervisor.v1", active_agent="default"),
        target=ExecutableRef(
            executable_id="builtin:add", executable_kind=ExecutableKind.TOOL
        ),
        objective="Execute add tool.",
        input=payload,
        context=ExecutionContext(
            memory_refs=(),
            artifact_refs=(),
            constraints=ExecutionConstraints(),
        ),
        metadata=ExecutionMetadata(
            trace_tags={}, created_at_utc="2026-03-04T20:00:00Z"
        ),
    )


@pytest.mark.unit
def test_tool_handler_maps_command_success_to_executable_ok() -> None:
    """Tool handler should map successful command result to ok envelope."""
    # Arrange - create adapter with deterministic successful tool result.
    handler = ToolExecutableHandler(
        executor=_ToolExecutorFixture(
            CommandResult.ok("Tool completed.", code="tool_ok", data={"sum": 5})
        )
    )
    request = _request(
        payload={
            "session": _session(),
            "skill_entry": _tool_skill_entry(),
            "user_text": '{"a": 2, "b": 3}',
        }
    )

    # Act - execute tool adapter request.
    result = handler.handle(request)

    # Assert - result is canonical success with provider/tool reference.
    assert result.status == ExecutableStatus.OK
    assert result.error is None
    assert result.output["message"] == "Tool completed."
    assert result.output["command_data"] == {"sum": 5}
    assert result.references == ("tool://builtin:add",)


@pytest.mark.unit
def test_tool_handler_rejects_missing_required_payload_fields() -> None:
    """Tool handler should fail when required request input fields are missing."""
    # Arrange - create adapter request without required session/skill entry.
    handler = ToolExecutableHandler(
        executor=_ToolExecutorFixture(CommandResult.ok("ok"))
    )
    request = _request(payload={"user_text": "noop"})

    # Act - execute malformed adapter request.
    result = handler.handle(request)

    # Assert - adapter emits deterministic input validation error.
    assert result.status == ExecutableStatus.ERROR
    assert result.error is not None
    assert result.error.code == "adapter_input_invalid"

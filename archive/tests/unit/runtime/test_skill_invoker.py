"""Unit tests for skill invoker dispatch behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.commands.types import CommandResult
from lily.runtime.executors.base import SkillExecutor
from lily.runtime.executors.llm_orchestration import LlmOrchestrationExecutor
from lily.runtime.llm_backend.base import LlmRunRequest, LlmRunResponse
from lily.runtime.skill_invoker import SkillInvoker
from lily.session.models import ModelConfig, Session
from lily.skills.types import (
    InvocationMode,
    SkillCapabilitySpec,
    SkillEntry,
    SkillSnapshot,
    SkillSource,
)


class _StubLlmBackend:
    """Test double for private LLM backend port."""

    def run(self, request: LlmRunRequest) -> LlmRunResponse:
        """Return stable response for tests.

        Args:
            request: Run request payload.

        Returns:
            Fixed response payload.
        """
        del request

        return LlmRunResponse(text="stub-response")


class _EchoToolDispatchExecutor:
    """Test executor for tool dispatch mode."""

    mode = InvocationMode.TOOL_DISPATCH

    def execute(
        self, entry: SkillEntry, session: Session, user_text: str
    ) -> CommandResult:
        del session
        return CommandResult.ok(f"tool:{entry.name}:{user_text}")


def _make_session() -> Session:
    """Create minimal session fixture for invoker tests.

    Returns:
        Session fixture.
    """
    return Session(
        session_id="session-runtime-test",
        active_agent="default",
        skill_snapshot=SkillSnapshot(version="v-test", skills=()),
        model_config=ModelConfig(),
    )


def _make_entry(name: str, mode: InvocationMode) -> SkillEntry:
    """Create skill entry fixture for invoker tests.

    Args:
        name: Skill name.
        mode: Invocation mode.

    Returns:
        Skill entry fixture.
    """
    return SkillEntry(
        name=name,
        source=SkillSource.BUNDLED,
        path=Path(f"/skills/{name}/SKILL.md"),
        invocation_mode=mode,
    )


@pytest.mark.unit
def test_invoker_dispatches_to_llm_executor() -> None:
    """Invoker should route llm_orchestration entries to LLM executor."""
    # Arrange - invoker with LLM executor, session, llm_orchestration entry
    invoker = SkillInvoker(executors=(LlmOrchestrationExecutor(_StubLlmBackend()),))
    session = _make_session()
    entry = _make_entry("echo", InvocationMode.LLM_ORCHESTRATION)

    # Act - invoke
    result = invoker.invoke(entry, session, "hello")

    # Assert - ok and stub response
    assert result.status.value == "ok"
    assert result.message == "stub-response"


@pytest.mark.unit
def test_invoker_returns_explicit_error_for_unbound_mode() -> None:
    """Invoker should return explicit error when executor binding is missing."""
    # Arrange - invoker with no executors, tool_dispatch entry
    invoker = SkillInvoker(executors=())
    session = _make_session()
    entry = _make_entry("dispatch_me", InvocationMode.TOOL_DISPATCH)

    # Act - invoke
    result = invoker.invoke(entry, session, "hello")

    # Assert - error and unbound message
    assert result.status.value == "error"
    assert (
        result.message
        == "Error: no executor bound for mode 'tool_dispatch' (skill 'dispatch_me')."
    )


@pytest.mark.unit
def test_invoker_dispatches_to_tool_executor() -> None:
    """Invoker should route tool_dispatch entries to tool executor."""
    # Arrange - invoker with echo tool executor, session, tool_dispatch entry
    executors: tuple[SkillExecutor, ...] = (_EchoToolDispatchExecutor(),)
    invoker = SkillInvoker(executors=executors)
    session = _make_session()
    entry = _make_entry("dispatch_me", InvocationMode.TOOL_DISPATCH)

    # Act - invoke
    result = invoker.invoke(entry, session, "payload")

    # Assert - ok and tool echo output
    assert result.status.value == "ok"
    assert result.message == "tool:dispatch_me:payload"


@pytest.mark.unit
def test_invoker_denies_undeclared_tool_capability() -> None:
    """Invoker should deny tool_dispatch entry missing declared tool capability."""
    # Arrange - invoker, entry with command_tool add but declared_tools subtract only
    executors: tuple[SkillExecutor, ...] = (_EchoToolDispatchExecutor(),)
    invoker = SkillInvoker(executors=executors)
    session = _make_session()
    entry = _make_entry("dispatch_me", InvocationMode.TOOL_DISPATCH).model_copy(
        update={
            "command_tool": "add",
            "capabilities": SkillCapabilitySpec(declared_tools=("subtract",)),
            "capabilities_declared": True,
        }
    )

    # Act - invoke
    result = invoker.invoke(entry, session, "payload")

    # Assert - skill_capability_denied
    assert result.status.value == "error"
    assert result.code == "skill_capability_denied"
    assert "undeclared tool 'builtin:add'" in result.message

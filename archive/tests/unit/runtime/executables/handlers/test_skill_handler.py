"""Unit tests for skill executable adapter handler."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.commands.types import CommandResult
from lily.runtime.executables.handlers.skill_handler import SkillExecutableHandler
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
from lily.skills.types import InvocationMode, SkillEntry, SkillSnapshot, SkillSource


class _FakeSkillInvoker:
    """Skill invoker fixture for deterministic adapter tests."""

    def __init__(self, result: CommandResult) -> None:
        """Store predetermined command result."""
        self._result = result

    def invoke(
        self, entry: SkillEntry, session: Session, user_text: str
    ) -> CommandResult:
        """Return deterministic command result fixture."""
        del entry
        del session
        del user_text
        return self._result


def _session_with_skill() -> Session:
    """Create session fixture containing one invokable skill entry."""
    skill = SkillEntry(
        name="security_review",
        source=SkillSource.BUNDLED,
        path=Path("/skills/security_review/SKILL.md"),
        invocation_mode=InvocationMode.LLM_ORCHESTRATION,
        instructions="Do security review.",
    )
    return Session(
        session_id="session-adapter-skill",
        active_agent="default",
        skill_snapshot=SkillSnapshot(version="v-test", skills=(skill,)),
        model_config=ModelConfig(),
    )


def _request(*, session: Session) -> ExecutableRequest:
    """Create skill executable request fixture."""
    return ExecutableRequest(
        run_id="run-001",
        step_id="step-001",
        caller=CallerContext(supervisor_id="supervisor.v1", active_agent="default"),
        target=ExecutableRef(
            executable_id="security_review",
            executable_kind=ExecutableKind.SKILL,
        ),
        objective="Run security review skill.",
        input={"session": session, "user_text": "check dependencies"},
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
def test_skill_handler_maps_command_success_to_executable_ok() -> None:
    """Skill handler should normalize success into executable envelope."""
    # Arrange - create adapter with successful skill invoker result.
    session = _session_with_skill()
    handler = SkillExecutableHandler(
        invoker=_FakeSkillInvoker(
            CommandResult.ok("Skill completed.", code="skill_ok", data={"x": 1})
        )
    )
    request = _request(session=session)

    # Act - handle skill request through executable adapter.
    result = handler.handle(request)

    # Assert - handler emits canonical ok envelope with normalized output/data.
    assert result.status == ExecutableStatus.OK
    assert result.error is None
    assert result.output["message"] == "Skill completed."
    assert result.output["command_data"] == {"x": 1}
    assert result.references == ("skill://security_review",)


@pytest.mark.unit
def test_skill_handler_maps_missing_skill_to_adapter_input_invalid() -> None:
    """Skill handler should fail deterministically when skill is absent."""
    # Arrange - create adapter request with empty skill snapshot.
    session = Session(
        session_id="session-adapter-empty",
        active_agent="default",
        skill_snapshot=SkillSnapshot(version="v-test", skills=()),
        model_config=ModelConfig(),
    )
    handler = SkillExecutableHandler(invoker=_FakeSkillInvoker(CommandResult.ok("ok")))
    request = _request(session=session)

    # Act - handle skill request with missing target skill entry.
    result = handler.handle(request)

    # Assert - missing skill path maps to adapter_input_invalid envelope.
    assert result.status == ExecutableStatus.ERROR
    assert result.error is not None
    assert result.error.code == "adapter_input_invalid"

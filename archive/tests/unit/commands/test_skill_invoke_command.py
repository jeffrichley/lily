"""Unit tests for `/skill <name>` command handler behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.commands.handlers.skill_invoke import SkillInvokeCommand
from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.session.models import ModelConfig, Session
from lily.skills.types import InvocationMode, SkillEntry, SkillSnapshot, SkillSource


class _CapturingInvoker:
    """Invoker test double that records selected skill and payload."""

    def __init__(self) -> None:
        """Initialize capture fields."""
        self.skill_name: str | None = None
        self.payload: str | None = None

    def invoke(
        self, entry: SkillEntry, session: Session, user_text: str
    ) -> CommandResult:
        """Capture invocation arguments and return success.

        Args:
            entry: Skill selected by handler.
            session: Active session.
            user_text: Payload forwarded by handler.

        Returns:
            Successful command result.
        """
        del session
        self.skill_name = entry.name
        self.payload = user_text
        return CommandResult.ok("captured")


def _skill(name: str) -> SkillEntry:
    """Create skill entry fixture.

    Args:
        name: Skill name.

    Returns:
        Skill entry fixture.
    """
    return SkillEntry(
        name=name,
        source=SkillSource.BUNDLED,
        path=Path(f"/skills/{name}/SKILL.md"),
        invocation_mode=InvocationMode.LLM_ORCHESTRATION,
    )


def _session(skills: tuple[SkillEntry, ...]) -> Session:
    """Create session fixture.

    Args:
        skills: Skill entries in snapshot.

    Returns:
        Session fixture with supplied snapshot.
    """
    return Session(
        session_id="session-echo-test",
        active_agent="default",
        skill_snapshot=SkillSnapshot(version="v-test", skills=skills),
        model_config=ModelConfig(),
    )


@pytest.mark.unit
def test_skill_invoke_forces_exact_snapshot_match() -> None:
    """Handler should delegate exactly requested skill with forwarded payload."""
    # Arrange - capturing invoker, handler, session with two skills, call for echo
    invoker = _CapturingInvoker()
    handler = SkillInvokeCommand(invoker)
    session = _session(skills=(_skill("echo"), _skill("echo_helper")))
    call = CommandCall(name="skill", args=("echo", "hello", "world"), raw="/skill ...")

    # Act - execute handler
    result = handler.execute(call, session)

    # Assert - ok result and invoker captured echo and payload
    assert result.status.value == "ok"
    assert result.message == "captured"
    assert invoker.skill_name == "echo"
    assert invoker.payload == "hello world"


@pytest.mark.unit
def test_skill_invoke_returns_invalid_args_when_name_missing() -> None:
    """Handler should fail with stable invalid-args envelope for empty args."""
    # Arrange - handler and session with one skill
    invoker = _CapturingInvoker()
    handler = SkillInvokeCommand(invoker)
    session = _session(skills=(_skill("echo"),))
    call = CommandCall(name="skill", args=(), raw="/skill")

    # Act - execute without required skill name arg
    result = handler.execute(call, session)

    # Assert - deterministic invalid-args envelope
    assert result.status.value == "error"
    assert result.code == "invalid_args"
    assert result.data == {"command": "skill"}
    assert "requires a skill name" in result.message
    assert invoker.skill_name is None
    assert invoker.payload is None


@pytest.mark.unit
def test_skill_invoke_returns_not_found_when_name_absent() -> None:
    """Handler should return stable not-found error for unknown skill name."""
    # Arrange - handler and session with one non-matching skill
    invoker = _CapturingInvoker()
    handler = SkillInvokeCommand(invoker)
    session = _session(skills=(_skill("echo"),))
    call = CommandCall(name="skill", args=("missing",), raw="/skill missing")

    # Act - execute for missing skill
    result = handler.execute(call, session)

    # Assert - deterministic not-found envelope and no invocation
    assert result.status.value == "error"
    assert result.code == "skill_not_found"
    assert result.data == {"skill": "missing"}
    assert "not found in snapshot" in result.message
    assert invoker.skill_name is None
    assert invoker.payload is None


@pytest.mark.unit
def test_skill_invoke_uses_case_sensitive_exact_name_lookup() -> None:
    """Handler should not match differently cased names."""
    # Arrange - handler with lowercase snapshot skill, uppercase request
    invoker = _CapturingInvoker()
    handler = SkillInvokeCommand(invoker)
    session = _session(skills=(_skill("echo"),))
    call = CommandCall(name="skill", args=("ECHO", "hello"), raw="/skill ECHO hello")

    # Act - execute with mismatched case
    result = handler.execute(call, session)

    # Assert - case-sensitive lookup yields not found
    assert result.status.value == "error"
    assert result.code == "skill_not_found"
    assert result.data == {"skill": "ECHO"}
    assert invoker.skill_name is None

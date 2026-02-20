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
    invoker = _CapturingInvoker()
    handler = SkillInvokeCommand(invoker)
    session = _session(skills=(_skill("echo"), _skill("echo_helper")))
    call = CommandCall(name="skill", args=("echo", "hello", "world"), raw="/skill ...")

    result = handler.execute(call, session)

    assert result.status.value == "ok"
    assert result.message == "captured"
    assert invoker.skill_name == "echo"
    assert invoker.payload == "hello world"

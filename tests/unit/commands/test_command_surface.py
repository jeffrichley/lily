"""Unit tests for deterministic command surface behavior."""

from __future__ import annotations

from pathlib import Path

from lily.runtime.facade import RuntimeFacade
from lily.session.models import ModelConfig, Session
from lily.skills.types import InvocationMode, SkillEntry, SkillSnapshot, SkillSource


def _make_session(skills: tuple[SkillEntry, ...]) -> Session:
    """Create a minimal session fixture with a supplied skill snapshot.

    Args:
        skills: Snapshot skill entries.

    Returns:
        Session configured for command-surface unit tests.
    """
    snapshot = SkillSnapshot(version="v-test", skills=skills)
    return Session(
        session_id="session-test",
        active_agent="default",
        skill_snapshot=snapshot,
        model_config=ModelConfig(),
    )


def _make_skill(name: str, summary: str = "") -> SkillEntry:
    """Create a deterministic skill entry fixture.

    Args:
        name: Skill name.
        summary: Skill summary text.

    Returns:
        Skill entry fixture.
    """
    return SkillEntry(
        name=name,
        source=SkillSource.BUNDLED,
        path=Path(f"/skills/{name}/SKILL.md"),
        summary=summary,
        invocation_mode=InvocationMode.LLM_ORCHESTRATION,
    )


def test_unknown_command_returns_explicit_error() -> None:
    """Unknown commands should fail with deterministic explicit error output."""
    runtime = RuntimeFacade()
    session = _make_session(skills=())

    result = runtime.handle_input("/unknown", session)

    assert result.status.value == "error"
    assert result.message == "Error: unknown command '/unknown'."


def test_skill_command_requires_name_argument() -> None:
    """`/skill` without name should fail with explicit missing arg message."""
    runtime = RuntimeFacade()
    session = _make_session(skills=())

    result = runtime.handle_input("/skill", session)

    assert result.status.value == "error"
    assert result.message == "Error: /skill requires a skill name."


def test_skill_command_missing_name_has_no_fallback() -> None:
    """Missing skill should return explicit no-fallback error."""
    runtime = RuntimeFacade()
    session = _make_session(skills=(_make_skill("echo"),))

    result = runtime.handle_input("/skill missing_name", session)

    assert result.status.value == "error"
    assert result.message == "Error: skill 'missing_name' not found in snapshot."


def test_skills_command_returns_deterministic_sorted_output() -> None:
    """`/skills` should list snapshot entries in deterministic sorted order."""
    runtime = RuntimeFacade()
    session = _make_session(
        skills=(
            _make_skill("zeta", summary="Zeta summary"),
            _make_skill("alpha", summary="Alpha summary"),
        )
    )

    result = runtime.handle_input("/skills", session)

    assert result.status.value == "ok"
    assert result.message.splitlines() == [
        "alpha - Alpha summary",
        "zeta - Zeta summary",
    ]


def test_skill_command_delegates_to_hidden_llm_adapter_path() -> None:
    """`/skill` should delegate through invoker/executor backend path."""
    runtime = RuntimeFacade()
    session = _make_session(skills=(_make_skill("echo", summary="Echo skill"),))

    result = runtime.handle_input("/skill echo hello world", session)

    assert result.status.value == "error"
    assert result.message == "Error: LLM backend is unavailable."

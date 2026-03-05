"""Unit tests for deterministic command surface behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.persona import FilePersonaRepository
from lily.runtime.facade import RuntimeFacade
from lily.session.factory import SessionFactory, SessionFactoryConfig
from lily.session.models import ModelConfig, Session
from lily.skills.types import (
    InvocationMode,
    SkillDiagnostic,
    SkillSnapshot,
    SkillSource,
)
from tests.unit.commands.command_surface_shared import (
    _make_session,
    _make_skill,
    _write_persona,
)


@pytest.mark.unit
def test_unknown_command_returns_explicit_error() -> None:
    """Unknown commands should fail with deterministic explicit error output."""
    # Arrange - runtime and empty session
    runtime = RuntimeFacade()
    session = _make_session(skills=())

    # Act - handle unknown command
    result = runtime.handle_input("/unknown", session)

    # Assert - error status and explicit message
    assert result.status.value == "error"
    assert result.message == "Error: unknown command '/unknown'."


@pytest.mark.unit
def test_skill_command_requires_name_argument() -> None:
    """`/skill` without name should fail with explicit missing arg message."""
    # Arrange - runtime and empty session
    runtime = RuntimeFacade()
    session = _make_session(skills=())

    # Act - handle /skill without name
    result = runtime.handle_input("/skill", session)

    # Assert - error and missing arg message
    assert result.status.value == "error"
    assert result.message == "Error: /skill requires a skill name."


@pytest.mark.unit
def test_skill_command_missing_name_has_no_fallback() -> None:
    """Missing skill should return explicit no-fallback error."""
    # Arrange - session with one skill, request different name
    runtime = RuntimeFacade()
    session = _make_session(skills=(_make_skill("echo"),))

    # Act - invoke /skill with missing skill name
    result = runtime.handle_input("/skill missing_name", session)

    # Assert - error and not-found message
    assert result.status.value == "error"
    assert result.message == "Error: skill 'missing_name' not found in snapshot."


@pytest.mark.unit
def test_skills_command_returns_deterministic_sorted_output() -> None:
    """`/skills` should list snapshot entries in deterministic sorted order."""
    # Arrange - session with skills in non-sorted order
    runtime = RuntimeFacade()
    session = _make_session(
        skills=(
            _make_skill("zeta", summary="Zeta summary"),
            _make_skill("alpha", summary="Alpha summary"),
        )
    )

    # Act - list skills
    result = runtime.handle_input("/skills", session)

    # Assert - ok and alphabetically sorted lines
    assert result.status.value == "ok"
    assert result.message.splitlines() == [
        "alpha - Alpha summary",
        "zeta - Zeta summary",
    ]


@pytest.mark.unit
def test_skills_command_includes_diagnostics_section() -> None:
    """`/skills` should include snapshot diagnostics deterministically."""
    # Arrange - session with snapshot that has diagnostics
    runtime = RuntimeFacade()
    snapshot = SkillSnapshot(
        version="v-test",
        skills=(
            _make_skill("alpha", summary="Alpha summary"),
            _make_skill("zeta", summary="Zeta summary"),
        ),
        diagnostics=(
            SkillDiagnostic(
                skill_name="echo",
                code="malformed_frontmatter",
                message="Bad frontmatter",
                source=SkillSource.WORKSPACE,
                path=Path("/workspace/echo"),
            ),
        ),
    )
    session = Session(
        session_id="session-test",
        active_agent="default",
        skill_snapshot=snapshot,
        model_config=ModelConfig(),
    )

    # Act - list skills
    result = runtime.handle_input("/skills", session)

    # Assert - ok and diagnostics section present
    assert result.status.value == "ok"
    assert "Diagnostics:" in result.message
    assert "- echo [malformed_frontmatter] Bad frontmatter" in result.message


@pytest.mark.unit
def test_skill_command_delegates_to_hidden_llm_adapter_path() -> None:
    """`/skill` should delegate through invoker/executor backend path."""
    # Arrange - session with llm_orchestration skill
    runtime = RuntimeFacade()
    session = _make_session(skills=(_make_skill("echo", summary="Echo skill"),))

    # Act - invoke skill (no LLM configured)
    result = runtime.handle_input("/skill echo hello world", session)

    # Assert - error when LLM unavailable
    assert result.status.value == "error"
    assert result.message == "Error: LLM backend is unavailable."


@pytest.mark.unit
def test_skill_command_tool_dispatch_executes_without_llm() -> None:
    """`/skill` should execute tool_dispatch skills deterministically."""
    # Arrange - session with tool_dispatch add skill
    runtime = RuntimeFacade()
    session = _make_session(
        skills=(
            _make_skill(
                "add",
                summary="Add two numbers",
                mode=InvocationMode.TOOL_DISPATCH,
                command_tool="add",
            ),
        )
    )

    # Act - invoke tool_dispatch skill
    result = runtime.handle_input("/skill add 2+2", session)

    # Assert - ok and tool result
    assert result.status.value == "ok"
    assert result.message == "4"


@pytest.mark.unit
def test_reload_skills_refreshes_current_session_snapshot(tmp_path: Path) -> None:
    """`/reload_skills` should update only current session snapshot contents."""
    # Arrange - factory with bundled echo, session created
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()

    echo_dir = bundled_dir / "echo"
    echo_dir.mkdir()
    (echo_dir / "SKILL.md").write_text(
        ("---\nsummary: Echo\ninvocation_mode: llm_orchestration\n---\n# Echo\n"),
        encoding="utf-8",
    )

    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"skills", "skill", "reload_skills"},
        )
    )
    session = factory.create()
    runtime = RuntimeFacade()

    assert [entry.name for entry in session.skill_snapshot.skills] == ["echo"]

    add_dir = workspace_dir / "add"
    add_dir.mkdir()
    (add_dir / "SKILL.md").write_text(
        (
            "---\n"
            "summary: Add\n"
            "invocation_mode: tool_dispatch\n"
            "command_tool: add\n"
            "capabilities:\n"
            "  declared_tools: [add]\n"
            "---\n"
            "# Add\n"
        ),
        encoding="utf-8",
    )

    # Act - reload skills
    result = runtime.handle_input("/reload_skills", session)

    # Assert - ok and snapshot now includes add and echo
    assert result.status.value == "ok"
    assert "Reloaded skills for current session." in result.message
    assert [entry.name for entry in session.skill_snapshot.skills] == ["add", "echo"]


@pytest.mark.unit
def test_reload_skills_rejects_arguments() -> None:
    """`/reload_skills` should reject unexpected arguments deterministically."""
    # Arrange - runtime and session
    runtime = RuntimeFacade()
    session = _make_session(skills=())

    # Act - reload_skills with argument
    result = runtime.handle_input("/reload_skills now", session)

    # Assert - error and explicit message
    assert result.status.value == "error"
    assert result.message == "Error: /reload_skills does not accept arguments."


@pytest.mark.unit
def test_reload_skills_errors_without_snapshot_config() -> None:
    """`/reload_skills` should fail when session cannot rebuild snapshots."""
    # Arrange - session without snapshot config (from _make_session)
    runtime = RuntimeFacade()
    session = _make_session(skills=())

    # Act - reload_skills
    result = runtime.handle_input("/reload_skills", session)

    # Assert - error when unavailable
    assert result.status.value == "error"
    assert result.message == "Error: /reload_skills is unavailable for this session."


@pytest.mark.unit
def test_help_requires_exactly_one_skill_name() -> None:
    """`/help` should require exactly one skill argument."""
    # Arrange - runtime and empty session
    runtime = RuntimeFacade()
    session = _make_session(skills=())

    # Act - help without skill name
    result = runtime.handle_input("/help", session)

    # Assert - error and explicit message
    assert result.status.value == "error"
    assert result.message == "Error: /help requires exactly one skill name."


@pytest.mark.unit
def test_help_fails_for_unknown_skill() -> None:
    """`/help <skill>` should fail clearly when skill is missing."""
    # Arrange - session with echo, request help for missing skill
    runtime = RuntimeFacade()
    session = _make_session(skills=(_make_skill("echo"),))

    # Act - help for unknown skill
    result = runtime.handle_input("/help missing", session)

    # Assert - error and not-found message
    assert result.status.value == "error"
    assert result.message == "Error: skill 'missing' not found in snapshot."


@pytest.mark.unit
def test_help_returns_snapshot_metadata_without_execution() -> None:
    """`/help <skill>` should return deterministic snapshot metadata."""
    # Arrange - session with tool_dispatch add skill
    runtime = RuntimeFacade()
    session = _make_session(
        skills=(
            _make_skill(
                "add",
                summary="Add two numbers",
                mode=InvocationMode.TOOL_DISPATCH,
                command_tool="add",
            ),
        )
    )

    # Act - help for add
    result = runtime.handle_input("/help add", session)

    # Assert - ok and metadata in message
    assert result.status.value == "ok"
    assert "# /help add" in result.message
    assert "- `invocation_mode`: tool_dispatch" in result.message
    assert "- `command_tool`: add" in result.message


@pytest.mark.unit
def test_alias_command_invokes_matching_skill() -> None:
    """`/<alias>` should invoke snapshot skill by frontmatter command alias."""
    # Arrange - session with add skill aliased as sum
    runtime = RuntimeFacade()
    session = _make_session(
        skills=(
            _make_skill(
                "add",
                summary="Add two numbers",
                mode=InvocationMode.TOOL_DISPATCH,
                command_tool="add",
                command="sum",
            ),
        )
    )

    # Act - invoke via alias
    result = runtime.handle_input("/sum 2+2", session)

    # Assert - ok and tool result
    assert result.status.value == "ok"
    assert result.message == "4"


@pytest.mark.unit
def test_alias_collision_returns_deterministic_error() -> None:
    """Ambiguous alias across skills should fail without fallback."""
    # Arrange - two skills with same command alias go
    runtime = RuntimeFacade()
    session = _make_session(
        skills=(
            _make_skill(
                "add",
                mode=InvocationMode.TOOL_DISPATCH,
                command_tool="add",
                command="go",
            ),
            _make_skill("echo", command="go"),
        )
    )

    # Act - invoke ambiguous alias
    result = runtime.handle_input("/go payload", session)

    # Assert - error and ambiguous message
    assert result.status.value == "error"
    assert result.message == "Error: command alias '/go' is ambiguous in snapshot."


@pytest.mark.unit
def test_built_in_command_precedence_over_alias() -> None:
    """Built-in commands should win even if a skill defines same alias."""
    # Arrange - skill with command=skills; built-in also has /skills
    runtime = RuntimeFacade()
    session = _make_session(
        skills=(
            _make_skill("echo", command="skills"),
            _make_skill("alpha", summary="Alpha summary"),
        )
    )

    # Act - invoke /skills
    result = runtime.handle_input("/skills", session)

    # Assert - built-in wins, list shown
    assert result.status.value == "ok"
    assert result.message.splitlines() == [
        "alpha - Alpha summary",
        "echo",
    ]


@pytest.mark.unit
def test_runtime_records_turns_in_conversation_state() -> None:
    """Runtime should append user/assistant entries to session conversation state."""
    # Arrange - runtime and empty session
    runtime = RuntimeFacade()
    session = _make_session(skills=())

    # Act - run /skills
    result = runtime.handle_input("/skills", session)

    # Assert - ok and conversation state has user + assistant turn
    assert result.status.value == "ok"
    assert len(session.conversation_state) == 2
    assert session.conversation_state[0].role.value == "user"
    assert session.conversation_state[0].content == "/skills"
    assert session.conversation_state[1].role.value == "assistant"


@pytest.mark.unit
def test_persona_list_use_show_and_style_commands(tmp_path: Path) -> None:
    """Persona and style commands should be deterministic and session-scoped."""
    # Arrange - persona repo with lily, chad, barbie; runtime and session
    personas_dir = tmp_path / "personas"
    _write_persona(
        personas_dir,
        "lily",
        "Professional executive assistant",
        "focus",
    )
    _write_persona(personas_dir, "chad", "Beach bro", "playful")
    _write_persona(personas_dir, "barbie", "Valley girl", "playful")
    runtime = RuntimeFacade(
        persona_repository=FilePersonaRepository(root_dir=personas_dir)
    )
    session = _make_session(skills=())

    listed = runtime.handle_input("/persona list", session)
    assert listed.status.value == "ok"
    assert "* default" not in listed.message
    assert "lily - Professional executive assistant" in listed.message
    assert "chad - Beach bro" in listed.message
    assert "barbie - Valley girl" in listed.message

    # Act - persona use chad
    used = runtime.handle_input("/persona use chad", session)
    assert used.status.value == "ok"
    assert session.active_persona == "chad"
    assert session.active_agent == "default"
    assert session.active_style is None

    # Act - persona show
    shown = runtime.handle_input("/persona show", session)
    assert shown.status.value == "ok"
    assert "# Persona: chad" in shown.message
    assert "- `default_style`: playful" in shown.message
    assert "- `effective_style`: playful" in shown.message

    # Act - style focus
    styled = runtime.handle_input("/style focus", session)
    assert styled.status.value == "ok"
    assert session.active_style is not None
    assert session.active_style.value == "focus"

    # Assert - persona show reflects effective_style override
    shown_after_style = runtime.handle_input("/persona show", session)
    assert "- `effective_style`: focus" in shown_after_style.message

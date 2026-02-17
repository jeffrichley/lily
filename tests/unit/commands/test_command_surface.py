"""Unit tests for deterministic command surface behavior."""

from __future__ import annotations

from pathlib import Path

from lily.persona import FilePersonaRepository
from lily.runtime.conversation import ConversationRequest, ConversationResponse
from lily.runtime.facade import RuntimeFacade
from lily.session.factory import SessionFactory, SessionFactoryConfig
from lily.session.models import ModelConfig, Session
from lily.skills.types import InvocationMode, SkillEntry, SkillSnapshot, SkillSource


class _ConversationCaptureExecutor:
    """Conversation executor fixture that captures last request."""

    def __init__(self) -> None:
        """Initialize capture slots."""
        self.last_request: ConversationRequest | None = None

    def run(self, request: ConversationRequest) -> ConversationResponse:
        """Capture request and return deterministic reply."""
        self.last_request = request
        return ConversationResponse(text="ok")


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


def _make_skill(
    name: str,
    summary: str = "",
    *,
    mode: InvocationMode = InvocationMode.LLM_ORCHESTRATION,
    command_tool: str | None = None,
    command: str | None = None,
) -> SkillEntry:
    """Create a deterministic skill entry fixture.

    Args:
        name: Skill name.
        summary: Skill summary text.
        mode: Invocation mode for the skill fixture.
        command_tool: Optional tool name for tool_dispatch fixtures.
        command: Optional alias command exposed by the skill.

    Returns:
        Skill entry fixture.
    """
    return SkillEntry(
        name=name,
        source=SkillSource.BUNDLED,
        path=Path(f"/skills/{name}/SKILL.md"),
        summary=summary,
        invocation_mode=mode,
        command=command,
        command_tool=command_tool,
    )


def _write_persona(root: Path, name: str, summary: str, default_style: str) -> None:
    """Write one persona markdown fixture.

    Args:
        root: Persona directory root.
        name: Persona identifier and filename stem.
        summary: Persona summary.
        default_style: Persona default style value.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.md").write_text(
        (
            "---\n"
            f"id: {name}\n"
            f"summary: {summary}\n"
            f"default_style: {default_style}\n"
            "---\n"
            f"You are {name}.\n"
        ),
        encoding="utf-8",
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


def test_skill_command_tool_dispatch_executes_without_llm() -> None:
    """`/skill` should execute tool_dispatch skills deterministically."""
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

    result = runtime.handle_input("/skill add 2+2", session)

    assert result.status.value == "ok"
    assert result.message == "4"


def test_reload_skills_refreshes_current_session_snapshot(tmp_path: Path) -> None:
    """`/reload_skills` should update only current session snapshot contents."""
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
            "---\n"
            "# Add\n"
        ),
        encoding="utf-8",
    )

    result = runtime.handle_input("/reload_skills", session)

    assert result.status.value == "ok"
    assert "Reloaded skills for current session." in result.message
    assert [entry.name for entry in session.skill_snapshot.skills] == ["add", "echo"]


def test_reload_skills_rejects_arguments() -> None:
    """`/reload_skills` should reject unexpected arguments deterministically."""
    runtime = RuntimeFacade()
    session = _make_session(skills=())

    result = runtime.handle_input("/reload_skills now", session)

    assert result.status.value == "error"
    assert result.message == "Error: /reload_skills does not accept arguments."


def test_reload_skills_errors_without_snapshot_config() -> None:
    """`/reload_skills` should fail when session cannot rebuild snapshots."""
    runtime = RuntimeFacade()
    session = _make_session(skills=())

    result = runtime.handle_input("/reload_skills", session)

    assert result.status.value == "error"
    assert result.message == "Error: /reload_skills is unavailable for this session."


def test_help_requires_exactly_one_skill_name() -> None:
    """`/help` should require exactly one skill argument."""
    runtime = RuntimeFacade()
    session = _make_session(skills=())

    result = runtime.handle_input("/help", session)

    assert result.status.value == "error"
    assert result.message == "Error: /help requires exactly one skill name."


def test_help_fails_for_unknown_skill() -> None:
    """`/help <skill>` should fail clearly when skill is missing."""
    runtime = RuntimeFacade()
    session = _make_session(skills=(_make_skill("echo"),))

    result = runtime.handle_input("/help missing", session)

    assert result.status.value == "error"
    assert result.message == "Error: skill 'missing' not found in snapshot."


def test_help_returns_snapshot_metadata_without_execution() -> None:
    """`/help <skill>` should return deterministic snapshot metadata."""
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

    result = runtime.handle_input("/help add", session)

    assert result.status.value == "ok"
    assert "# /help add" in result.message
    assert "- `invocation_mode`: tool_dispatch" in result.message
    assert "- `command_tool`: add" in result.message


def test_alias_command_invokes_matching_skill() -> None:
    """`/<alias>` should invoke snapshot skill by frontmatter command alias."""
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

    result = runtime.handle_input("/sum 2+2", session)

    assert result.status.value == "ok"
    assert result.message == "4"


def test_alias_collision_returns_deterministic_error() -> None:
    """Ambiguous alias across skills should fail without fallback."""
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

    result = runtime.handle_input("/go payload", session)

    assert result.status.value == "error"
    assert result.message == "Error: command alias '/go' is ambiguous in snapshot."


def test_built_in_command_precedence_over_alias() -> None:
    """Built-in commands should win even if a skill defines same alias."""
    runtime = RuntimeFacade()
    session = _make_session(
        skills=(
            _make_skill("echo", command="skills"),
            _make_skill("alpha", summary="Alpha summary"),
        )
    )

    result = runtime.handle_input("/skills", session)

    assert result.status.value == "ok"
    assert result.message.splitlines() == [
        "alpha - Alpha summary",
        "echo",
    ]


def test_runtime_records_turns_in_conversation_state() -> None:
    """Runtime should append user/assistant entries to session conversation state."""
    runtime = RuntimeFacade()
    session = _make_session(skills=())

    result = runtime.handle_input("/skills", session)

    assert result.status.value == "ok"
    assert len(session.conversation_state) == 2
    assert session.conversation_state[0].role.value == "user"
    assert session.conversation_state[0].content == "/skills"
    assert session.conversation_state[1].role.value == "assistant"


def test_persona_list_use_show_and_style_commands(tmp_path: Path) -> None:
    """Persona and style commands should be deterministic and session-scoped."""
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

    used = runtime.handle_input("/persona use chad", session)
    assert used.status.value == "ok"
    assert session.active_agent == "chad"
    assert session.active_style is None

    shown = runtime.handle_input("/persona show", session)
    assert shown.status.value == "ok"
    assert "# Persona: chad" in shown.message
    assert "- `default_style`: playful" in shown.message
    assert "- `effective_style`: playful" in shown.message

    styled = runtime.handle_input("/style focus", session)
    assert styled.status.value == "ok"
    assert session.active_style is not None
    assert session.active_style.value == "focus"

    shown_after_style = runtime.handle_input("/persona show", session)
    assert "- `effective_style`: focus" in shown_after_style.message


def test_memory_commands_roundtrip(tmp_path: Path) -> None:
    """Remember/show/forget should roundtrip through personality memory store."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    personas_dir = tmp_path / "personas"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_persona(personas_dir, "lily", "Professional executive assistant", "focus")

    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"remember", "forget", "memory"},
        )
    )
    session = factory.create(active_agent="lily")
    runtime = RuntimeFacade(
        persona_repository=FilePersonaRepository(root_dir=personas_dir)
    )

    remember = runtime.handle_input("/remember favorite number is 42", session)
    assert remember.status.value == "ok"
    assert remember.code == "memory_saved"
    memory_id = remember.data["id"] if remember.data is not None else ""
    assert memory_id.startswith("mem_")

    shown = runtime.handle_input("/memory show", session)
    assert shown.status.value == "ok"
    assert "favorite number is 42" in shown.message

    forgot = runtime.handle_input(f"/forget {memory_id}", session)
    assert forgot.status.value == "ok"
    assert forgot.code == "memory_deleted"

    shown_after_forget = runtime.handle_input("/memory show", session)
    assert shown_after_forget.status.value == "ok"
    assert shown_after_forget.code == "memory_empty"


def test_reload_persona_refreshes_cache_for_current_session(tmp_path: Path) -> None:
    """`/reload_persona` should refresh repository cache and expose new personas."""
    personas_dir = tmp_path / "personas"
    _write_persona(personas_dir, "lily", "Executive assistant", "focus")
    repository = FilePersonaRepository(root_dir=personas_dir)
    runtime = RuntimeFacade(persona_repository=repository)
    session = _make_session(skills=())

    before = runtime.handle_input("/persona list", session)
    assert "chad" not in before.message

    _write_persona(personas_dir, "chad", "Beach bro", "playful")
    still_cached = runtime.handle_input("/persona list", session)
    assert "chad" not in still_cached.message

    reloaded = runtime.handle_input("/reload_persona", session)
    after = runtime.handle_input("/persona list", session)
    assert reloaded.status.value == "ok"
    assert reloaded.code == "persona_reloaded"
    assert "chad" in after.message


def test_persona_export_and_import_commands(tmp_path: Path) -> None:
    """`/persona export|import` should roundtrip persona markdown artifacts."""
    personas_dir = tmp_path / "personas"
    _write_persona(personas_dir, "lily", "Executive assistant", "focus")
    runtime = RuntimeFacade(
        persona_repository=FilePersonaRepository(root_dir=personas_dir)
    )
    session = _make_session(skills=())
    export_path = tmp_path / "exports" / "lily.md"

    exported = runtime.handle_input(f"/persona export lily {export_path}", session)
    assert exported.status.value == "ok"
    assert exported.code == "persona_exported"
    assert export_path.exists()

    incoming = tmp_path / "incoming" / "zen.md"
    incoming.parent.mkdir(parents=True, exist_ok=True)
    incoming.write_text(
        (
            "---\n"
            "id: zen\n"
            "summary: Calm helper\n"
            "default_style: balanced\n"
            "---\n"
            "You are zen.\n"
        ),
        encoding="utf-8",
    )
    imported = runtime.handle_input(f"/persona import {incoming}", session)
    assert imported.status.value == "ok"
    assert imported.code == "persona_imported"

    listed = runtime.handle_input("/persona list", session)
    assert "zen - Calm helper" in listed.message


def test_agent_commands_persona_backed_compatibility(tmp_path: Path) -> None:
    """`/agent` commands should use persona-backed compatibility behavior."""
    personas_dir = tmp_path / "personas"
    _write_persona(personas_dir, "lily", "Executive assistant", "focus")
    _write_persona(personas_dir, "chad", "Beach bro", "playful")
    runtime = RuntimeFacade(
        persona_repository=FilePersonaRepository(root_dir=personas_dir)
    )
    session = _make_session(skills=())

    listed = runtime.handle_input("/agent list", session)
    assert listed.status.value == "ok"
    assert listed.code == "agent_listed"

    used = runtime.handle_input("/agent use chad", session)
    assert used.status.value == "ok"
    assert used.code == "agent_set"
    assert session.active_agent == "chad"

    shown = runtime.handle_input("/agent show", session)
    assert shown.status.value == "ok"
    assert shown.code == "agent_shown"
    assert "Agent: chad" in shown.message


def test_context_aware_tone_adaptation_without_style_override(tmp_path: Path) -> None:
    """Conversation route should derive style from context when no explicit override."""
    personas_dir = tmp_path / "personas"
    _write_persona(personas_dir, "lily", "Executive assistant", "balanced")
    capture = _ConversationCaptureExecutor()
    runtime = RuntimeFacade(
        conversation_executor=capture,
        persona_repository=FilePersonaRepository(root_dir=personas_dir),
    )
    session = _make_session(skills=())
    session.active_agent = "lily"
    session.active_style = None

    result = runtime.handle_input("urgent: prod incident, fix now", session)

    assert result.status.value == "ok"
    assert capture.last_request is not None
    assert capture.last_request.persona_context.style_level.value == "focus"


def test_memory_command_family_long_short_and_evidence_paths(tmp_path: Path) -> None:
    """`/memory short|long|evidence` command family should route deterministically."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"remember", "forget", "memory"},
        )
    )
    session = factory.create(active_agent="lily")
    runtime = RuntimeFacade()

    remembered = runtime.handle_input("/remember favorite color is blue", session)
    assert remembered.status.value == "ok"

    long_show = runtime.handle_input(
        "/memory long show --domain user_profile favorite",
        session,
    )
    assert long_show.status.value == "ok"
    assert "favorite color is blue" in long_show.message

    short_show = runtime.handle_input("/memory short show", session)
    assert short_show.status.value == "ok"
    assert short_show.code == "memory_short_shown"

    evidence_show = runtime.handle_input("/memory evidence show", session)
    assert evidence_show.status.value == "ok"
    assert evidence_show.code == "memory_evidence_unavailable"

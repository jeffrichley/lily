"""Unit tests for deterministic command surface behavior."""

from __future__ import annotations

from pathlib import Path

from lily.memory import (
    ConsolidationBackend,
    MemoryWriteRequest,
    StoreBackedPersonalityMemoryRepository,
)
from lily.persona import FilePersonaRepository
from lily.runtime.conversation import ConversationRequest, ConversationResponse
from lily.runtime.facade import RuntimeFacade
from lily.session.factory import SessionFactory, SessionFactoryConfig
from lily.session.models import Message, MessageRole, ModelConfig, Session
from lily.skills.types import (
    InvocationMode,
    SkillCapabilitySpec,
    SkillDiagnostic,
    SkillEntry,
    SkillSnapshot,
    SkillSource,
)


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
    capabilities = SkillCapabilitySpec()
    if mode == InvocationMode.TOOL_DISPATCH and command_tool is not None:
        capabilities = SkillCapabilitySpec(declared_tools=(command_tool,))
    return SkillEntry(
        name=name,
        source=SkillSource.BUNDLED,
        path=Path(f"/skills/{name}/SKILL.md"),
        summary=summary,
        invocation_mode=mode,
        command=command,
        command_tool=command_tool,
        capabilities=capabilities,
        capabilities_declared=(mode == InvocationMode.TOOL_DISPATCH),
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


def test_skills_command_includes_diagnostics_section() -> None:
    """`/skills` should include snapshot diagnostics deterministically."""
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

    result = runtime.handle_input("/skills", session)

    assert result.status.value == "ok"
    assert "Diagnostics:" in result.message
    assert "- echo [malformed_frontmatter] Bad frontmatter" in result.message


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
            "capabilities:\n"
            "  declared_tools: [add]\n"
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


def test_conversation_request_includes_repository_backed_memory_summary(
    tmp_path: Path,
) -> None:
    """Conversation route should inject retrieved memory summary into request."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"remember", "memory"},
        )
    )
    session = factory.create(active_agent="lily")
    capture = _ConversationCaptureExecutor()
    runtime = RuntimeFacade(conversation_executor=capture)

    remembered = runtime.handle_input("/remember favorite number is 42", session)
    assert remembered.status.value == "ok"

    _ = runtime.handle_input("what is my favorite number?", session)

    assert capture.last_request is not None
    assert "favorite number is 42" in capture.last_request.memory_summary


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
    assert evidence_show.code == "memory_evidence_empty"


def test_memory_evidence_ingest_and_show_with_citations(tmp_path: Path) -> None:
    """`/memory evidence` should ingest local text and return cited hits."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    notes = tmp_path / "architecture_notes.txt"
    notes.write_text(
        (
            "Agent memory design should preserve canonical precedence.\n"
            "Evidence retrieval is non-canonical context for recall support.\n"
        ),
        encoding="utf-8",
    )
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"memory"},
        )
    )
    session = factory.create(active_agent="lily")
    runtime = RuntimeFacade()

    ingested = runtime.handle_input(f"/memory evidence ingest {notes}", session)
    shown = runtime.handle_input("/memory evidence show canonical precedence", session)

    assert ingested.status.value == "ok"
    assert ingested.code == "memory_evidence_ingested"
    assert shown.status.value == "ok"
    assert shown.code == "memory_evidence_listed"
    assert shown.data is not None
    assert shown.data.get("non_canonical") is True
    assert shown.data.get("canonical_precedence") == "structured_long_term"
    assert "architecture_notes.txt#chunk-" in shown.message


def test_memory_evidence_results_remain_non_canonical_vs_structured(
    tmp_path: Path,
) -> None:
    """Contradicting evidence should remain non-canonical versus structured memory."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    notes = tmp_path / "prefs.txt"
    notes.write_text(
        "User favorite color is red from an old transcript.",
        encoding="utf-8",
    )
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"remember", "memory"},
        )
    )
    session = factory.create(active_agent="lily")
    runtime = RuntimeFacade()

    _ = runtime.handle_input("/remember favorite color is blue", session)
    _ = runtime.handle_input(f"/memory evidence ingest {notes}", session)

    structured = runtime.handle_input(
        "/memory long show --domain user_profile favorite color",
        session,
    )
    evidence = runtime.handle_input("/memory evidence show favorite color", session)

    assert structured.status.value == "ok"
    assert "favorite color is blue" in structured.message
    assert evidence.status.value == "ok"
    assert evidence.data is not None
    assert evidence.data.get("non_canonical") is True
    assert evidence.data.get("canonical_precedence") == "structured_long_term"


def test_memory_long_show_domain_isolation(tmp_path: Path) -> None:
    """`/memory long show --domain` should isolate personality subdomains."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"memory"},
        )
    )
    session = factory.create(active_agent="lily")
    runtime = RuntimeFacade()

    store_file = workspace_dir.parent / "memory" / "langgraph_store.sqlite"
    repository = StoreBackedPersonalityMemoryRepository(store_file=store_file)
    repository.remember(
        MemoryWriteRequest(
            namespace="persona_core/workspace:workspace/persona:lily",
            content="Core directive only",
        )
    )
    repository.remember(
        MemoryWriteRequest(
            namespace="working_rules/workspace:workspace/persona:lily",
            content="Working rule only",
        )
    )
    repository.remember(
        MemoryWriteRequest(
            namespace="user_profile/workspace:workspace/persona:lily",
            content="Profile data only",
        )
    )

    core = runtime.handle_input("/memory long show --domain persona_core", session)
    rules = runtime.handle_input("/memory long show --domain working_rules", session)
    profile = runtime.handle_input("/memory long show --domain user_profile", session)

    assert core.status.value == "ok"
    assert "Core directive only" in core.message
    assert "Working rule only" not in core.message
    assert "Profile data only" not in core.message
    assert rules.status.value == "ok"
    assert "Working rule only" in rules.message
    assert "Core directive only" not in rules.message
    assert profile.status.value == "ok"
    assert "Profile data only" in profile.message
    assert "Core directive only" not in profile.message


def test_memory_long_tool_requires_opt_in_flag(tmp_path: Path) -> None:
    """Tool-backed memory command should fail when tooling flag is disabled."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"memory"},
        )
    )
    session = factory.create(active_agent="lily")
    runtime = RuntimeFacade(memory_tooling_enabled=False)

    result = runtime.handle_input("/memory long tool show favorite", session)

    assert result.status.value == "error"
    assert result.code == "memory_tooling_disabled"


def test_memory_long_tool_remember_enforces_policy_redline(tmp_path: Path) -> None:
    """Tool-backed remember should preserve deterministic policy-denied behavior."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"memory"},
        )
    )
    session = factory.create(active_agent="lily")
    runtime = RuntimeFacade(memory_tooling_enabled=True)

    result = runtime.handle_input(
        "/memory long tool remember --domain user_profile api_key=sk-123",
        session,
    )

    assert result.status.value == "error"
    assert result.code == "memory_policy_denied"


def test_memory_long_tool_show_uses_langmem_adapter_when_enabled(
    tmp_path: Path,
) -> None:
    """Explicit tool route should search via LangMem and keep stable envelope."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"memory"},
        )
    )
    session = factory.create(active_agent="lily")
    runtime = RuntimeFacade(memory_tooling_enabled=True)

    wrote = runtime.handle_input(
        "/memory long tool remember --domain user_profile favorite number is 42",
        session,
    )
    assert wrote.status.value == "ok"
    assert wrote.code == "memory_langmem_saved"

    shown = runtime.handle_input(
        "/memory long tool show --domain user_profile favorite",
        session,
    )

    assert shown.status.value == "ok"
    assert shown.code == "memory_langmem_listed"
    assert shown.data is not None
    assert shown.data.get("route") == "langmem_search_tool"
    assert "favorite number is 42" in shown.message


def test_memory_tooling_auto_apply_switches_standard_show_route(tmp_path: Path) -> None:
    """Auto-apply flag should route regular long-show through LangMem tooling."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"memory"},
        )
    )
    session = factory.create(active_agent="lily")
    runtime = RuntimeFacade(
        memory_tooling_enabled=True,
        memory_tooling_auto_apply=True,
    )

    wrote = runtime.handle_input(
        "/memory long tool remember --domain user_profile favorite color is blue",
        session,
    )
    assert wrote.status.value == "ok"

    shown = runtime.handle_input(
        "/memory long show --domain user_profile favorite", session
    )

    assert shown.status.value == "ok"
    assert shown.code == "memory_langmem_listed"
    assert shown.data is not None
    assert shown.data.get("route") == "langmem_search_tool"


def test_memory_long_consolidate_disabled_by_default(tmp_path: Path) -> None:
    """Consolidation command should fail deterministically when disabled."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"memory"},
        )
    )
    session = factory.create(active_agent="lily")
    runtime = RuntimeFacade(consolidation_enabled=False)

    result = runtime.handle_input("/memory long consolidate", session)

    assert result.status.value == "error"
    assert result.code == "memory_consolidation_disabled"


def test_memory_long_consolidate_rule_based_writes_candidates(tmp_path: Path) -> None:
    """Rule-based consolidation should infer and persist candidate memories."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"memory"},
        )
    )
    session = factory.create(active_agent="lily")
    session.conversation_state.append(
        Message(role=MessageRole.USER, content="My favorite number is 42")
    )
    runtime = RuntimeFacade(consolidation_enabled=True)

    consolidated = runtime.handle_input("/memory long consolidate", session)
    shown = runtime.handle_input(
        "/memory long show --domain user_profile favorite", session
    )

    assert consolidated.status.value == "ok"
    assert consolidated.code == "memory_consolidation_ran"
    assert shown.status.value == "ok"
    assert "favorite number is 42" in shown.message


def test_memory_long_consolidate_langmem_manager_backend(tmp_path: Path) -> None:
    """LangMem-manager consolidation backend should write deterministic memories."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"memory"},
        )
    )
    session = factory.create(active_agent="lily")
    session.conversation_state.append(
        Message(role=MessageRole.USER, content="My name is Jeff")
    )
    runtime = RuntimeFacade(
        consolidation_enabled=True,
        consolidation_backend=ConsolidationBackend.LANGMEM_MANAGER,
        memory_tooling_enabled=True,
    )

    consolidated = runtime.handle_input("/memory long consolidate", session)
    shown = runtime.handle_input(
        "/memory long tool show --domain user_profile name",
        session,
    )

    assert consolidated.status.value == "ok"
    assert consolidated.data is not None
    assert consolidated.data.get("backend") == "langmem_manager"
    assert shown.status.value == "ok"
    assert shown.code == "memory_langmem_listed"
    assert "name is Jeff" in shown.message


def test_memory_long_verify_updates_last_verified(tmp_path: Path) -> None:
    """`/memory long verify` should set verified status and last_verified timestamp."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"remember", "memory"},
        )
    )
    session = factory.create(active_agent="lily")
    runtime = RuntimeFacade()

    remembered = runtime.handle_input("/remember my favorite editor is vim", session)
    assert remembered.status.value == "ok"
    memory_id = str((remembered.data or {}).get("id", ""))

    verified = runtime.handle_input(f"/memory long verify {memory_id}", session)
    listed = runtime.handle_input(
        "/memory long show --domain user_profile --include-conflicted favorite",
        session,
    )

    assert verified.status.value == "ok"
    assert verified.code == "memory_verified"
    assert listed.status.value == "ok"
    assert listed.data is not None
    records = listed.data.get("records")
    assert isinstance(records, list)
    target = next((item for item in records if item.get("id") == memory_id), None)
    assert isinstance(target, dict)
    assert target.get("status") == "verified"
    assert target.get("last_verified")


def test_memory_long_show_excludes_conflicted_unless_requested(tmp_path: Path) -> None:
    """Conflicted records should be hidden by default and visible when requested."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"memory"},
        )
    )
    session = factory.create(active_agent="lily")
    runtime = RuntimeFacade(consolidation_enabled=True)
    session.conversation_state.append(
        Message(role=MessageRole.USER, content="My favorite color is green")
    )
    _ = runtime.handle_input("/memory long consolidate", session)
    session.conversation_state.append(
        Message(role=MessageRole.USER, content="My favorite color is blue")
    )
    _ = runtime.handle_input("/memory long consolidate", session)

    hidden = runtime.handle_input(
        "/memory long show --domain user_profile green",
        session,
    )
    visible = runtime.handle_input(
        "/memory long show --domain user_profile --include-conflicted green",
        session,
    )

    assert hidden.status.value == "ok"
    assert hidden.code == "memory_empty"
    assert visible.status.value == "ok"
    assert "favorite color is green" in visible.message


def test_scheduled_auto_consolidation_runs_on_interval(tmp_path: Path) -> None:
    """Scheduled auto consolidation should run on configured conversation interval."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"memory"},
        )
    )
    session = factory.create(active_agent="lily")
    session.conversation_state.append(
        Message(role=MessageRole.USER, content="My favorite movie is Inception")
    )
    runtime = RuntimeFacade(
        conversation_executor=_ConversationCaptureExecutor(),
        consolidation_enabled=True,
        consolidation_auto_run_every_n_turns=1,
    )

    _ = runtime.handle_input("hello there", session)
    shown = runtime.handle_input(
        "/memory long show --domain user_profile movie",
        session,
    )

    assert shown.status.value == "ok"
    assert "favorite movie is Inception" in shown.message

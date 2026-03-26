"""Unit tests for command surface stateful persona/agent/memory flows."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.agents import FileAgentRepository
from lily.memory import (
    ConsolidationBackend,
    MemoryWriteRequest,
    StoreBackedPersonalityMemoryRepository,
)
from lily.persona import FilePersonaRepository
from lily.runtime.facade import RuntimeFacade
from lily.session.factory import SessionFactory, SessionFactoryConfig
from lily.session.models import Message, MessageRole
from tests.unit.commands.command_surface_shared import (
    _ConversationCaptureExecutor,
    _make_session,
    _write_agent,
    _write_persona,
)


@pytest.mark.unit
def test_memory_commands_roundtrip(tmp_path: Path) -> None:
    """Remember/show/forget should roundtrip through personality memory store."""
    # Arrange - factory, session with lily, runtime with persona repo
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
    session = factory.create(active_agent="lily", active_persona="lily")
    runtime = RuntimeFacade(
        persona_repository=FilePersonaRepository(root_dir=personas_dir)
    )

    # Act - remember
    remember = runtime.handle_input("/remember favorite number is 42", session)
    assert remember.status.value == "ok"
    assert remember.code == "memory_saved"
    memory_id = remember.data["id"] if remember.data is not None else ""
    assert memory_id.startswith("mem_")

    # Act - memory show
    shown = runtime.handle_input("/memory show", session)
    assert shown.status.value == "ok"
    assert "favorite number is 42" in shown.message

    # Act - forget
    forgot = runtime.handle_input(f"/forget {memory_id}", session)
    assert forgot.status.value == "ok"
    assert forgot.code == "memory_deleted"

    # Assert - memory show is empty after forget
    shown_after_forget = runtime.handle_input("/memory show", session)
    assert shown_after_forget.status.value == "ok"
    assert shown_after_forget.code == "memory_empty"


@pytest.mark.unit
def test_reload_persona_refreshes_cache_for_current_session(tmp_path: Path) -> None:
    """`/reload_persona` should refresh repository cache and expose new personas."""
    # Arrange - repo with lily, runtime, session
    personas_dir = tmp_path / "personas"
    _write_persona(personas_dir, "lily", "Executive assistant", "focus")
    repository = FilePersonaRepository(root_dir=personas_dir)
    runtime = RuntimeFacade(persona_repository=repository)
    session = _make_session(skills=())

    before = runtime.handle_input("/persona list", session)
    assert "chad" not in before.message

    _write_persona(personas_dir, "chad", "Beach bro", "playful")
    # Act - list before reload (cached), then reload, then list after
    still_cached = runtime.handle_input("/persona list", session)
    assert "chad" not in still_cached.message

    reloaded = runtime.handle_input("/reload_persona", session)
    after = runtime.handle_input("/persona list", session)
    # Assert - reload ok and chad now visible
    assert reloaded.status.value == "ok"
    assert reloaded.code == "persona_reloaded"
    assert "chad" in after.message


@pytest.mark.unit
def test_persona_export_and_import_commands(tmp_path: Path) -> None:
    """`/persona export|import` should roundtrip persona markdown artifacts."""
    # Arrange - repo with lily, runtime, session, export path
    personas_dir = tmp_path / "personas"
    _write_persona(personas_dir, "lily", "Executive assistant", "focus")
    runtime = RuntimeFacade(
        persona_repository=FilePersonaRepository(root_dir=personas_dir)
    )
    session = _make_session(skills=())
    export_path = tmp_path / "exports" / "lily.md"

    # Act - export lily
    exported = runtime.handle_input(f"/persona export lily {export_path}", session)
    assert exported.status.value == "ok"
    assert exported.code == "persona_exported"
    assert export_path.exists()

    # Arrange - incoming zen persona file
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
    # Act - import zen
    imported = runtime.handle_input(f"/persona import {incoming}", session)
    assert imported.status.value == "ok"
    assert imported.code == "persona_imported"

    # Assert - zen appears in list
    listed = runtime.handle_input("/persona list", session)
    assert "zen - Calm helper" in listed.message


@pytest.mark.unit
def test_agent_commands_use_real_agent_repository(tmp_path: Path) -> None:
    """`/agent` commands should resolve from first-class agent repository."""
    # Arrange - separate persona/agent repositories, runtime, session
    personas_dir = tmp_path / "personas"
    agents_dir = tmp_path / "agents"
    _write_persona(personas_dir, "lily", "Executive assistant", "focus")
    _write_persona(personas_dir, "chad", "Beach bro", "playful")
    _write_agent(agents_dir, "ops", "Operational executor")
    _write_agent(agents_dir, "research", "Research executor")
    runtime = RuntimeFacade(
        persona_repository=FilePersonaRepository(root_dir=personas_dir),
        agent_repository=FileAgentRepository(root_dir=agents_dir),
    )
    session = _make_session(skills=())

    # Act - list and use real agent id
    listed = runtime.handle_input("/agent list", session)
    # Assert - list/use/show are backed by agent repository, not personas
    assert listed.status.value == "ok"
    assert listed.code == "agent_listed"
    assert "ops - Operational executor" in listed.message
    assert "chad" not in listed.message

    used = runtime.handle_input("/agent use ops", session)
    assert used.status.value == "ok"
    assert used.code == "agent_set"
    assert session.active_agent == "ops"
    assert session.active_persona == "default"

    shown = runtime.handle_input("/agent show", session)
    assert shown.status.value == "ok"
    assert shown.code == "agent_shown"
    assert "Agent: ops" in shown.message


@pytest.mark.unit
def test_agent_use_missing_returns_not_found_without_mutating_state(
    tmp_path: Path,
) -> None:
    """Missing `/agent use` target should return agent_not_found and keep state."""
    # Arrange - runtime with one known agent and session default state
    personas_dir = tmp_path / "personas"
    agents_dir = tmp_path / "agents"
    _write_persona(personas_dir, "lily", "Executive assistant", "focus")
    _write_agent(agents_dir, "ops", "Operational executor")
    runtime = RuntimeFacade(
        persona_repository=FilePersonaRepository(root_dir=personas_dir),
        agent_repository=FileAgentRepository(root_dir=agents_dir),
    )
    session = _make_session(skills=())
    session.active_persona = "lily"
    session.active_agent = "default"

    # Act - attempt switch to missing agent id
    result = runtime.handle_input("/agent use missing", session)

    # Assert - deterministic not-found code and unchanged session state
    assert result.status.value == "error"
    assert result.code == "agent_not_found"
    assert result.data == {"agent": "missing"}
    assert session.active_agent == "default"
    assert session.active_persona == "lily"


@pytest.mark.unit
def test_context_aware_tone_adaptation_without_style_override(tmp_path: Path) -> None:
    """Conversation route should derive style from context when no explicit override."""
    # Arrange - persona with default_style, runtime, session
    personas_dir = tmp_path / "personas"
    _write_persona(personas_dir, "lily", "Executive assistant", "balanced")
    capture = _ConversationCaptureExecutor()
    runtime = RuntimeFacade(
        conversation_executor=capture,
        persona_repository=FilePersonaRepository(root_dir=personas_dir),
    )
    session = _make_session(skills=())
    session.active_persona = "lily"
    session.active_style = None

    # Act - send message (no explicit style)
    result = runtime.handle_input("urgent: prod incident, fix now", session)

    # Assert - request gets focus style from context
    assert result.status.value == "ok"
    assert capture.last_request is not None
    assert capture.last_request.persona_context.style_level.value == "focus"


@pytest.mark.unit
def test_conversation_request_includes_repository_backed_memory_summary(
    tmp_path: Path,
) -> None:
    """Conversation route should inject retrieved memory summary into request."""
    # Arrange - factory, session with lily, capture executor, runtime
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
    session = factory.create(active_agent="lily", active_persona="lily")
    capture = _ConversationCaptureExecutor()
    runtime = RuntimeFacade(conversation_executor=capture)

    # Act - remember then send conversation message
    remembered = runtime.handle_input("/remember favorite number is 42", session)
    assert remembered.status.value == "ok"

    _ = runtime.handle_input("what is my favorite number?", session)

    # Assert - request includes memory summary
    assert capture.last_request is not None
    assert "favorite number is 42" in capture.last_request.memory_summary


@pytest.mark.unit
def test_memory_command_family_long_short_and_evidence_paths(tmp_path: Path) -> None:
    """`/memory short|long|evidence` command family should route deterministically."""
    # Arrange - factory, session with lily, runtime
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
    session = factory.create(active_agent="lily", active_persona="lily")
    runtime = RuntimeFacade()

    # Act - remember, then long show, short show, evidence show
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
    # Assert - each path returns expected code/message
    assert evidence_show.status.value == "ok"
    assert evidence_show.code == "memory_evidence_empty"


@pytest.mark.unit
def test_memory_evidence_ingest_and_show_with_citations(tmp_path: Path) -> None:
    """`/memory evidence` should ingest local text and return cited hits."""
    # Arrange - dirs, notes file, factory, session, runtime
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
    session = factory.create(active_agent="lily", active_persona="lily")
    runtime = RuntimeFacade()

    # Act - evidence ingest then show with query
    ingested = runtime.handle_input(f"/memory evidence ingest {notes}", session)
    shown = runtime.handle_input("/memory evidence show canonical precedence", session)

    # Assert - ingested ok, show returns non_canonical cited results
    assert ingested.status.value == "ok"
    assert ingested.code == "memory_evidence_ingested"
    assert shown.status.value == "ok"
    assert shown.code == "memory_evidence_listed"
    assert shown.data is not None
    assert shown.data.get("non_canonical") is True
    assert shown.data.get("canonical_precedence") == "structured_long_term"
    assert "architecture_notes.txt#chunk-" in shown.message


@pytest.mark.unit
def test_memory_evidence_results_remain_non_canonical_vs_structured(
    tmp_path: Path,
) -> None:
    """Contradicting evidence should remain non-canonical versus structured memory."""
    # Arrange - dirs, prefs notes, factory, session with remembered color, runtime
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
    session = factory.create(active_agent="lily", active_persona="lily")
    runtime = RuntimeFacade()

    # Act - remember blue, ingest evidence (red), then long show and evidence show
    _ = runtime.handle_input("/remember favorite color is blue", session)
    _ = runtime.handle_input(f"/memory evidence ingest {notes}", session)

    structured = runtime.handle_input(
        "/memory long show --domain user_profile favorite color",
        session,
    )
    evidence = runtime.handle_input("/memory evidence show favorite color", session)

    # Assert - structured shows blue; evidence stays non_canonical with precedence
    assert structured.status.value == "ok"
    assert "favorite color is blue" in structured.message
    assert evidence.status.value == "ok"
    assert evidence.data is not None
    assert evidence.data.get("non_canonical") is True
    assert evidence.data.get("canonical_precedence") == "structured_long_term"


@pytest.mark.unit
def test_memory_long_show_domain_isolation(tmp_path: Path) -> None:
    """`/memory long show --domain` should isolate personality subdomains."""
    # Arrange - factory, session, runtime, repo with memories in three domains
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
    session = factory.create(active_agent="lily", active_persona="lily")
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

    # Act - show each domain
    core = runtime.handle_input("/memory long show --domain persona_core", session)
    rules = runtime.handle_input("/memory long show --domain working_rules", session)
    profile = runtime.handle_input("/memory long show --domain user_profile", session)

    # Assert - each domain shows only its content
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


@pytest.mark.unit
def test_memory_long_tool_requires_opt_in_flag(tmp_path: Path) -> None:
    """Tool-backed memory command should fail when tooling flag is disabled."""
    # Arrange - factory, session, runtime with memory_tooling_enabled=False
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
    session = factory.create(active_agent="lily", active_persona="lily")
    runtime = RuntimeFacade(memory_tooling_enabled=False)

    # Act - invoke long tool show
    result = runtime.handle_input("/memory long tool show favorite", session)

    # Assert - error and tooling disabled code
    assert result.status.value == "error"
    assert result.code == "memory_tooling_disabled"


@pytest.mark.unit
def test_memory_long_tool_remember_enforces_policy_redline(tmp_path: Path) -> None:
    """Tool-backed remember should preserve deterministic policy-denied behavior."""
    # Arrange - factory, session, runtime with tooling enabled
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
    session = factory.create(active_agent="lily", active_persona="lily")
    runtime = RuntimeFacade(memory_tooling_enabled=True)

    # Act - remember policy-sensitive content (api_key)
    result = runtime.handle_input(
        "/memory long tool remember --domain user_profile api_key=sk-123",
        session,
    )

    # Assert - policy denied
    assert result.status.value == "error"
    assert result.code == "memory_policy_denied"


@pytest.mark.unit
def test_memory_long_tool_show_uses_langmem_adapter_when_enabled(
    tmp_path: Path,
) -> None:
    """Explicit tool route should search via LangMem and keep stable envelope."""
    # Arrange - factory, session, runtime with memory_tooling_enabled=True
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
    session = factory.create(active_agent="lily", active_persona="lily")
    runtime = RuntimeFacade(memory_tooling_enabled=True)

    # Act - remember then long tool show
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

    # Assert - show uses langmem route and returns content
    assert shown.status.value == "ok"
    assert shown.code == "memory_langmem_listed"
    assert shown.data is not None
    assert shown.data.get("route") == "langmem_search_tool"
    assert "favorite number is 42" in shown.message


@pytest.mark.unit
def test_memory_tooling_auto_apply_switches_standard_show_route(tmp_path: Path) -> None:
    """Auto-apply flag should route regular long-show through LangMem tooling."""
    # Arrange - factory, session, runtime with auto_apply True
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
    session = factory.create(active_agent="lily", active_persona="lily")
    runtime = RuntimeFacade(
        memory_tooling_enabled=True,
        memory_tooling_auto_apply=True,
    )

    # Act - remember then standard long show (no 'tool' in path)
    wrote = runtime.handle_input(
        "/memory long tool remember --domain user_profile favorite color is blue",
        session,
    )
    assert wrote.status.value == "ok"

    shown = runtime.handle_input(
        "/memory long show --domain user_profile favorite", session
    )

    # Assert - standard long show uses langmem route when auto_apply
    assert shown.status.value == "ok"
    assert shown.code == "memory_langmem_listed"
    assert shown.data is not None
    assert shown.data.get("route") == "langmem_search_tool"


@pytest.mark.unit
def test_memory_long_consolidate_disabled_by_default(tmp_path: Path) -> None:
    """Consolidation command should fail deterministically when disabled."""
    # Arrange - factory, session, runtime with consolidation_enabled=False
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
    session = factory.create(active_agent="lily", active_persona="lily")
    runtime = RuntimeFacade(consolidation_enabled=False)

    # Act - invoke consolidate
    result = runtime.handle_input("/memory long consolidate", session)

    # Assert - error and disabled code
    assert result.status.value == "error"
    assert result.code == "memory_consolidation_disabled"


@pytest.mark.unit
def test_memory_long_consolidate_rule_based_writes_candidates(tmp_path: Path) -> None:
    """Rule-based consolidation should infer and persist candidate memories."""
    # Arrange - factory, session with conversation state, runtime with consolidation on
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
    session = factory.create(active_agent="lily", active_persona="lily")
    session.conversation_state.append(
        Message(role=MessageRole.USER, content="My favorite number is 42")
    )
    runtime = RuntimeFacade(consolidation_enabled=True)

    # Act - consolidate then long show
    consolidated = runtime.handle_input("/memory long consolidate", session)
    shown = runtime.handle_input(
        "/memory long show --domain user_profile favorite", session
    )

    # Assert - consolidation ran and content appears in long show
    assert consolidated.status.value == "ok"
    assert consolidated.code == "memory_consolidation_ran"
    assert shown.status.value == "ok"
    assert "favorite number is 42" in shown.message


@pytest.mark.unit
def test_memory_long_consolidate_langmem_manager_backend(tmp_path: Path) -> None:
    """LangMem-manager consolidation backend should write deterministic memories."""
    # Arrange - factory, session with conversation, runtime with langmem consolidation
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
    session = factory.create(active_agent="lily", active_persona="lily")
    session.conversation_state.append(
        Message(role=MessageRole.USER, content="My name is Jeff")
    )
    runtime = RuntimeFacade(
        consolidation_enabled=True,
        consolidation_backend=ConsolidationBackend.LANGMEM_MANAGER,
        memory_tooling_enabled=True,
    )

    # Act - consolidate then long tool show
    consolidated = runtime.handle_input("/memory long consolidate", session)
    shown = runtime.handle_input(
        "/memory long tool show --domain user_profile name",
        session,
    )

    # Assert - backend langmem_manager and content in show
    assert consolidated.status.value == "ok"
    assert consolidated.data is not None
    assert consolidated.data.get("backend") == "langmem_manager"
    assert shown.status.value == "ok"
    assert shown.code == "memory_langmem_listed"
    assert "name is Jeff" in shown.message

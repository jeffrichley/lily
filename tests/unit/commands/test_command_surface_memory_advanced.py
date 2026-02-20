"""Unit tests for memory commands: verify, show conflicted, auto consolidate."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.facade import RuntimeFacade
from lily.session.factory import SessionFactory, SessionFactoryConfig
from lily.session.models import Message, MessageRole
from tests.unit.commands.command_surface_shared import _ConversationCaptureExecutor


@pytest.mark.unit
def test_memory_long_verify_updates_last_verified(tmp_path: Path) -> None:
    """`/memory long verify` should set verified status and last_verified timestamp."""
    # Arrange - factory, session, runtime; remember a fact to get memory id
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

    # Act - verify then list with include-conflicted
    verified = runtime.handle_input(f"/memory long verify {memory_id}", session)
    listed = runtime.handle_input(
        "/memory long show --domain user_profile --include-conflicted favorite",
        session,
    )

    # Assert - verified code and record has status/last_verified
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


@pytest.mark.unit
def test_memory_long_show_excludes_conflicted_unless_requested(tmp_path: Path) -> None:
    """Conflicted records should be hidden by default and visible when requested."""
    # Arrange - factory, session, runtime; create conflicted memories via consolidate
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

    # Act - show without then with --include-conflicted
    hidden = runtime.handle_input(
        "/memory long show --domain user_profile green",
        session,
    )
    visible = runtime.handle_input(
        "/memory long show --domain user_profile --include-conflicted green",
        session,
    )

    # Assert - default hides conflicted; flag exposes them
    assert hidden.status.value == "ok"
    assert hidden.code == "memory_empty"
    assert visible.status.value == "ok"
    assert "favorite color is green" in visible.message


@pytest.mark.unit
def test_scheduled_auto_consolidation_runs_on_interval(tmp_path: Path) -> None:
    """Scheduled auto consolidation should run on configured conversation interval."""
    # Arrange - factory, session with conversation state, runtime with auto every 1 turn
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

    # Act - send one turn to trigger auto consolidation
    _ = runtime.handle_input("hello there", session)
    shown = runtime.handle_input(
        "/memory long show --domain user_profile movie",
        session,
    )
    # Assert - consolidation ran and content in long show
    assert shown.status.value == "ok"
    assert "favorite movie is Inception" in shown.message

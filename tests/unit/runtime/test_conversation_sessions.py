"""Unit tests for SQLite-backed conversation session persistence."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from lily.runtime.conversation_sessions import (
    ConversationSessionStore,
    ConversationSessionStoreError,
    NoConversationSessionsError,
    UnknownConversationIdError,
    default_sessions_db_path,
)

pytestmark = pytest.mark.unit


def test_default_sessions_db_path_is_rooted_under_dot_lily(tmp_path: Path) -> None:
    """Resolves default DB path under `.lily/sessions.sqlite3`."""
    # Arrange - use a deterministic workspace root.
    # Act - resolve path from workspace root.
    resolved = default_sessions_db_path(tmp_path)

    # Assert - relative location remains local-first under .lily.
    assert resolved == tmp_path / ".lily" / "sessions.sqlite3"


def test_start_new_creates_session_and_sets_last_pointer(tmp_path: Path) -> None:
    """Creates a new session with deterministic metadata defaults."""
    # Arrange - initialize an empty session store.
    store = ConversationSessionStore(tmp_path / "sessions.sqlite3")

    # Act - create one new conversation id.
    conversation_id = store.start_new()
    snapshot = store.snapshot()

    # Assert - session exists and is marked as active last.
    assert snapshot.schema_version == 1
    assert snapshot.active_last_id == conversation_id
    assert len(snapshot.sessions) == 1
    assert snapshot.sessions[0].conversation_id == conversation_id
    assert snapshot.sessions[0].turn_count == 0


def test_attach_returns_existing_id_and_updates_last_pointer(tmp_path: Path) -> None:
    """Attaches to an existing session and records it as active last."""
    # Arrange - create two sessions so attach can point at a prior one.
    store = ConversationSessionStore(tmp_path / "sessions.sqlite3")
    first_id = store.start_new()
    second_id = store.start_new()

    # Act - attach explicitly to first session.
    attached = store.attach(first_id)
    snapshot = store.snapshot()

    # Assert - returned id and active pointer are updated to first session.
    assert attached == first_id
    assert snapshot.active_last_id == first_id
    assert second_id != first_id


def test_attach_unknown_conversation_id_raises(tmp_path: Path) -> None:
    """Fails deterministically when attach id does not exist."""
    # Arrange - initialize an empty store.
    store = ConversationSessionStore(tmp_path / "sessions.sqlite3")

    # Act - attempt to attach unknown id.
    with pytest.raises(UnknownConversationIdError) as err:
        store.attach("missing-id")

    # Assert - error message is deterministic.
    assert "Unknown conversation id for attach" in str(err.value)


def test_attach_last_without_prior_session_raises(tmp_path: Path) -> None:
    """Fails deterministically when no prior conversation exists."""
    # Arrange - initialize an empty store.
    store = ConversationSessionStore(tmp_path / "sessions.sqlite3")

    # Act - request attach-last from empty store.
    with pytest.raises(NoConversationSessionsError) as err:
        store.attach_last()

    # Assert - error message is deterministic.
    assert "No prior conversation" in str(err.value)


def test_attach_last_returns_most_recent_session(tmp_path: Path) -> None:
    """Returns active last id when sessions already exist."""
    # Arrange - create one session which becomes active last.
    store = ConversationSessionStore(tmp_path / "sessions.sqlite3")
    conversation_id = store.start_new()

    # Act - attach to last known session.
    attached = store.attach_last()

    # Assert - attached id matches persisted active last id.
    assert attached == conversation_id


def test_record_turn_increments_turn_count_and_updates_last(tmp_path: Path) -> None:
    """Updates metadata for an existing session turn record."""
    # Arrange - create two sessions so last pointer can move.
    store = ConversationSessionStore(tmp_path / "sessions.sqlite3")
    first_id = store.start_new()
    second_id = store.start_new()

    # Act - record turns against first session.
    store.record_turn(first_id, turns=2)
    snapshot = store.snapshot()
    first_record = next(
        record for record in snapshot.sessions if record.conversation_id == first_id
    )

    # Assert - turn count and last pointer both move to first session.
    assert first_record.turn_count == 2
    assert snapshot.active_last_id == first_id
    assert second_id != first_id


def test_record_turn_with_non_positive_turns_raises(tmp_path: Path) -> None:
    """Rejects non-positive turn increment values."""
    # Arrange - create one session.
    store = ConversationSessionStore(tmp_path / "sessions.sqlite3")
    conversation_id = store.start_new()

    # Act - record an invalid non-positive turn count.
    with pytest.raises(ConversationSessionStoreError) as err:
        store.record_turn(conversation_id, turns=0)

    # Assert - error message is deterministic.
    assert "must be greater than zero" in str(err.value)


def test_record_turn_unknown_conversation_id_raises(tmp_path: Path) -> None:
    """Rejects turn updates for unknown conversation ids."""
    # Arrange - initialize empty store.
    store = ConversationSessionStore(tmp_path / "sessions.sqlite3")

    # Act - update turns for unknown session id.
    with pytest.raises(UnknownConversationIdError) as err:
        store.record_turn("missing-id")

    # Assert - error message is deterministic.
    assert "unknown conversation id" in str(err.value).lower()


def test_schema_version_mismatch_raises_on_first_operation(tmp_path: Path) -> None:
    """Raises when existing DB metadata schema version differs."""
    # Arrange - create store then tamper schema version metadata.
    db_path = tmp_path / "sessions.sqlite3"
    store = ConversationSessionStore(db_path)
    store.start_new()

    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO metadata(key, value)
            VALUES('schema_version', '999')
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """
        )
        conn.commit()

    # Act - reopen store and execute first operation.
    reopened = ConversationSessionStore(db_path)
    with pytest.raises(ConversationSessionStoreError) as err:
        reopened.snapshot()

    # Assert - mismatch error is deterministic.
    assert "Unsupported conversation session schema version" in str(err.value)

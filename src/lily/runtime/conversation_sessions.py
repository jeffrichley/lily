"""SQLite-backed conversation session persistence for CLI/TUI attach and resume."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

_SCHEMA_VERSION = 1
_DEFAULT_DB_RELATIVE_PATH = Path(".lily") / "sessions.sqlite3"


class ConversationSessionStoreError(RuntimeError):
    """Raised when conversation session persistence operations fail."""


class UnknownConversationIdError(ConversationSessionStoreError):
    """Raised when attaching or updating an unknown conversation id."""


class NoConversationSessionsError(ConversationSessionStoreError):
    """Raised when no prior conversation exists for attach-last behavior."""


class ConversationSessionRecord(BaseModel):
    """Persisted metadata for one conversation session."""

    model_config = ConfigDict(frozen=True)

    conversation_id: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    updated_at: str = Field(min_length=1)
    turn_count: int = Field(ge=0)


class ConversationSessionsSnapshot(BaseModel):
    """Typed snapshot of persisted conversation session state."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = Field(ge=1)
    active_last_id: str | None
    sessions: list[ConversationSessionRecord]


def default_sessions_db_path(workspace_root: Path | None = None) -> Path:
    """Resolve the default local-first SQLite store path under `.lily/`.

    Args:
        workspace_root: Optional repository/workspace root path.

    Returns:
        Absolute or relative path to `.lily/sessions.sqlite3`.
    """
    if workspace_root is None:
        return _DEFAULT_DB_RELATIVE_PATH
    return workspace_root / _DEFAULT_DB_RELATIVE_PATH


def _utc_now_iso() -> str:
    """Return current timestamp in deterministic ISO-8601 UTC format.

    Returns:
        ISO timestamp string for the current UTC time.
    """
    return datetime.now(tz=UTC).isoformat()


class ConversationSessionStore:
    """Persistence wrapper for session create/attach/last operations."""

    def __init__(self, database_path: Path) -> None:
        """Initialize store with local SQLite path and parent directory.

        Args:
            database_path: SQLite database file path.
        """
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        """Open one SQLite connection for store operations.

        Returns:
            SQLite connection for this store database.
        """
        return sqlite3.connect(self._database_path)

    def _ensure_schema(self) -> None:
        """Create schema and enforce expected schema version.

        Raises:
            ConversationSessionStoreError: If existing schema version mismatches.
        """
        with closing(self._connect()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    conversation_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    turn_count INTEGER NOT NULL
                )
                """
            )

            schema_row = conn.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            if schema_row is None:
                conn.execute(
                    "INSERT INTO metadata(key, value) VALUES(?, ?)",
                    ("schema_version", str(_SCHEMA_VERSION)),
                )
                conn.commit()
                return

            actual_schema = int(schema_row[0])
            if actual_schema != _SCHEMA_VERSION:
                msg = (
                    "Unsupported conversation session schema version: "
                    f"expected {_SCHEMA_VERSION}, found {actual_schema}."
                )
                raise ConversationSessionStoreError(msg)
            conn.commit()

    def _set_last(self, conn: sqlite3.Connection, conversation_id: str) -> None:
        """Persist active last conversation id.

        Args:
            conn: Open SQLite connection.
            conversation_id: Conversation id to persist as active last.
        """
        conn.execute(
            """
            INSERT INTO metadata(key, value)
            VALUES('active_last_id', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (conversation_id,),
        )

    def _session_exists(
        self,
        conn: sqlite3.Connection,
        conversation_id: str,
    ) -> bool:
        """Check whether one conversation id exists.

        Args:
            conn: Open SQLite connection.
            conversation_id: Conversation id to look up.

        Returns:
            True when a matching session row exists, otherwise False.
        """
        row = conn.execute(
            "SELECT conversation_id FROM sessions WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        return row is not None

    def start_new(self) -> str:
        """Create a new conversation session id and set it as active last.

        Returns:
            Newly generated conversation id.
        """
        self._ensure_schema()
        conversation_id = str(uuid4())
        now_iso = _utc_now_iso()
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO sessions(
                    conversation_id, created_at, updated_at, turn_count
                )
                VALUES(?, ?, ?, 0)
                """,
                (conversation_id, now_iso, now_iso),
            )
            self._set_last(conn, conversation_id)
            conn.commit()
        return conversation_id

    def attach(self, conversation_id: str) -> str:
        """Attach to an existing conversation id and mark it as active last.

        Args:
            conversation_id: Explicit target conversation id.

        Returns:
            The same attached conversation id.

        Raises:
            UnknownConversationIdError: If the id does not exist in persistence.
        """
        self._ensure_schema()
        with closing(self._connect()) as conn:
            if not self._session_exists(conn, conversation_id):
                msg = (
                    "Unknown conversation id for attach: "
                    f"'{conversation_id}'. Start a new conversation first."
                )
                raise UnknownConversationIdError(msg)
            self._set_last(conn, conversation_id)
            conn.commit()
        return conversation_id

    def attach_last(self) -> str:
        """Attach to most recently active conversation id.

        Returns:
            Most-recently active conversation id.

        Raises:
            NoConversationSessionsError: If no prior session is stored.
            UnknownConversationIdError: If last id points to missing session row.
        """
        self._ensure_schema()
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT value FROM metadata WHERE key = 'active_last_id'"
            ).fetchone()
            if row is None:
                msg = "No prior conversation is available for --last-conversation."
                raise NoConversationSessionsError(msg)
            conversation_id = str(row[0])
            if not self._session_exists(conn, conversation_id):
                msg = (
                    "Stored last conversation id is missing from session records: "
                    f"'{conversation_id}'."
                )
                raise UnknownConversationIdError(msg)
            self._set_last(conn, conversation_id)
            conn.commit()
        return conversation_id

    def record_turn(self, conversation_id: str, turns: int = 1) -> None:
        """Increment turn metadata and update active-last pointer.

        Args:
            conversation_id: Conversation id to update.
            turns: Number of turns to add.

        Raises:
            ConversationSessionStoreError: If turns is not strictly positive.
            UnknownConversationIdError: If the conversation id is missing.
        """
        self._ensure_schema()
        if turns <= 0:
            msg = "record_turn 'turns' must be greater than zero."
            raise ConversationSessionStoreError(msg)

        now_iso = _utc_now_iso()
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                """
                UPDATE sessions
                SET turn_count = turn_count + ?, updated_at = ?
                WHERE conversation_id = ?
                """,
                (turns, now_iso, conversation_id),
            )
            if cursor.rowcount != 1:
                msg = (
                    "Cannot record turn for unknown conversation id: "
                    f"'{conversation_id}'."
                )
                raise UnknownConversationIdError(msg)
            self._set_last(conn, conversation_id)
            conn.commit()

    def snapshot(self) -> ConversationSessionsSnapshot:
        """Return a typed snapshot of persisted session state.

        Returns:
            In-memory typed snapshot of schema version, last id, and sessions.
        """
        self._ensure_schema()
        with closing(self._connect()) as conn:
            schema_row = conn.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            last_row = conn.execute(
                "SELECT value FROM metadata WHERE key = 'active_last_id'"
            ).fetchone()
            rows = conn.execute(
                """
                SELECT conversation_id, created_at, updated_at, turn_count
                FROM sessions
                ORDER BY created_at ASC
                """
            ).fetchall()

        session_records = [
            ConversationSessionRecord(
                conversation_id=str(row[0]),
                created_at=str(row[1]),
                updated_at=str(row[2]),
                turn_count=int(row[3]),
            )
            for row in rows
        ]
        return ConversationSessionsSnapshot(
            schema_version=int(schema_row[0]) if schema_row is not None else 0,
            active_last_id=str(last_row[0]) if last_row is not None else None,
            sessions=session_records,
        )

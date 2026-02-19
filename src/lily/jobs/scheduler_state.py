"""Durable scheduler state storage for J3 lifecycle controls."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path


class JobScheduleState(StrEnum):
    """Durable lifecycle state for one scheduled job."""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


@dataclass(frozen=True)
class StoredJobScheduleState:
    """Stored state row for one job."""

    job_id: str
    state: JobScheduleState
    spec_hash: str
    updated_at: str


class SchedulerStateStore:
    """SQLite-backed store for scheduler lifecycle and spec hash state."""

    def __init__(self, sqlite_path: Path) -> None:
        """Create store and ensure required schema exists.

        Args:
            sqlite_path: SQLite file path for scheduler state.
        """
        self._sqlite_path = sqlite_path
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def get(self, job_id: str) -> StoredJobScheduleState | None:
        """Read one stored state row by job id.

        Args:
            job_id: Target job id.

        Returns:
            Stored state row when present, otherwise ``None``.
        """
        with closing(self._connect()) as conn:
            row = conn.execute(
                (
                    "SELECT job_id, state, spec_hash, updated_at "
                    "FROM lily_job_schedule_state "
                    "WHERE job_id = ?"
                ),
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return StoredJobScheduleState(
            job_id=str(row[0]),
            state=JobScheduleState(str(row[1])),
            spec_hash=str(row[2]),
            updated_at=str(row[3]),
        )

    def upsert(
        self,
        *,
        job_id: str,
        state: JobScheduleState,
        spec_hash: str,
    ) -> StoredJobScheduleState:
        """Insert or update one job state row.

        Args:
            job_id: Target job id.
            state: Lifecycle state to persist.
            spec_hash: Deterministic job spec hash.

        Returns:
            Persisted state row.
        """
        updated_at = _utc_now()
        with closing(self._connect()) as conn:
            conn.execute(
                (
                    "INSERT INTO lily_job_schedule_state "
                    "(job_id, state, spec_hash, updated_at) "
                    "VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(job_id) DO UPDATE SET "
                    "state = excluded.state, "
                    "spec_hash = excluded.spec_hash, "
                    "updated_at = excluded.updated_at"
                ),
                (job_id, state.value, spec_hash, updated_at),
            )
            conn.commit()
        return StoredJobScheduleState(
            job_id=job_id,
            state=state,
            spec_hash=spec_hash,
            updated_at=updated_at,
        )

    def list_all(self) -> tuple[StoredJobScheduleState, ...]:
        """List all stored scheduler state rows ordered by job id.

        Returns:
            Deterministically ordered state rows.
        """
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT job_id, state, spec_hash, updated_at "
                "FROM lily_job_schedule_state "
                "ORDER BY job_id"
            ).fetchall()
        return tuple(
            StoredJobScheduleState(
                job_id=str(row[0]),
                state=JobScheduleState(str(row[1])),
                spec_hash=str(row[2]),
                updated_at=str(row[3]),
            )
            for row in rows
        )

    def _initialize(self) -> None:
        """Create required scheduler state schema if missing."""
        with closing(self._connect()) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS lily_job_schedule_state ("
                "job_id TEXT PRIMARY KEY,"
                "state TEXT NOT NULL,"
                "spec_hash TEXT NOT NULL,"
                "updated_at TEXT NOT NULL"
                ")"
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        """Create sqlite connection with defensive pragmas.

        Returns:
            SQLite connection.
        """
        conn = sqlite3.connect(self._sqlite_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn


def _utc_now() -> str:
    """Return UTC timestamp in stable RFC3339-like format.

    Returns:
        UTC timestamp string.
    """
    return (
        datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )

"""Unit tests for checkpointer backend construction."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from langgraph.checkpoint.base import empty_checkpoint
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from lily.config import CheckpointerBackend, CheckpointerSettings
from lily.runtime.checkpointing import CheckpointerBuildError, build_checkpointer


@pytest.mark.unit
def test_build_checkpointer_memory_backend() -> None:
    """Memory backend should construct in-memory saver with no sqlite path."""
    result = build_checkpointer(
        CheckpointerSettings(backend=CheckpointerBackend.MEMORY)
    )

    assert isinstance(result.saver, InMemorySaver)
    assert result.resolved_sqlite_path is None


@pytest.mark.unit
def test_build_checkpointer_sqlite_creates_file(tmp_path: Path) -> None:
    """SQLite backend should create resolved file path and saver."""
    sqlite_path = tmp_path / "checkpoints" / "phase1.sqlite"
    result = build_checkpointer(
        CheckpointerSettings(
            backend=CheckpointerBackend.SQLITE,
            sqlite_path=str(sqlite_path),
        )
    )

    assert isinstance(result.saver, SqliteSaver)
    assert result.resolved_sqlite_path == sqlite_path
    assert sqlite_path.exists()
    result.saver.conn.close()


@pytest.mark.unit
def test_sqlite_checkpointer_persists_history_and_replay_across_restart(
    tmp_path: Path,
) -> None:
    """SQLite saver should preserve checkpoints across new saver instances."""
    sqlite_path = tmp_path / "checkpoints" / "restart.sqlite"
    settings = CheckpointerSettings(
        backend=CheckpointerBackend.SQLITE,
        sqlite_path=str(sqlite_path),
    )

    first = build_checkpointer(settings)
    saver_one = cast(SqliteSaver, first.saver)
    config = {"configurable": {"thread_id": "session-1", "checkpoint_ns": ""}}

    first_result = saver_one.put(
        config,
        empty_checkpoint(),
        {"source": "unit", "step": 1, "writes": {}, "parents": {}},
        {},
    )
    saver_one.put(
        config,
        empty_checkpoint(),
        {"source": "unit", "step": 2, "writes": {}, "parents": {}},
        {},
    )
    saver_one.conn.close()

    second = build_checkpointer(settings)
    saver_two = cast(SqliteSaver, second.saver)
    latest = saver_two.get_tuple(config)
    assert latest is not None

    history = list(saver_two.list(config))
    assert len(history) == 2

    replay = saver_two.get_tuple(
        {
            "configurable": {
                "thread_id": "session-1",
                "checkpoint_ns": "",
                "checkpoint_id": first_result["configurable"]["checkpoint_id"],
            }
        }
    )
    assert replay is not None
    saver_two.conn.close()


@pytest.mark.unit
def test_build_checkpointer_postgres_contract_errors_until_implemented() -> None:
    """Postgres backend should fail with explicit deterministic message for now."""
    try:
        build_checkpointer(
            CheckpointerSettings(
                backend=CheckpointerBackend.POSTGRES,
                postgres_dsn="postgresql://user:pass@localhost/lily",
            )
        )
    except CheckpointerBuildError as exc:
        assert "not implemented" in str(exc)
        assert "Supported backends: sqlite, memory" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected CheckpointerBuildError")

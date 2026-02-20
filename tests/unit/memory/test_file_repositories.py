"""Unit tests for file-backed split memory repositories."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from lily.memory import (
    FileBackedPersonalityMemoryRepository,
    FileBackedTaskMemoryRepository,
    MemoryError,
    MemoryErrorCode,
    MemoryQuery,
    MemoryWriteRequest,
)


def _personality_repo(tmp_path: Path) -> FileBackedPersonalityMemoryRepository:
    """Create personality repo fixture."""
    return FileBackedPersonalityMemoryRepository(root_dir=tmp_path / "memory")


def _task_repo(tmp_path: Path) -> FileBackedTaskMemoryRepository:
    """Create task repo fixture."""
    return FileBackedTaskMemoryRepository(root_dir=tmp_path / "memory")


@pytest.mark.unit
def test_personality_memory_roundtrip_and_dedup(tmp_path: Path) -> None:
    """Personality repository should upsert duplicate namespace/content writes."""
    repo = _personality_repo(tmp_path)

    first = repo.remember(
        MemoryWriteRequest(namespace="global", content="User prefers concise replies.")
    )
    second = repo.remember(
        MemoryWriteRequest(namespace="global", content="User prefers concise replies.")
    )
    results = repo.query(MemoryQuery(query="concise", namespace="global"))

    assert first.id == second.id
    assert len(results) == 1
    assert results[0].store.value == "personality_memory"


@pytest.mark.unit
def test_task_memory_requires_namespace_for_query(tmp_path: Path) -> None:
    """Task queries should fail deterministically when namespace is absent."""
    repo = _task_repo(tmp_path)
    repo.remember(MemoryWriteRequest(namespace="task-1", content="Finish phase 3."))

    try:
        repo.query(MemoryQuery(query="phase"))
    except MemoryError as exc:
        assert exc.code == MemoryErrorCode.NAMESPACE_REQUIRED
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected MemoryError")


@pytest.mark.unit
def test_no_cross_store_leakage_between_personality_and_task(tmp_path: Path) -> None:
    """Split stores should not leak records across repository boundaries."""
    personality = _personality_repo(tmp_path)
    task = _task_repo(tmp_path)

    personality.remember(
        MemoryWriteRequest(
            namespace="global", content="Favorite color is dark royal purple."
        )
    )
    task.remember(
        MemoryWriteRequest(
            namespace="task-42", content="Favorite color is dark royal purple."
        )
    )

    personality_hits = personality.query(
        MemoryQuery(query="favorite", namespace="global")
    )
    task_hits = task.query(MemoryQuery(query="favorite", namespace="task-42"))

    assert len(personality_hits) == 1
    assert personality_hits[0].store.value == "personality_memory"
    assert len(task_hits) == 1
    assert task_hits[0].store.value == "task_memory"


@pytest.mark.unit
def test_forget_missing_id_returns_deterministic_not_found(tmp_path: Path) -> None:
    """Forget should emit stable not-found memory error."""
    repo = _personality_repo(tmp_path)

    try:
        repo.forget("mem_missing")
    except MemoryError as exc:
        assert exc.code == MemoryErrorCode.NOT_FOUND
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected MemoryError")


@pytest.mark.unit
def test_invalid_store_payload_returns_schema_mismatch(tmp_path: Path) -> None:
    """Invalid JSON structure should map to deterministic schema mismatch error."""
    root = tmp_path / "memory"
    root.mkdir(parents=True, exist_ok=True)
    (root / "personality_memory.json").write_text('{"not":"a list"}', encoding="utf-8")
    repo = FileBackedPersonalityMemoryRepository(root_dir=root)

    try:
        repo.query(MemoryQuery(query="anything", namespace="global"))
    except MemoryError as exc:
        assert exc.code == MemoryErrorCode.SCHEMA_MISMATCH
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected MemoryError")


@pytest.mark.unit
def test_memory_policy_denied_blocks_sensitive_writes(tmp_path: Path) -> None:
    """Memory writes should fail deterministically for sensitive content."""
    repo = _personality_repo(tmp_path)

    try:
        repo.remember(MemoryWriteRequest(namespace="global", content="api_key=sk-123"))
    except MemoryError as exc:
        assert exc.code == MemoryErrorCode.POLICY_DENIED
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected MemoryError")


@pytest.mark.unit
def test_query_excludes_archived_conflicted_and_expired_by_default(
    tmp_path: Path,
) -> None:
    """Default query should hide archived/conflicted/expired records."""
    repo = _personality_repo(tmp_path)
    now = datetime.now(UTC)
    repo.remember(
        MemoryWriteRequest(
            namespace="global",
            content="active preference",
            status="verified",
        )
    )
    repo.remember(
        MemoryWriteRequest(
            namespace="global",
            content="archived preference",
            status="archived",
        )
    )
    repo.remember(
        MemoryWriteRequest(
            namespace="global",
            content="conflicted preference",
            status="conflicted",
        )
    )
    repo.remember(
        MemoryWriteRequest(
            namespace="global",
            content="expired preference",
            status="verified",
            expires_at=now - timedelta(days=1),
        )
    )

    visible = repo.query(MemoryQuery(query="*", namespace="global", limit=20))
    all_rows = repo.query(
        MemoryQuery(
            query="*",
            namespace="global",
            limit=20,
            include_archived=True,
            include_conflicted=True,
            include_expired=True,
        )
    )

    visible_contents = {row.content for row in visible}
    all_contents = {row.content for row in all_rows}
    assert visible_contents == {"active preference"}
    assert {
        "active preference",
        "archived preference",
        "conflicted preference",
        "expired preference",
    } <= all_contents

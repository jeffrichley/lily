"""Unit tests for LangGraph Store-backed memory repositories."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from lily.memory import (
    FileBackedPersonalityMemoryRepository,
    MemoryError,
    MemoryErrorCode,
    MemoryQuery,
    MemoryWriteRequest,
    StoreBackedPersonalityMemoryRepository,
    StoreBackedTaskMemoryRepository,
    store_repository,
)


@pytest.mark.unit
def test_store_personality_roundtrip_matches_file_behavior(tmp_path: Path) -> None:
    """Store-backed personality repo should match file-backed roundtrip semantics."""
    # Arrange - store and file repos
    store_repo = StoreBackedPersonalityMemoryRepository(
        store_file=tmp_path / "memory" / "store.sqlite"
    )
    file_repo = FileBackedPersonalityMemoryRepository(root_dir=tmp_path / "memory-file")

    # Act - remember same content twice in each, then query
    store_first = store_repo.remember(
        MemoryWriteRequest(namespace="user_profile:lily", content="User likes concise")
    )
    store_second = store_repo.remember(
        MemoryWriteRequest(namespace="user_profile:lily", content="User likes concise")
    )
    file_first = file_repo.remember(
        MemoryWriteRequest(namespace="user_profile:lily", content="User likes concise")
    )
    file_second = file_repo.remember(
        MemoryWriteRequest(namespace="user_profile:lily", content="User likes concise")
    )

    # Assert - dedup ids match and query returns same content
    assert store_first.id == store_second.id
    assert file_first.id == file_second.id

    store_results = store_repo.query(
        MemoryQuery(query="concise", namespace="user_profile:lily")
    )
    file_results = file_repo.query(
        MemoryQuery(query="concise", namespace="user_profile:lily")
    )
    # Assert - dedup and single hit in both; content matches
    assert len(store_results) == len(file_results) == 1
    assert store_results[0].content == file_results[0].content


@pytest.mark.unit
def test_store_task_repo_requires_namespace(tmp_path: Path) -> None:
    """Store-backed task repo should enforce required namespace query contract."""
    # Arrange - repo with one record
    repo = StoreBackedTaskMemoryRepository(
        store_file=tmp_path / "memory" / "store.sqlite"
    )
    repo.remember(MemoryWriteRequest(namespace="task-1", content="Finish phase 2"))

    # Act - query without namespace
    try:
        repo.query(MemoryQuery(query="phase"))
    except MemoryError as exc:
        # Assert - NAMESPACE_REQUIRED
        assert exc.code == MemoryErrorCode.NAMESPACE_REQUIRED
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected MemoryError")


@pytest.mark.unit
def test_store_forget_missing_returns_not_found(tmp_path: Path) -> None:
    """Store-backed forget should keep deterministic missing-id contract."""
    # Arrange - repo
    repo = StoreBackedPersonalityMemoryRepository(
        store_file=tmp_path / "memory" / "store.sqlite"
    )

    # Act - forget non-existent id
    try:
        repo.forget("mem_missing")
    except MemoryError as exc:
        # Assert - NOT_FOUND
        assert exc.code == MemoryErrorCode.NOT_FOUND
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected MemoryError")


@pytest.mark.unit
def test_store_policy_denied_matches_file_behavior(tmp_path: Path) -> None:
    """Store-backed writes should enforce same memory policy denial contract."""
    # Arrange - store and file repos
    store_repo = StoreBackedPersonalityMemoryRepository(
        store_file=tmp_path / "memory" / "store.sqlite"
    )
    file_repo = FileBackedPersonalityMemoryRepository(root_dir=tmp_path / "memory-file")

    # Act - remember sensitive content in each
    for repo in (store_repo, file_repo):
        try:
            repo.remember(
                MemoryWriteRequest(
                    namespace="user_profile:lily",
                    content="api_key=sk-123",
                )
            )
        except MemoryError as exc:
            # Assert - POLICY_DENIED
            assert exc.code == MemoryErrorCode.POLICY_DENIED
        else:  # pragma: no cover - defensive assertion
            raise AssertionError("Expected MemoryError")


@pytest.mark.unit
def test_store_query_and_forget_paginate_across_large_namespace_set(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Query/forget should traverse full dataset beyond one backend page."""
    # Arrange - small page sizes, repo, write 7 records
    monkeypatch.setattr(store_repository, "_SEARCH_PAGE_SIZE", 2)
    monkeypatch.setattr(store_repository, "_NAMESPACE_PAGE_SIZE", 1)
    repo = StoreBackedPersonalityMemoryRepository(
        store_file=tmp_path / "memory" / "store.sqlite"
    )

    target_id = ""
    for index in range(7):
        record = repo.remember(
            MemoryWriteRequest(
                namespace=f"user_profile/lane-{index % 3}/persona:lily",
                content=f"Fact {index}",
            )
        )
        if index == 6:
            target_id = record.id

    # Act - query all, forget one, query again
    matches = repo.query(MemoryQuery(query="Fact", limit=20))
    repo.forget(target_id)
    after = repo.query(MemoryQuery(query="Fact", limit=20))

    # Assert - 7 then 6, target_id gone
    assert len(matches) == 7
    assert len(after) == 6
    assert all(record.id != target_id for record in after)


@pytest.mark.unit
def test_store_query_excludes_archived_conflicted_and_expired_by_default(
    tmp_path: Path,
) -> None:
    """Store query should hide archived/conflicted/expired by default."""
    # Arrange - repo with verified, archived, conflicted, expired records
    repo = StoreBackedPersonalityMemoryRepository(
        store_file=tmp_path / "memory" / "store.sqlite"
    )
    now = datetime.now(UTC)
    repo.remember(
        MemoryWriteRequest(
            namespace="user_profile/workspace:workspace/persona:lily",
            content="active preference",
            status="verified",
        )
    )
    repo.remember(
        MemoryWriteRequest(
            namespace="user_profile/workspace:workspace/persona:lily",
            content="archived preference",
            status="archived",
        )
    )
    repo.remember(
        MemoryWriteRequest(
            namespace="user_profile/workspace:workspace/persona:lily",
            content="conflicted preference",
            status="conflicted",
        )
    )
    repo.remember(
        MemoryWriteRequest(
            namespace="user_profile/workspace:workspace/persona:lily",
            content="expired preference",
            status="verified",
            expires_at=now - timedelta(days=1),
        )
    )

    # Act - default query then query with include flags
    visible = repo.query(
        MemoryQuery(
            query="*",
            namespace="user_profile/workspace:workspace/persona:lily",
            limit=20,
        )
    )
    all_rows = repo.query(
        MemoryQuery(
            query="*",
            namespace="user_profile/workspace:workspace/persona:lily",
            limit=20,
            include_archived=True,
            include_conflicted=True,
            include_expired=True,
        )
    )

    # Assert - default hides archived/conflicted/expired; include flags expose all
    assert {row.content for row in visible} == {"active preference"}
    assert {
        "active preference",
        "archived preference",
        "conflicted preference",
        "expired preference",
    } <= {row.content for row in all_rows}

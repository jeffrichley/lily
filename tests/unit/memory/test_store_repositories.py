"""Unit tests for LangGraph Store-backed memory repositories."""

from __future__ import annotations

from pathlib import Path

from lily.memory import (
    FileBackedPersonalityMemoryRepository,
    MemoryError,
    MemoryErrorCode,
    MemoryQuery,
    MemoryWriteRequest,
    StoreBackedPersonalityMemoryRepository,
    StoreBackedTaskMemoryRepository,
)


def test_store_personality_roundtrip_matches_file_behavior(tmp_path: Path) -> None:
    """Store-backed personality repo should match file-backed roundtrip semantics."""
    store_repo = StoreBackedPersonalityMemoryRepository(
        store_file=tmp_path / "memory" / "store.sqlite"
    )
    file_repo = FileBackedPersonalityMemoryRepository(root_dir=tmp_path / "memory-file")

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

    assert store_first.id == store_second.id
    assert file_first.id == file_second.id

    store_results = store_repo.query(
        MemoryQuery(query="concise", namespace="user_profile:lily")
    )
    file_results = file_repo.query(
        MemoryQuery(query="concise", namespace="user_profile:lily")
    )
    assert len(store_results) == len(file_results) == 1
    assert store_results[0].content == file_results[0].content


def test_store_task_repo_requires_namespace(tmp_path: Path) -> None:
    """Store-backed task repo should enforce required namespace query contract."""
    repo = StoreBackedTaskMemoryRepository(
        store_file=tmp_path / "memory" / "store.sqlite"
    )
    repo.remember(MemoryWriteRequest(namespace="task-1", content="Finish phase 2"))

    try:
        repo.query(MemoryQuery(query="phase"))
    except MemoryError as exc:
        assert exc.code == MemoryErrorCode.NAMESPACE_REQUIRED
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected MemoryError")


def test_store_forget_missing_returns_not_found(tmp_path: Path) -> None:
    """Store-backed forget should keep deterministic missing-id contract."""
    repo = StoreBackedPersonalityMemoryRepository(
        store_file=tmp_path / "memory" / "store.sqlite"
    )

    try:
        repo.forget("mem_missing")
    except MemoryError as exc:
        assert exc.code == MemoryErrorCode.NOT_FOUND
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected MemoryError")


def test_store_policy_denied_matches_file_behavior(tmp_path: Path) -> None:
    """Store-backed writes should enforce same memory policy denial contract."""
    store_repo = StoreBackedPersonalityMemoryRepository(
        store_file=tmp_path / "memory" / "store.sqlite"
    )
    file_repo = FileBackedPersonalityMemoryRepository(root_dir=tmp_path / "memory-file")

    for repo in (store_repo, file_repo):
        try:
            repo.remember(
                MemoryWriteRequest(
                    namespace="user_profile:lily",
                    content="api_key=sk-123",
                )
            )
        except MemoryError as exc:
            assert exc.code == MemoryErrorCode.POLICY_DENIED
        else:  # pragma: no cover - defensive assertion
            raise AssertionError("Expected MemoryError")

"""Unit tests for prompt-memory retrieval and ranking behavior."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lily.memory import (
    MemoryQuery,
    MemoryRecord,
    MemoryStore,
    PromptMemoryRetrievalService,
    RetrievalPolicy,
)


class _PersonalityRepo:
    """Test repository fixture for personality memory."""

    def __init__(self, rows: dict[str, tuple[MemoryRecord, ...]]) -> None:
        """Store rows by namespace.

        Args:
            rows: Namespace to records mapping.
        """
        self._rows = rows

    def remember(self, request: object) -> MemoryRecord:
        """Unused protocol method for this fixture."""
        raise NotImplementedError

    def forget(self, memory_id: str) -> None:
        """Unused protocol method for this fixture."""
        del memory_id
        raise NotImplementedError

    def query(self, query: MemoryQuery) -> tuple[MemoryRecord, ...]:
        """Return records for namespace with confidence filter support.

        Args:
            query: Query payload.

        Returns:
            Matching records tuple.
        """
        rows = list(self._rows.get(query.namespace or "", ()))
        if query.min_confidence is not None:
            rows = [row for row in rows if row.confidence >= query.min_confidence]
        return tuple(rows[: query.limit])


class _TaskRepo(_PersonalityRepo):
    """Task repository fixture using same behavior as personality fixture."""


def _record(  # noqa: PLR0913
    *,
    record_id: str,
    store: MemoryStore,
    namespace: str,
    content: str,
    confidence: float,
    updated_at: datetime,
) -> MemoryRecord:
    """Create deterministic memory record fixture.

    Args:
        record_id: Stable id.
        store: Memory store identifier.
        namespace: Namespace token.
        content: Record content.
        confidence: Confidence score.
        updated_at: Record update timestamp.

    Returns:
        Memory record fixture.
    """
    return MemoryRecord(
        id=record_id,
        store=store,
        namespace=namespace,
        content=content,
        confidence=confidence,
        created_at=updated_at,
        updated_at=updated_at,
    )


@pytest.mark.unit
def test_retrieval_priority_and_confidence_threshold() -> None:
    """Retrieval should prioritize stable domains and filter low-confidence rows."""
    now = datetime.now(UTC)
    personality = _PersonalityRepo(
        rows={
            "working_rules/a": (
                _record(
                    record_id="wr-1",
                    store=MemoryStore.PERSONALITY,
                    namespace="working_rules/a",
                    content="Always respond with concise bulleted action plans.",
                    confidence=0.95,
                    updated_at=now,
                ),
            ),
            "persona_core/a": (
                _record(
                    record_id="pc-1",
                    store=MemoryStore.PERSONALITY,
                    namespace="persona_core/a",
                    content="You are an executive assistant persona.",
                    confidence=0.85,
                    updated_at=now,
                ),
            ),
            "user_profile/a": (
                _record(
                    record_id="up-1",
                    store=MemoryStore.PERSONALITY,
                    namespace="user_profile/a",
                    content="User prefers concise answers and roadmap checklists.",
                    confidence=0.9,
                    updated_at=now,
                ),
                _record(
                    record_id="up-2",
                    store=MemoryStore.PERSONALITY,
                    namespace="user_profile/a",
                    content="Low-confidence stale preference.",
                    confidence=0.2,
                    updated_at=now,
                ),
            ),
        }
    )
    task = _TaskRepo(
        rows={
            "task_memory/task:session-1": (
                _record(
                    record_id="tm-1",
                    store=MemoryStore.TASK,
                    namespace="task_memory/task:session-1",
                    content="Task includes phase 3 retrieval rollout.",
                    confidence=0.9,
                    updated_at=now,
                ),
            )
        }
    )
    service = PromptMemoryRetrievalService(
        personality_repository=personality,
        task_repository=task,
        policy=RetrievalPolicy(confidence_threshold=0.6, max_per_domain=2, max_total=8),
    )

    summary = service.build_memory_summary(
        user_text="please do concise phase 3 roadmap work",
        personality_namespaces={
            "working_rules": "working_rules/a",
            "persona_core": "persona_core/a",
            "user_profile": "user_profile/a",
        },
        task_namespaces=("task_memory/task:session-1",),
    )

    assert summary
    assert summary.index("working_rules:") < summary.index("persona_core:")
    assert summary.index("persona_core:") < summary.index("user_profile:")
    assert summary.index("user_profile:") < summary.index("task_memory:")
    assert "Low-confidence stale preference." not in summary


@pytest.mark.unit
def test_retrieval_uses_recency_tiebreak_with_equal_lexical_score() -> None:
    """Records with equal lexical score should be ordered by recency."""
    older = datetime(2025, 1, 1, tzinfo=UTC)
    newer = datetime(2025, 1, 2, tzinfo=UTC)
    personality = _PersonalityRepo(
        rows={
            "user_profile/a": (
                _record(
                    record_id="old",
                    store=MemoryStore.PERSONALITY,
                    namespace="user_profile/a",
                    content="User likes concise answers.",
                    confidence=0.8,
                    updated_at=older,
                ),
                _record(
                    record_id="new",
                    store=MemoryStore.PERSONALITY,
                    namespace="user_profile/a",
                    content="User likes concise responses.",
                    confidence=0.8,
                    updated_at=newer,
                ),
            )
        }
    )
    task = _TaskRepo(rows={})
    service = PromptMemoryRetrievalService(
        personality_repository=personality,
        task_repository=task,
        policy=RetrievalPolicy(max_per_domain=2, max_total=2),
    )

    summary = service.build_memory_summary(
        user_text="concise please",
        personality_namespaces={
            "working_rules": "",
            "persona_core": "",
            "user_profile": "user_profile/a",
        },
        task_namespaces=(),
    )

    assert summary.index("responses.") < summary.index("answers.")

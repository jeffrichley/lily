"""Prompt-memory retrieval and summarization helpers."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from lily.memory.models import MemoryQuery, MemoryRecord
from lily.memory.repository import PersonalityMemoryRepository, TaskMemoryRepository
from lily.observability import memory_metrics
from lily.prompting import truncate_with_marker

_DOMAIN_PRIORITY: tuple[str, ...] = (
    "working_rules",
    "persona_core",
    "user_profile",
    "task_memory",
)
_WORD_PATTERN = re.compile(r"[a-z0-9_]+")
_MIN_TOKEN_LENGTH = 3


class RetrievalPolicy(BaseModel):
    """Deterministic policy for prompt-memory retrieval."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    confidence_threshold: float = 0.6
    max_per_domain: int = Field(default=2, ge=1, le=10)
    max_total: int = Field(default=8, ge=1, le=20)
    summary_max_chars: int = Field(default=900, ge=100, le=3000)


@dataclass(frozen=True)
class _ScoredRecord:
    """Internal scored record for deterministic ranking."""

    domain: str
    record: MemoryRecord
    lexical_score: int


class PromptMemoryRetrievalService:
    """Repository-backed memory retrieval for prompt assembly."""

    def __init__(
        self,
        *,
        personality_repository: PersonalityMemoryRepository,
        task_repository: TaskMemoryRepository,
        policy: RetrievalPolicy | None = None,
    ) -> None:
        """Create retrieval service.

        Args:
            personality_repository: Personality memory repository adapter.
            task_repository: Task memory repository adapter.
            policy: Optional retrieval policy override.
        """
        self._personality_repository = personality_repository
        self._task_repository = task_repository
        self._policy = policy or RetrievalPolicy()

    def build_memory_summary(
        self,
        *,
        user_text: str,
        personality_namespaces: dict[str, str],
        task_namespaces: tuple[str, ...],
    ) -> str:
        """Build prompt-ready memory summary with deterministic ranking.

        Args:
            user_text: Current user turn text.
            personality_namespaces: Domain->namespace mapping.
            task_namespaces: Namespaces eligible for task retrieval.

        Returns:
            Deterministic memory summary for prompt section; empty when none.
        """
        query_tokens = _tokenize(user_text)
        selected = self._retrieve_ranked(
            query_tokens=query_tokens,
            personality_namespaces=personality_namespaces,
            task_namespaces=task_namespaces,
        )
        memory_metrics.record_retrieval(hit_count=len(selected))
        if not selected:
            return ""
        grouped: dict[str, list[_ScoredRecord]] = defaultdict(list)
        for item in selected:
            grouped[item.domain].append(item)
        lines: list[str] = []
        for domain in _DOMAIN_PRIORITY:
            rows = grouped.get(domain, [])
            if not rows:
                continue
            lines.append(f"{domain}:")
            lines.extend(
                (
                    f"- {row.record.content} "
                    f"(conf={row.record.confidence:.2f}, id={row.record.id})"
                )
                for row in rows
            )
        summary = "\n".join(lines).strip()
        return truncate_with_marker(
            summary,
            max_chars=self._policy.summary_max_chars,
            label="retrieved_memory_summary",
        )

    def _retrieve_ranked(
        self,
        *,
        query_tokens: set[str],
        personality_namespaces: dict[str, str],
        task_namespaces: tuple[str, ...],
    ) -> tuple[_ScoredRecord, ...]:
        """Retrieve and rank records from prioritized domains.

        Args:
            query_tokens: Tokenized user turn text.
            personality_namespaces: Domain->namespace mapping.
            task_namespaces: Task namespace candidates.

        Returns:
            Deterministically ordered scored records.
        """
        candidates: list[_ScoredRecord] = []
        for domain in _DOMAIN_PRIORITY:
            if domain == "task_memory":
                candidates.extend(
                    self._query_task_candidates(
                        query_tokens=query_tokens,
                        namespaces=task_namespaces,
                    )
                )
                continue
            namespace = personality_namespaces.get(domain, "").strip()
            if not namespace:
                continue
            candidates.extend(
                self._query_personality_candidates(
                    domain=domain,
                    namespace=namespace,
                    query_tokens=query_tokens,
                )
            )

        selected: list[_ScoredRecord] = []
        by_domain: dict[str, int] = defaultdict(int)
        for domain in _DOMAIN_PRIORITY:
            domain_rows = [item for item in candidates if item.domain == domain]
            for item in _sort_rows(domain_rows):
                if by_domain[domain] >= self._policy.max_per_domain:
                    break
                if len(selected) >= self._policy.max_total:
                    return tuple(selected)
                selected.append(item)
                by_domain[domain] += 1
        return tuple(selected)

    def _query_personality_candidates(
        self,
        *,
        domain: str,
        namespace: str,
        query_tokens: set[str],
    ) -> tuple[_ScoredRecord, ...]:
        """Query one personality namespace and return scored candidates.

        Args:
            domain: Personality domain name.
            namespace: Namespace path string.
            query_tokens: Tokenized user query terms.

        Returns:
            Scored personality candidates.
        """
        records = self._personality_repository.query(
            MemoryQuery(
                query="*",
                namespace=namespace,
                limit=20,
                min_confidence=self._policy.confidence_threshold,
            )
        )
        return tuple(
            _ScoredRecord(
                domain=domain,
                record=record,
                lexical_score=_score_text(record.content, query_tokens),
            )
            for record in records
        )

    def _query_task_candidates(
        self,
        *,
        query_tokens: set[str],
        namespaces: tuple[str, ...],
    ) -> tuple[_ScoredRecord, ...]:
        """Query task namespaces and return scored candidates.

        Args:
            query_tokens: Tokenized user query terms.
            namespaces: Constrained task namespaces.

        Returns:
            Scored task-memory candidates.
        """
        rows: list[_ScoredRecord] = []
        for namespace in namespaces:
            records = self._task_repository.query(
                MemoryQuery(
                    query="*",
                    namespace=namespace,
                    limit=20,
                    min_confidence=self._policy.confidence_threshold,
                )
            )
            rows.extend(
                _ScoredRecord(
                    domain="task_memory",
                    record=record,
                    lexical_score=_score_text(record.content, query_tokens),
                )
                for record in records
            )
        return tuple(rows)


def _sort_rows(rows: list[_ScoredRecord]) -> tuple[_ScoredRecord, ...]:
    """Sort rows using lexical score, recency, then stable id tiebreak.

    Args:
        rows: Candidate rows for one domain.

    Returns:
        Sorted scored rows.
    """
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                -row.lexical_score,
                -row.record.updated_at.timestamp(),
                row.record.id,
            ),
        )
    )


def _score_text(text: str, tokens: set[str]) -> int:
    """Compute deterministic lexical overlap score.

    Args:
        text: Candidate memory text.
        tokens: Query token set.

    Returns:
        Overlap score.
    """
    if not tokens:
        return 0
    words = _tokenize(text)
    return sum(1 for token in tokens if token in words)


def _tokenize(text: str) -> set[str]:
    """Tokenize text into normalized lexical units.

    Args:
        text: Source text.

    Returns:
        Normalized token set.
    """
    return {
        item
        for item in _WORD_PATTERN.findall(text.lower())
        if len(item) >= _MIN_TOKEN_LENGTH and not item.isdigit()
    }

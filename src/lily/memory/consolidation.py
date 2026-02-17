"""Background consolidation helpers for long-term memory."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from lily.memory.langmem_tools import LangMemToolingAdapter
from lily.memory.models import (
    MemoryQuery,
    MemoryRecord,
    MemorySource,
    MemoryWriteRequest,
)
from lily.memory.repository import PersonalityMemoryRepository, TaskMemoryRepository
from lily.session.models import Message, MessageRole

_FAVORITE_PATTERN = re.compile(
    r"\bmy favorite (?P<field>[a-z0-9_ ]{2,40}) is (?P<value>[^.?!]{1,120})",
    re.IGNORECASE,
)
_NAME_PATTERN = re.compile(
    r"\bmy name is (?P<value>[a-z][a-z0-9_ -]{1,60})",
    re.IGNORECASE,
)
_PREFER_PATTERN = re.compile(
    r"\bi prefer (?P<value>[^.?!]{3,120})",
    re.IGNORECASE,
)
_TASK_FACT_PATTERN = re.compile(
    r"\btask (?P<task>[a-z0-9_\-]{1,40})[: ]+(?P<fact>[^.?!]{3,120})",
    re.IGNORECASE,
)


class ConsolidationBackend(StrEnum):
    """Supported consolidation backend identifiers."""

    RULE_BASED = "rule_based"
    LANGMEM_MANAGER = "langmem_manager"


class ConsolidationRequest(BaseModel):
    """Consolidation request payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str = Field(min_length=1)
    history: tuple[Message, ...]
    personality_namespace: str = Field(min_length=1)
    enabled: bool = False
    backend: ConsolidationBackend = ConsolidationBackend.RULE_BASED
    llm_assisted_enabled: bool = False
    dry_run: bool = False


class ConsolidationResult(BaseModel):
    """Structured consolidation result payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    backend: ConsolidationBackend
    proposed: int = 0
    written: int = 0
    skipped: int = 0
    notes: tuple[str, ...] = ()
    records: tuple[str, ...] = ()


class ConsolidationEngine(Protocol):
    """Consolidation execution protocol."""

    def run(self, request: ConsolidationRequest) -> ConsolidationResult:
        """Execute one consolidation pass.

        Args:
            request: Consolidation request.
        """


@dataclass(frozen=True)
class _PersonalityCandidate:
    """Personality memory candidate."""

    content: str
    conflict_group: str


@dataclass(frozen=True)
class _TaskCandidate:
    """Task memory candidate."""

    task: str
    content: str


class RuleBasedConsolidationEngine:
    """Deterministic rule-based consolidation engine."""

    def __init__(
        self,
        *,
        personality_repository: PersonalityMemoryRepository,
        task_repository: TaskMemoryRepository | None = None,
    ) -> None:
        """Create engine.

        Args:
            personality_repository: Personality repository for writes.
            task_repository: Optional task repository for task-fact writes.
        """
        self._personality_repository = personality_repository
        self._task_repository = task_repository

    def run(self, request: ConsolidationRequest) -> ConsolidationResult:
        """Execute deterministic extraction and repository writes.

        Args:
            request: Consolidation request payload.

        Returns:
            Consolidation result summary.
        """
        if not request.enabled:
            return ConsolidationResult(
                status="disabled",
                backend=request.backend,
                notes=("Consolidation is disabled by config.",),
            )
        personality_candidates, task_candidates, labels = _collect_candidates(
            request.history
        )
        proposed = len(labels)
        early = _early_consolidation_result(
            request=request,
            proposed=proposed,
            labels=labels,
        )
        if early is not None:
            return early
        written, skipped = self._write_candidates(
            request=request,
            personality_candidates=personality_candidates,
            task_candidates=task_candidates,
        )
        return ConsolidationResult(
            status="ok",
            backend=request.backend,
            proposed=proposed,
            written=written,
            skipped=skipped,
            records=labels,
            notes=_completion_notes(
                prefix="Rule-based consolidation completed.",
                llm_assisted_enabled=request.llm_assisted_enabled,
            ),
        )

    def _write_candidates(
        self,
        *,
        request: ConsolidationRequest,
        personality_candidates: tuple[_PersonalityCandidate, ...],
        task_candidates: tuple[_TaskCandidate, ...],
    ) -> tuple[int, int]:
        """Write personality/task candidates and apply conflict policy.

        Args:
            request: Consolidation request payload.
            personality_candidates: Personality candidates to write.
            task_candidates: Task candidates to write.

        Returns:
            Written and skipped counts.
        """
        written = 0
        skipped = 0
        existing = _load_personality_records(
            repository=self._personality_repository,
            namespace=request.personality_namespace,
        )
        written, skipped = self._write_personality_candidates(
            request=request,
            personality_candidates=personality_candidates,
            existing=existing,
        )
        if self._task_repository is not None:
            written += self._write_task_candidates(
                request=request,
                task_candidates=task_candidates,
            )
        return written, skipped

    def _write_personality_candidates(
        self,
        *,
        request: ConsolidationRequest,
        personality_candidates: tuple[_PersonalityCandidate, ...],
        existing: tuple[MemoryRecord, ...],
    ) -> tuple[int, int]:
        """Write personality candidates with conflict handling.

        Args:
            request: Consolidation request payload.
            personality_candidates: Personality candidates to write.
            existing: Existing personality records in namespace.

        Returns:
            Written and skipped counts.
        """
        written = 0
        skipped = 0
        current = existing
        for candidate in personality_candidates:
            normalized = candidate.content.strip().lower()
            if normalized in {record.content.strip().lower() for record in current}:
                skipped += 1
                continue
            written += _mark_conflicts(
                repository=self._personality_repository,
                existing=current,
                candidate=candidate,
                request=request,
            )
            self._personality_repository.remember(
                MemoryWriteRequest(
                    namespace=request.personality_namespace,
                    content=candidate.content,
                    source=MemorySource.INFERENCE,
                    confidence=0.8,
                    session_id=request.session_id,
                    status="needs_verification",
                    conflict_group=candidate.conflict_group,
                    last_verified=None,
                )
            )
            written += 1
            current = _load_personality_records(
                repository=self._personality_repository,
                namespace=request.personality_namespace,
            )
        return written, skipped

    def _write_task_candidates(
        self,
        *,
        request: ConsolidationRequest,
        task_candidates: tuple[_TaskCandidate, ...],
    ) -> int:
        """Write task-memory candidates.

        Args:
            request: Consolidation request payload.
            task_candidates: Task candidates to write.

        Returns:
            Number of records written.
        """
        assert self._task_repository is not None
        writes = 0
        for task_candidate in task_candidates:
            self._task_repository.remember(
                MemoryWriteRequest(
                    namespace=_task_namespace(task_candidate.task),
                    content=task_candidate.content,
                    source=MemorySource.INFERENCE,
                    confidence=0.75,
                    session_id=request.session_id,
                    status="needs_verification",
                    last_verified=None,
                    conflict_group=f"task:{task_candidate.task}",
                )
            )
            writes += 1
        return writes


class LangMemManagerConsolidationEngine:
    """LangMem-managed consolidation engine using manage-memory tooling."""

    def __init__(self, *, tooling_adapter: LangMemToolingAdapter) -> None:
        """Create engine.

        Args:
            tooling_adapter: LangMem tooling adapter.
        """
        self._tooling_adapter = tooling_adapter

    def run(self, request: ConsolidationRequest) -> ConsolidationResult:
        """Execute candidate extraction and LangMem manage writes.

        Args:
            request: Consolidation request payload.

        Returns:
            Consolidation result summary.
        """
        if not request.enabled:
            return ConsolidationResult(
                status="disabled",
                backend=request.backend,
                notes=("Consolidation is disabled by config.",),
            )
        personality_candidates = _extract_personality_candidates(request.history)
        task_candidates = _extract_task_candidates(request.history)
        proposed = len(personality_candidates) + len(task_candidates)
        if proposed == 0:
            return ConsolidationResult(
                status="ok",
                backend=request.backend,
                proposed=0,
                written=0,
                skipped=0,
                notes=("No candidate memories detected.",),
            )
        all_labels = tuple(
            [candidate.content for candidate in personality_candidates]
            + [
                f"task {task_candidate.task}: {task_candidate.content}"
                for task_candidate in task_candidates
            ]
        )
        if request.dry_run:
            return ConsolidationResult(
                status="dry_run",
                backend=request.backend,
                proposed=proposed,
                written=0,
                skipped=0,
                records=all_labels,
            )
        writes = 0
        for candidate in personality_candidates:
            self._tooling_adapter.remember(
                namespace=request.personality_namespace,
                content=candidate.content,
                tool_name="lily_memory_manage_consolidation",
            )
            writes += 1
        for task_candidate in task_candidates:
            self._tooling_adapter.remember(
                namespace=_task_namespace(task_candidate.task),
                content=task_candidate.content,
                tool_name="lily_memory_manage_consolidation_task",
            )
            writes += 1
        notes = ["LangMem-manager consolidation completed."]
        if request.llm_assisted_enabled:
            notes.append("LLM-assisted mode is metadata-only in this build.")
        return ConsolidationResult(
            status="ok",
            backend=request.backend,
            proposed=proposed,
            written=writes,
            skipped=0,
            records=all_labels,
            notes=tuple(notes),
        )


def _collect_candidates(
    history: tuple[Message, ...],
) -> tuple[
    tuple[_PersonalityCandidate, ...],
    tuple[_TaskCandidate, ...],
    tuple[str, ...],
]:
    """Collect extracted candidates and deterministic display labels.

    Args:
        history: Conversation history.

    Returns:
        Personality candidates, task candidates, and display labels.
    """
    personality_candidates = _extract_personality_candidates(history)
    task_candidates = _extract_task_candidates(history)
    labels = tuple(
        [candidate.content for candidate in personality_candidates]
        + [
            f"task {task_candidate.task}: {task_candidate.content}"
            for task_candidate in task_candidates
        ]
    )
    return personality_candidates, task_candidates, labels


def _early_consolidation_result(
    *,
    request: ConsolidationRequest,
    proposed: int,
    labels: tuple[str, ...],
) -> ConsolidationResult | None:
    """Return an early result when no writes should occur.

    Args:
        request: Consolidation request payload.
        proposed: Proposed write count.
        labels: Candidate labels for dry-run output.

    Returns:
        Consolidation result when early return applies, otherwise ``None``.
    """
    if proposed == 0:
        return ConsolidationResult(
            status="ok",
            backend=request.backend,
            proposed=0,
            written=0,
            skipped=0,
            notes=("No candidate memories detected.",),
        )
    if request.dry_run:
        return ConsolidationResult(
            status="dry_run",
            backend=request.backend,
            proposed=proposed,
            written=0,
            skipped=0,
            records=labels,
        )
    return None


def _completion_notes(*, prefix: str, llm_assisted_enabled: bool) -> tuple[str, ...]:
    """Build deterministic completion notes payload.

    Args:
        prefix: Base completion note.
        llm_assisted_enabled: Whether llm-assisted metadata is enabled.

    Returns:
        Deterministic notes tuple.
    """
    notes = [prefix]
    if llm_assisted_enabled:
        notes.append("LLM-assisted mode is metadata-only in this build.")
    return tuple(notes)


def _load_personality_records(
    *,
    repository: PersonalityMemoryRepository,
    namespace: str,
) -> tuple[MemoryRecord, ...]:
    """Load all personality records for one namespace with full visibility.

    Args:
        repository: Personality repository.
        namespace: Target namespace.

    Returns:
        Existing records.
    """
    return repository.query(
        MemoryQuery(
            query="*",
            namespace=namespace,
            limit=20,
            include_archived=True,
            include_expired=True,
            include_conflicted=True,
        )
    )


def _mark_conflicts(
    *,
    repository: PersonalityMemoryRepository,
    existing: tuple[MemoryRecord, ...],
    candidate: _PersonalityCandidate,
    request: ConsolidationRequest,
) -> int:
    """Mark conflicting records for the same conflict group.

    Args:
        repository: Personality repository.
        existing: Existing records.
        candidate: Incoming candidate.
        request: Consolidation request.

    Returns:
        Number of records updated as conflicted.
    """
    writes = 0
    normalized_candidate = candidate.content.strip().lower()
    for record in existing:
        if record.conflict_group != candidate.conflict_group:
            continue
        if record.content.strip().lower() == normalized_candidate:
            continue
        if record.status == "conflicted":
            continue
        repository.remember(
            MemoryWriteRequest(
                namespace=record.namespace,
                content=record.content,
                source=MemorySource.SYSTEM,
                confidence=record.confidence,
                tags=record.tags,
                preference_type=record.preference_type,
                stability=record.stability,
                task_id=record.task_id,
                session_id=request.session_id,
                status="conflicted",
                expires_at=record.expires_at,
                last_verified=record.last_verified,
                conflict_group=candidate.conflict_group,
            )
        )
        writes += 1
    return writes


def _extract_personality_candidates(
    history: tuple[Message, ...],
) -> tuple[_PersonalityCandidate, ...]:
    """Extract personality-memory candidates from user conversation turns.

    Args:
        history: Conversation history.

    Returns:
        Deduplicated personality candidates.
    """
    candidates: list[_PersonalityCandidate] = []
    for event in history[-50:]:
        if event.role != MessageRole.USER:
            continue
        text = " ".join(event.content.split())
        favorite_match = _FAVORITE_PATTERN.search(text)
        if favorite_match is not None:
            field = favorite_match.group("field").strip().lower()
            value = favorite_match.group("value").strip()
            candidates.append(
                _PersonalityCandidate(
                    content=f"favorite {field} is {value}",
                    conflict_group=f"favorite:{field}",
                )
            )
        name_match = _NAME_PATTERN.search(text)
        if name_match is not None:
            candidates.append(
                _PersonalityCandidate(
                    content=f"name is {name_match.group('value').strip()}",
                    conflict_group="identity:name",
                )
            )
        prefer_match = _PREFER_PATTERN.search(text)
        if prefer_match is not None:
            candidates.append(
                _PersonalityCandidate(
                    content=f"prefers {prefer_match.group('value').strip()}",
                    conflict_group="preference:general",
                )
            )
    deduped: dict[str, _PersonalityCandidate] = {}
    for candidate in candidates:
        normalized = candidate.content.strip().lower()
        if normalized:
            deduped[normalized] = candidate
    return tuple(deduped.values())


def _extract_task_candidates(
    history: tuple[Message, ...],
) -> tuple[_TaskCandidate, ...]:
    """Extract task-memory candidates from user conversation turns.

    Args:
        history: Conversation history.

    Returns:
        Deduplicated task candidates.
    """
    candidates: list[_TaskCandidate] = []
    for event in history[-50:]:
        if event.role != MessageRole.USER:
            continue
        text = " ".join(event.content.split())
        task_match = _TASK_FACT_PATTERN.search(text)
        if task_match is None:
            continue
        task = task_match.group("task").strip().lower()
        fact = task_match.group("fact").strip()
        candidates.append(_TaskCandidate(task=task, content=fact))
    deduped: dict[str, _TaskCandidate] = {}
    for candidate in candidates:
        key = f"{candidate.task}::{candidate.content.strip().lower()}"
        deduped[key] = candidate
    return tuple(deduped.values())


def _task_namespace(task: str) -> str:
    """Build deterministic task-memory namespace.

    Args:
        task: Task identifier.

    Returns:
        Task namespace string.
    """
    return f"task_memory/task:{task.strip()}"

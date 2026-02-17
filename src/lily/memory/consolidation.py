"""Background consolidation helpers for long-term memory."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from lily.memory.langmem_tools import LangMemToolingAdapter
from lily.memory.models import MemorySource, MemoryWriteRequest
from lily.memory.repository import PersonalityMemoryRepository
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


class RuleBasedConsolidationEngine:
    """Deterministic rule-based consolidation engine."""

    def __init__(self, *, personality_repository: PersonalityMemoryRepository) -> None:
        """Create engine.

        Args:
            personality_repository: Personality repository for writes.
        """
        self._personality_repository = personality_repository

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
        candidates = _extract_candidates(request.history)
        if not candidates:
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
                proposed=len(candidates),
                written=0,
                skipped=0,
                records=tuple(candidates),
            )
        now = datetime.now(UTC)
        written = 0
        for content in candidates:
            self._personality_repository.remember(
                MemoryWriteRequest(
                    namespace=request.personality_namespace,
                    content=content,
                    source=MemorySource.INFERENCE,
                    confidence=0.8,
                    session_id=request.session_id,
                    status="needs_verification",
                    last_verified=now if request.llm_assisted_enabled else None,
                )
            )
            written += 1
        return ConsolidationResult(
            status="ok",
            backend=request.backend,
            proposed=len(candidates),
            written=written,
            skipped=0,
            records=tuple(candidates),
            notes=(
                "Rule-based consolidation completed.",
                "LLM-assisted mode is metadata-only in this build.",
            )
            if request.llm_assisted_enabled
            else ("Rule-based consolidation completed.",),
        )


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
        candidates = _extract_candidates(request.history)
        if not candidates:
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
                proposed=len(candidates),
                written=0,
                skipped=0,
                records=tuple(candidates),
            )
        writes = 0
        for content in candidates:
            self._tooling_adapter.remember(
                namespace=request.personality_namespace,
                content=content,
                tool_name="lily_memory_manage_consolidation",
            )
            writes += 1
        notes = ["LangMem-manager consolidation completed."]
        if request.llm_assisted_enabled:
            notes.append("LLM-assisted mode is metadata-only in this build.")
        return ConsolidationResult(
            status="ok",
            backend=request.backend,
            proposed=len(candidates),
            written=writes,
            skipped=0,
            records=tuple(candidates),
            notes=tuple(notes),
        )


def _extract_candidates(history: tuple[Message, ...]) -> tuple[str, ...]:
    """Extract deterministic candidate memory statements from conversation.

    Args:
        history: Conversation history.

    Returns:
        Deduplicated candidate memory strings.
    """
    candidates: list[str] = []
    for event in history[-50:]:
        if event.role != MessageRole.USER:
            continue
        text = " ".join(event.content.split())
        favorite_match = _FAVORITE_PATTERN.search(text)
        if favorite_match is not None:
            field = favorite_match.group("field").strip().lower()
            value = favorite_match.group("value").strip()
            candidates.append(f"favorite {field} is {value}")
        name_match = _NAME_PATTERN.search(text)
        if name_match is not None:
            candidates.append(f"name is {name_match.group('value').strip()}")
        prefer_match = _PREFER_PATTERN.search(text)
        if prefer_match is not None:
            candidates.append(f"prefers {prefer_match.group('value').strip()}")
    deduped: dict[str, str] = {}
    for candidate in candidates:
        normalized = candidate.strip().lower()
        if normalized:
            deduped[normalized] = candidate.strip()
    return tuple(deduped.values())

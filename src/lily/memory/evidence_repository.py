"""Semantic evidence repository for non-canonical citation retrieval."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from lily.memory.models import MemoryError, MemoryErrorCode
from lily.observability import memory_metrics

_WORD_PATTERN = re.compile(r"[a-z0-9]{2,}", re.IGNORECASE)
_EVIDENCE_FILE = "evidence_memory.json"


class EvidenceChunkingMode(StrEnum):
    """Supported evidence chunking strategies."""

    RECURSIVE = "recursive"
    TOKEN = "token"  # nosec B105 - chunker mode label, not credential data


@dataclass(frozen=True)
class EvidenceChunkingSettings:
    """Evidence chunking strategy configuration."""

    mode: EvidenceChunkingMode = EvidenceChunkingMode.RECURSIVE
    chunk_size: int = 360
    chunk_overlap: int = 40
    token_encoding_name: str = "cl100k_base"


class EvidenceChunk(BaseModel):
    """Persisted evidence chunk payload."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    namespace: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvidenceHit(BaseModel):
    """Search hit payload with citation metadata."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    namespace: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    citation: str = Field(min_length=1)
    score: float = Field(ge=0)
    snippet: str = Field(min_length=1)


class FileBackedEvidenceRepository:
    """File-backed evidence repository with deterministic lexical scoring."""

    def __init__(
        self,
        *,
        root_dir: Path,
        chunking: EvidenceChunkingSettings | None = None,
    ) -> None:
        """Create evidence repository.

        Args:
            root_dir: Memory root directory.
            chunking: Chunking configuration for ingestion.
        """
        self._root_dir = root_dir
        self._path = root_dir / _EVIDENCE_FILE
        self._chunking = chunking or EvidenceChunkingSettings()

    def ingest(self, *, namespace: str, path_or_ref: str) -> tuple[EvidenceChunk, ...]:
        """Ingest one local text file into chunked evidence records.

        Args:
            namespace: Evidence namespace token.
            path_or_ref: Local file path.

        Returns:
            Newly written chunks.

        Raises:
            MemoryError: For invalid input or unreadable payload.
        """
        normalized_ns, normalized_ref = _normalize_ingest_input(
            namespace=namespace,
            path_or_ref=path_or_ref,
        )
        text = _read_source_text(path_or_ref=normalized_ref)
        chunks = _chunk_text(text=text, settings=self._chunking)
        if not chunks:
            raise MemoryError(
                MemoryErrorCode.INVALID_INPUT,
                f"Evidence source '{normalized_ref}' is empty.",
            )
        all_rows = self._load_rows()
        written = _append_new_chunks(
            rows=all_rows,
            namespace=normalized_ns,
            source_ref=normalized_ref,
            chunks=chunks,
        )
        self._save_rows(all_rows)
        _record_written_chunks(namespace=normalized_ns, count=len(written))
        return tuple(written)

    def query(
        self,
        *,
        namespace: str,
        query: str,
        limit: int = 5,
    ) -> tuple[EvidenceHit, ...]:
        """Query evidence records and return scored citation hits.

        Args:
            namespace: Evidence namespace token.
            query: Query text.
            limit: Maximum result count.

        Returns:
            Scored evidence hits ordered by relevance.

        Raises:
            MemoryError: For invalid inputs.
        """
        normalized_ns = namespace.strip()
        normalized_query = query.strip()
        if not normalized_ns or not normalized_query:
            raise MemoryError(
                MemoryErrorCode.INVALID_INPUT,
                "Evidence query requires namespace and query.",
            )
        bounded_limit = min(max(limit, 1), 20)
        rows = [row for row in self._load_rows() if row.namespace == normalized_ns]
        if normalized_query == "*":
            recent_rows = sorted(rows, key=lambda item: item.updated_at, reverse=True)
            selected = recent_rows[:bounded_limit]
            hits = tuple(
                EvidenceHit(
                    id=row.id,
                    namespace=row.namespace,
                    source_ref=row.source_ref,
                    citation=_citation(row),
                    score=1.0,
                    snippet=row.content,
                )
                for row in selected
            )
            memory_metrics.record_read(namespace=normalized_ns, hit_count=len(hits))
            return hits
        scored: list[tuple[float, EvidenceChunk]] = []
        for row in rows:
            score = _lexical_score(query=normalized_query, content=row.content)
            if score <= 0:
                continue
            scored.append((score, row))
        ranked = sorted(
            scored,
            key=lambda pair: (pair[0], pair[1].updated_at),
            reverse=True,
        )[:bounded_limit]
        hits = tuple(
            EvidenceHit(
                id=row.id,
                namespace=row.namespace,
                source_ref=row.source_ref,
                citation=_citation(row),
                score=round(score, 4),
                snippet=row.content,
            )
            for score, row in ranked
        )
        memory_metrics.record_read(namespace=normalized_ns, hit_count=len(hits))
        return hits

    def _load_rows(self) -> list[EvidenceChunk]:
        """Load and validate persisted evidence rows.

        Returns:
            Parsed evidence chunk rows.

        Raises:
            MemoryError: If payload is unreadable or invalid.
        """
        if not self._path.exists():
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MemoryError(
                MemoryErrorCode.SCHEMA_MISMATCH,
                "Evidence store payload is unreadable.",
            ) from exc
        if not isinstance(raw, list):
            raise MemoryError(
                MemoryErrorCode.SCHEMA_MISMATCH,
                "Evidence store payload must be a list.",
            )
        parsed: list[EvidenceChunk] = []
        for item in raw:
            try:
                parsed.append(EvidenceChunk.model_validate(item))
            except ValidationError as exc:
                raise MemoryError(
                    MemoryErrorCode.SCHEMA_MISMATCH,
                    "Evidence store payload contains invalid rows.",
                ) from exc
        return parsed

    def _save_rows(self, rows: list[EvidenceChunk]) -> None:
        """Persist rows atomically.

        Args:
            rows: Evidence chunk rows to persist.

        Raises:
            MemoryError: If persistence fails.
        """
        try:
            self._root_dir.mkdir(parents=True, exist_ok=True)
            payload = [row.model_dump(mode="json") for row in rows]
            temp_path = self._path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            temp_path.replace(self._path)
        except OSError as exc:
            raise MemoryError(
                MemoryErrorCode.STORE_UNAVAILABLE,
                "Evidence store is unavailable.",
            ) from exc


def _chunk_text(
    *,
    text: str,
    settings: EvidenceChunkingSettings,
) -> tuple[str, ...]:
    """Split text with configured LangChain splitter.

    Args:
        text: Raw evidence text.
        settings: Chunking strategy settings.

    Returns:
        Normalized chunk tuple.
    """
    normalized = " ".join(text.split())
    if not normalized:
        return ()
    splitter = _build_text_splitter(settings)
    return tuple(
        chunk.strip() for chunk in splitter.split_text(normalized) if chunk.strip()
    )


def _build_text_splitter(
    settings: EvidenceChunkingSettings,
) -> RecursiveCharacterTextSplitter:
    """Build configured LangChain text splitter.

    Args:
        settings: Chunking strategy settings.

    Returns:
        Configured text splitter.
    """
    if settings.mode == EvidenceChunkingMode.TOKEN:
        return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name=settings.token_encoding_name,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


def _chunk_id(*, namespace: str, source_ref: str, chunk: str) -> str:
    """Build deterministic chunk id hash.

    Args:
        namespace: Evidence namespace token.
        source_ref: Source reference path.
        chunk: Chunk content.

    Returns:
        Deterministic evidence chunk id.
    """
    payload = f"{namespace.strip()}::{source_ref.strip()}::{chunk.strip()}".encode()
    return f"ev_{sha256(payload).hexdigest()}"


def _normalize_ingest_input(*, namespace: str, path_or_ref: str) -> tuple[str, str]:
    """Normalize and validate ingest input parameters.

    Args:
        namespace: Evidence namespace token.
        path_or_ref: Source path string.

    Returns:
        Normalized namespace and path.

    Raises:
        MemoryError: If required fields are missing.
    """
    normalized_ns = namespace.strip()
    normalized_ref = path_or_ref.strip()
    if normalized_ns and normalized_ref:
        return normalized_ns, normalized_ref
    raise MemoryError(
        MemoryErrorCode.INVALID_INPUT,
        "Evidence ingest requires namespace and path.",
    )


def _read_source_text(*, path_or_ref: str) -> str:
    """Read source text from local file path.

    Args:
        path_or_ref: Source path string.

    Returns:
        Decoded source text.

    Raises:
        MemoryError: If path is missing or unreadable.
    """
    source_path = Path(path_or_ref)
    if not source_path.exists() or not source_path.is_file():
        raise MemoryError(
            MemoryErrorCode.NOT_FOUND,
            f"Evidence source '{path_or_ref}' was not found.",
        )
    try:
        return source_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MemoryError(
            MemoryErrorCode.STORE_UNAVAILABLE,
            f"Evidence source '{path_or_ref}' is unreadable.",
        ) from exc


def _append_new_chunks(
    *,
    rows: list[EvidenceChunk],
    namespace: str,
    source_ref: str,
    chunks: tuple[str, ...],
) -> list[EvidenceChunk]:
    """Append non-duplicate chunk rows and return newly written rows.

    Args:
        rows: Existing rows list to mutate.
        namespace: Evidence namespace token.
        source_ref: Source reference path.
        chunks: Normalized chunk tuple.

    Returns:
        Newly written chunk rows.
    """
    existing_ids = {row.id for row in rows}
    now = datetime.now(UTC)
    written: list[EvidenceChunk] = []
    for index, chunk in enumerate(chunks):
        chunk_id = _chunk_id(namespace=namespace, source_ref=source_ref, chunk=chunk)
        if chunk_id in existing_ids:
            continue
        row = EvidenceChunk(
            id=chunk_id,
            namespace=namespace,
            source_ref=source_ref,
            chunk_index=index,
            content=chunk,
            created_at=now,
            updated_at=now,
        )
        rows.append(row)
        written.append(row)
        existing_ids.add(chunk_id)
    return written


def _record_written_chunks(*, namespace: str, count: int) -> None:
    """Record write metrics for ingested chunks.

    Args:
        namespace: Evidence namespace token.
        count: Number of chunk writes.
    """
    for _ in range(max(count, 0)):
        memory_metrics.record_write(namespace=namespace)


def _citation(row: EvidenceChunk) -> str:
    """Build deterministic source citation label.

    Args:
        row: Evidence chunk row.

    Returns:
        Citation label.
    """
    return f"{row.source_ref}#chunk-{row.chunk_index + 1}"


def _lexical_score(*, query: str, content: str) -> float:
    """Score lexical overlap between query and content.

    Args:
        query: Query text.
        content: Candidate content text.

    Returns:
        Non-negative relevance score.
    """
    query_terms = _token_set(query)
    content_terms = _token_set(content)
    if not query_terms or not content_terms:
        return 0.0
    overlap = len(query_terms.intersection(content_terms))
    if overlap == 0:
        return 0.0
    return overlap / math.sqrt(len(query_terms) * len(content_terms))


def _token_set(text: str) -> set[str]:
    """Extract normalized token set for deterministic lexical scoring.

    Args:
        text: Raw text payload.

    Returns:
        Lower-cased token set.
    """
    return {match.group(0).lower() for match in _WORD_PATTERN.finditer(text)}

"""Unit tests for semantic evidence repository behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.memory.evidence_repository import (
    EvidenceChunkingMode,
    EvidenceChunkingSettings,
    FileBackedEvidenceRepository,
)
from lily.memory.models import MemoryError


@pytest.mark.unit
def test_evidence_ingest_and_query_returns_ranked_hits(tmp_path: Path) -> None:
    """Ingested evidence should be queryable with citation metadata."""
    repository = FileBackedEvidenceRepository(root_dir=tmp_path / "memory")
    source = tmp_path / "notes.txt"
    source.write_text(
        (
            "The deployment checklist requires health checks.\n"
            "Always validate canary metrics before full rollout.\n"
            "Postmortems must include action items.\n"
        ),
        encoding="utf-8",
    )

    written = repository.ingest(
        namespace="evidence/workspace:test",
        path_or_ref=str(source),
    )
    hits = repository.query(
        namespace="evidence/workspace:test",
        query="canary rollout metrics",
        limit=5,
    )

    assert len(written) >= 1
    assert len(hits) >= 1
    assert "notes.txt#chunk-" in hits[0].citation
    assert hits[0].score > 0


@pytest.mark.unit
def test_evidence_ingest_missing_path_returns_not_found(tmp_path: Path) -> None:
    """Ingest should fail with deterministic missing-source error."""
    repository = FileBackedEvidenceRepository(root_dir=tmp_path / "memory")

    try:
        repository.ingest(
            namespace="evidence/workspace:test",
            path_or_ref=str(tmp_path / "missing.txt"),
        )
    except MemoryError as exc:
        assert exc.code.value == "memory_not_found"
        return
    raise AssertionError("Expected ingest to raise MemoryError for missing source.")


@pytest.mark.unit
def test_evidence_ingest_supports_recursive_splitter_config(tmp_path: Path) -> None:
    """Repository should use recursive splitter when configured."""
    repository = FileBackedEvidenceRepository(
        root_dir=tmp_path / "memory",
        chunking=EvidenceChunkingSettings(
            mode=EvidenceChunkingMode.RECURSIVE,
            chunk_size=64,
            chunk_overlap=8,
        ),
    )
    source = tmp_path / "long.txt"
    source.write_text(" ".join(["alpha"] * 200), encoding="utf-8")

    written = repository.ingest(
        namespace="evidence/workspace:test",
        path_or_ref=str(source),
    )

    assert len(written) > 1


@pytest.mark.unit
def test_evidence_ingest_supports_token_splitter_config(tmp_path: Path) -> None:
    """Repository should use token-aware splitter when configured."""
    repository = FileBackedEvidenceRepository(
        root_dir=tmp_path / "memory",
        chunking=EvidenceChunkingSettings(
            mode=EvidenceChunkingMode.TOKEN,
            chunk_size=32,
            chunk_overlap=8,
            token_encoding_name="cl100k_base",
        ),
    )
    source = tmp_path / "tokens.txt"
    source.write_text(" ".join(["beta"] * 300), encoding="utf-8")

    written = repository.ingest(
        namespace="evidence/workspace:test",
        path_or_ref=str(source),
    )

    assert len(written) > 1

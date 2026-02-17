"""Unit tests for semantic evidence repository behavior."""

from __future__ import annotations

from pathlib import Path

from lily.memory.evidence_repository import FileBackedEvidenceRepository
from lily.memory.models import MemoryError


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

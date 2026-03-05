"""Semantic evidence routes for `/memory evidence` commands."""

from __future__ import annotations

from lily.commands.types import CommandResult
from lily.memory import FileBackedEvidenceRepository, MemoryError


def run_evidence_ingest(
    *,
    repository: FileBackedEvidenceRepository,
    namespace: str,
    args: tuple[str, ...],
) -> CommandResult:
    """Execute `/memory evidence ingest <path_or_ref>`.

    Args:
        repository: Evidence repository implementation.
        namespace: Evidence namespace token.
        args: Raw ingest args.

    Returns:
        Deterministic command result.
    """
    path_or_ref = " ".join(args).strip()
    if not path_or_ref:
        return CommandResult.error(
            "Error: /memory evidence ingest requires a path.",
            code="invalid_args",
            data={"command": "memory", "subcommand": "evidence ingest"},
        )
    try:
        rows = repository.ingest(namespace=namespace, path_or_ref=path_or_ref)
    except MemoryError as exc:
        return CommandResult.error(f"Error: {exc}", code=exc.code.value)
    return CommandResult.ok(
        f"Ingested {len(rows)} evidence chunk(s).",
        code="memory_evidence_ingested",
        data={
            "route": "semantic_evidence",
            "namespace": namespace,
            "source": path_or_ref,
            "chunks": len(rows),
            "non_canonical": True,
        },
    )


def run_evidence_show(
    *,
    repository: FileBackedEvidenceRepository,
    namespace: str,
    args: tuple[str, ...],
) -> CommandResult:
    """Execute `/memory evidence show [query]`.

    Args:
        repository: Evidence repository implementation.
        namespace: Evidence namespace token.
        args: Raw show args.

    Returns:
        Deterministic command result.
    """
    query = " ".join(args).strip() or "*"
    try:
        hits = repository.query(namespace=namespace, query=query, limit=10)
    except MemoryError as exc:
        return CommandResult.error(f"Error: {exc}", code=exc.code.value)
    if not hits:
        return CommandResult.ok(
            "No semantic evidence hits found.",
            code="memory_evidence_empty",
            data={
                "query": query,
                "records": [],
                "route": "semantic_evidence",
                "non_canonical": True,
                "canonical_precedence": "structured_long_term",
            },
        )
    lines = [f"{hit.snippet} [{hit.citation}] (score={hit.score:.3f})" for hit in hits]
    return CommandResult.ok(
        "\n".join(lines),
        code="memory_evidence_listed",
        data={
            "query": query,
            "records": [
                {
                    "id": hit.id,
                    "namespace": hit.namespace,
                    "source": hit.source_ref,
                    "citation": hit.citation,
                    "score": hit.score,
                    "content": hit.snippet,
                }
                for hit in hits
            ],
            "route": "semantic_evidence",
            "non_canonical": True,
            "canonical_precedence": "structured_long_term",
        },
    )

"""Global SQLite artifact index. Phase C: one DB for all runs."""

import json
import sqlite3
from pathlib import Path

from pydantic.types import JsonValue

from lily.kernel.artifact_ref import ArtifactRef, ProducerKind, StorageKind
from lily.kernel.paths import get_index_path

TABLE_NAME = "artifacts"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    storage_kind TEXT NOT NULL,
    artifact_name TEXT,
    rel_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    producer_id TEXT NOT NULL,
    producer_kind TEXT NOT NULL,
    inputs_json TEXT NOT NULL
)
"""


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_SQL)


def _ref_to_row(ref: ArtifactRef) -> dict[str, JsonValue]:
    """Convert ArtifactRef to index row (storage_kind/producer_kind as strings).

    Args:
        ref: The artifact reference to convert.

    Returns:
        A dict suitable for SQLite row insertion.
    """
    return {
        "artifact_id": ref.artifact_id,
        "run_id": ref.run_id,
        "artifact_type": ref.artifact_type,
        "storage_kind": ref.storage_kind.value,
        "artifact_name": ref.artifact_name,
        "rel_path": ref.rel_path,
        "sha256": ref.sha256,
        "created_at": ref.created_at,
        "producer_id": ref.producer_id,
        "producer_kind": ref.producer_kind.value,
        "inputs_json": json.dumps(ref.input_artifact_refs),
    }


def _row_to_ref(row: sqlite3.Row | tuple) -> ArtifactRef:
    """Build ArtifactRef from index row.

    Args:
        row: A SQLite row or tuple from the artifacts table.

    Returns:
        The reconstructed ArtifactRef.
    """
    if isinstance(row, tuple):
        # columns in CREATE order
        (
            artifact_id,
            run_id,
            artifact_type,
            storage_kind,
            artifact_name,
            rel_path,
            sha256,
            created_at,
            producer_id,
            producer_kind,
            inputs_json,
        ) = row
    else:
        artifact_id = row["artifact_id"]
        run_id = row["run_id"]
        artifact_type = row["artifact_type"]
        storage_kind = row["storage_kind"]
        artifact_name = row["artifact_name"]
        rel_path = row["rel_path"]
        sha256 = row["sha256"]
        created_at = row["created_at"]
        producer_id = row["producer_id"]
        producer_kind = row["producer_kind"]
        inputs_json = row["inputs_json"]
    return ArtifactRef(
        artifact_id=artifact_id,
        run_id=run_id,
        artifact_type=artifact_type,
        storage_kind=StorageKind(storage_kind),
        artifact_name=artifact_name,
        rel_path=rel_path,
        sha256=sha256,
        created_at=created_at,
        producer_id=producer_id or "",
        producer_kind=ProducerKind(producer_kind),
        input_artifact_refs=json.loads(inputs_json) if inputs_json else [],
    )


def open_index(workspace_root: Path) -> sqlite3.Connection:
    """Open connection to global index; create file and table if needed.

    Args:
        workspace_root: Root of the workspace containing .iris/index.

    Returns:
        An open SQLite connection with row_factory set.
    """
    index_path = get_index_path(workspace_root)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(index_path))
    conn.row_factory = sqlite3.Row
    _ensure_table(conn)
    return conn


def insert_artifact(conn: sqlite3.Connection, ref: ArtifactRef) -> None:
    """Insert one artifact row in a transaction. Caller commits.

    Args:
        conn: Open index connection.
        ref: Artifact reference to insert.
    """
    row = _ref_to_row(ref)
    conn.execute(
        """
        INSERT INTO artifacts (
            artifact_id, run_id, artifact_type, storage_kind, artifact_name,
            rel_path, sha256, created_at, producer_id, producer_kind, inputs_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["artifact_id"],
            row["run_id"],
            row["artifact_type"],
            row["storage_kind"],
            row["artifact_name"],
            row["rel_path"],
            row["sha256"],
            row["created_at"],
            row["producer_id"],
            row["producer_kind"],
            row["inputs_json"],
        ),
    )


def get_artifact_by_id(
    conn: sqlite3.Connection, artifact_id: str
) -> ArtifactRef | None:
    """Look up a single artifact by artifact_id. Returns None if not found.

    Args:
        conn: Open index connection.
        artifact_id: The artifact ID to look up.

    Returns:
        The ArtifactRef if found, else None.
    """
    cur = conn.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,))
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_ref(row)


def list_artifacts(
    conn: sqlite3.Connection,
    run_id: str,
    *,
    artifact_type: str | None = None,
    producer_id: str | None = None,
) -> list[ArtifactRef]:
    """Query artifacts by run_id with optional filters. Returns list of ArtifactRef.

    Args:
        conn: Open index connection.
        run_id: Run ID to filter by.
        artifact_type: Optional artifact type filter.
        producer_id: Optional producer ID filter.

    Returns:
        List of matching ArtifactRefs, ordered by created_at.
    """
    sql = "SELECT * FROM artifacts WHERE run_id = ?"
    params: list[str] = [run_id]
    if artifact_type is not None:
        sql += " AND artifact_type = ?"
        params.append(artifact_type)
    if producer_id is not None:
        sql += " AND producer_id = ?"
        params.append(producer_id)
    sql += " ORDER BY created_at"
    cur = conn.execute(sql, params)
    return [_row_to_ref(row) for row in cur.fetchall()]

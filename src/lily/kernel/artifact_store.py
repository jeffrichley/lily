"""Artifact store: put_json / put_file / get / open_path / list. Layer 1: put_envelope / get_envelope / get_validated."""

import hashlib
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from lily.kernel.artifact_id import generate_artifact_id
from lily.kernel.artifact_ref import ArtifactRef, StorageKind, ProducerKind
from lily.kernel.artifact_index import open_index, insert_artifact, list_artifacts
from lily.kernel.paths import ARTIFACTS_DIR, resolve_artifact_path
from lily.kernel.envelope import Envelope, EnvelopeMeta
from lily.kernel.canonical import hash_payload
from lily.kernel.envelope_validator import EnvelopeValidator

PAYLOAD_JSON = "payload.json"
PAYLOAD_TXT = "payload.txt"
META_JSON = "meta.json"
FILE_ARTIFACT_DEFAULT_NAME = "file"


def _sha256_file(path: Path) -> str:
    """Compute sha256 hex digest of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _workspace_root_from_run_root(run_root: Path) -> Path:
    """Derive workspace root from run_root (.iris/runs/<run_id> -> workspace)."""
    return run_root.resolve().parent.parent.parent


class ArtifactStore:
    """Store and retrieve artifacts under a run directory. Phase C: global SQLite index."""

    def __init__(self, run_root: Path, run_id: str) -> None:
        self._run_root = run_root.resolve()
        self._run_id = run_id
        self._workspace_root = _workspace_root_from_run_root(self._run_root)

    def put_json(
        self,
        artifact_type: str,
        payload: Any,
        metadata: dict[str, Any] | None = None,
        artifact_name: str | None = None,
        producer_id: str = "",
        producer_kind: ProducerKind = ProducerKind.SYSTEM,
        input_artifact_refs: list[str] | None = None,
    ) -> ArtifactRef:
        """
        Write JSON artifact. Creates artifacts/<artifact_id>/payload.json and meta.json.
        Computes sha256 of stored file. Overwrite impossible (new artifact_id each time).
        """
        artifact_id = generate_artifact_id()
        rel_dir = f"{ARTIFACTS_DIR}/{artifact_id}"
        abs_dir = self._run_root / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=False)  # exist_ok=False: no overwrite
        payload_path = abs_dir / PAYLOAD_JSON
        content_bytes = json.dumps(payload, indent=2).encode("utf-8")
        fd = os.open(
            str(payload_path),
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o644,
        )
        try:
            os.write(fd, content_bytes)
            os.fsync(fd)
        finally:
            os.close(fd)
        sha256 = _sha256_file(payload_path)
        created_at = _now_iso()
        rel_path = f"{rel_dir}/{PAYLOAD_JSON}"
        ref = ArtifactRef(
            artifact_id=artifact_id,
            run_id=self._run_id,
            artifact_type=artifact_type,
            storage_kind=StorageKind.JSON,
            rel_path=rel_path,
            sha256=sha256,
            created_at=created_at,
            producer_id=producer_id or "",
            producer_kind=producer_kind,
            artifact_name=artifact_name,
            input_artifact_refs=input_artifact_refs or [],
        )
        # Durability: payload exists and is fsync'd; now insert index row and commit.
        conn = open_index(self._workspace_root)
        try:
            insert_artifact(conn, ref)
            conn.commit()
        finally:
            conn.close()
        meta_path = abs_dir / META_JSON
        meta_path.write_text(
            json.dumps(ref.model_dump_for_meta(), indent=2),
            encoding="utf-8",
        )
        return ref

    def put_text(
        self,
        artifact_type: str,
        payload: str,
        metadata: dict[str, Any] | None = None,
        artifact_name: str | None = None,
        producer_id: str = "",
        producer_kind: ProducerKind = ProducerKind.SYSTEM,
        input_artifact_refs: list[str] | None = None,
    ) -> ArtifactRef:
        """
        Write plain-text artifact. Creates artifacts/<artifact_id>/payload.txt and meta.json.
        Computes sha256 of stored file. Overwrite impossible (new artifact_id each time).
        """
        artifact_id = generate_artifact_id()
        rel_dir = f"{ARTIFACTS_DIR}/{artifact_id}"
        abs_dir = self._run_root / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=False)
        payload_path = abs_dir / PAYLOAD_TXT
        content_bytes = payload.encode("utf-8")
        fd = os.open(
            str(payload_path),
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o644,
        )
        try:
            os.write(fd, content_bytes)
            os.fsync(fd)
        finally:
            os.close(fd)
        sha256 = _sha256_file(payload_path)
        created_at = _now_iso()
        rel_path = f"{rel_dir}/{PAYLOAD_TXT}"
        ref = ArtifactRef(
            artifact_id=artifact_id,
            run_id=self._run_id,
            artifact_type=artifact_type,
            storage_kind=StorageKind.TEXT,
            rel_path=rel_path,
            sha256=sha256,
            created_at=created_at,
            producer_id=producer_id or "",
            producer_kind=producer_kind,
            artifact_name=artifact_name,
            input_artifact_refs=input_artifact_refs or [],
        )
        conn = open_index(self._workspace_root)
        try:
            insert_artifact(conn, ref)
            conn.commit()
        finally:
            conn.close()
        meta_path = abs_dir / META_JSON
        meta_path.write_text(
            json.dumps(ref.model_dump_for_meta(), indent=2),
            encoding="utf-8",
        )
        return ref

    def get(self, ref: ArtifactRef) -> Any:
        """
        Read artifact by ref. Valid for json and text storage_kind (returns parsed JSON or str).
        Validates ref belongs to this run and path is confined to run root.
        """
        if ref.run_id != self._run_id:
            raise ValueError(
                f"ArtifactRef run_id {ref.run_id!r} does not match store run_id {self._run_id!r}"
            )
        if ref.storage_kind not in (StorageKind.JSON, StorageKind.TEXT):
            raise ValueError(
                f"get() only supports storage_kind=json or text, got {ref.storage_kind!r}"
            )
        path = resolve_artifact_path(self._run_root, ref.rel_path)
        if not path.exists():
            raise FileNotFoundError(f"Artifact payload not found: {path}")
        text = path.read_text(encoding="utf-8")
        if ref.storage_kind == StorageKind.JSON:
            return json.loads(text)
        return text

    def put_file(
        self,
        artifact_type: str,
        source_path: Path | str,
        metadata: dict[str, Any] | None = None,
        artifact_name: str | None = None,
        move: bool = False,
        producer_id: str = "",
        producer_kind: ProducerKind = ProducerKind.SYSTEM,
        input_artifact_refs: list[str] | None = None,
    ) -> ArtifactRef:
        """
        Store a file artifact. Default: copy (preserves caller's file). move=True for big blobs.
        Always computes sha256 of the stored file. Insert index row after payload is durable.
        """
        src = Path(source_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source file not found: {src}")
        # Safe filename: base name only (no path traversal)
        stored_name = src.name.strip() or FILE_ARTIFACT_DEFAULT_NAME
        if "/" in stored_name or "\\" in stored_name or stored_name in (".", ".."):
            stored_name = FILE_ARTIFACT_DEFAULT_NAME
        artifact_id = generate_artifact_id()
        rel_dir = f"{ARTIFACTS_DIR}/{artifact_id}"
        abs_dir = self._run_root / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=False)
        dest_path = abs_dir / stored_name
        if move:
            shutil.move(str(src), str(dest_path))
        else:
            shutil.copy2(str(src), str(dest_path))
        # fsync stored file for durability (O_RDWR so fsync works on Windows)
        fd = os.open(str(dest_path), os.O_RDWR)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        sha256 = _sha256_file(dest_path)
        created_at = _now_iso()
        rel_path = f"{rel_dir}/{stored_name}"
        ref = ArtifactRef(
            artifact_id=artifact_id,
            run_id=self._run_id,
            artifact_type=artifact_type,
            storage_kind=StorageKind.FILE,
            rel_path=rel_path,
            sha256=sha256,
            created_at=created_at,
            producer_id=producer_id or "",
            producer_kind=producer_kind,
            artifact_name=artifact_name,
            input_artifact_refs=input_artifact_refs or [],
        )
        conn = open_index(self._workspace_root)
        try:
            insert_artifact(conn, ref)
            conn.commit()
        finally:
            conn.close()
        meta_path = abs_dir / META_JSON
        meta_path.write_text(
            json.dumps(ref.model_dump_for_meta(), indent=2),
            encoding="utf-8",
        )
        return ref

    def open_path(self, ref: ArtifactRef) -> Path:
        """
        Return on-disk path for a file artifact. Only valid for storage_kind=file.
        Path is validated to be under run root (path traversal blocked).
        """
        if ref.run_id != self._run_id:
            raise ValueError(
                f"ArtifactRef run_id {ref.run_id!r} does not match store run_id {self._run_id!r}"
            )
        if ref.storage_kind != StorageKind.FILE:
            raise ValueError(
                f"open_path() only supports storage_kind=file, got {ref.storage_kind!r}"
            )
        path = resolve_artifact_path(self._run_root, ref.rel_path)
        if not path.exists():
            raise FileNotFoundError(f"Artifact file not found: {path}")
        return path

    def list(
        self,
        run_id: str | None = None,
        *,
        artifact_type: str | None = None,
        producer_id: str | None = None,
    ) -> list[ArtifactRef]:
        """List artifacts by run_id (default this store's run_id) with optional filters."""
        rid = run_id if run_id is not None else self._run_id
        conn = open_index(self._workspace_root)
        try:
            return list_artifacts(
                conn, rid, artifact_type=artifact_type, producer_id=producer_id
            )
        finally:
            conn.close()

    # --- Layer 1: envelope helpers (additive; do not change existing API) ---

    def put_envelope(
        self,
        schema_id: str,
        payload_model: BaseModel,
        meta_fields: dict[str, Any],
        artifact_name: str | None = None,
    ) -> ArtifactRef:
        """Build envelope, set payload_sha256, store via put_json. Returns ArtifactRef."""
        payload_dict = payload_model.model_dump(mode="json")
        payload_sha256 = hash_payload(payload_dict)
        created_at = meta_fields.get("created_at")
        if created_at is None:
            created_at = datetime.now(UTC)
        elif isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        meta = EnvelopeMeta(
            schema_id=schema_id,
            producer_id=meta_fields.get("producer_id", ""),
            producer_kind=meta_fields.get("producer_kind", "system"),
            created_at=created_at,
            inputs=meta_fields.get("inputs", []),
            payload_sha256=payload_sha256,
        )
        envelope = Envelope(meta=meta, payload=payload_dict)
        envelope_dict = envelope.model_dump(mode="json")
        return self.put_json(
            schema_id,
            envelope_dict,
            artifact_name=artifact_name,
            producer_id=meta.producer_id,
            producer_kind=ProducerKind(meta.producer_kind),
            input_artifact_refs=meta.inputs,
        )

    def get_envelope(self, artifact_ref: ArtifactRef) -> Envelope:
        """Load artifact JSON and return Envelope[Any]. No validation."""
        data = self.get(artifact_ref)
        return Envelope.model_validate(data)

    def get_validated(
        self, artifact_ref: ArtifactRef, validator: EnvelopeValidator
    ) -> tuple[EnvelopeMeta, BaseModel]:
        """Load envelope, validate via EnvelopeValidator, return (meta, payload_model)."""
        envelope = self.get_envelope(artifact_ref)
        return validator.validate(envelope)

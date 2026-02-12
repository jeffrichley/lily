"""ArtifactRef schema. Layer 0."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel
from pydantic.types import JsonValue


class StorageKind(StrEnum):
    """How the artifact is stored on disk."""

    JSON = "json"
    TEXT = "text"
    FILE = "file"


class ProducerKind(StrEnum):
    """Provenance: who produced the artifact."""

    TOOL = "tool"
    LLM = "llm"
    HUMAN = "human"
    SYSTEM = "system"


class ArtifactRef(BaseModel):
    """Reference to an artifact. Immutable; paths relative to run root."""

    artifact_id: str
    run_id: str
    artifact_type: str  # e.g. work_order.v1, gate_report.v1
    storage_kind: StorageKind
    rel_path: str  # relative to run root, e.g. artifacts/<id>/payload.json
    sha256: str
    created_at: str  # ISO 8601
    producer_id: str = ""
    producer_kind: ProducerKind = ProducerKind.SYSTEM
    artifact_name: str | None = None
    input_artifact_refs: list[str] = []  # artifact_ids

    def model_dump_for_meta(self) -> dict[str, JsonValue]:
        """Serialize for meta.json (no Pydantic wrapper).

        Returns:
            Dict suitable for meta.json.
        """
        return self.model_dump(mode="json")

    @classmethod
    def from_meta_dict(cls, d: dict[str, JsonValue]) -> ArtifactRef:
        """Deserialize from meta.json.

        Args:
            d: Dict loaded from meta.json.

        Returns:
            Validated ArtifactRef.
        """
        return cls.model_validate(d)

"""Layer 1: Envelope and EnvelopeMeta — universal typed wrapper (pure data, no IO)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, TypeVar

from pydantic import BaseModel

# SchemaId convention: <name>.v<integer> (e.g. work_order.v1, echo_payload.v1).
# Version lives only inside schema_id; no separate schema_version field.

ProducerKindLiteral = Literal["tool", "llm", "human", "system"]


class EnvelopeMeta(BaseModel):
    """Metadata for an enveloped payload. Pure data; no IO or registry."""

    model_config = {"extra": "forbid"}

    schema_id: str
    producer_id: str
    producer_kind: ProducerKindLiteral
    created_at: datetime
    inputs: list[str]  # artifact IDs only, not ArtifactRef
    payload_sha256: str


T = TypeVar("T")


class Envelope[T](BaseModel):
    """Generic envelope: meta + payload. Pure data; no registry, hashing, or IO."""

    meta: EnvelopeMeta
    payload: T

    model_config = {"extra": "forbid"}

"""Layer 1: EnvelopeValidator — boundary enforcement (meta + hash + schema)."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from lily.kernel.canonical import hash_payload
from lily.kernel.envelope import Envelope, EnvelopeMeta
from lily.kernel.schema_registry import SchemaRegistry, SchemaRegistryError


class EnvelopeValidationError(Exception):
    """Raised when envelope validation fails (hash mismatch, missing schema, invalid payload)."""

    pass


class EnvelopeValidator:
    """Validates envelope at boundary: meta structure, payload hash, payload schema."""

    def __init__(self, registry: SchemaRegistry) -> None:
        self._registry = registry

    def validate(self, envelope: Envelope) -> tuple[EnvelopeMeta, BaseModel]:
        """Validate envelope: meta, recompute hash vs payload_sha256, validate payload via registry.

        Returns (meta, payload_model). Raises EnvelopeValidationError on hash mismatch,
        unknown schema_id, or invalid payload shape.
        """
        meta = envelope.meta
        # 1. Meta structure is already validated by Envelope model
        # 2. Recompute payload hash and compare
        computed = hash_payload(envelope.payload)
        if computed != meta.payload_sha256:
            raise EnvelopeValidationError(
                f"Payload hash mismatch: computed {computed!r}, meta has {meta.payload_sha256!r}"
            )
        # 3. Validate payload via registry
        try:
            payload_model = self._registry.validate(meta.schema_id, envelope.payload)
        except SchemaRegistryError as e:
            raise EnvelopeValidationError(f"Schema validation failed: {e}") from e
        except ValidationError as e:
            raise EnvelopeValidationError(f"Payload validation failed: {e}") from e
        return (meta, payload_model)

"""Layer 1: EnvelopeValidator (Phase 4)."""

from datetime import UTC, datetime

import pytest
from pydantic import BaseModel

from lily.kernel.canonical import hash_payload
from lily.kernel.envelope import Envelope, EnvelopeMeta
from lily.kernel.envelope_validator import EnvelopeValidationError, EnvelopeValidator
from lily.kernel.schema_registry import SchemaRegistry


class EchoPayload(BaseModel):
    """Echo payload for tests."""

    echo: str


def _make_envelope(
    payload: dict, payload_sha256: str, schema_id: str = "echo_payload.v1"
) -> Envelope:
    meta = EnvelopeMeta(
        schema_id=schema_id,
        producer_id="test",
        producer_kind="tool",
        created_at=datetime.now(UTC),
        inputs=[],
        payload_sha256=payload_sha256,
    )
    return Envelope(meta=meta, payload=payload)


def test_validate_success() -> None:
    """Successful validation returns (meta, payload_model)."""
    reg = SchemaRegistry()
    reg.register("echo_payload.v1", EchoPayload)
    validator = EnvelopeValidator(reg)
    payload = {"echo": "hi"}
    correct_hash = hash_payload(payload)
    env = _make_envelope(payload, correct_hash)
    meta, model = validator.validate(env)
    assert meta.schema_id == "echo_payload.v1"
    assert isinstance(model, EchoPayload)
    assert model.echo == "hi"


def test_validate_hash_mismatch() -> None:
    """Hash mismatch raises EnvelopeValidationError."""
    reg = SchemaRegistry()
    reg.register("echo_payload.v1", EchoPayload)
    validator = EnvelopeValidator(reg)
    payload = {"echo": "hi"}
    env = _make_envelope(payload, "wrong_hash")
    with pytest.raises(
        EnvelopeValidationError, match=r"hash mismatch|Payload hash mismatch"
    ):
        validator.validate(env)


def test_validate_missing_schema() -> None:
    """Unknown schema_id in registry raises EnvelopeValidationError."""
    reg = SchemaRegistry()
    # do not register echo_payload.v1
    validator = EnvelopeValidator(reg)
    payload = {"echo": "hi"}
    env = _make_envelope(payload, hash_payload(payload), schema_id="echo_payload.v1")
    with pytest.raises(
        EnvelopeValidationError,
        match=r"Schema validation failed|Unknown schema_id",
    ):
        validator.validate(env)


def test_validate_invalid_payload() -> None:
    """Invalid payload shape raises EnvelopeValidationError."""
    reg = SchemaRegistry()
    reg.register("echo_payload.v1", EchoPayload)
    validator = EnvelopeValidator(reg)
    payload = {"wrong": "shape"}  # missing required "echo"
    env = _make_envelope(payload, hash_payload(payload))
    with pytest.raises(EnvelopeValidationError, match="Payload validation failed"):
        validator.validate(env)


def test_validator_recomputes_hash_from_payload_via_canonical() -> None:
    """EnvelopeValidator recomputes hash from payload via canonical serialization.

    Not from stored blob. So payload dict key order does not matter; hash is always
    canonical. This prevents whitespace/field-order differences from bypassing
    integrity.
    """
    reg = SchemaRegistry()
    reg.register("echo_payload.v1", EchoPayload)
    validator = EnvelopeValidator(reg)
    # Hash must be computed from canonical form (sorted keys). Payload with keys in
    # different order still produces same canonical bytes.
    payload_arbitrary_order = {"b": "y", "a": "x", "echo": "hi"}
    canonical_hash = hash_payload(
        {"echo": "hi", "a": "x", "b": "y"}
    )  # same logical payload
    assert hash_payload(payload_arbitrary_order) == canonical_hash
    env = _make_envelope(payload_arbitrary_order, canonical_hash)
    _meta, model = validator.validate(env)
    assert model.echo == "hi"

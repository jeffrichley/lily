"""Layer 1: Envelope and EnvelopeMeta — core types (Phase 1)."""

from datetime import UTC, datetime

import pytest

from lily.kernel.envelope import Envelope, EnvelopeMeta


def test_envelope_meta_fields() -> None:
    """EnvelopeMeta has required fields and producer_kind is Literal."""
    meta = EnvelopeMeta(
        schema_id="echo_payload.v1",
        producer_id="test-runner",
        producer_kind="tool",
        created_at=datetime.now(UTC),
        inputs=[],
        payload_sha256="abc123",
    )
    assert meta.schema_id == "echo_payload.v1"
    assert meta.producer_kind == "tool"
    assert meta.inputs == []


def test_envelope_meta_rejects_invalid_producer_kind() -> None:
    """producer_kind must be one of tool, llm, human, system."""
    with pytest.raises(ValueError, match=r"producer_kind|Literal"):
        EnvelopeMeta(
            schema_id="x.v1",
            producer_id="",
            producer_kind="invalid",  # type: ignore[arg-type]
            created_at=datetime.now(UTC),
            inputs=[],
            payload_sha256="",
        )


def test_envelope_meta_inputs_artifact_ids_only() -> None:
    """Inputs is list[str] (artifact IDs), not ArtifactRef."""
    meta = EnvelopeMeta(
        schema_id="x.v1",
        producer_id="",
        producer_kind="system",
        created_at=datetime.now(UTC),
        inputs=["id1", "id2"],
        payload_sha256="",
    )
    assert meta.inputs == ["id1", "id2"]


def test_envelope_roundtrip_serialize_deserialize_dict() -> None:
    """Round-trip serialize/deserialize Envelope[dict]."""
    meta = EnvelopeMeta(
        schema_id="work_order.v1",
        producer_id="cli",
        producer_kind="human",
        created_at=datetime.now(UTC),
        inputs=[],
        payload_sha256="deadbeef",
    )
    payload = {"task": "hello", "steps": []}
    env = Envelope(meta=meta, payload=payload)
    data = env.model_dump(mode="json")
    restored = Envelope.model_validate(data)
    assert restored.meta.schema_id == env.meta.schema_id
    assert restored.payload == payload


def test_envelope_roundtrip_json_bytes() -> None:
    """Envelope[dict] round-trips via model_dump_json / model_validate_json."""
    meta = EnvelopeMeta(
        schema_id="echo_payload.v1",
        producer_id="test",
        producer_kind="llm",
        created_at=datetime.now(UTC),
        inputs=["art-1"],
        payload_sha256="sha",
    )
    env = Envelope(meta=meta, payload={"echo": "hi"})
    raw = env.model_dump_json()
    restored = Envelope.model_validate_json(raw)
    assert restored.meta.schema_id == "echo_payload.v1"
    assert restored.payload == {"echo": "hi"}


def test_envelope_meta_forbids_extra_fields() -> None:
    """EnvelopeMeta rejects extra fields (extra=forbid)."""
    with pytest.raises(ValueError, match=r"extra|forbid|not permitted"):
        EnvelopeMeta(
            schema_id="x.v1",
            producer_id="",
            producer_kind="system",
            created_at=datetime.now(UTC),
            inputs=[],
            payload_sha256="",
            extra_field="not_allowed",  # type: ignore[arg-type]
        )


def test_envelope_pure_data_no_extra_fields() -> None:
    """Envelope rejects extra fields (extra=forbid)."""
    meta = EnvelopeMeta(
        schema_id="x.v1",
        producer_id="",
        producer_kind="system",
        created_at=datetime.now(UTC),
        inputs=[],
        payload_sha256="",
    )
    with pytest.raises(ValueError, match=r"extra|forbid|not permitted"):
        Envelope(meta=meta, payload={}, unexpected="field")  # type: ignore[call-arg]

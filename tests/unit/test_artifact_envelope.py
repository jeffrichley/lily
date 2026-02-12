"""Layer 1: ArtifactStore envelope helpers (Phase 5)."""

from pathlib import Path

import pytest
from pydantic import BaseModel

from lily.kernel import (
    ArtifactStore,
    EnvelopeValidationError,
    EnvelopeValidator,
    SchemaRegistry,
    create_run,
)


class EchoPayload(BaseModel):
    """Minimal payload for envelope round-trip tests."""

    echo: str


def test_put_envelope_get_envelope_roundtrip(workspace_root: Path) -> None:
    """put_envelope then get_envelope returns equivalent envelope (round-trip)."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    payload = EchoPayload(echo="hello")
    meta_fields = {
        "producer_id": "test",
        "producer_kind": "tool",
        "inputs": [],
    }
    ref = store.put_envelope(
        "echo_payload.v1", payload, meta_fields, artifact_name="echo"
    )
    assert ref.artifact_id
    assert ref.artifact_type == "echo_payload.v1"
    envelope = store.get_envelope(ref)
    assert envelope.meta.schema_id == "echo_payload.v1"
    assert envelope.payload == {"echo": "hello"}


def test_get_validated_returns_meta_and_model(workspace_root: Path) -> None:
    """get_validated enforces schema and hash; returns (meta, payload_model)."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    reg = SchemaRegistry()
    reg.register("echo_payload.v1", EchoPayload)
    validator = EnvelopeValidator(reg)
    payload = EchoPayload(echo="validated")
    ref = store.put_envelope(
        "echo_payload.v1",
        payload,
        {"producer_id": "cli", "producer_kind": "human", "inputs": []},
    )
    meta, model = store.get_validated(ref, validator)
    assert meta.schema_id == "echo_payload.v1"
    assert isinstance(model, EchoPayload)
    assert model.echo == "validated"


def test_get_validated_fails_when_schema_not_registered(workspace_root: Path) -> None:
    """get_validated raises when schema_id is not in registry."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    reg = SchemaRegistry()
    reg.register("echo_payload.v1", EchoPayload)
    payload = EchoPayload(echo="x")
    ref = store.put_envelope(
        "echo_payload.v1",
        payload,
        {"producer_id": "", "producer_kind": "system", "inputs": []},
    )
    reg2 = SchemaRegistry()  # fresh registry without echo_payload.v1
    validator2 = EnvelopeValidator(reg2)
    with pytest.raises(EnvelopeValidationError):
        store.get_validated(ref, validator2)


def test_get_validated_fails_on_schema_drift(workspace_root: Path) -> None:
    """If the registered model is changed later (stricter schema), get_validated fails.

    Store envelope with EchoPayload (echo only). Then register a stricter model with
    an extra required field. get_validated must fail — desired behavior, not a bug.
    """
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    payload = EchoPayload(echo="hi")
    ref = store.put_envelope(
        "echo_payload.v1",
        payload,
        {"producer_id": "", "producer_kind": "system", "inputs": []},
    )

    # Stricter model: same schema_id but now requires extra required field
    class EchoPayloadStrict(BaseModel):
        echo: str
        version: int  # required

    reg = SchemaRegistry()
    reg.register("echo_payload.v1", EchoPayloadStrict, override=True)
    validator = EnvelopeValidator(reg)
    with pytest.raises(EnvelopeValidationError):
        store.get_validated(ref, validator)


def test_integration_create_run_put_envelope_get_validated_typed(
    workspace_root: Path,
) -> None:
    """Integration: create run, put_envelope, get_validated, assert payload typed.

    Layer 0 + Layer 1 boundary: one toy schema (echo.v1), full round-trip,
    typed payload.
    """
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    reg = SchemaRegistry()
    reg.register("echo_payload.v1", EchoPayload)
    validator = EnvelopeValidator(reg)
    payload = EchoPayload(echo="airtight")
    ref = store.put_envelope(
        "echo_payload.v1",
        payload,
        {"producer_id": "integration", "producer_kind": "tool", "inputs": []},
        artifact_name="echo",
    )
    meta, model = store.get_validated(ref, validator)
    assert meta.schema_id == "echo_payload.v1"
    assert isinstance(model, EchoPayload)
    assert model.echo == "airtight"

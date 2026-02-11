"""Layer 1: Schema Registry (Phase 3)."""

import pytest
from pydantic import BaseModel, ValidationError

from lily.kernel.schema_registry import SchemaRegistry, SchemaRegistryError


class EchoPayload(BaseModel):
    """Toy schema for tests (no domain logic)."""

    echo: str


class EchoPayloadV2(BaseModel):
    echo: str
    version: int = 2


def test_register_get():
    """Register and get returns the model class."""
    reg = SchemaRegistry()
    reg.register("echo_payload.v1", EchoPayload)
    model = reg.get("echo_payload.v1")
    assert model is EchoPayload


def test_validate_returns_typed_instance():
    """validate returns an instance of the registered model."""
    reg = SchemaRegistry()
    reg.register("echo_payload.v1", EchoPayload)
    instance = reg.validate("echo_payload.v1", {"echo": "hi"})
    assert isinstance(instance, EchoPayload)
    assert instance.echo == "hi"


def test_duplicate_registration_raises():
    """Duplicate registration raises unless override=True."""
    reg = SchemaRegistry()
    reg.register("echo_payload.v1", EchoPayload)
    with pytest.raises(ValueError, match="already registered"):
        reg.register("echo_payload.v1", EchoPayload)
    with pytest.raises(ValueError, match="already registered"):
        reg.register("echo_payload.v1", EchoPayloadV2)


def test_override_replaces_registration():
    """override=True allows replacing a registration."""
    reg = SchemaRegistry()
    reg.register("echo_payload.v1", EchoPayload)
    reg.register("echo_payload.v1", EchoPayloadV2, override=True)
    instance = reg.validate("echo_payload.v1", {"echo": "x", "version": 2})
    assert isinstance(instance, EchoPayloadV2)
    assert instance.version == 2


def test_get_unknown_schema_raises():
    """get() with unknown schema_id raises SchemaRegistryError."""
    reg = SchemaRegistry()
    with pytest.raises(SchemaRegistryError, match="Unknown schema_id"):
        reg.get("unknown.v1")


def test_validate_unknown_schema_raises():
    """validate() with unknown schema_id raises SchemaRegistryError."""
    reg = SchemaRegistry()
    with pytest.raises(SchemaRegistryError, match="Unknown schema_id"):
        reg.validate("unknown.v1", {})


def test_validate_invalid_payload_raises():
    """validate() with wrong shape raises Pydantic ValidationError (clear validation errors)."""
    reg = SchemaRegistry()
    reg.register("echo_payload.v1", EchoPayload)
    with pytest.raises(ValidationError):
        reg.validate("echo_payload.v1", {"wrong": "shape"})
    with pytest.raises(ValidationError):
        reg.validate("echo_payload.v1", "not a dict")
    with pytest.raises(ValidationError):
        reg.validate("echo_payload.v1", {"echo": 123})  # wrong type for echo


def test_registry_stores_model_class_only_no_per_validation_state():
    """SchemaRegistry stores the model class only; no state per validation. Safe to reuse across runs."""
    reg = SchemaRegistry()
    reg.register("echo_payload.v1", EchoPayload)
    a = reg.validate("echo_payload.v1", {"echo": "first"})
    b = reg.validate("echo_payload.v1", {"echo": "second"})
    assert a.echo == "first"
    assert b.echo == "second"
    assert reg.get("echo_payload.v1") is EchoPayload  # stored by reference (class)

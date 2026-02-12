"""Layer 4: PolicyViolation schema and envelope validation."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lily.kernel import (
    Envelope,
    EnvelopeMeta,
    EnvelopeValidator,
    PolicyViolationPayload,
    hash_payload,
    register_policy_schemas,
)
from lily.kernel.policy_models import POLICY_VIOLATION_SCHEMA_ID
from lily.kernel.schema_registry import SchemaRegistry


def test_valid_payload_passes() -> None:
    """PolicyViolationPayload accepts valid fields."""
    ts = datetime.now(UTC)
    payload = PolicyViolationPayload(
        step_id="s1",
        violation_type="tool_not_allowed",
        details="local_command not in allowed_tools",
        timestamp=ts,
    )
    assert payload.step_id == "s1"
    assert payload.violation_type == "tool_not_allowed"
    assert payload.details == "local_command not in allowed_tools"
    assert payload.timestamp == ts


@pytest.mark.parametrize(
    "keys_to_include",
    [
        ("step_id", "violation_type", "details"),  # missing timestamp
        ("step_id", "violation_type", "timestamp"),  # missing details
        ("step_id", "details", "timestamp"),  # missing violation_type
        ("violation_type", "details", "timestamp"),  # missing step_id
    ],
    ids=[
        "missing_timestamp",
        "missing_details",
        "missing_violation_type",
        "missing_step_id",
    ],
)
def test_missing_required_fields_fail(
    keys_to_include: tuple[str, ...],
) -> None:
    """Missing required fields raise ValidationError."""
    ts = datetime.now(UTC)
    base = {
        "step_id": "s1",
        "violation_type": "x",
        "details": "x",
        "timestamp": ts,
    }
    kwargs = {k: base[k] for k in keys_to_include}
    with pytest.raises(ValidationError):
        PolicyViolationPayload(**kwargs)


def test_schema_registry_can_validate_policy_violation_v1() -> None:
    """SchemaRegistry can validate policy_violation.v1 after register_policy_schemas."""
    reg = SchemaRegistry()
    register_policy_schemas(reg)
    assert reg.get(POLICY_VIOLATION_SCHEMA_ID) is PolicyViolationPayload

    payload_dict = {
        "step_id": "s1",
        "violation_type": "write_denied",
        "details": "wrote to /etc/passwd",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    instance = reg.validate(POLICY_VIOLATION_SCHEMA_ID, payload_dict)
    assert isinstance(instance, PolicyViolationPayload)
    assert instance.step_id == "s1"
    assert instance.violation_type == "write_denied"


def test_envelope_validation_works() -> None:
    """Envelope with policy_violation.v1 payload validates via EnvelopeValidator."""
    reg = SchemaRegistry()
    register_policy_schemas(reg)

    payload = PolicyViolationPayload(
        step_id="s1",
        violation_type="tool_not_allowed",
        details="executor kind not in allowlist",
        timestamp=datetime.now(UTC),
    )
    payload_dict = payload.model_dump(mode="json")
    payload_sha256 = hash_payload(payload_dict)

    meta = EnvelopeMeta(
        schema_id=POLICY_VIOLATION_SCHEMA_ID,
        producer_id="kernel",
        producer_kind="system",
        created_at=datetime.now(UTC),
        inputs=[],
        payload_sha256=payload_sha256,
    )
    envelope = Envelope(meta=meta, payload=payload_dict)

    validator = EnvelopeValidator(reg)
    meta_out, payload_model = validator.validate(envelope)
    assert meta_out.schema_id == POLICY_VIOLATION_SCHEMA_ID
    assert isinstance(payload_model, PolicyViolationPayload)
    assert payload_model.step_id == "s1"
    assert payload_model.violation_type == "tool_not_allowed"

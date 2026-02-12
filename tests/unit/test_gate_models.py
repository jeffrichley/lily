"""Layer 3: Gate result payload and schema registration."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lily.kernel.gate_models import (
    GATE_RESULT_SCHEMA_ID,
    GateResultPayload,
    GateStatus,
    register_gate_schemas,
)
from lily.kernel.schema_registry import SchemaRegistry, SchemaRegistryError


def test_payload_validates_correctly():
    """GateResultPayload accepts valid fields."""
    ts = datetime.now(UTC)
    payload = GateResultPayload(
        gate_id="g1",
        status=GateStatus.PASSED,
        reason=None,
        log_artifact_ids=[],
        metrics=None,
        timestamp=ts,
    )
    assert payload.gate_id == "g1"
    assert payload.status == GateStatus.PASSED
    assert payload.reason is None
    assert payload.log_artifact_ids == []
    assert payload.metrics is None
    assert payload.timestamp == ts

    payload2 = GateResultPayload(
        gate_id="g2",
        status=GateStatus.FAILED,
        reason="exit code 1",
        log_artifact_ids=["art-a", "art-b"],
        metrics={"duration_s": 0.5},
        timestamp=ts,
    )
    assert payload2.status == GateStatus.FAILED
    assert payload2.reason == "exit code 1"
    assert payload2.log_artifact_ids == ["art-a", "art-b"]
    assert payload2.metrics == {"duration_s": 0.5}


def test_missing_required_fields_fail():
    """Missing required fields raise ValidationError."""
    with pytest.raises(ValidationError):
        GateResultPayload(
            gate_id="g1",
            status=GateStatus.PASSED,
            # missing timestamp
        )
    with pytest.raises(ValidationError):
        GateResultPayload(
            gate_id="g1",
            timestamp=datetime.now(UTC),
            # missing status
        )
    with pytest.raises(ValidationError):
        GateResultPayload(
            status=GateStatus.PASSED,
            timestamp=datetime.now(UTC),
            # missing gate_id
        )


def test_invalid_status_fails():
    """Invalid status value raises ValidationError."""
    with pytest.raises(ValidationError):
        GateResultPayload(
            gate_id="g1",
            status="invalid",
            timestamp=datetime.now(UTC),
        )


def test_schema_registry_can_validate_gate_result_v1():
    """SchemaRegistry can validate gate_result.v1 after register_gate_schemas."""
    reg = SchemaRegistry()
    register_gate_schemas(reg)
    assert reg.get(GATE_RESULT_SCHEMA_ID) is GateResultPayload

    payload_dict = {
        "gate_id": "my-gate",
        "status": "passed",
        "reason": None,
        "log_artifact_ids": [],
        "metrics": None,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    instance = reg.validate(GATE_RESULT_SCHEMA_ID, payload_dict)
    assert isinstance(instance, GateResultPayload)
    assert instance.gate_id == "my-gate"
    assert instance.status == GateStatus.PASSED


def test_schema_registry_unknown_schema_raises():
    """get/validate with unknown schema_id raises SchemaRegistryError."""
    reg = SchemaRegistry()
    register_gate_schemas(reg)
    with pytest.raises(SchemaRegistryError, match="Unknown schema_id"):
        reg.get("other.v1")
    with pytest.raises(SchemaRegistryError, match="Unknown schema_id"):
        reg.validate("other.v1", {})

"""Unit tests for executable envelope model validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from lily.runtime.executables.models import (
    CallerContext,
    ExecutableKind,
    ExecutableRequest,
    ExecutableResult,
    ExecutableStatus,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionMetadata,
    ExecutionMetrics,
    GateDecision,
)


def _request_payload() -> dict[str, object]:
    """Build a valid executable request payload."""
    return {
        "run_id": "run-001",
        "step_id": "step-001",
        "parent_step_id": None,
        "caller": CallerContext(
            supervisor_id="supervisor.v1",
            active_agent="risk_analyst",
        ),
        "target": {
            "executable_id": "nightly_security_council",
            "executable_kind": ExecutableKind.WORKFLOW,
            "version": "v1",
        },
        "objective": "Run nightly council analysis.",
        "input": {"topic": "security posture"},
        "context": ExecutionContext(
            memory_refs=("mem-1",),
            artifact_refs=("artifact-1",),
            constraints=ExecutionConstraints(
                timeout_ms=30_000,
                retry_budget=2,
                cost_budget=4.5,
            ),
        ),
        "metadata": ExecutionMetadata(
            trace_tags={"channel": "ops"},
            created_at_utc="2026-03-04T20:00:00Z",
        ),
    }


@pytest.mark.unit
def test_executable_request_accepts_valid_payload() -> None:
    """ExecutableRequest should validate with required identity and caller context."""
    # Arrange - build a valid canonical request payload.
    payload = _request_payload()

    # Act - validate payload against executable request schema.
    request = ExecutableRequest.model_validate(payload)

    # Assert - run/step identity and caller authority fields are preserved.
    assert request.run_id == "run-001"
    assert request.step_id == "step-001"
    assert request.caller.supervisor_id == "supervisor.v1"
    assert request.caller.active_agent == "risk_analyst"
    assert request.target.executable_kind == ExecutableKind.WORKFLOW


@pytest.mark.unit
def test_executable_request_requires_identity_fields() -> None:
    """ExecutableRequest should reject missing run-step identity fields."""
    # Arrange - remove required run identifier from an otherwise valid payload.
    payload = _request_payload()
    payload.pop("run_id")

    # Act - validate and capture field-specific validation failure.
    with pytest.raises(ValidationError) as exc_info:
        ExecutableRequest.model_validate(payload)

    # Assert - validation error identifies the missing required field.
    assert "run_id" in str(exc_info.value)


@pytest.mark.unit
def test_executable_request_rejects_extra_fields() -> None:
    """ExecutableRequest should reject undeclared fields at all levels."""
    # Arrange - inject an undeclared top-level field.
    payload = _request_payload()
    payload["unexpected"] = "nope"

    # Act - validate and capture strict-schema failure.
    with pytest.raises(ValidationError) as exc_info:
        ExecutableRequest.model_validate(payload)

    # Assert - extra field is rejected by strict model config.
    assert "Extra inputs are not permitted" in str(exc_info.value)


@pytest.mark.unit
def test_executable_request_requires_caller_authority_fields() -> None:
    """Caller context should reject missing authority identifiers."""
    # Arrange - omit active_agent from caller authority context.
    payload = _request_payload()
    payload["caller"] = {"supervisor_id": "supervisor.v1"}

    # Act - validate and capture nested caller validation failure.
    with pytest.raises(ValidationError) as exc_info:
        ExecutableRequest.model_validate(payload)

    # Assert - nested required authority field is reported.
    assert "active_agent" in str(exc_info.value)


@pytest.mark.unit
def test_executable_result_error_required_when_status_is_not_ok() -> None:
    """Error payload must be present for non-ok execution status."""
    # Arrange - build an error-status result payload with missing error envelope.
    payload = {
        "run_id": "run-001",
        "step_id": "step-001",
        "status": ExecutableStatus.ERROR,
        "output": {},
        "references": (),
        "artifacts": (),
        "metrics": ExecutionMetrics(duration_ms=42),
        "error": None,
    }

    # Act - validate and capture status/error consistency failure.
    with pytest.raises(ValidationError) as exc_info:
        ExecutableResult.model_validate(payload)

    # Assert - validator enforces non-ok statuses to include error payload.
    assert "error is required when status is not 'ok'" in str(exc_info.value)


@pytest.mark.unit
def test_executable_result_rejects_error_payload_when_status_ok() -> None:
    """Error payload must be absent for ok execution status."""
    # Arrange - build an ok-status result payload that incorrectly includes error data.
    payload = {
        "run_id": "run-001",
        "step_id": "step-001",
        "status": ExecutableStatus.OK,
        "output": {"result": "done"},
        "references": (),
        "artifacts": (),
        "metrics": ExecutionMetrics(duration_ms=21),
        "error": {
            "code": "unexpected_error",
            "message": "should not exist",
            "retryable": False,
            "data": {},
        },
    }

    # Act - validate and capture status/error consistency failure.
    with pytest.raises(ValidationError) as exc_info:
        ExecutableResult.model_validate(payload)

    # Assert - validator enforces ok statuses to omit error payload.
    assert "error must be null when status is 'ok'" in str(exc_info.value)


@pytest.mark.unit
def test_gate_decision_rejects_unknown_outcome() -> None:
    """GateDecision should enforce deterministic outcome enum values."""
    # Arrange - create decision payload with non-canonical outcome value.
    payload = {
        "run_id": "run-001",
        "step_id": "step-001",
        "outcome": "continue",
        "reason_code": "policy_unknown",
        "reason_message": "not deterministic",
        "next_step_hint": None,
    }

    # Act - validate and capture enum validation failure.
    with pytest.raises(ValidationError) as exc_info:
        GateDecision.model_validate(payload)

    # Assert - non-enum outcome is rejected deterministically.
    assert "outcome" in str(exc_info.value)

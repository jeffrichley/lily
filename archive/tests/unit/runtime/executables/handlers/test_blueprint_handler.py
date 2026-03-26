"""Unit tests for blueprint executable adapter handler."""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from pydantic import BaseModel, ConfigDict

from lily.blueprints.models import (
    BlueprintError,
    BlueprintErrorCode,
    BlueprintRunEnvelope,
)
from lily.runtime.executables.handlers.blueprint_handler import (
    BlueprintExecutableHandler,
)
from lily.runtime.executables.models import (
    CallerContext,
    ExecutableKind,
    ExecutableRef,
    ExecutableRequest,
    ExecutableStatus,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionMetadata,
)


class _BindingsModel(BaseModel):
    """Bindings schema fixture for blueprint adapter tests."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: str


class _BlueprintFixture:
    """Blueprint fixture with deterministic compile result."""

    id = "nightly_security_council"
    version = "v1"
    summary = "Security council blueprint"
    bindings_schema = _BindingsModel
    input_schema = _BindingsModel
    output_schema = _BindingsModel

    @staticmethod
    def compile(bindings: BaseModel) -> _CompiledRunnableFixture:
        """Return compiled runnable fixture."""
        return _CompiledRunnableFixture(mode=str(bindings.mode))


class _CompiledRunnableFixture:
    """Compiled blueprint runnable fixture."""

    def __init__(self, *, mode: str) -> None:
        """Store mode value for response payload verification."""
        self._mode = mode

    def invoke(self, raw_input: Mapping[str, object]) -> BlueprintRunEnvelope:
        """Return deterministic blueprint run envelope."""
        return BlueprintRunEnvelope(
            status="ok",
            artifacts=("summary.md",),
            references=("ref://council",),
            payload={"mode": self._mode, "topic": raw_input.get("topic", "")},
        )


class _BlueprintRegistryFixture:
    """Blueprint registry fixture for adapter tests."""

    def resolve(self, blueprint_id: str) -> _BlueprintFixture:
        """Resolve known blueprint id or raise deterministic error."""
        if blueprint_id != "nightly_security_council":
            raise BlueprintError(
                BlueprintErrorCode.NOT_FOUND,
                "Error: blueprint not found.",
                data={"blueprint": blueprint_id},
            )
        return _BlueprintFixture()

    @staticmethod
    def validate_bindings(
        *, blueprint_id: str, raw_bindings: dict[str, object]
    ) -> BaseModel:
        """Validate bindings fixture or raise deterministic validation error."""
        if blueprint_id != "nightly_security_council":
            raise BlueprintError(
                BlueprintErrorCode.NOT_FOUND,
                "Error: blueprint not found.",
                data={"blueprint": blueprint_id},
            )
        return _BindingsModel.model_validate(raw_bindings)


def _request(*, blueprint_id: str = "nightly_security_council") -> ExecutableRequest:
    """Create blueprint executable request fixture."""
    return ExecutableRequest(
        run_id="run-001",
        step_id="step-001",
        caller=CallerContext(supervisor_id="supervisor.v1", active_agent="default"),
        target=ExecutableRef(
            executable_id=blueprint_id,
            executable_kind=ExecutableKind.BLUEPRINT,
        ),
        objective="Execute blueprint.",
        input={"bindings": {"mode": "strict"}, "run_input": {"topic": "deps"}},
        context=ExecutionContext(
            memory_refs=(),
            artifact_refs=(),
            constraints=ExecutionConstraints(),
        ),
        metadata=ExecutionMetadata(
            trace_tags={}, created_at_utc="2026-03-04T20:00:00Z"
        ),
    )


@pytest.mark.unit
def test_blueprint_handler_maps_successful_run_to_ok_result() -> None:
    """Blueprint handler should normalize successful run into executable result."""
    # Arrange - create blueprint handler with deterministic registry fixture.
    handler = BlueprintExecutableHandler(registry=_BlueprintRegistryFixture())
    request = _request()

    # Act - handle blueprint request through adapter boundary.
    result = handler.handle(request)

    # Assert - result is successful with blueprint payload/references/artifacts.
    assert result.status == ExecutableStatus.OK
    assert result.error is None
    assert result.output["mode"] == "strict"
    assert result.references == ("ref://council",)
    assert result.artifacts == ("summary.md",)


@pytest.mark.unit
def test_blueprint_handler_maps_registry_errors_deterministically() -> None:
    """Blueprint handler should map registry failure to deterministic error result."""
    # Arrange - create handler and request for unknown blueprint id.
    handler = BlueprintExecutableHandler(registry=_BlueprintRegistryFixture())
    request = _request(blueprint_id="unknown_blueprint")

    # Act - handle unknown blueprint request.
    result = handler.handle(request)

    # Assert - unknown blueprint maps to blueprint_not_found error envelope.
    assert result.status == ExecutableStatus.ERROR
    assert result.error is not None
    assert result.error.code == BlueprintErrorCode.NOT_FOUND.value

"""Executable adapter for blueprint compilation and invocation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, cast

from pydantic import BaseModel

from lily.blueprints.models import (
    Blueprint,
    BlueprintError,
    BlueprintRunEnvelope,
    BlueprintRunStatus,
)
from lily.runtime.executables.handlers._common import (
    elapsed_ms,
    error_result,
    require_input_value,
    started_timer,
)
from lily.runtime.executables.handlers.base import BaseExecutableHandler
from lily.runtime.executables.models import (
    ExecutableError,
    ExecutableKind,
    ExecutableRequest,
    ExecutableResult,
    ExecutableStatus,
    ExecutionMetrics,
)


class _CompiledBlueprintRunnable(Protocol):
    """Protocol for compiled blueprint runnable targets."""

    def invoke(self, raw_input: Mapping[str, object]) -> BlueprintRunEnvelope:
        """Execute one compiled blueprint request."""


class BlueprintRegistryPort(Protocol):
    """Protocol for blueprint registry operations used by adapter."""

    def resolve(self, blueprint_id: str) -> Blueprint:
        """Resolve one blueprint by id."""

    def validate_bindings(
        self,
        *,
        blueprint_id: str,
        raw_bindings: Mapping[str, object],
    ) -> BaseModel:
        """Validate bindings payload for one blueprint id."""


class BlueprintExecutableHandler(BaseExecutableHandler):
    """Adapter handler for blueprint runtime path."""

    kind = ExecutableKind.BLUEPRINT

    def __init__(self, registry: BlueprintRegistryPort) -> None:
        """Store blueprint registry dependency.

        Args:
            registry: Blueprint registry service.
        """
        self._registry = registry

    def handle(self, request: ExecutableRequest) -> ExecutableResult:
        """Execute one blueprint request via compile + invoke path."""
        started = started_timer()
        try:
            bindings = _require_mapping(request.input, key="bindings")
            run_input = _require_mapping(request.input, key="run_input")
        except (TypeError, ValueError) as exc:
            return error_result(
                request=request,
                error=ExecutableError(
                    code="adapter_input_invalid",
                    message=f"Error: blueprint adapter input is invalid: {exc}",
                    retryable=False,
                    data={"target_id": request.target.executable_id},
                ),
                duration_ms=elapsed_ms(started),
            )
        try:
            blueprint = self._registry.resolve(request.target.executable_id)
            validated_bindings = self._registry.validate_bindings(
                blueprint_id=blueprint.id,
                raw_bindings=bindings,
            )
            compiled = cast(
                _CompiledBlueprintRunnable, blueprint.compile(validated_bindings)
            )
            run = compiled.invoke(run_input)
        except BlueprintError as exc:
            return error_result(
                request=request,
                error=ExecutableError(
                    code=exc.code.value,
                    message=str(exc),
                    retryable=False,
                    data=exc.data,
                ),
                duration_ms=elapsed_ms(started),
            )

        status = (
            ExecutableStatus.OK
            if run.status == BlueprintRunStatus.OK
            else ExecutableStatus.ERROR
        )
        return ExecutableResult(
            run_id=request.run_id,
            step_id=request.step_id,
            status=status,
            output=run.payload,
            references=run.references,
            artifacts=run.artifacts,
            metrics=ExecutionMetrics(duration_ms=elapsed_ms(started)),
            error=(
                None
                if status == ExecutableStatus.OK
                else ExecutableError(
                    code="blueprint_execution_failed",
                    message="Error: blueprint runtime returned error status.",
                    retryable=False,
                    data={"target_id": request.target.executable_id},
                )
            ),
        )


def _require_mapping(
    payload: dict[str, object],
    *,
    key: str,
) -> dict[str, object]:
    """Require one mapping payload field for blueprint adapter requests."""
    value = require_input_value(payload, key=key, expected_type=dict)
    return {str(k): cast(object, v) for k, v in value.items()}

"""Shared adapter helpers for executable handler implementations."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from lily.commands.types import CommandResult, CommandStatus
from lily.runtime.executables.models import (
    ExecutableError,
    ExecutableRequest,
    ExecutableResult,
    ExecutableStatus,
    ExecutionMetrics,
)


@dataclass(frozen=True)
class ResultArtifacts:
    """Optional references/artifacts emitted by adapters."""

    references: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()


def started_timer() -> float:
    """Return timer start for deterministic duration tracking."""
    return perf_counter()


def elapsed_ms(started: float) -> int:
    """Return elapsed milliseconds from monotonic timer start."""
    elapsed = perf_counter() - started
    return int(max(elapsed, 0) * 1000)


def command_to_result(
    *,
    request: ExecutableRequest,
    command: CommandResult,
    duration_ms: int,
    links: ResultArtifacts | None = None,
    output: dict[str, object] | None = None,
) -> ExecutableResult:
    """Convert command-result envelope to canonical executable result."""
    resolved_links = links if links is not None else ResultArtifacts()
    command_data = _normalize_command_data(command.data)
    normalized_output = output if output is not None else {"message": command.message}
    if command.status == CommandStatus.OK:
        return ExecutableResult(
            run_id=request.run_id,
            step_id=request.step_id,
            status=ExecutableStatus.OK,
            output={**normalized_output, "command_data": command_data},
            references=resolved_links.references,
            artifacts=resolved_links.artifacts,
            metrics=ExecutionMetrics(duration_ms=duration_ms),
            error=None,
        )
    return ExecutableResult(
        run_id=request.run_id,
        step_id=request.step_id,
        status=ExecutableStatus.ERROR,
        output=normalized_output,
        references=resolved_links.references,
        artifacts=resolved_links.artifacts,
        metrics=ExecutionMetrics(duration_ms=duration_ms),
        error=ExecutableError(
            code=command.code,
            message=command.message,
            retryable=False,
            data=command_data,
        ),
    )


def error_result(
    *,
    request: ExecutableRequest,
    error: ExecutableError,
    duration_ms: int,
) -> ExecutableResult:
    """Build canonical deterministic error result for adapter boundaries."""
    return ExecutableResult(
        run_id=request.run_id,
        step_id=request.step_id,
        status=ExecutableStatus.ERROR,
        output={},
        references=(),
        artifacts=(),
        metrics=ExecutionMetrics(duration_ms=duration_ms),
        error=error,
    )


def require_input_value[T](
    payload: dict[str, object],
    *,
    key: str,
    expected_type: type[T],
) -> T:
    """Validate one typed adapter input field from request payload.

    Args:
        payload: Request input payload.
        key: Required field key.
        expected_type: Required runtime type.

    Returns:
        Typed field value.

    Raises:
        ValueError: If key is missing.
        TypeError: If value type does not match expectation.
    """
    if key not in payload:
        raise ValueError(f"Missing required input field '{key}'.")
    value = payload[key]
    if not isinstance(value, expected_type):
        raise TypeError(
            f"Input field '{key}' has invalid type. Expected {expected_type.__name__}."
        )
    return value


def _normalize_command_data(data: dict[str, object] | None) -> dict[str, object]:
    """Normalize command data payload into object-only mapping."""
    if data is None:
        return {}
    return {str(key): value for key, value in data.items()}

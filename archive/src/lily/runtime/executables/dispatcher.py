"""Registry-based executable dispatcher with deterministic error envelopes."""

from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter

from lily.runtime.executables.handlers.base import BaseExecutableHandler
from lily.runtime.executables.models import (
    ExecutableError,
    ExecutableKind,
    ExecutableRequest,
    ExecutableResult,
    ExecutableStatus,
    ExecutionMetrics,
)
from lily.runtime.executables.resolver import ResolverBindingError
from lily.runtime.executables.types import ExecutableResolver


class RegistryExecutableDispatcher:
    """Dispatch executable requests through resolver + handler registry map."""

    def __init__(
        self,
        *,
        resolver: ExecutableResolver,
        handlers: Mapping[ExecutableKind, BaseExecutableHandler],
    ) -> None:
        """Store deterministic resolver and handler registry.

        Args:
            resolver: Deterministic executable resolver.
            handlers: Registry map keyed by executable kind.
        """
        self._resolver = resolver
        self._handlers = dict(handlers)

    def dispatch(self, request: ExecutableRequest) -> ExecutableResult:
        """Resolve and dispatch one executable request.

        Args:
            request: Canonical executable request.

        Returns:
            Canonical executable result envelope.
        """
        started = perf_counter()
        try:
            resolved_ref = self._resolver.resolve(request)
        except ResolverBindingError as exc:
            return _error_result(
                request=request,
                error=ExecutableError(
                    code=exc.code,
                    message=exc.message,
                    retryable=False,
                    data=exc.data,
                ),
                duration_ms=_duration_ms(started),
            )

        if resolved_ref.executable_kind is None:
            return _error_result(
                request=request,
                error=ExecutableError(
                    code="resolver_invalid_binding",
                    message=(
                        "Error: resolver produced executable reference without "
                        "executable_kind."
                    ),
                    retryable=False,
                    data={"target_id": resolved_ref.executable_id},
                ),
                duration_ms=_duration_ms(started),
            )

        handler = self._handlers.get(resolved_ref.executable_kind)
        if handler is None:
            return _error_result(
                request=request,
                error=ExecutableError(
                    code="dispatcher_handler_unbound",
                    message=(
                        "Error: no handler is registered for resolved executable_kind."
                    ),
                    retryable=False,
                    data={
                        "target_id": resolved_ref.executable_id,
                        "executable_kind": resolved_ref.executable_kind.value,
                    },
                ),
                duration_ms=_duration_ms(started),
            )

        resolved_request = request.model_copy(update={"target": resolved_ref})
        try:
            return handler.handle(resolved_request)
        except Exception as exc:  # pragma: no cover - defensive boundary
            return _error_result(
                request=request,
                error=ExecutableError(
                    code="dispatcher_handler_failed",
                    message=(
                        "Error: executable handler raised an unexpected exception "
                        "during dispatch."
                    ),
                    retryable=False,
                    data={
                        "target_id": resolved_ref.executable_id,
                        "executable_kind": resolved_ref.executable_kind.value,
                        "reason": str(exc),
                    },
                ),
                duration_ms=_duration_ms(started),
            )


def _error_result(
    *,
    request: ExecutableRequest,
    error: ExecutableError,
    duration_ms: int,
) -> ExecutableResult:
    """Build canonical deterministic error envelope."""
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


def _duration_ms(started: float) -> int:
    """Return elapsed milliseconds for deterministic metrics payload."""
    elapsed = perf_counter() - started
    return int(max(elapsed, 0) * 1000)

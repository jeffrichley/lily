"""Unit tests for registry-based executable dispatcher behavior."""

from __future__ import annotations

import pytest

from lily.runtime.executables.dispatcher import RegistryExecutableDispatcher
from lily.runtime.executables.handlers.base import BaseExecutableHandler
from lily.runtime.executables.models import (
    CallerContext,
    ExecutableError,
    ExecutableKind,
    ExecutableRef,
    ExecutableRequest,
    ExecutableResult,
    ExecutableStatus,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionMetadata,
    ExecutionMetrics,
)
from lily.runtime.executables.resolver import ExecutableCatalogResolver


def _request(
    *,
    executable_id: str = "nightly_security_council",
    executable_kind: ExecutableKind | None = None,
) -> ExecutableRequest:
    """Build executable request fixture for dispatcher tests."""
    return ExecutableRequest(
        run_id="run-001",
        step_id="step-001",
        caller=CallerContext(supervisor_id="supervisor.v1", active_agent="default"),
        target=ExecutableRef(
            executable_id=executable_id,
            executable_kind=executable_kind,
        ),
        objective="Execute one deterministic step.",
        input={"topic": "security"},
        context=ExecutionContext(
            memory_refs=(),
            artifact_refs=(),
            constraints=ExecutionConstraints(),
        ),
        metadata=ExecutionMetadata(
            trace_tags={},
            created_at_utc="2026-03-04T20:00:00Z",
        ),
    )


class _WorkflowHandler(BaseExecutableHandler):
    """Handler fixture that returns deterministic success payload."""

    kind = ExecutableKind.WORKFLOW

    def handle(self, request: ExecutableRequest) -> ExecutableResult:
        """Return deterministic success result for dispatcher tests."""
        return ExecutableResult(
            run_id=request.run_id,
            step_id=request.step_id,
            status=ExecutableStatus.OK,
            output={"resolved_kind": request.target.executable_kind.value},
            references=("ref://workflow",),
            artifacts=("artifact://summary",),
            metrics=ExecutionMetrics(duration_ms=7),
            error=None,
        )


class _RaisingWorkflowHandler(BaseExecutableHandler):
    """Handler fixture that raises to test dispatcher error boundaries."""

    kind = ExecutableKind.WORKFLOW

    def handle(self, request: ExecutableRequest) -> ExecutableResult:
        """Raise an exception to trigger dispatcher fallback error envelope."""
        del request
        raise RuntimeError("unexpected boom")


@pytest.mark.unit
def test_dispatcher_routes_to_registered_handler() -> None:
    """Dispatcher should resolve and route to the registered kind handler."""
    # Arrange - create resolver and dispatcher with workflow handler registered.
    resolver = ExecutableCatalogResolver(
        catalog=(
            ExecutableRef(
                executable_id="nightly_security_council",
                executable_kind=ExecutableKind.WORKFLOW,
            ),
        )
    )
    dispatcher = RegistryExecutableDispatcher(
        resolver=resolver,
        handlers={ExecutableKind.WORKFLOW: _WorkflowHandler()},
    )
    request = _request(executable_id="nightly_security_council")

    # Act - dispatch request through resolver and handler registry.
    result = dispatcher.dispatch(request)

    # Assert - dispatcher returns successful canonical envelope from handler.
    assert result.status == ExecutableStatus.OK
    assert result.output["resolved_kind"] == "workflow"
    assert result.error is None


@pytest.mark.unit
def test_dispatcher_returns_unresolved_error_when_resolver_fails() -> None:
    """Dispatcher should normalize unresolved resolver failures to error envelope."""
    # Arrange - create resolver without the requested executable id.
    resolver = ExecutableCatalogResolver(
        catalog=(
            ExecutableRef(
                executable_id="nightly_security_council",
                executable_kind=ExecutableKind.WORKFLOW,
            ),
        )
    )
    dispatcher = RegistryExecutableDispatcher(
        resolver=resolver,
        handlers={ExecutableKind.WORKFLOW: _WorkflowHandler()},
    )
    request = _request(executable_id="missing_target")

    # Act - dispatch request and capture deterministic resolver error mapping.
    result = dispatcher.dispatch(request)

    # Assert - dispatcher emits canonical error envelope with unresolved code.
    assert result.status == ExecutableStatus.ERROR
    assert isinstance(result.error, ExecutableError)
    assert result.error.code == "resolver_unresolved"
    assert result.error.data["target_id"] == "missing_target"


@pytest.mark.unit
def test_dispatcher_returns_ambiguous_error_from_resolver() -> None:
    """Dispatcher should preserve resolver_ambiguous deterministic error code."""
    # Arrange - create resolver with duplicate id collisions to force ambiguity.
    resolver = ExecutableCatalogResolver(
        catalog=(
            ExecutableRef(
                executable_id="nightly_security_council",
                executable_kind=ExecutableKind.WORKFLOW,
            ),
            ExecutableRef(
                executable_id="nightly_security_council",
                executable_kind=ExecutableKind.BLUEPRINT,
            ),
        )
    )
    dispatcher = RegistryExecutableDispatcher(
        resolver=resolver,
        handlers={ExecutableKind.WORKFLOW: _WorkflowHandler()},
    )
    request = _request(executable_id="nightly_security_council")

    # Act - dispatch request and capture ambiguity envelope from resolver.
    result = dispatcher.dispatch(request)

    # Assert - ambiguity is returned as deterministic error payload.
    assert result.status == ExecutableStatus.ERROR
    assert isinstance(result.error, ExecutableError)
    assert result.error.code == "resolver_ambiguous"
    assert result.error.data["candidate_count"] == 2


@pytest.mark.unit
def test_dispatcher_returns_handler_unbound_error_for_missing_kind_handler() -> None:
    """Dispatcher should fail when resolved kind has no registered handler."""
    # Arrange - create resolver that resolves to workflow without workflow handler.
    resolver = ExecutableCatalogResolver(
        catalog=(
            ExecutableRef(
                executable_id="nightly_security_council",
                executable_kind=ExecutableKind.WORKFLOW,
            ),
        )
    )
    dispatcher = RegistryExecutableDispatcher(
        resolver=resolver,
        handlers={},
    )
    request = _request(executable_id="nightly_security_council")

    # Act - dispatch request and capture missing-handler envelope.
    result = dispatcher.dispatch(request)

    # Assert - missing handler is deterministic and machine-readable.
    assert result.status == ExecutableStatus.ERROR
    assert isinstance(result.error, ExecutableError)
    assert result.error.code == "dispatcher_handler_unbound"
    assert result.error.data["executable_kind"] == "workflow"


@pytest.mark.unit
def test_dispatcher_returns_handler_failed_for_unexpected_handler_exception() -> None:
    """Dispatcher should convert handler exceptions to deterministic error result."""
    # Arrange - create dispatcher with handler that raises unexpectedly.
    resolver = ExecutableCatalogResolver(
        catalog=(
            ExecutableRef(
                executable_id="nightly_security_council",
                executable_kind=ExecutableKind.WORKFLOW,
            ),
        )
    )
    dispatcher = RegistryExecutableDispatcher(
        resolver=resolver,
        handlers={ExecutableKind.WORKFLOW: _RaisingWorkflowHandler()},
    )
    request = _request(executable_id="nightly_security_council")

    # Act - dispatch request and capture exception boundary result.
    result = dispatcher.dispatch(request)

    # Assert - dispatcher returns stable handler failure envelope.
    assert result.status == ExecutableStatus.ERROR
    assert isinstance(result.error, ExecutableError)
    assert result.error.code == "dispatcher_handler_failed"
    assert "unexpected boom" in str(result.error.data["reason"])

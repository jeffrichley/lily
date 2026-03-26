"""Unit tests for deterministic executable resolver behavior."""

from __future__ import annotations

import pytest

from lily.runtime.executables.models import (
    CallerContext,
    ExecutableKind,
    ExecutableRef,
    ExecutableRequest,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionMetadata,
)
from lily.runtime.executables.resolver import (
    ExecutableCatalogResolver,
    ResolverBindingError,
)


def _request(
    *,
    executable_id: str,
    executable_kind: ExecutableKind | None = None,
) -> ExecutableRequest:
    """Build executable request fixture for resolver tests."""
    return ExecutableRequest(
        run_id="run-001",
        step_id="step-001",
        caller=CallerContext(supervisor_id="supervisor.v1", active_agent="default"),
        target=ExecutableRef(
            executable_id=executable_id,
            executable_kind=executable_kind,
        ),
        objective="Execute one deterministic step.",
        input={},
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


@pytest.mark.unit
def test_resolver_returns_single_exact_match() -> None:
    """Resolver should return exact executable reference for unique id."""
    # Arrange - create resolver catalog with one matching executable id.
    resolver = ExecutableCatalogResolver(
        catalog=(
            ExecutableRef(
                executable_id="nightly_security_council",
                executable_kind=ExecutableKind.WORKFLOW,
                version="v1",
            ),
        )
    )
    request = _request(executable_id="nightly_security_council")

    # Act - resolve request target from deterministic catalog.
    resolved = resolver.resolve(request)

    # Assert - resolver returns the exact catalog reference with concrete kind.
    assert resolved.executable_id == "nightly_security_council"
    assert resolved.executable_kind == ExecutableKind.WORKFLOW
    assert resolved.version == "v1"


@pytest.mark.unit
def test_resolver_returns_unresolved_for_unknown_target_id() -> None:
    """Resolver should fail with resolver_unresolved for unknown id."""
    # Arrange - create resolver with no entry for the requested id.
    resolver = ExecutableCatalogResolver(
        catalog=(
            ExecutableRef(
                executable_id="nightly_security_council",
                executable_kind=ExecutableKind.WORKFLOW,
            ),
        )
    )
    request = _request(executable_id="unknown_target")

    # Act - resolve request and capture deterministic unresolved failure.
    with pytest.raises(ResolverBindingError) as exc_info:
        resolver.resolve(request)

    # Assert - resolver emits deterministic unresolved code and target metadata.
    assert exc_info.value.code == "resolver_unresolved"
    assert exc_info.value.data["target_id"] == "unknown_target"


@pytest.mark.unit
def test_resolver_returns_ambiguous_for_duplicate_ids_without_kind_hint() -> None:
    """Resolver should fail with resolver_ambiguous when duplicate ids exist."""
    # Arrange - create resolver with duplicate executable ids across kinds.
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
    request = _request(executable_id="nightly_security_council")

    # Act - resolve request and capture deterministic ambiguity failure.
    with pytest.raises(ResolverBindingError) as exc_info:
        resolver.resolve(request)

    # Assert - ambiguity payload includes candidate count and kinds.
    assert exc_info.value.code == "resolver_ambiguous"
    assert exc_info.value.data["target_id"] == "nightly_security_council"
    assert exc_info.value.data["candidate_count"] == 2
    assert exc_info.value.data["candidate_kinds"] == ["blueprint", "workflow"]


@pytest.mark.unit
def test_resolver_uses_kind_hint_to_select_deterministic_match() -> None:
    """Resolver should filter duplicate ids by executable_kind hint."""
    # Arrange - create resolver with duplicate ids and a matching kind hint request.
    resolver = ExecutableCatalogResolver(
        catalog=(
            ExecutableRef(
                executable_id="nightly_security_council",
                executable_kind=ExecutableKind.WORKFLOW,
                version="v2",
            ),
            ExecutableRef(
                executable_id="nightly_security_council",
                executable_kind=ExecutableKind.BLUEPRINT,
                version="v1",
            ),
        )
    )
    request = _request(
        executable_id="nightly_security_council",
        executable_kind=ExecutableKind.WORKFLOW,
    )

    # Act - resolve request with kind hint.
    resolved = resolver.resolve(request)

    # Assert - resolver binds to the workflow candidate only.
    assert resolved.executable_kind == ExecutableKind.WORKFLOW
    assert resolved.version == "v2"

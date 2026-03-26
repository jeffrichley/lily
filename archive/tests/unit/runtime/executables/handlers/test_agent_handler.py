"""Unit tests for agent executable adapter handler."""

from __future__ import annotations

import pytest

from lily.agents.models import AgentCatalog, AgentProfile
from lily.agents.service import AgentService
from lily.runtime.executables.handlers.agent_handler import AgentExecutableHandler
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
from lily.session.models import ModelConfig, Session
from lily.skills.types import SkillSnapshot


class _AgentRepositoryFixture:
    """Fixture implementing minimal repository protocol for agent service tests."""

    def __init__(self, profiles: tuple[AgentProfile, ...]) -> None:
        """Store deterministic in-memory profiles."""
        self._catalog = AgentCatalog(agents=profiles)

    def load_catalog(self) -> AgentCatalog:
        """Return deterministic catalog fixture."""
        return self._catalog

    def get(self, agent_id: str) -> AgentProfile | None:
        """Resolve one profile by id from fixture catalog."""
        return self._catalog.get(agent_id)


def _request(
    *, action: str = "get", payload: dict[str, object] | None = None
) -> ExecutableRequest:
    """Create agent executable request fixture."""
    base_input: dict[str, object] = {"action": action, "agent_id": "ops"}
    if payload is not None:
        base_input.update(payload)
    return ExecutableRequest(
        run_id="run-001",
        step_id="step-001",
        caller=CallerContext(supervisor_id="supervisor.v1", active_agent="default"),
        target=ExecutableRef(executable_id="ops", executable_kind=ExecutableKind.AGENT),
        objective="Resolve or activate agent.",
        input=base_input,
        context=ExecutionContext(
            memory_refs=(),
            artifact_refs=(),
            constraints=ExecutionConstraints(),
        ),
        metadata=ExecutionMetadata(
            trace_tags={}, created_at_utc="2026-03-04T20:00:00Z"
        ),
    )


def _session() -> Session:
    """Create basic session fixture."""
    return Session(
        session_id="session-agent-adapter",
        active_agent="default",
        skill_snapshot=SkillSnapshot(version="v-test", skills=()),
        model_config=ModelConfig(),
    )


@pytest.mark.unit
def test_agent_handler_returns_ok_for_known_agent_lookup() -> None:
    """Agent handler should return resolved agent profile details."""
    # Arrange - create handler with in-memory agent catalog.
    service = AgentService(
        repository=_AgentRepositoryFixture(
            profiles=(
                AgentProfile(
                    agent_id="ops",
                    summary="Operations agent",
                    policy="safe_eval",
                    declared_tools=("builtin:add",),
                ),
            )
        )
    )
    handler = AgentExecutableHandler(service=service)
    request = _request()

    # Act - execute deterministic agent lookup.
    result = handler.handle(request)

    # Assert - adapter returns canonical success with agent reference.
    assert result.status == ExecutableStatus.OK
    assert result.error is None
    assert result.output["agent_id"] == "ops"
    assert result.references == ("agent://ops",)


@pytest.mark.unit
def test_agent_handler_set_active_requires_session_payload() -> None:
    """Agent handler should reject set-active action without a session."""
    # Arrange - create handler and set_active request missing session input.
    service = AgentService(
        repository=_AgentRepositoryFixture(
            profiles=(AgentProfile(agent_id="ops", summary="Operations agent"),)
        )
    )
    handler = AgentExecutableHandler(service=service)
    request = _request(action="set_active")

    # Act - execute malformed set_active request.
    result = handler.handle(request)

    # Assert - adapter emits deterministic input validation error.
    assert result.status == ExecutableStatus.ERROR
    assert result.error is not None
    assert result.error.code == "adapter_input_invalid"


@pytest.mark.unit
def test_agent_handler_sets_active_agent_when_session_provided() -> None:
    """Agent handler should set session active agent for set_active action."""
    # Arrange - create handler and set_active request with required session.
    service = AgentService(
        repository=_AgentRepositoryFixture(
            profiles=(AgentProfile(agent_id="ops", summary="Operations agent"),)
        )
    )
    handler = AgentExecutableHandler(service=service)
    session = _session()
    request = _request(action="set_active", payload={"session": session})

    # Act - execute set_active adapter request.
    result = handler.handle(request)

    # Assert - session mutation and envelope payload are deterministic.
    assert result.status == ExecutableStatus.OK
    assert result.error is None
    assert session.active_agent == "ops"
    assert result.output["action"] == "set_active"

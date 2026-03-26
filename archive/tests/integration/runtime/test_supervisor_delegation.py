"""Integration tests for supervisor runtime delegation flow."""

from __future__ import annotations

import pytest

from lily.runtime.executables.dispatcher import RegistryExecutableDispatcher
from lily.runtime.executables.models import (
    CallerContext,
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
from lily.runtime.orchestration.supervisor import SupervisorRuntime


class _PlannerFixture:
    """Planner fixture returning deterministic typed raw payload."""

    @staticmethod
    def plan(_: object) -> object:
        """Return one deterministic two-step plan."""
        return {
            "plan_id": "plan-integration",
            "summary": "Run skill then tool",
            "steps": (
                {
                    "step_id": "step-001",
                    "target": {
                        "executable_id": "security_review",
                        "executable_kind": "skill",
                    },
                    "objective": "Run security review skill.",
                    "input": {"payload": "review deps"},
                },
                {
                    "step_id": "step-002",
                    "target": {
                        "executable_id": "builtin:add",
                        "executable_kind": "tool",
                    },
                    "objective": "Compute risk score.",
                    "input": {"payload": "2+3"},
                },
            ),
        }


class _SkillHandler:
    """Skill handler fixture for dispatcher integration tests."""

    kind = ExecutableKind.SKILL

    @staticmethod
    def handle(request: ExecutableRequest) -> ExecutableResult:
        """Return deterministic skill success envelope."""
        return ExecutableResult(
            run_id=request.run_id,
            step_id=request.step_id,
            status=ExecutableStatus.OK,
            output={"kind": "skill", "objective": request.objective},
            references=("ref://skill",),
            artifacts=(),
            metrics=ExecutionMetrics(duration_ms=3),
            error=None,
        )


class _ToolHandler:
    """Tool handler fixture for dispatcher integration tests."""

    kind = ExecutableKind.TOOL

    @staticmethod
    def handle(request: ExecutableRequest) -> ExecutableResult:
        """Return deterministic tool success envelope."""
        return ExecutableResult(
            run_id=request.run_id,
            step_id=request.step_id,
            status=ExecutableStatus.OK,
            output={"kind": "tool", "objective": request.objective},
            references=("ref://tool",),
            artifacts=(),
            metrics=ExecutionMetrics(duration_ms=4),
            error=None,
        )


def _request() -> ExecutableRequest:
    """Create supervisor root request fixture."""
    return ExecutableRequest(
        run_id="run-001",
        step_id="supervisor-step-001",
        caller=CallerContext(supervisor_id="supervisor.v1", active_agent="ops"),
        target=ExecutableRef(executable_id="supervisor"),
        objective="Execute security workflow.",
        input={"user_text": "run security workflow"},
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


@pytest.mark.integration
def test_supervisor_delegates_multi_step_plan_via_dispatcher() -> None:
    """Supervisor should execute deterministic multi-step delegated flow."""
    # Arrange - compose resolver and dispatcher with skill/tool handlers.
    resolver = ExecutableCatalogResolver(
        catalog=(
            ExecutableRef(
                executable_id="security_review",
                executable_kind=ExecutableKind.SKILL,
            ),
            ExecutableRef(
                executable_id="builtin:add",
                executable_kind=ExecutableKind.TOOL,
            ),
        )
    )
    dispatcher = RegistryExecutableDispatcher(
        resolver=resolver,
        handlers={
            ExecutableKind.SKILL: _SkillHandler(),
            ExecutableKind.TOOL: _ToolHandler(),
        },
    )
    runtime = SupervisorRuntime(
        planner=_PlannerFixture(),
        dispatcher=dispatcher,
    )
    request = _request()

    # Act - execute supervisor runtime end-to-end delegation path.
    result = runtime.execute(request)

    # Assert - run completes with deterministic multi-step aggregation output.
    assert result.status == ExecutableStatus.OK
    assert result.error is None
    assert result.output["steps_executed"] == 2
    assert result.output["step_statuses"] == [
        {"step_id": "step-001", "status": "ok"},
        {"step_id": "step-002", "status": "ok"},
    ]
    assert result.references == ("ref://skill", "ref://tool")

"""Unit tests for supervisor orchestration runtime and aggregation."""

from __future__ import annotations

import pytest

from lily.runtime.executables.models import (
    CallerContext,
    ExecutableError,
    ExecutableRef,
    ExecutableRequest,
    ExecutableResult,
    ExecutableStatus,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionMetadata,
    ExecutionMetrics,
)
from lily.runtime.orchestration.aggregator import SupervisorAggregator
from lily.runtime.orchestration.plan_models import (
    SupervisorPlan,
    SupervisorPlannerRequest,
)
from lily.runtime.orchestration.supervisor import SupervisorRuntime


class _PlannerFixture:
    """Planner fixture returning deterministic raw plan payloads."""

    def __init__(self, payload: object) -> None:
        """Store planner payload fixture."""
        self._payload = payload
        self.requests: list[SupervisorPlannerRequest] = []

    def plan(self, request: SupervisorPlannerRequest) -> object:
        """Return deterministic payload and record request."""
        self.requests.append(request)
        return self._payload


class _DispatcherFixture:
    """Dispatcher fixture returning deterministic step results."""

    def __init__(self, results: dict[str, ExecutableResult]) -> None:
        """Store per-step result fixtures."""
        self._results = results
        self.requests: list[ExecutableRequest] = []

    def dispatch(self, request: ExecutableRequest) -> ExecutableResult:
        """Return configured result for one delegated step request."""
        self.requests.append(request)
        return self._results[request.step_id]


def _supervisor_request() -> ExecutableRequest:
    """Create canonical supervisor executable request fixture."""
    return ExecutableRequest(
        run_id="run-001",
        step_id="supervisor-step-001",
        caller=CallerContext(supervisor_id="supervisor.v1", active_agent="ops"),
        target=ExecutableRef(executable_id="supervisor", executable_kind=None),
        objective="Run nightly security workflow.",
        input={"user_text": "run the security workflow"},
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


def _ok_step_result(*, run_id: str, step_id: str, ref: str) -> ExecutableResult:
    """Create deterministic ok step result fixture."""
    return ExecutableResult(
        run_id=run_id,
        step_id=step_id,
        status=ExecutableStatus.OK,
        output={"step": step_id},
        references=(ref,),
        artifacts=(),
        metrics=ExecutionMetrics(duration_ms=5),
        error=None,
    )


@pytest.mark.unit
def test_supervisor_executes_multi_step_plan_through_dispatcher() -> None:
    """Supervisor should execute planner steps sequentially via dispatcher."""
    # Arrange - create planner with two typed delegated steps and ok results.
    planner = _PlannerFixture(
        payload={
            "plan_id": "plan-001",
            "summary": "Nightly security workflow",
            "steps": (
                {
                    "step_id": "step-a",
                    "target": {
                        "executable_id": "security_review",
                        "executable_kind": "skill",
                    },
                    "objective": "Run security review.",
                    "input": {"session": "session-ref"},
                },
                {
                    "step_id": "step-b",
                    "target": {
                        "executable_id": "nightly_security_council",
                        "executable_kind": "blueprint",
                    },
                    "objective": "Execute security blueprint.",
                    "input": {"bindings": {}, "run_input": {}},
                },
            ),
        }
    )
    dispatcher = _DispatcherFixture(
        results={
            "step-a": _ok_step_result(
                run_id="run-001",
                step_id="step-a",
                ref="ref://skill",
            ),
            "step-b": _ok_step_result(
                run_id="run-001",
                step_id="step-b",
                ref="ref://blueprint",
            ),
        }
    )
    runtime = SupervisorRuntime(planner=planner, dispatcher=dispatcher)
    request = _supervisor_request()

    # Act - execute supervisor orchestration run.
    result = runtime.execute(request)

    # Assert - planner and dispatcher boundaries are exercised deterministically.
    assert len(planner.requests) == 1
    assert len(dispatcher.requests) == 2
    assert all(req.parent_step_id == request.step_id for req in dispatcher.requests)
    assert result.status == ExecutableStatus.OK
    assert result.error is None
    assert result.output["steps_executed"] == 2
    assert result.references == ("ref://skill", "ref://blueprint")


@pytest.mark.unit
def test_supervisor_returns_plan_invalid_for_untyped_planner_output() -> None:
    """Supervisor should reject invalid planner payloads at schema boundary."""
    # Arrange - create planner that returns malformed untyped output.
    planner = _PlannerFixture(payload={"invalid": "shape"})
    dispatcher = _DispatcherFixture(results={})
    runtime = SupervisorRuntime(planner=planner, dispatcher=dispatcher)
    request = _supervisor_request()

    # Act - execute supervisor with invalid planner output.
    result = runtime.execute(request)

    # Assert - supervisor fails with deterministic plan validation error.
    assert result.status == ExecutableStatus.ERROR
    assert result.error is not None
    assert result.error.code == "supervisor_plan_invalid"
    assert len(dispatcher.requests) == 0


@pytest.mark.unit
def test_aggregator_surfaces_failed_step_with_provenance() -> None:
    """Aggregator should preserve provenance and surface failed step details."""
    # Arrange - create plan and results containing one failed step.
    request = _supervisor_request()
    plan = SupervisorPlan.model_validate(
        {
            "plan_id": "plan-err",
            "summary": "Failing plan",
            "steps": (
                {
                    "step_id": "step-a",
                    "target": {"executable_id": "a", "executable_kind": "tool"},
                    "objective": "Step a",
                    "input": {},
                },
                {
                    "step_id": "step-b",
                    "target": {"executable_id": "b", "executable_kind": "tool"},
                    "objective": "Step b",
                    "input": {},
                },
            ),
        }
    )
    ok_first = _ok_step_result(run_id="run-001", step_id="step-a", ref="ref://a")
    failed = ExecutableResult(
        run_id="run-001",
        step_id="step-b",
        status=ExecutableStatus.ERROR,
        output={},
        references=("ref://b",),
        artifacts=(),
        metrics=ExecutionMetrics(duration_ms=8),
        error=ExecutableError(
            code="tool_failed",
            message="Tool failed.",
            retryable=False,
            data={},
        ),
    )
    aggregator = SupervisorAggregator()

    # Act - aggregate a partial success/failure step sequence.
    result = aggregator.aggregate(
        request=request,
        plan=plan,
        step_results=(ok_first, failed),
        started_at=0.0,
    )

    # Assert - error envelope includes deterministic failed-step metadata.
    assert result.status == ExecutableStatus.ERROR
    assert result.error is not None
    assert result.error.code == "supervisor_step_failed"
    assert result.error.data["failed_step_id"] == "step-b"
    assert result.references == ("ref://a", "ref://b")

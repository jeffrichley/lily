"""Supervisor runtime for LLM-planned executable delegation."""

from __future__ import annotations

from time import perf_counter
from typing import Protocol

from pydantic import ValidationError

from lily.runtime.executables.models import (
    ExecutableError,
    ExecutableRequest,
    ExecutableResult,
    ExecutableStatus,
    ExecutionMetrics,
)
from lily.runtime.executables.types import ExecutableDispatcher
from lily.runtime.orchestration.aggregator import SupervisorAggregator
from lily.runtime.orchestration.plan_models import (
    SupervisorPlan,
    SupervisorPlannerRequest,
)


class SupervisorPlanner(Protocol):
    """Planner contract for supervisor typed plan generation."""

    def plan(self, request: SupervisorPlannerRequest) -> object:
        """Generate raw planner output for one supervisor request.

        Args:
            request: Typed planner request context.
        """


class PydanticAiPlanRunner(Protocol):
    """Port for PydanticAI-backed planning execution."""

    def run(self, request: SupervisorPlannerRequest) -> object:
        """Run one planning turn and return raw structured output."""


class PydanticAiSupervisorPlanner(SupervisorPlanner):
    """LLM-first planner adapter backed by a PydanticAI runner port."""

    def __init__(self, *, runner: PydanticAiPlanRunner) -> None:
        """Store PydanticAI planning runner dependency.

        Args:
            runner: PydanticAI planning runner port.
        """
        self._runner = runner

    def plan(self, request: SupervisorPlannerRequest) -> object:
        """Produce raw typed-plan payload from PydanticAI runner.

        Args:
            request: Typed planner request context.

        Returns:
            Raw planner output to be schema-validated by supervisor runtime.
        """
        return self._runner.run(request)


class SupervisorRuntime:
    """Execute planner-emitted multi-step plan through dispatcher boundaries."""

    def __init__(
        self,
        *,
        planner: SupervisorPlanner,
        dispatcher: ExecutableDispatcher,
        aggregator: SupervisorAggregator | None = None,
        max_steps: int = 8,
    ) -> None:
        """Store runtime dependencies for one supervisor execution path.

        Args:
            planner: Planner dependency (LLM-backed in V1).
            dispatcher: Executable dispatcher dependency.
            aggregator: Optional deterministic result aggregator.
            max_steps: Hard bound for delegated steps in one run.
        """
        self._planner = planner
        self._dispatcher = dispatcher
        self._aggregator = aggregator or SupervisorAggregator()
        self._max_steps = max_steps

    def execute(self, request: ExecutableRequest) -> ExecutableResult:
        """Execute supervisor request with typed planning and delegation.

        Args:
            request: Root supervisor executable request.

        Returns:
            Canonical supervisor result envelope.
        """
        started = perf_counter()
        plan_request = SupervisorPlannerRequest(
            run_id=request.run_id,
            supervisor_step_id=request.step_id,
            caller=request.caller,
            objective=request.objective,
            input=request.input,
        )
        try:
            raw_plan = self._planner.plan(plan_request)
            plan = SupervisorPlan.model_validate(raw_plan)
        except ValidationError as exc:
            return _error_result(
                request=request,
                error=ExecutableError(
                    code="supervisor_plan_invalid",
                    message=(
                        "Error: supervisor planner returned invalid plan payload."
                    ),
                    retryable=False,
                    data={"validation_errors": exc.errors()},
                ),
                started=started,
            )

        if len(plan.steps) > self._max_steps:
            return _error_result(
                request=request,
                error=ExecutableError(
                    code="supervisor_step_budget_exceeded",
                    message="Error: supervisor plan exceeds maximum step budget.",
                    retryable=False,
                    data={"max_steps": self._max_steps, "step_count": len(plan.steps)},
                ),
                started=started,
            )

        step_results: list[ExecutableResult] = []
        for step in plan.steps:
            delegated_request = ExecutableRequest(
                run_id=request.run_id,
                step_id=step.step_id,
                parent_step_id=request.step_id,
                caller=request.caller,
                target=step.target,
                objective=step.objective,
                input=step.input,
                context=request.context,
                metadata=request.metadata,
            )
            step_result = self._dispatcher.dispatch(delegated_request)
            step_results.append(step_result)
            if step_result.status != ExecutableStatus.OK:
                break

        return self._aggregator.aggregate(
            request=request,
            plan=plan,
            step_results=tuple(step_results),
            started_at=started,
        )


def _error_result(
    *,
    request: ExecutableRequest,
    error: ExecutableError,
    started: float,
) -> ExecutableResult:
    """Build deterministic supervisor runtime error envelope."""
    elapsed_ms = int(max(perf_counter() - started, 0) * 1000)
    return ExecutableResult(
        run_id=request.run_id,
        step_id=request.step_id,
        status=ExecutableStatus.ERROR,
        output={},
        references=(),
        artifacts=(),
        metrics=ExecutionMetrics(duration_ms=elapsed_ms),
        error=error,
    )

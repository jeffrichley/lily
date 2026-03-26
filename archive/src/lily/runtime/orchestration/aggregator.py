"""Deterministic aggregation for supervisor delegated execution results."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable
from time import perf_counter

from lily.runtime.executables.models import (
    ExecutableError,
    ExecutableRequest,
    ExecutableResult,
    ExecutableStatus,
    ExecutionMetrics,
)
from lily.runtime.orchestration.plan_models import SupervisorPlan


class SupervisorAggregator:
    """Aggregate delegated step results into one canonical supervisor result."""

    def aggregate(
        self,
        *,
        request: ExecutableRequest,
        plan: SupervisorPlan,
        step_results: tuple[ExecutableResult, ...],
        started_at: float,
    ) -> ExecutableResult:
        """Build deterministic supervisor result from delegated step outputs.

        Args:
            request: Root supervisor request.
            plan: Executed plan.
            step_results: Delegated execution results in run order.
            started_at: Monotonic run start time.

        Returns:
            Canonical aggregated result envelope.
        """
        elapsed_ms = int(max(perf_counter() - started_at, 0) * 1000)
        references = _dedupe_refs(
            ref for step in step_results for ref in step.references
        )
        artifacts = _dedupe_refs(
            artifact for step in step_results for artifact in step.artifacts
        )

        failed = next(
            (step for step in step_results if step.status != ExecutableStatus.OK),
            None,
        )
        if failed is None:
            return ExecutableResult(
                run_id=request.run_id,
                step_id=request.step_id,
                status=ExecutableStatus.OK,
                output={
                    "plan_id": plan.plan_id,
                    "plan_summary": plan.summary,
                    "steps_executed": len(step_results),
                    "step_statuses": [
                        {"step_id": step.step_id, "status": step.status.value}
                        for step in step_results
                    ],
                },
                references=references,
                artifacts=artifacts,
                metrics=ExecutionMetrics(duration_ms=elapsed_ms),
                error=None,
            )

        failed_error = failed.error
        assert failed_error is not None
        return ExecutableResult(
            run_id=request.run_id,
            step_id=request.step_id,
            status=ExecutableStatus.ERROR,
            output={
                "plan_id": plan.plan_id,
                "plan_summary": plan.summary,
                "steps_executed": len(step_results),
                "failed_step_id": failed.step_id,
            },
            references=references,
            artifacts=artifacts,
            metrics=ExecutionMetrics(duration_ms=elapsed_ms),
            error=ExecutableError(
                code="supervisor_step_failed",
                message=("Error: supervisor delegated step failed and run stopped."),
                retryable=failed_error.retryable,
                data={
                    "failed_step_id": failed.step_id,
                    "failed_code": failed_error.code,
                    "failed_message": failed_error.message,
                },
            ),
        )


def _dedupe_refs(values: Iterable[object]) -> tuple[str, ...]:
    """Return deterministic insertion-ordered unique tuple of references."""
    unique = OrderedDict[str, None]()
    for value in values:
        text = str(value)
        unique[text] = None
    return tuple(unique.keys())

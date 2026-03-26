"""Typed supervisor planning models for orchestration runtime."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lily.runtime.executables.models import CallerContext, ExecutableRef


class SupervisorPlanStep(BaseModel):
    """One delegated executable step emitted by supervisor planner."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    step_id: str = Field(min_length=1)
    target: ExecutableRef
    objective: str = Field(min_length=1)
    input: dict[str, object]


class SupervisorPlan(BaseModel):
    """Typed multi-step plan emitted by planner and executed by runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan_id: str = Field(min_length=1)
    summary: str = ""
    steps: tuple[SupervisorPlanStep, ...]

    @model_validator(mode="after")
    def _validate_step_ids_unique(self) -> SupervisorPlan:
        """Require deterministic unique step ids within one plan."""
        seen: set[str] = set()
        for step in self.steps:
            if step.step_id in seen:
                raise ValueError("plan steps must have unique step_id values.")
            seen.add(step.step_id)
        return self


class SupervisorPlannerRequest(BaseModel):
    """Planner prompt context built from one supervisor run request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    supervisor_step_id: str = Field(min_length=1)
    caller: CallerContext
    objective: str = Field(min_length=1)
    input: dict[str, object]

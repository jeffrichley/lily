"""Layer 4: Routing models and engine. Deterministic control flow from runtime outcomes."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, model_validator


class RoutingActionType(str, Enum):
    """Routing action types."""

    RETRY_STEP = "retry_step"
    GOTO_STEP = "goto_step"
    ESCALATE = "escalate"
    ABORT_RUN = "abort_run"
    CONTINUE = "continue"


class RoutingCondition(BaseModel):
    """When to apply a routing rule. All specified fields must match (conjunctive)."""

    model_config = {"extra": "forbid"}

    step_status: Literal["succeeded", "failed"] | None = None
    gate_status: Literal["passed", "failed"] | None = None
    retry_exhausted: bool | None = None
    policy_violation: bool | None = None
    step_id: str | None = None
    gate_id: str | None = None

    def matches(self, context: "RoutingContext") -> bool:
        """Return True if all specified fields match the context."""
        if self.step_status is not None and context.step_status != self.step_status:
            return False
        if self.gate_status is not None and context.gate_status != self.gate_status:
            return False
        if (
            self.retry_exhausted is not None
            and context.retry_exhausted != self.retry_exhausted
        ):
            return False
        if (
            self.policy_violation is not None
            and context.policy_violation != self.policy_violation
        ):
            return False
        if self.step_id is not None and context.step_id != self.step_id:
            return False
        if self.gate_id is not None and context.gate_id != self.gate_id:
            return False
        return True


class RoutingAction(BaseModel):
    """What to do when a rule matches."""

    model_config = {"extra": "forbid"}

    type: RoutingActionType
    target_step_id: str | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def _goto_step_requires_target(self) -> "RoutingAction":
        if self.type == RoutingActionType.GOTO_STEP and not self.target_step_id:
            raise ValueError("target_step_id is required when type is goto_step")
        return self


class RoutingRule(BaseModel):
    """Declarative routing rule: when condition matches, apply action."""

    model_config = {"extra": "forbid"}

    rule_id: str
    when: RoutingCondition
    action: RoutingAction


class RoutingContext(BaseModel):
    """Input for routing evaluation. Built from RunState + step/gate outcomes."""

    model_config = {"extra": "forbid"}

    step_status: Literal["succeeded", "failed"] | None = None
    gate_status: Literal["passed", "failed"] | None = None
    retry_exhausted: bool = False
    policy_violation: bool = False
    step_id: str | None = None
    gate_id: str | None = None


class RoutingEngine:
    """
    Pure routing evaluator. No side effects. Deterministic.
    Does not mutate RunState; returns RoutingAction for Runner to apply.
    """

    @staticmethod
    def evaluate(
        context: RoutingContext,
        rules: list[RoutingRule],
    ) -> RoutingAction:
        """
        Evaluate routing rules deterministically. First matching rule wins.
        Default behavior if no rule matches:
        - step failed (or policy_violation) -> abort_run
        - step succeeded -> continue
        """
        for rule in rules:
            if rule.when.matches(context):
                return rule.action

        # Default behavior
        if context.policy_violation:
            return RoutingAction(type=RoutingActionType.ABORT_RUN, reason="default")
        if context.gate_status == "failed":
            return RoutingAction(type=RoutingActionType.ABORT_RUN, reason="default")
        if context.step_status == "failed":
            if context.retry_exhausted:
                return RoutingAction(type=RoutingActionType.ABORT_RUN, reason="default")
            return RoutingAction(type=RoutingActionType.RETRY_STEP, reason="default")
        return RoutingAction(type=RoutingActionType.CONTINUE, reason="default")

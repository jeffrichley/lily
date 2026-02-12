"""Layer 4: RoutingEngine — deterministic rule evaluation."""

import pytest

from lily.kernel.routing_models import (
    RoutingAction,
    RoutingActionType,
    RoutingCondition,
    RoutingContext,
    RoutingEngine,
    RoutingRule,
)


def test_matching_rule_triggers_correct_action():
    """First matching rule triggers its action."""
    context = RoutingContext(
        step_status="failed",
        retry_exhausted=False,
        step_id="s1",
    )
    rules = [
        RoutingRule(
            rule_id="r1",
            when=RoutingCondition(step_status="failed", retry_exhausted=False),
            action=RoutingAction(
                type=RoutingActionType.RETRY_STEP, reason="retry once"
            ),
        ),
    ]
    result = RoutingEngine.evaluate(context, rules)
    assert result.type == RoutingActionType.RETRY_STEP
    assert result.reason == "retry once"


def test_rule_order_respected():
    """First matching rule wins; later rules ignored."""
    context = RoutingContext(step_status="failed", step_id="s1")
    rules = [
        RoutingRule(
            rule_id="r_abort",
            when=RoutingCondition(step_status="failed"),
            action=RoutingAction(type=RoutingActionType.ABORT_RUN),
        ),
        RoutingRule(
            rule_id="r_retry",
            when=RoutingCondition(step_status="failed"),
            action=RoutingAction(type=RoutingActionType.RETRY_STEP),
        ),
    ]
    result = RoutingEngine.evaluate(context, rules)
    assert result.type == RoutingActionType.ABORT_RUN


def test_default_behavior_when_no_rules_match():
    """Default: step failed + retry_exhausted -> abort; else retry; step succeeded -> continue."""
    ctx_failed_retries_left = RoutingContext(
        step_status="failed", retry_exhausted=False
    )
    ctx_failed_exhausted = RoutingContext(step_status="failed", retry_exhausted=True)
    ctx_succeeded = RoutingContext(step_status="succeeded")

    result_retry = RoutingEngine.evaluate(ctx_failed_retries_left, [])
    assert result_retry.type == RoutingActionType.RETRY_STEP

    result_abort = RoutingEngine.evaluate(ctx_failed_exhausted, [])
    assert result_abort.type == RoutingActionType.ABORT_RUN

    result_succeeded = RoutingEngine.evaluate(ctx_succeeded, [])
    assert result_succeeded.type == RoutingActionType.CONTINUE


def test_default_abort_on_policy_violation():
    """Policy violation defaults to abort_run when no rule matches."""
    context = RoutingContext(
        step_status="succeeded",
        policy_violation=True,
    )
    result = RoutingEngine.evaluate(context, [])
    assert result.type == RoutingActionType.ABORT_RUN


def test_goto_step_requires_target_step_id():
    """RoutingAction validates target_step_id when type is goto_step."""
    with pytest.raises(ValueError, match="target_step_id is required"):
        RoutingAction(type=RoutingActionType.GOTO_STEP, target_step_id=None)

    # With target_step_id it's valid
    action = RoutingAction(
        type=RoutingActionType.GOTO_STEP,
        target_step_id="s2",
        reason="recover",
    )
    assert action.target_step_id == "s2"


def test_condition_conjunctive():
    """All specified condition fields must match."""
    context = RoutingContext(
        step_status="failed",
        step_id="s1",
        gate_status="passed",
        retry_exhausted=True,
    )
    # Rule requires step_id=s2; context has s1 -> no match
    rules = [
        RoutingRule(
            rule_id="r1",
            when=RoutingCondition(step_status="failed", step_id="s2"),
            action=RoutingAction(type=RoutingActionType.RETRY_STEP),
        ),
    ]
    result = RoutingEngine.evaluate(context, rules)
    # Falls through to default (retry_exhausted -> abort)
    assert result.type == RoutingActionType.ABORT_RUN


def test_condition_ignores_none_fields():
    """None fields in condition are ignored (match any)."""
    context = RoutingContext(step_status="succeeded", step_id="s1")
    rules = [
        RoutingRule(
            rule_id="r1",
            when=RoutingCondition(step_status="succeeded"),  # gate_status=None ignored
            action=RoutingAction(type=RoutingActionType.CONTINUE, reason="ok"),
        ),
    ]
    result = RoutingEngine.evaluate(context, rules)
    assert result.type == RoutingActionType.CONTINUE
    assert result.reason == "ok"

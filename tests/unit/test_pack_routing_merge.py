"""Unit tests for pack routing rule merging (Layer 6)."""

from __future__ import annotations

import pytest

from lily.kernel.pack_registration import merge_routing_rules
from lily.kernel.routing_models import (
    RoutingAction,
    RoutingActionType,
    RoutingCondition,
    RoutingRule,
)


def _rule(rule_id: str, step_status: str | None = "failed") -> RoutingRule:
    return RoutingRule(
        rule_id=rule_id,
        when=RoutingCondition(step_status=step_status),
        action=RoutingAction(type=RoutingActionType.RETRY_STEP),
    )


def test_rules_merge_correctly() -> None:
    """Rules from multiple packs merge in order with no duplicates."""
    pack_a_rules = [_rule("a.retry"), _rule("a.abort")]
    pack_b_rules = [_rule("b.escalate")]
    merged = merge_routing_rules([pack_a_rules, pack_b_rules])
    assert len(merged) == 3
    assert merged[0].rule_id == "a.retry"
    assert merged[1].rule_id == "a.abort"
    assert merged[2].rule_id == "b.escalate"


def test_duplicate_rule_id_fails() -> None:
    """Duplicate rule_id across packs raises ValueError."""
    pack_a = [_rule("shared.rule")]
    pack_b = [_rule("shared.rule")]
    with pytest.raises(ValueError, match="Duplicate routing rule_id.*shared\\.rule"):
        merge_routing_rules([pack_a, pack_b])


def test_deterministic_order_preserved() -> None:
    """Order is deterministic (by pack order, then rule order within pack)."""
    a = [_rule("first"), _rule("second")]
    b = [_rule("third")]
    m1 = merge_routing_rules([a, b])
    m2 = merge_routing_rules([a, b])
    assert [r.rule_id for r in m1] == [r.rule_id for r in m2] == ["first", "second", "third"]


def test_empty_list_returns_empty() -> None:
    """No packs yields empty list."""
    assert merge_routing_rules([]) == []
    assert merge_routing_rules([[], []]) == []

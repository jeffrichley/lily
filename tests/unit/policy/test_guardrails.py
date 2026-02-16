"""Unit tests for policy guardrail decisions and precedence contract."""

from __future__ import annotations

from lily.policy import (
    PRECEDENCE_CONTRACT,
    evaluate_memory_write,
    evaluate_post_generation,
    evaluate_pre_generation,
    force_safe_style,
    resolve_effective_style,
)
from lily.prompting import PersonaStyleLevel
from tests.unit.policy.redline_fixtures import (
    CONVERSATION_INPUT_DENY,
    CONVERSATION_OUTPUT_DENY,
    MEMORY_DENY,
)


def test_precedence_contract_constant_is_documented() -> None:
    """Policy precedence contract should be stable and explicit."""
    assert (
        PRECEDENCE_CONTRACT
        == "safety > user_style > persona_default > stochastic_expression"
    )


def test_resolve_effective_style_prefers_user_style() -> None:
    """User style should take precedence over persona default style."""
    resolved = resolve_effective_style(user_style=PersonaStyleLevel.PLAYFUL)
    assert resolved == PersonaStyleLevel.PLAYFUL


def test_force_safe_style_overrides_to_focus() -> None:
    """Safety override style should be focus."""
    assert force_safe_style() == PersonaStyleLevel.FOCUS


def test_pre_generation_redlines_block_policy_bypass_requests() -> None:
    """Pre-generation policy should deny known bypass prompts."""
    for text in CONVERSATION_INPUT_DENY:
        decision = evaluate_pre_generation(text)
        assert decision.allowed is False
        assert decision.code == "conversation_policy_denied"


def test_post_generation_redlines_block_dependency_language() -> None:
    """Post-generation policy should deny manipulative dependency output."""
    for text in CONVERSATION_OUTPUT_DENY:
        decision = evaluate_post_generation(text)
        assert decision.allowed is False
        assert decision.code == "conversation_policy_denied"


def test_memory_redlines_block_sensitive_content() -> None:
    """Memory policy should deny sensitive secret-like content."""
    for text in MEMORY_DENY:
        decision = evaluate_memory_write(text)
        assert decision.allowed is False
        assert decision.code == "memory_policy_denied"


def test_policy_allows_normal_safe_content() -> None:
    """Policy should allow normal input/output/memory content."""
    assert (
        evaluate_pre_generation("Can you summarize today's progress?").allowed is True
    )
    assert evaluate_post_generation("Here is a concise summary.").allowed is True
    assert evaluate_memory_write("User prefers concise summaries.").allowed is True

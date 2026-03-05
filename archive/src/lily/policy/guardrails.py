"""Policy guardrails for conversation and memory operations."""

from __future__ import annotations

import re
from dataclasses import dataclass

from lily.prompting import PersonaStyleLevel

PRECEDENCE_CONTRACT = "safety > user_style > persona_default > stochastic_expression"
_PERSONA_DEFAULT_STYLE = PersonaStyleLevel.BALANCED
_SAFETY_FORCED_STYLE = PersonaStyleLevel.FOCUS

_PRE_INPUT_BLOCK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bignore\b.*\binstructions?\b", re.IGNORECASE),
    re.compile(r"\bbypass\b.*\b(safety|policy|guardrails?)\b", re.IGNORECASE),
)
_POST_OUTPUT_BLOCK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\byou only need me\b", re.IGNORECASE),
    re.compile(r"\bdon't talk to (anyone|others?)\b", re.IGNORECASE),
    re.compile(r"\bI should replace your (friends|family)\b", re.IGNORECASE),
)
_MEMORY_BLOCK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(api[_-]?key|token|password|secret)", re.IGNORECASE),
    re.compile(r"\bssn\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class PolicyDecision:
    """Result of deterministic policy evaluation."""

    allowed: bool
    code: str | None = None
    reason: str = ""


def resolve_effective_style(
    *, user_style: PersonaStyleLevel | None
) -> PersonaStyleLevel:
    """Resolve style using precedence contract for non-violating turns.

    Args:
        user_style: User-selected style for the current session/turn.

    Returns:
        Effective style respecting precedence contract.
    """
    if user_style is not None:
        return user_style
    return _PERSONA_DEFAULT_STYLE


def evaluate_pre_generation(user_text: str) -> PolicyDecision:
    """Evaluate user input against pre-generation policy guardrails.

    Args:
        user_text: Raw normalized user text.

    Returns:
        Deterministic policy decision.
    """
    text = user_text.strip()
    for pattern in _PRE_INPUT_BLOCK_PATTERNS:
        if pattern.search(text):
            return PolicyDecision(
                allowed=False,
                code="conversation_policy_denied",
                reason="Input requested policy bypass.",
            )
    return PolicyDecision(allowed=True)


def evaluate_post_generation(text: str) -> PolicyDecision:
    """Evaluate generated assistant text against post-generation guardrails.

    Args:
        text: Candidate assistant output text.

    Returns:
        Deterministic policy decision.
    """
    normalized = text.strip()
    for pattern in _POST_OUTPUT_BLOCK_PATTERNS:
        if pattern.search(normalized):
            return PolicyDecision(
                allowed=False,
                code="conversation_policy_denied",
                reason="Output violated dependency/manipulation policy.",
            )
    return PolicyDecision(allowed=True)


def evaluate_memory_write(content: str) -> PolicyDecision:
    """Evaluate candidate memory content before persistence.

    Args:
        content: Candidate memory content text.

    Returns:
        Deterministic policy decision.
    """
    text = content.strip()
    for pattern in _MEMORY_BLOCK_PATTERNS:
        if pattern.search(text):
            return PolicyDecision(
                allowed=False,
                code="memory_policy_denied",
                reason="Memory content contains blocked sensitive data.",
            )
    return PolicyDecision(allowed=True)


def force_safe_style() -> PersonaStyleLevel:
    """Return style used when safety must override style preferences.

    Returns:
        Safety-forced style level.
    """
    return _SAFETY_FORCED_STYLE

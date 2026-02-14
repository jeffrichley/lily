"""Eligibility rule evaluation for skills."""

from __future__ import annotations

import shutil
from typing import Protocol

from lily.skills.types import EligibilityContext, SkillEntry, SkillMetadata


class EligibilityRule(Protocol):
    """Strategy protocol for a single eligibility rule."""

    def is_eligible(
        self, metadata: SkillMetadata, context: EligibilityContext
    ) -> tuple[bool, str | None]:
        """Return ``(eligible, reason)`` for a single rule.

        Args:
            metadata: Parsed skill metadata to evaluate.
            context: Runtime context used for eligibility checks.
        """


class OsEligibilityRule:
    """Validate OS/platform constraints."""

    def is_eligible(
        self, metadata: SkillMetadata, context: EligibilityContext
    ) -> tuple[bool, str | None]:
        """Check whether current platform satisfies ``eligibility.os``.

        Args:
            metadata: Parsed skill metadata to evaluate.
            context: Runtime context used for eligibility checks.

        Returns:
            A tuple containing whether the rule passes and an optional reason.
        """
        allowed = metadata.eligibility.os
        if not allowed:
            return True, None
        if context.platform in allowed:
            return True, None
        return False, f"OS '{context.platform}' not in allowed set {list(allowed)}"


class EnvEligibilityRule:
    """Validate required environment variables."""

    def is_eligible(
        self, metadata: SkillMetadata, context: EligibilityContext
    ) -> tuple[bool, str | None]:
        """Check whether all ``eligibility.env`` variables are present.

        Args:
            metadata: Parsed skill metadata to evaluate.
            context: Runtime context used for eligibility checks.

        Returns:
            A tuple containing whether the rule passes and an optional reason.
        """
        required = metadata.eligibility.env
        if not required:
            return True, None
        missing = [name for name in required if not context.env.get(name)]
        if not missing:
            return True, None
        return False, f"Missing required env vars: {', '.join(missing)}"


class BinaryEligibilityRule:
    """Validate required binaries on PATH."""

    def is_eligible(
        self, metadata: SkillMetadata, _context: EligibilityContext
    ) -> tuple[bool, str | None]:
        """Check whether all ``eligibility.binaries`` resolve on PATH.

        Args:
            metadata: Parsed skill metadata to evaluate.
            _context: Unused runtime context retained for protocol compatibility.

        Returns:
            A tuple containing whether the rule passes and an optional reason.
        """
        required = metadata.eligibility.binaries
        if not required:
            return True, None
        missing = [name for name in required if shutil.which(name) is None]
        if not missing:
            return True, None
        return False, f"Missing required binaries: {', '.join(missing)}"


def evaluate_metadata_eligibility(
    metadata: SkillMetadata,
    context: EligibilityContext,
) -> tuple[bool, tuple[str, ...]]:
    """Evaluate all metadata eligibility rules for a skill.

    Args:
        metadata: Parsed skill metadata to evaluate.
        context: Runtime context used for eligibility checks.

    Returns:
        A tuple containing overall eligibility and failure reasons.
    """
    rules: tuple[EligibilityRule, ...] = (
        OsEligibilityRule(),
        EnvEligibilityRule(),
        BinaryEligibilityRule(),
    )

    reasons: list[str] = []
    for rule in rules:
        is_ok, reason = rule.is_eligible(metadata, context)
        if not is_ok:
            reasons.append(reason or "Unknown eligibility failure")

    return len(reasons) == 0, tuple(reasons)


def evaluate_tool_requirements(
    entry: SkillEntry,
    context: EligibilityContext,
) -> tuple[bool, tuple[str, ...]]:
    """Check required tools against current available tool policy context.

    Args:
        entry: Resolved skill entry under evaluation.
        context: Runtime context containing available tool policy.

    Returns:
        A tuple containing overall eligibility and failure reasons.
    """
    if context.available_tools is None:
        return True, ()

    missing = sorted(set(entry.requires_tools) - set(context.available_tools))
    if not missing:
        return True, ()
    return False, tuple(f"Missing required tool: {name}" for name in missing)

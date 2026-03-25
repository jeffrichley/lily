"""Typed skill package models and validation helpers for SKILL.md contracts."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SkillTypeName = Literal["standard", "playbook", "procedural", "agent"]

_KEBAB_CASE_RECOMMENDED = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_RESERVED_NAME_PREFIXES = ("claude", "anthropic")


class SkillValidationError(ValueError):
    """Raised when SKILL.md content fails contract validation."""

    def __init__(self, message: str, *, field: str | None = None) -> None:
        """Create a validation error with an optional affected field path.

        Args:
            message: Human-readable explanation.
            field: Optional dot-path of the failing field (for example ``name``).
        """
        self.field = field
        super().__init__(message)


class SkillMetadata(BaseModel):
    """Validated YAML frontmatter for a skill package (guide-aligned required keys)."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )

    name: str = Field(min_length=1)
    description: str = Field(min_length=1, max_length=1024)
    license: str | None = None
    compatibility: str | None = None
    allowed_tools: str | None = Field(None, alias="allowed-tools")
    metadata: dict[str, Any] | None = None
    skill_type: SkillTypeName | None = Field(
        default=None,
        alias="type",
        description=(
            "Optional package shape hint. "
            "'standard' is the default flat package: SKILL.md at the skill "
            "directory root (e.g. skills/<name>/SKILL.md) with optional references/, "
            "assets/, scripts/ — not nested under playbook/procedural/agent adapter "
            "folders. Other values reserve post-MVP execution-adapter layouts; "
            "MVP retrieval does not branch on these yet."
        ),
    )

    @field_validator("name", "description", "license", "compatibility", "allowed_tools")
    @classmethod
    def _non_empty_strings_when_present(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not str(v).strip():
            msg = "value must not be empty or whitespace-only"
            raise ValueError(msg)
        return str(v)

    def to_summary(self) -> SkillSummary:
        """Derive an index record from this metadata.

        Returns:
            Frozen summary suitable for catalog injection and indexing keys.
        """
        canonical_key = normalize_skill_name(self.name)
        return SkillSummary(
            name=self.name,
            description=self.description,
            canonical_key=canonical_key,
            skill_type=self.skill_type,
        )


class SkillSummary(BaseModel):
    """Minimal skill metadata used for catalog injection and indexing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str
    canonical_key: str
    skill_type: SkillTypeName | None = None


def normalize_skill_name(name: str) -> str:
    """Map author-facing ``name`` to the internal canonical key (lowercase kebab-like).

    Args:
        name: Non-empty skill name from frontmatter.

    Returns:
        Normalized key for stable indexing and retrieval.

    Raises:
        SkillValidationError: If normalization yields an empty string.
    """
    lowered = name.strip().lower()
    step = re.sub(r"[\s_]+", "-", lowered)
    collapsed = re.sub(r"-+", "-", step).strip("-")
    if not collapsed:
        msg = "name normalizes to an empty canonical key"
        raise SkillValidationError(msg, field="name")
    return collapsed


def is_recommended_kebab_case_skill_name(name: str) -> bool:
    """Return True when ``name`` matches the authoring recommendation (kebab-case).

    Non-matching names are still accepted at parse time; use this for doctor/lint hints.

    Args:
        name: Skill name as authored.

    Returns:
        Whether the name follows the recommended ``^[a-z0-9]+(-[a-z0-9]+)*$`` pattern.
    """
    return bool(_KEBAB_CASE_RECOMMENDED.fullmatch(name.strip()))


def reserved_provider_name_prefix(name: str) -> bool:
    """Return True if ``name`` uses a blocked provider prefix (case-insensitive).

    Args:
        name: Skill name to check.

    Returns:
        True when the name starts with a reserved ``claude`` or ``anthropic`` prefix.
    """
    lower = name.strip().lower()
    return lower.startswith(_RESERVED_NAME_PREFIXES)

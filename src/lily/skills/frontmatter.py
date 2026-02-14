"""SKILL.md frontmatter parsing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from lily.skills.types import InvocationMode, SkillMetadata

FRONTMATTER_DELIMITER = "---"


def _extract_frontmatter(raw: str) -> tuple[str | None, str]:
    """Extract raw frontmatter text and markdown body.

    Args:
        raw: Raw ``SKILL.md`` file content.

    Returns:
        A tuple of optional raw frontmatter text and markdown body.

    Raises:
        ValueError: If the opening delimiter exists without a closing delimiter.
    """
    lines = raw.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return None, raw

    end_idx = -1
    for idx in range(1, len(lines)):
        if lines[idx].strip() == FRONTMATTER_DELIMITER:
            end_idx = idx
            break

    if end_idx == -1:
        raise ValueError("Invalid frontmatter: missing closing delimiter")

    frontmatter_text = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")
    return frontmatter_text, body


def _load_frontmatter_mapping(frontmatter_text: str) -> dict[str, Any]:
    """Load YAML frontmatter into a dictionary.

    Args:
        frontmatter_text: Raw YAML frontmatter content.

    Returns:
        Parsed frontmatter mapping.

    Raises:
        ValueError: If parsed YAML is not a mapping/object.
    """
    parsed = yaml.safe_load(frontmatter_text)
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise ValueError("Invalid frontmatter: expected a YAML mapping/object")
    return parsed


def _validate_metadata(
    metadata_dict: dict[str, Any], skill_path: Path | None
) -> SkillMetadata:
    """Validate and normalize parsed metadata.

    Args:
        metadata_dict: Parsed frontmatter mapping.
        skill_path: Optional skill file path used for contextual errors.

    Returns:
        Validated skill metadata object.

    Raises:
        ValueError: If metadata validation fails.
    """
    origin = f" ({skill_path})" if skill_path else ""
    try:
        metadata = SkillMetadata.model_validate(metadata_dict)
    except ValidationError as exc:
        raise ValueError(f"Malformed skill frontmatter{origin}: {exc}") from exc

    if (
        metadata.invocation_mode == InvocationMode.TOOL_DISPATCH
        and not metadata.command_tool
    ):
        raise ValueError(
            f"Malformed skill frontmatter{origin}: tool_dispatch requires command_tool",
        )

    return metadata


def parse_skill_markdown(
    raw: str, skill_path: Path | None = None
) -> tuple[SkillMetadata, str]:
    """Parse SKILL.md into validated metadata and markdown body.

    Args:
        raw: Raw ``SKILL.md`` file content.
        skill_path: Optional file path used for contextual validation errors.

    Returns:
        A tuple of validated metadata and markdown body content.
    """
    frontmatter_text, body = _extract_frontmatter(raw)
    if frontmatter_text is None:
        return SkillMetadata(), body

    metadata_dict = _load_frontmatter_mapping(frontmatter_text)
    metadata = _validate_metadata(metadata_dict, skill_path)
    return metadata, body

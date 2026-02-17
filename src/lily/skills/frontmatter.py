"""SKILL.md frontmatter parsing."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from lily.skills.types import InvocationMode, SkillMetadata

FRONTMATTER_DELIMITER = "---"
_PROVIDER_ID_RE = r"^[a-z][a-z0-9_]*$"


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
    payload = dict(metadata_dict)
    payload["capabilities_declared"] = "capabilities" in metadata_dict
    try:
        metadata = SkillMetadata.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Malformed skill frontmatter{origin}: {exc}") from exc

    _validate_tool_dispatch_metadata(metadata, origin)

    return metadata


def _validate_tool_dispatch_metadata(metadata: SkillMetadata, origin: str) -> None:
    """Apply tool_dispatch-specific validation rules.

    Args:
        metadata: Parsed skill metadata.
        origin: Optional contextual origin suffix for errors.

    Raises:
        ValueError: If tool-dispatch metadata is invalid.
    """
    if metadata.invocation_mode != InvocationMode.TOOL_DISPATCH:
        return
    if not metadata.command_tool:
        raise ValueError(
            f"Malformed skill frontmatter{origin}: tool_dispatch requires command_tool",
        )
    if re.fullmatch(_PROVIDER_ID_RE, metadata.command_tool_provider) is None:
        raise ValueError(
            (
                f"Malformed skill frontmatter{origin}: invalid command_tool_provider "
                f"'{metadata.command_tool_provider}'"
            ),
        )
    declared = set(metadata.capabilities.declared_tools)
    qualified = f"{metadata.command_tool_provider}:{metadata.command_tool}"
    if metadata.command_tool in declared or qualified in declared:
        _validate_plugin_metadata(metadata, origin)
        return
    raise ValueError(
        (
            f"Malformed skill frontmatter{origin}: tool_dispatch command_tool "
            f"'{metadata.command_tool}' must be declared in "
            "capabilities.declared_tools"
        ),
    )


def _validate_plugin_metadata(metadata: SkillMetadata, origin: str) -> None:
    """Apply plugin-provider metadata validation rules.

    Args:
        metadata: Parsed skill metadata.
        origin: Optional contextual origin suffix for errors.

    Raises:
        ValueError: If plugin metadata is invalid.
    """
    if metadata.command_tool_provider != "plugin":
        return
    if metadata.plugin.entrypoint is None:
        raise ValueError(
            f"Malformed skill frontmatter{origin}: plugin provider requires "
            "plugin.entrypoint",
        )
    for field_name, values in (
        ("plugin.source_files", metadata.plugin.source_files),
        ("plugin.asset_files", metadata.plugin.asset_files),
        ("plugin.env_allowlist", metadata.plugin.env_allowlist),
    ):
        if any(not value.strip() for value in values):
            raise ValueError(
                f"Malformed skill frontmatter{origin}: {field_name} contains empty "
                "value",
            )


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

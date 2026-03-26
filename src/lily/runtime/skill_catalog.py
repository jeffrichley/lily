"""Parse and validate ``SKILL.md`` skill packages (frontmatter + body)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import frontmatter  # type: ignore[import-untyped]
import yaml
from packaging.version import InvalidVersion, Version
from pydantic import ValidationError

from lily.runtime.skill_types import (
    SkillMetadata,
    SkillValidationError,
    reserved_provider_name_prefix,
)

_SKILL_MD_FILENAME = "SKILL.md"


@dataclass(frozen=True, slots=True)
class ParsedSkillMarkdown:
    """Result of parsing one ``SKILL.md`` file."""

    metadata: SkillMetadata
    body: str
    source_path: Path | None


def load_skill_md(path: Path) -> ParsedSkillMarkdown:
    """Read ``path`` and parse a skill package.

    Args:
        path: Path to a file named ``SKILL.md``.

    Returns:
        Parsed metadata and markdown body.

    Raises:
        SkillValidationError: If the file is unreadable or invalid.
    """
    if path.name != _SKILL_MD_FILENAME:
        msg = (
            f"skill package file must be named '{_SKILL_MD_FILENAME}', "
            f"got '{path.name}'"
        )
        raise SkillValidationError(msg, field="path")
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"unable to read skill file '{path}': {exc}"
        raise SkillValidationError(msg, field="path") from exc
    return parse_skill_markdown(raw, source_path=path)


def parse_skill_markdown(
    raw: str,
    *,
    source_path: Path | None = None,
) -> ParsedSkillMarkdown:
    """Parse frontmatter and body from raw ``SKILL.md`` text.

    Args:
        raw: Full file contents.
        source_path: Optional path for error context only.

    Returns:
        Validated metadata and body text.

    Raises:
        SkillValidationError: On malformed YAML, contract violations, or policy rejects.
    """
    try:
        post = frontmatter.loads(raw)
    except yaml.YAMLError as exc:
        prefix = f"skill file '{source_path}'" if source_path else "skill markdown"
        msg = f"{prefix}: frontmatter YAML parse failed: {exc}"
        raise SkillValidationError(msg, field="frontmatter") from exc

    meta = post.metadata
    if not isinstance(meta, dict):
        msg = "frontmatter must parse to a YAML mapping"
        raise SkillValidationError(msg, field="frontmatter")

    _reject_angle_bracket_values(meta, path_prefix="")
    try:
        model = SkillMetadata.model_validate(meta)
    except ValidationError as exc:
        errors = exc.errors()
        if not errors:
            failed = "frontmatter validation failed"
            raise SkillValidationError(failed, field="frontmatter") from exc
        first = errors[0]
        loc_parts = [str(loc) for loc in first.get("loc", ())]
        loc = ".".join(loc_parts) if loc_parts else "frontmatter"
        pyd_msg = first.get("msg", "validation error")
        raise SkillValidationError(f"{loc}: {pyd_msg}", field=loc) from exc

    _validate_reserved_skill_name(model.name)
    _validate_metadata_version_semver(model.metadata)

    body = post.content if isinstance(post.content, str) else ""
    return ParsedSkillMarkdown(metadata=model, body=body, source_path=source_path)


def _reject_angle_bracket_values(obj: object, *, path_prefix: str) -> None:
    """Reject ``<`` and ``>`` in any string value (including nested structures).

    Args:
        obj: Parsed YAML value to scan recursively.
        path_prefix: Dot-path prefix used in error messages.
    """
    if isinstance(obj, str):
        _reject_angle_brackets_in_string(obj, path_prefix)
        return
    if isinstance(obj, dict):
        _reject_angle_brackets_in_mapping(obj, path_prefix)
        return
    if isinstance(obj, list):
        _reject_angle_brackets_in_sequence(obj, path_prefix)
        return


def _reject_angle_brackets_in_string(value: str, path_prefix: str) -> None:
    """Reject angle brackets inside a scalar string.

    Args:
        value: YAML string value.
        path_prefix: Dot-path prefix for error context.

    Raises:
        SkillValidationError: If ``value`` contains ``<`` or ``>``.
    """
    if "<" not in value and ">" not in value:
        return
    loc = path_prefix or "<root>"
    msg = (
        f"frontmatter{loc}: angle brackets '<' and '>' are not allowed in "
        "frontmatter values"
    )
    raise SkillValidationError(msg, field=f"frontmatter{loc}")


def _reject_angle_brackets_in_mapping(
    obj: dict[object, object], path_prefix: str
) -> None:
    """Reject angle brackets in mapping keys and recurse into values.

    Args:
        obj: YAML mapping.
        path_prefix: Dot-path prefix for nested keys.

    Raises:
        SkillValidationError: If a key or nested value contains angle brackets.
    """
    for key, val in obj.items():
        key_str = str(key)
        if isinstance(key, str) and ("<" in key or ">" in key):
            loc = f"{path_prefix}.{key_str}" if path_prefix else f".{key_str}"
            msg = f"frontmatter{loc}: angle brackets are not allowed in mapping keys"
            raise SkillValidationError(msg, field=f"frontmatter{loc}")
        sub = f"{path_prefix}.{key_str}" if path_prefix else f".{key_str}"
        _reject_angle_bracket_values(val, path_prefix=sub)


def _reject_angle_brackets_in_sequence(obj: list[object], path_prefix: str) -> None:
    """Recurse angle-bracket checks for each list element.

    Args:
        obj: YAML sequence.
        path_prefix: Dot-path prefix for indexed elements.
    """
    for i, val in enumerate(obj):
        sub = f"{path_prefix}[{i}]"
        _reject_angle_bracket_values(val, path_prefix=sub)


def _validate_reserved_skill_name(name: str) -> None:
    """Reject names that use a reserved provider prefix.

    Args:
        name: Parsed ``name`` field from frontmatter.

    Raises:
        SkillValidationError: If the name starts with a blocked prefix.
    """
    if reserved_provider_name_prefix(name):
        msg = (
            "name must not use a reserved provider prefix "
            "(names starting with 'claude' or 'anthropic' are blocked)"
        )
        raise SkillValidationError(msg, field="name")


def _validate_metadata_version_semver(meta: dict[str, Any] | None) -> None:
    """Ensure ``metadata.version`` is a semver string when present.

    Args:
        meta: Optional ``metadata`` mapping from frontmatter.

    Raises:
        SkillValidationError: If ``version`` is present but not a valid semver string.
    """
    if meta is None or "version" not in meta:
        return
    raw = meta["version"]
    if not isinstance(raw, str):
        msg = "metadata.version must be a semver string"
        raise SkillValidationError(msg, field="metadata.version")
    try:
        Version(raw)
    except InvalidVersion:
        msg = f"metadata.version is not a valid semver: {raw!r}"
        raise SkillValidationError(msg, field="metadata.version") from None

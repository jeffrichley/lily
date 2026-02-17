"""Documentation frontmatter validation and remediation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

_DOCS_ROOT = "docs"
_MARKDOWN_SUFFIX = ".md"
_FRONTMATTER_DELIMITER = "---"
_REQUIRED_FIELDS = ("owner", "last_updated", "status", "source_of_truth")
_VALID_STATUSES = {"active", "reference", "archived"}
_INVALID_TEXT_VALUES = {"", "TBD", "TODO", "@todo", "YYYY-MM-DD"}


@dataclass(frozen=True)
class ValidationConfig:
    """Runtime configuration for docs validation."""

    docs_root: Path
    max_active_age_days: int = 21
    auto_fix_missing_frontmatter: bool = False
    owner_placeholder: str = "TBD"
    date_placeholder: str = "TBD"


def _all_docs_markdown_files(docs_root: Path) -> list[Path]:
    """Return sorted markdown files under the docs root.

    Args:
        docs_root: Root docs directory to scan recursively.

    Returns:
        Sorted list of markdown paths.
    """
    return sorted(docs_root.rglob(f"*{_MARKDOWN_SUFFIX}"))


def _extract_frontmatter(raw: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Extract YAML frontmatter from a markdown document.

    Args:
        raw: Entire markdown file content.

    Returns:
        Tuple of parsed frontmatter mapping (or None) and parse errors.
    """
    normalized = raw.lstrip("\ufeff")
    if not normalized.startswith(f"{_FRONTMATTER_DELIMITER}\n"):
        return None, []
    lines = normalized.splitlines()
    end_index = -1
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == _FRONTMATTER_DELIMITER:
            end_index = index
            break
    if end_index == -1:
        return None, [
            "Frontmatter start delimiter found, but closing delimiter is missing."
        ]
    yaml_payload = "\n".join(lines[1:end_index])
    try:
        loaded = yaml.safe_load(yaml_payload)
    except yaml.YAMLError as exc:
        return None, [f"Malformed frontmatter YAML: {exc}"]
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        return None, ["Frontmatter must be a YAML object/mapping."]
    return loaded, []


def _default_frontmatter_block(owner_placeholder: str, date_placeholder: str) -> str:
    """Build the placeholder frontmatter inserted by auto-fix mode.

    Args:
        owner_placeholder: Placeholder value written for owner.
        date_placeholder: Placeholder value written for last_updated.

    Returns:
        Serialized YAML frontmatter block.
    """
    return (
        "---\n"
        f'owner: "{owner_placeholder}"\n'
        f'last_updated: "{date_placeholder}"\n'
        'status: "reference"\n'
        "source_of_truth: false\n"
        "---\n\n"
    )


def _is_invalid_text_value(value: object) -> bool:
    """Return True when the value is not an acceptable non-empty string.

    Args:
        value: Candidate value from parsed frontmatter.

    Returns:
        True when the value is non-string, empty, or a placeholder token.
    """
    return not isinstance(value, str) or value.strip() in _INVALID_TEXT_VALUES


def _validate_last_updated(
    last_updated: object, *, today: date, max_age_days: int
) -> list[str]:
    """Validate last_updated format and staleness constraints.

    Args:
        last_updated: Raw last_updated value from frontmatter.
        today: Current date used to evaluate staleness.
        max_age_days: Maximum allowed age for active docs.

    Returns:
        Deterministic validation error messages for last_updated.
    """
    if _is_invalid_text_value(last_updated):
        return ["Field 'last_updated' must be a concrete ISO date (YYYY-MM-DD)."]
    assert isinstance(last_updated, str)
    try:
        updated_on = date.fromisoformat(last_updated)
    except ValueError:
        return ["Field 'last_updated' must use ISO date format YYYY-MM-DD."]
    age_days = (today - updated_on).days
    if age_days < 0:
        return ["Field 'last_updated' cannot be in the future."]
    if age_days > max_age_days:
        return [
            "Field 'last_updated' is stale for active docs "
            f"({age_days} days old; max {max_age_days})."
        ]
    return []


def _validate_required_fields(frontmatter: dict[str, Any]) -> list[str]:
    """Validate required frontmatter keys exist.

    Args:
        frontmatter: Parsed frontmatter mapping.

    Returns:
        Missing-field validation errors.
    """
    return [
        f"Missing required field '{key}'."
        for key in _REQUIRED_FIELDS
        if key not in frontmatter
    ]


def _validate_common_values(
    owner: object, status: object, source_of_truth: object
) -> list[str]:
    """Validate owner, status, and source_of_truth fields.

    Args:
        owner: Raw owner field value.
        status: Raw status field value.
        source_of_truth: Raw source_of_truth field value.

    Returns:
        Validation errors for the common non-date fields.
    """
    errors: list[str] = []
    if _is_invalid_text_value(owner):
        errors.append("Field 'owner' must be a concrete non-placeholder value.")
    if _is_invalid_text_value(status) or status not in _VALID_STATUSES:
        errors.append("Field 'status' must be one of: active, reference, archived.")
    if not isinstance(source_of_truth, bool):
        errors.append("Field 'source_of_truth' must be a boolean value.")
    return errors


def _validate_non_active_last_updated(last_updated: object) -> list[str]:
    """Validate last_updated for non-active docs.

    Args:
        last_updated: Raw last_updated value from frontmatter.

    Returns:
        Validation errors for date format/presence.
    """
    if _is_invalid_text_value(last_updated):
        return ["Field 'last_updated' must be a concrete ISO date (YYYY-MM-DD)."]
    try:
        date.fromisoformat(str(last_updated))
    except ValueError:
        return ["Field 'last_updated' must use ISO date format YYYY-MM-DD."]
    return []


def _validate_frontmatter_values(
    frontmatter: dict[str, Any],
    *,
    today: date,
    max_age_days: int,
) -> list[str]:
    """Validate required keys and field value semantics.

    Args:
        frontmatter: Parsed frontmatter mapping.
        today: Current date used for staleness checks.
        max_age_days: Maximum age for active docs.

    Returns:
        Validation errors for required fields and value semantics.
    """
    errors = _validate_required_fields(frontmatter)
    if errors:
        return errors

    owner = frontmatter["owner"]
    status = frontmatter["status"]
    source_of_truth = frontmatter["source_of_truth"]
    last_updated = frontmatter["last_updated"]

    errors.extend(_validate_common_values(owner, status, source_of_truth))
    if status == "active":
        errors.extend(
            _validate_last_updated(last_updated, today=today, max_age_days=max_age_days)
        )
    else:
        errors.extend(_validate_non_active_last_updated(last_updated))

    return errors


def validate_docs_frontmatter(
    config: ValidationConfig, *, today: date | None = None
) -> list[str]:
    """Validate docs frontmatter and optionally auto-fix missing frontmatter.

    Args:
        config: Validation configuration.
        today: Optional override for deterministic tests.

    Returns:
        A list of validation failures. Empty list means pass.
    """
    now = today or datetime.now(tz=UTC).date()
    errors: list[str] = []
    docs_root = config.docs_root
    if not docs_root.exists():
        return [f"Docs root does not exist: {docs_root}"]

    for path in _all_docs_markdown_files(docs_root):
        raw = path.read_text(encoding="utf-8")
        frontmatter, parse_errors = _extract_frontmatter(raw)
        if frontmatter is None and config.auto_fix_missing_frontmatter:
            block = _default_frontmatter_block(
                config.owner_placeholder, config.date_placeholder
            )
            path.write_text(block + raw, encoding="utf-8")
            raw = path.read_text(encoding="utf-8")
            frontmatter, parse_errors = _extract_frontmatter(raw)
        if frontmatter is None:
            errors.append(f"{path}: Missing frontmatter block.")
            continue
        if parse_errors:
            errors.extend([f"{path}: {parse_error}" for parse_error in parse_errors])
            continue
        value_errors = _validate_frontmatter_values(
            frontmatter, today=now, max_age_days=config.max_active_age_days
        )
        errors.extend([f"{path}: {value_error}" for value_error in value_errors])
    return errors


def default_config(repo_root: Path) -> ValidationConfig:
    """Return default repository-level docs validation config.

    Args:
        repo_root: Repository root path.

    Returns:
        Default validation configuration targeting `docs/`.
    """
    return ValidationConfig(docs_root=repo_root / _DOCS_ROOT)

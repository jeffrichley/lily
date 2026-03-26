"""Documentation frontmatter validation and remediation helpers."""

from __future__ import annotations

import re
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
_ROADMAP_REL_PATH = Path("dev/roadmap.md")
_STATUS_REL_PATH = Path("dev/status.md")
_DEBT_REL_PATH = Path("dev/debt/debt_tracker.md")
_SYSTEM_IMPROVEMENTS_HEADING = "## System Improvements (Internal Work)"
_CURRENT_FOCUS_HEADING = "## Current Focus"
_RECENTLY_COMPLETED_HEADING = "## Recently Completed"
_SYSTEM_IMPROVEMENT_ID_RE = re.compile(r"\bSI-\d{3}\b")
_DEBT_ID_RE = re.compile(r"\bDEBT-\d{3}\b")
_SYSTEM_IMPROVEMENTS_MIN_COLUMNS = 4


@dataclass(frozen=True)
class ValidationConfig:
    """Runtime configuration for docs validation."""

    docs_root: Path
    max_active_age_days: int = 21
    auto_fix_missing_frontmatter: bool = False
    owner_placeholder: str = "TBD"
    date_placeholder: str = "TBD"


@dataclass(frozen=True)
class _StatusTraceContext:
    """Shared context for one status section traceability pass."""

    section_label: str
    status_by_id: dict[str, str]
    debt_ids: set[str]
    status_path: Path
    forbidden_status: str
    forbidden_message: str


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


def _extract_markdown_section(markdown: str, heading: str) -> str:
    """Return markdown section body for a heading or empty string if absent.

    Args:
        markdown: Full markdown document text.
        heading: Exact heading marker to split on.

    Returns:
        Section body content, or empty string when heading is missing.
    """
    if heading not in markdown:
        return ""
    section = markdown.split(heading, 1)[1]
    return section.split("\n## ", 1)[0]


def _parse_roadmap_system_improvements(
    roadmap_path: Path,
) -> tuple[dict[str, str], list[str]]:
    """Parse roadmap system improvement IDs and statuses.

    Args:
        roadmap_path: Path to the roadmap markdown document.

    Returns:
        Tuple of `{SI-XXX: status}` mapping and deterministic parse errors.
    """
    roadmap_raw = roadmap_path.read_text(encoding="utf-8")
    section = _extract_markdown_section(roadmap_raw, _SYSTEM_IMPROVEMENTS_HEADING)
    if not section:
        return ({}, ["Missing 'System Improvements (Internal Work)' section."])

    status_by_id: dict[str, str] = {}
    errors: list[str] = []
    for line in section.splitlines():
        parsed_row, row_errors = _parse_system_improvement_row(
            raw_line=line, known_ids=set(status_by_id)
        )
        errors.extend(row_errors)
        if parsed_row is None:
            continue
        improvement_id, improvement_status = parsed_row
        status_by_id[improvement_id] = improvement_status
    return (status_by_id, errors)


def _parse_system_improvement_row(
    *, raw_line: str, known_ids: set[str]
) -> tuple[tuple[str, str] | None, list[str]]:
    """Parse one roadmap table line into `(id, status)` or skip/error.

    Args:
        raw_line: One raw line from the roadmap section.
        known_ids: IDs already parsed for duplicate detection.

    Returns:
        Parsed row tuple and row-level parse/validation errors.
    """
    stripped = raw_line.strip()
    if not stripped.startswith("|"):
        return (None, [])
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if not cells or cells[0] == "ID" or set(cells[0]) <= {"-", ":"}:
        return (None, [])
    if len(cells) < _SYSTEM_IMPROVEMENTS_MIN_COLUMNS:
        return (
            None,
            [
                "System improvements table rows must include ID, improvement, "
                "priority, and status columns."
            ],
        )

    improvement_id = cells[0]
    if _SYSTEM_IMPROVEMENT_ID_RE.fullmatch(improvement_id) is None:
        return (
            None,
            [f"Invalid system improvement ID '{improvement_id}' (expected SI-XXX)."],
        )
    if improvement_id in known_ids:
        return (None, [f"Duplicate system improvement ID '{improvement_id}'."])
    return ((improvement_id, cells[3].lower()), [])


def _extract_status_bullets(status_raw: str, heading: str) -> list[str]:
    """Extract one section's markdown bullet items.

    Args:
        status_raw: Full status markdown document text.
        heading: Section heading to extract.

    Returns:
        List of bullet texts from that section.
    """
    section = _extract_markdown_section(status_raw, heading)
    return [
        line.strip()[2:].strip()
        for line in section.splitlines()
        if line.strip().startswith("- ")
    ]


def _validate_status_roadmap_traceability(docs_root: Path) -> list[str]:
    """Validate status/roadmap traceability for system-improvement IDs.

    Args:
        docs_root: Root `docs/` directory.

    Returns:
        Traceability validation errors for status/roadmap linkage.
    """
    roadmap_path = docs_root / _ROADMAP_REL_PATH
    status_path = docs_root / _STATUS_REL_PATH
    if not roadmap_path.exists() or not status_path.exists():
        return []

    status_by_id, roadmap_errors = _parse_roadmap_system_improvements(roadmap_path)
    errors = [f"{roadmap_path}: {error}" for error in roadmap_errors]
    debt_ids, debt_errors = _parse_debt_ids(docs_root / _DEBT_REL_PATH)
    errors.extend(debt_errors)

    status_raw = status_path.read_text(encoding="utf-8")
    current_focus = _extract_status_bullets(status_raw, _CURRENT_FOCUS_HEADING)
    recently_completed = _extract_status_bullets(
        status_raw, _RECENTLY_COMPLETED_HEADING
    )
    errors.extend(
        _validate_current_focus_traceability(
            current_focus=current_focus,
            status_by_id=status_by_id,
            debt_ids=debt_ids,
            status_path=status_path,
        )
    )
    errors.extend(
        _validate_recently_completed_traceability(
            recently_completed=recently_completed,
            status_by_id=status_by_id,
            debt_ids=debt_ids,
            status_path=status_path,
        )
    )
    return errors


def _validate_current_focus_traceability(
    *,
    current_focus: list[str],
    status_by_id: dict[str, str],
    debt_ids: set[str],
    status_path: Path,
) -> list[str]:
    """Validate system-improvement references in Current Focus.

    Args:
        current_focus: Current Focus bullet texts.
        status_by_id: Parsed roadmap status by SI ID.
        debt_ids: Known DEBT IDs from debt tracker.
        status_path: Status doc path for error prefixing.

    Returns:
        Traceability validation errors for Current Focus bullets.
    """
    errors: list[str] = []
    context = _StatusTraceContext(
        section_label="Current Focus",
        status_by_id=status_by_id,
        debt_ids=debt_ids,
        status_path=status_path,
        forbidden_status="completed",
        forbidden_message=(
            "Current Focus references completed system improvement '{id}'."
        ),
    )
    for bullet in current_focus:
        errors.extend(
            _validate_status_bullet_traceability(
                bullet=bullet,
                context=context,
            )
        )
    return errors


def _validate_recently_completed_traceability(
    *,
    recently_completed: list[str],
    status_by_id: dict[str, str],
    debt_ids: set[str],
    status_path: Path,
) -> list[str]:
    """Validate system-improvement references in Recently Completed.

    Args:
        recently_completed: Recently Completed bullet texts.
        status_by_id: Parsed roadmap status by SI ID.
        debt_ids: Known DEBT IDs from debt tracker.
        status_path: Status doc path for error prefixing.

    Returns:
        Traceability validation errors for Recently Completed bullets.
    """
    errors: list[str] = []
    context = _StatusTraceContext(
        section_label="Recently Completed",
        status_by_id=status_by_id,
        debt_ids=debt_ids,
        status_path=status_path,
        forbidden_status="open",
        forbidden_message=(
            "Recently Completed marks system improvement '{id}' complete while "
            "roadmap status is Open."
        ),
    )
    for bullet in recently_completed:
        errors.extend(
            _validate_status_bullet_traceability(
                bullet=bullet,
                context=context,
            )
        )
    return errors


def _parse_debt_ids(debt_path: Path) -> tuple[set[str], list[str]]:
    """Parse DEBT-XXX identifiers from debt tracker checkbox items.

    Args:
        debt_path: Path to debt tracker markdown file.

    Returns:
        Tuple of parsed DEBT ID set and parse errors.
    """
    items, errors = _parse_debt_items(debt_path)
    return ({item_id for item_id, _, _ in items}, errors)


def _parse_debt_items(
    debt_path: Path,
) -> tuple[list[tuple[str, list[str], str]], list[str]]:
    """Parse debt checkbox items and attached metadata lines.

    Args:
        debt_path: Path to debt tracker markdown file.

    Returns:
        Tuple of parsed items and parse errors.
        Each item is `(debt_id, metadata_lines, checkbox_line)`.
    """
    if not debt_path.exists():
        return ([], [])
    raw = debt_path.read_text(encoding="utf-8")
    items: list[tuple[str, list[str], str]] = []
    errors: list[str] = []
    current_index: int | None = None
    for line in raw.splitlines():
        stripped = line.strip()
        is_checkbox = stripped.startswith("- [ ]") or stripped.startswith("- [x]")
        if not is_checkbox:
            if current_index is not None:
                items[current_index][1].append(stripped)
            continue
        matches = _DEBT_ID_RE.findall(stripped)
        if len(matches) != 1:
            errors.append(
                f"{debt_path}: Debt checkbox item must include exactly one "
                f"DEBT-XXX ID: '{stripped}'"
            )
            current_index = None
            continue
        items.append((matches[0], [], stripped))
        current_index = len(items) - 1
    return (items, errors)


def _validate_status_bullet_traceability(
    *,
    bullet: str,
    context: _StatusTraceContext,
) -> list[str]:
    """Validate SI/DEBT IDs in one status bullet for one section.

    Args:
        bullet: One status bullet text.
        context: Shared section-specific validation context.

    Returns:
        Traceability validation errors for that bullet.
    """
    errors: list[str] = []
    system_ids = _SYSTEM_IMPROVEMENT_ID_RE.findall(bullet)
    debt_ids_in_bullet = _DEBT_ID_RE.findall(bullet)
    lowered = bullet.lower()

    if "system improvement" in lowered and not system_ids:
        errors.append(
            f"{context.status_path}: {context.section_label} system-improvement "
            "bullet must include "
            f"an SI-XXX ID: '{bullet}'"
        )
    if "debt" in lowered and not debt_ids_in_bullet:
        errors.append(
            f"{context.status_path}: {context.section_label} debt-backed bullet "
            "must include a "
            f"DEBT-XXX ID: '{bullet}'"
        )

    for improvement_id in system_ids:
        if improvement_id not in context.status_by_id:
            errors.append(
                f"{context.status_path}: {context.section_label} references unknown "
                "system "
                f"improvement ID '{improvement_id}'."
            )
            continue
        if context.status_by_id[improvement_id] == context.forbidden_status:
            errors.append(
                f"{context.status_path}: "
                f"{context.forbidden_message.format(id=improvement_id)}"
            )

    errors.extend(
        [
            f"{context.status_path}: {context.section_label} references unknown "
            f"debt ID '{debt_id}'."
            for debt_id in debt_ids_in_bullet
            if debt_id not in context.debt_ids
        ]
    )
    return errors


def _validate_debt_roadmap_traceability(docs_root: Path) -> list[str]:
    """Validate debt-item IDs and roadmap links in debt tracker.

    Args:
        docs_root: Root `docs/` directory.

    Returns:
        Traceability validation errors for debt/roadmap linkage.
    """
    roadmap_path = docs_root / _ROADMAP_REL_PATH
    debt_path = docs_root / _DEBT_REL_PATH
    if not roadmap_path.exists() or not debt_path.exists():
        return []

    status_by_id, roadmap_errors = _parse_roadmap_system_improvements(roadmap_path)
    errors = [f"{roadmap_path}: {error}" for error in roadmap_errors]
    items, debt_errors = _parse_debt_items(debt_path)
    errors.extend(debt_errors)

    seen_debt_ids: set[str] = set()
    for debt_id, metadata_lines, _ in items:
        if debt_id in seen_debt_ids:
            errors.append(f"{debt_path}: Duplicate debt ID '{debt_id}'.")
        seen_debt_ids.add(debt_id)
        errors.extend(
            _validate_debt_roadmap_links(
                debt_id=debt_id,
                metadata_lines=metadata_lines,
                status_by_id=status_by_id,
                debt_path=debt_path,
            )
        )
    return errors


def _validate_debt_roadmap_links(
    *,
    debt_id: str,
    metadata_lines: list[str],
    status_by_id: dict[str, str],
    debt_path: Path,
) -> list[str]:
    """Validate one debt item's `Roadmap: SI-XXX` references.

    Args:
        debt_id: One parsed debt item ID.
        metadata_lines: Associated indented metadata lines.
        status_by_id: Parsed roadmap status by SI ID.
        debt_path: Debt tracker path for error prefixing.

    Returns:
        Validation errors for this debt item's roadmap links.
    """
    errors: list[str] = []
    roadmap_lines = [line for line in metadata_lines if "Roadmap:" in line]
    for line in roadmap_lines:
        for improvement_id in _SYSTEM_IMPROVEMENT_ID_RE.findall(line):
            if improvement_id not in status_by_id:
                errors.append(
                    f"{debt_path}: Debt item '{debt_id}' references unknown "
                    f"roadmap ID '{improvement_id}'."
                )
                continue
            if status_by_id[improvement_id] == "completed":
                errors.append(
                    f"{debt_path}: Debt item '{debt_id}' references roadmap "
                    f"item '{improvement_id}' already marked Completed."
                )
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
    errors.extend(_validate_status_roadmap_traceability(docs_root))
    errors.extend(_validate_debt_roadmap_traceability(docs_root))
    return errors


def default_config(repo_root: Path) -> ValidationConfig:
    """Return default repository-level docs validation config.

    Args:
        repo_root: Repository root path.

    Returns:
        Default validation configuration targeting `docs/`.
    """
    return ValidationConfig(docs_root=repo_root / _DOCS_ROOT)

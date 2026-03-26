"""Unit tests for docs frontmatter validation and auto-fix behavior."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from lily.docs_validator import ValidationConfig, validate_docs_frontmatter


def _write(path: Path, content: str) -> None:
    """Write UTF-8 text to a file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_traceability_docs(
    tmp_path: Path, *, current_focus_bullet: str, recently_completed_bullet: str
) -> None:
    """Write minimal roadmap/status docs for traceability validation tests."""
    _write(
        tmp_path / "docs" / "dev" / "roadmap.md",
        (
            "---\n"
            'owner: "@jeffrichley"\n'
            'last_updated: "2026-03-03"\n'
            'status: "active"\n'
            "source_of_truth: true\n"
            "---\n\n"
            "# Roadmap\n\n"
            "## System Improvements (Internal Work)\n\n"
            "| ID | Improvement | Priority | Status | Enables |\n"
            "|---|---|---:|---|---|\n"
            "| SI-001 | Example completed | 5 | Completed | Reliability |\n"
            "| SI-002 | Example open | 4 | Open | Operability |\n"
        ),
    )
    _write(
        tmp_path / "docs" / "dev" / "status.md",
        (
            "---\n"
            'owner: "@jeffrichley"\n'
            'last_updated: "2026-03-03"\n'
            'status: "active"\n'
            "source_of_truth: true\n"
            "---\n\n"
            "# Status\n\n"
            "## Current Focus\n\n"
            f"- {current_focus_bullet}\n\n"
            "## Recently Completed\n\n"
            f"- {recently_completed_bullet}\n"
        ),
    )


def _write_debt_tracker(tmp_path: Path, *, debt_lines: list[str]) -> None:
    """Write minimal debt tracker with caller-provided debt lines."""
    _write(
        tmp_path / "docs" / "dev" / "debt" / "debt_tracker.md",
        (
            "---\n"
            'owner: "@jeffrichley"\n'
            'last_updated: "2026-03-03"\n'
            'status: "active"\n'
            "source_of_truth: true\n"
            "---\n\n"
            "# Debt\n\n"
            "## Active Debt\n\n"
            "### P3\n\n"
            f"{chr(10).join(debt_lines)}\n"
        ),
    )


@pytest.mark.unit
def test_validator_adds_missing_frontmatter_with_fix_and_then_fails_placeholders(
    tmp_path: Path,
) -> None:
    """Fix mode should inject frontmatter but still fail until values are real."""
    # Arrange - doc without frontmatter and config with auto_fix enabled
    doc_path = tmp_path / "docs" / "dev" / "missing.md"
    _write(doc_path, "# Missing frontmatter\n")
    config = ValidationConfig(
        docs_root=tmp_path / "docs",
        auto_fix_missing_frontmatter=True,
    )

    # Act - validate
    errors = validate_docs_frontmatter(config, today=date(2026, 2, 17))

    # Assert - file updated with frontmatter but errors mention owner and last_updated
    updated = doc_path.read_text(encoding="utf-8")
    assert updated.startswith("---\n")
    assert any("owner" in error for error in errors)
    assert any("last_updated" in error for error in errors)


@pytest.mark.unit
def test_validator_fails_stale_active_doc(tmp_path: Path) -> None:
    """Active docs should fail when last_updated exceeds max age."""
    # Arrange - active doc with old last_updated and config with max age 21
    _write(
        tmp_path / "docs" / "dev" / "status.md",
        (
            "---\n"
            'owner: "@jeffrichley"\n'
            'last_updated: "2026-01-01"\n'
            'status: "active"\n'
            "source_of_truth: true\n"
            "---\n\n"
            "# Status\n"
        ),
    )
    config = ValidationConfig(docs_root=tmp_path / "docs", max_active_age_days=21)

    # Act - validate with today 2026-02-17
    errors = validate_docs_frontmatter(config, today=date(2026, 2, 17))

    # Assert - stale error reported
    assert any("stale for active docs" in error for error in errors)


@pytest.mark.unit
def test_validator_passes_valid_docs(tmp_path: Path) -> None:
    """Valid frontmatter with fresh active docs should pass."""
    # Arrange - fresh active doc and archived doc with valid frontmatter
    _write(
        tmp_path / "docs" / "dev" / "status.md",
        (
            "---\n"
            'owner: "@jeffrichley"\n'
            'last_updated: "2026-02-17"\n'
            'status: "active"\n'
            "source_of_truth: true\n"
            "---\n\n"
            "# Status\n"
        ),
    )
    _write(
        tmp_path / "docs" / "archive" / "old.md",
        (
            "---\n"
            'owner: "@jeffrichley"\n'
            'last_updated: "2026-01-01"\n'
            'status: "archived"\n'
            "source_of_truth: false\n"
            "---\n\n"
            "# Old\n"
        ),
    )
    config = ValidationConfig(docs_root=tmp_path / "docs", max_active_age_days=21)

    # Act - validate
    errors = validate_docs_frontmatter(config, today=date(2026, 2, 17))

    # Assert - no errors
    assert errors == []


@pytest.mark.unit
def test_validator_passes_traceable_system_improvements(tmp_path: Path) -> None:
    """Status system-improvement references should pass when IDs/statuses align."""
    # Arrange - status references open item in focus and completed item in completed
    _write_traceability_docs(
        tmp_path,
        current_focus_bullet=(
            "Advance operability work (Priority 4 system improvement, SI-002)."
        ),
        recently_completed_bullet="Delivered migration hardening (SI-001).",
    )
    config = ValidationConfig(docs_root=tmp_path / "docs", max_active_age_days=21)

    # Act - validate traceability constraints
    errors = validate_docs_frontmatter(config, today=date(2026, 3, 3))

    # Assert - no consistency drift errors
    assert errors == []


@pytest.mark.unit
def test_validator_fails_unknown_system_improvement_reference(tmp_path: Path) -> None:
    """Status references must point to known roadmap SI IDs."""
    # Arrange - current focus points to SI ID absent from roadmap
    _write_traceability_docs(
        tmp_path,
        current_focus_bullet=(
            "Advance operability work (Priority 4 system improvement, SI-999)."
        ),
        recently_completed_bullet="Delivered migration hardening (SI-001).",
    )
    config = ValidationConfig(docs_root=tmp_path / "docs", max_active_age_days=21)

    # Act - validate traceability constraints
    errors = validate_docs_frontmatter(config, today=date(2026, 3, 3))

    # Assert - unknown ID error is reported deterministically
    assert any("unknown system improvement ID 'SI-999'" in error for error in errors)


@pytest.mark.unit
def test_validator_fails_recently_completed_when_roadmap_still_open(
    tmp_path: Path,
) -> None:
    """Recently completed cannot claim completion for roadmap items still Open."""
    # Arrange - completed section references an open roadmap system-improvement ID
    _write_traceability_docs(
        tmp_path,
        current_focus_bullet=(
            "Advance operability work (Priority 4 system improvement, SI-002)."
        ),
        recently_completed_bullet="Delivered migration hardening (SI-002).",
    )
    config = ValidationConfig(docs_root=tmp_path / "docs", max_active_age_days=21)

    # Act - validate traceability constraints
    errors = validate_docs_frontmatter(config, today=date(2026, 3, 3))

    # Assert - open/completed mismatch is reported
    assert any("status is Open" in error for error in errors)


@pytest.mark.unit
def test_validator_passes_debt_traceability_with_valid_roadmap_link(
    tmp_path: Path,
) -> None:
    """Debt item links should pass when DEBT/SI IDs are valid and open."""
    # Arrange - valid DEBT ID and Roadmap link to open SI item
    _write_traceability_docs(
        tmp_path,
        current_focus_bullet=(
            "Advance operability work (Priority 4 system improvement, SI-002)."
        ),
        recently_completed_bullet="Delivered migration hardening (SI-001).",
    )
    _write_debt_tracker(
        tmp_path,
        debt_lines=[
            "- [ ] [DEBT-001] Add multi-process persistence safety strategy",
            "  - Roadmap: `SI-002`",
        ],
    )
    config = ValidationConfig(docs_root=tmp_path / "docs", max_active_age_days=21)

    # Act - validate docs + debt traceability
    errors = validate_docs_frontmatter(config, today=date(2026, 3, 3))

    # Assert - no debt traceability errors
    assert errors == []


@pytest.mark.unit
def test_validator_fails_debt_traceability_for_unknown_roadmap_id(
    tmp_path: Path,
) -> None:
    """Debt item roadmap links must reference known SI IDs."""
    # Arrange - valid DEBT ID but unknown roadmap SI reference
    _write_traceability_docs(
        tmp_path,
        current_focus_bullet=(
            "Advance operability work (Priority 4 system improvement, SI-002)."
        ),
        recently_completed_bullet="Delivered migration hardening (SI-001).",
    )
    _write_debt_tracker(
        tmp_path,
        debt_lines=[
            "- [ ] [DEBT-001] Add multi-process persistence safety strategy",
            "  - Roadmap: `SI-999`",
        ],
    )
    config = ValidationConfig(docs_root=tmp_path / "docs", max_active_age_days=21)

    # Act - validate docs + debt traceability
    errors = validate_docs_frontmatter(config, today=date(2026, 3, 3))

    # Assert - unknown roadmap ID is reported
    assert any("references unknown roadmap ID 'SI-999'" in error for error in errors)


@pytest.mark.unit
def test_validator_fails_debt_traceability_when_roadmap_item_completed(
    tmp_path: Path,
) -> None:
    """Debt links to completed roadmap system improvements should fail."""
    # Arrange - DEBT item points to completed SI-001
    _write_traceability_docs(
        tmp_path,
        current_focus_bullet=(
            "Advance operability work (Priority 4 system improvement, SI-002)."
        ),
        recently_completed_bullet="Delivered migration hardening (SI-001).",
    )
    _write_debt_tracker(
        tmp_path,
        debt_lines=[
            "- [ ] [DEBT-001] Add multi-process persistence safety strategy",
            "  - Roadmap: `SI-001`",
        ],
    )
    config = ValidationConfig(docs_root=tmp_path / "docs", max_active_age_days=21)

    # Act - validate docs + debt traceability
    errors = validate_docs_frontmatter(config, today=date(2026, 3, 3))

    # Assert - completed roadmap link is rejected
    assert any("already marked Completed" in error for error in errors)


@pytest.mark.unit
def test_validator_fails_current_focus_debt_bullet_without_debt_id(
    tmp_path: Path,
) -> None:
    """Debt-backed current-focus bullets must carry a DEBT-XXX identifier."""
    # Arrange - debt-focused status bullet omits DEBT identifier
    _write_traceability_docs(
        tmp_path,
        current_focus_bullet="Close debt item for runtime locking strategy.",
        recently_completed_bullet="Delivered migration hardening (SI-001).",
    )
    _write_debt_tracker(
        tmp_path,
        debt_lines=["- [ ] [DEBT-001] Add multi-process persistence safety strategy"],
    )
    config = ValidationConfig(docs_root=tmp_path / "docs", max_active_age_days=21)

    # Act - run docs validation
    errors = validate_docs_frontmatter(config, today=date(2026, 3, 3))

    # Assert - missing DEBT token is reported
    assert any(
        "Current Focus debt-backed bullet must include a DEBT-XXX" in err
        for err in errors
    )


@pytest.mark.unit
def test_validator_fails_status_when_referencing_unknown_debt_id(
    tmp_path: Path,
) -> None:
    """Status DEBT references must resolve to known debt tracker IDs."""
    # Arrange - status references a debt ID absent from debt tracker
    _write_traceability_docs(
        tmp_path,
        current_focus_bullet="Close debt item for runtime locking strategy (DEBT-999).",
        recently_completed_bullet="Delivered migration hardening (SI-001).",
    )
    _write_debt_tracker(
        tmp_path,
        debt_lines=["- [ ] [DEBT-001] Add multi-process persistence safety strategy"],
    )
    config = ValidationConfig(docs_root=tmp_path / "docs", max_active_age_days=21)

    # Act - run docs validation
    errors = validate_docs_frontmatter(config, today=date(2026, 3, 3))

    # Assert - unknown debt ID is reported deterministically
    assert any(
        "Current Focus references unknown debt ID 'DEBT-999'" in err for err in errors
    )

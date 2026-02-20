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


@pytest.mark.unit
def test_validator_adds_missing_frontmatter_with_fix_and_then_fails_placeholders(
    tmp_path: Path,
) -> None:
    """Fix mode should inject frontmatter but still fail until values are real."""
    doc_path = tmp_path / "docs" / "dev" / "missing.md"
    _write(doc_path, "# Missing frontmatter\n")
    config = ValidationConfig(
        docs_root=tmp_path / "docs",
        auto_fix_missing_frontmatter=True,
    )

    errors = validate_docs_frontmatter(config, today=date(2026, 2, 17))

    updated = doc_path.read_text(encoding="utf-8")
    assert updated.startswith("---\n")
    assert any("owner" in error for error in errors)
    assert any("last_updated" in error for error in errors)


@pytest.mark.unit
def test_validator_fails_stale_active_doc(tmp_path: Path) -> None:
    """Active docs should fail when last_updated exceeds max age."""
    _write(
        tmp_path / "docs" / "dev" / "status.md",
        (
            "---\n"
            'owner: "@team"\n'
            'last_updated: "2026-01-01"\n'
            'status: "active"\n'
            "source_of_truth: true\n"
            "---\n\n"
            "# Status\n"
        ),
    )
    config = ValidationConfig(docs_root=tmp_path / "docs", max_active_age_days=21)

    errors = validate_docs_frontmatter(config, today=date(2026, 2, 17))

    assert any("stale for active docs" in error for error in errors)


@pytest.mark.unit
def test_validator_passes_valid_docs(tmp_path: Path) -> None:
    """Valid frontmatter with fresh active docs should pass."""
    _write(
        tmp_path / "docs" / "dev" / "status.md",
        (
            "---\n"
            'owner: "@team"\n'
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
            'owner: "@team"\n'
            'last_updated: "2026-01-01"\n'
            'status: "archived"\n'
            "source_of_truth: false\n"
            "---\n\n"
            "# Old\n"
        ),
    )
    config = ValidationConfig(docs_root=tmp_path / "docs", max_active_age_days=21)

    errors = validate_docs_frontmatter(config, today=date(2026, 2, 17))

    assert errors == []

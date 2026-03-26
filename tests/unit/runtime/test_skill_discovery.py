"""Unit tests for skill filesystem discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.config_schema import SkillsConfig
from lily.runtime.skill_discovery import discover_skill_candidates

pytestmark = pytest.mark.unit


def _write_skill_package(skill_dir: Path, *, name: str, version: str | None) -> None:
    """Write a minimal valid SKILL.md under ``skill_dir``."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    ver_block = ""
    if version is not None:
        ver_block = f'\nmetadata:\n  version: "{version}"\n'
    body = f"""---
name: {name}
description: "test skill"{ver_block}
---
# T
"""
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")


def test_discover_disabled_returns_empty() -> None:
    """When skills are disabled, discovery yields no candidates."""
    # Arrange - disabled config with roots present
    cfg = SkillsConfig(enabled=False, roots={"repository": ["."]})
    # Act - run discovery from an arbitrary base path
    candidates, events = discover_skill_candidates(cfg, base_path=Path.cwd())
    # Assert - no candidates and no diagnostic events
    assert candidates == []
    assert events == []


def test_discover_sorts_skill_directories_lexically(tmp_path: Path) -> None:
    """Skill subdirectories are visited in sorted name order."""
    # Arrange - two skills under repository root (reverse creation order)
    root = tmp_path / "skills"
    _write_skill_package(root / "zebra", name="zebra", version=None)
    _write_skill_package(root / "alpha", name="alpha", version=None)
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
    )
    # Act - discover skills relative to tmp_path
    candidates, _events = discover_skill_candidates(cfg, base_path=tmp_path)
    # Assert - lexical order of subdirectories (alpha before zebra)
    assert [c.summary.canonical_key for c in candidates] == ["alpha", "zebra"]


def test_discover_skips_missing_root_with_event(tmp_path: Path) -> None:
    """Missing root directory records a skipped_invalid diagnostic."""
    # Arrange - root path does not exist
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": ["nope-not-here"]},
        scopes_precedence=["repository", "user", "system"],
    )
    # Act - discover with a missing root path
    candidates, events = discover_skill_candidates(cfg, base_path=tmp_path)
    # Assert - skip event recorded and no candidates
    assert candidates == []
    assert len(events) == 1
    assert events[0].kind == "skipped_invalid"


def test_discover_skips_child_without_skill_md(tmp_path: Path) -> None:
    """Directories without SKILL.md are ignored without events."""
    # Arrange - empty child directory
    root = tmp_path / "skills"
    (root / "empty").mkdir(parents=True)
    _write_skill_package(root / "ok", name="ok", version=None)
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
    )
    # Act - discover under repository skills root
    candidates, _events = discover_skill_candidates(cfg, base_path=tmp_path)
    # Assert - only directories with SKILL.md become candidates
    assert [c.summary.canonical_key for c in candidates] == ["ok"]

"""Unit tests for skill registry merge and policy filters."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.config_schema import SkillsConfig
from lily.runtime.skill_discovery import discover_skill_candidates
from lily.runtime.skill_registry import build_skill_registry

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


def test_user_scope_wins_over_repository(tmp_path: Path) -> None:
    """Later scope in ``scopes_precedence`` wins on duplicate canonical keys."""
    # Arrange - duplicate skill name across repository and user roots
    repo_root = tmp_path / "repo_skills"
    user_root = tmp_path / "user_skills"
    _write_skill_package(repo_root / "pkg", name="dup", version="1.0.0")
    _write_skill_package(user_root / "pkg", name="dup", version="1.0.0")
    cfg = SkillsConfig(
        enabled=True,
        roots={
            "repository": [str(repo_root.relative_to(tmp_path))],
            "user": [str(user_root.relative_to(tmp_path))],
        },
        scopes_precedence=["repository", "user", "system"],
    )
    # Act - discover candidates then build merged registry
    candidates, _disc = discover_skill_candidates(cfg, base_path=tmp_path)
    registry = build_skill_registry(candidates, cfg)
    # Assert - winning entry is from user scope and shadowing is recorded
    entry = registry.get("dup")
    assert entry is not None
    assert entry.scope == "user"
    kinds = [e.kind for e in registry.events]
    assert "discovered" in kinds
    assert "shadowed" in kinds


def test_semver_tiebreak_within_same_scope(tmp_path: Path) -> None:
    """Higher semver wins when scope matches."""
    # Arrange - two packages same canonical name in one scope
    root = tmp_path / "skills"
    _write_skill_package(root / "older", name="x", version="1.0.0")
    _write_skill_package(root / "newer", name="x", version="2.0.0")
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
    )
    # Act - discover and merge within a single scope
    candidates, _ = discover_skill_candidates(cfg, base_path=tmp_path)
    registry = build_skill_registry(candidates, cfg)
    # Assert - higher semver package wins the canonical key
    entry = registry.get("x")
    assert entry is not None
    assert entry.skill_dir.name == "newer"


def test_lexical_tiebreak_same_version(tmp_path: Path) -> None:
    """Lexicographic skill_dir path breaks ties for same scope and version."""
    # Arrange - same version string, different folders
    root = tmp_path / "skills"
    _write_skill_package(root / "aaa", name="y", version="1.0.0")
    _write_skill_package(root / "zzz", name="y", version="1.0.0")
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
    )
    # Act - discover and merge with identical versions
    candidates, _ = discover_skill_candidates(cfg, base_path=tmp_path)
    registry = build_skill_registry(candidates, cfg)
    # Assert - lexicographically greater skill_dir wins
    entry = registry.get("y")
    assert entry is not None
    assert entry.skill_dir.name == "zzz"


def test_denylist_excludes_canonical_key(tmp_path: Path) -> None:
    """Denylist removes a skill from the merged registry."""
    # Arrange - one skill and denylist containing its key
    root = tmp_path / "skills"
    _write_skill_package(root / "nope", name="blocked", version=None)
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
        denylist=["blocked"],
    )
    # Act - discover then apply denylist policy
    candidates, _ = discover_skill_candidates(cfg, base_path=tmp_path)
    registry = build_skill_registry(candidates, cfg)
    # Assert - denied key is absent and no registry events emitted
    assert registry.get("blocked") is None
    assert registry.events == []


def test_allowlist_restricts_keys(tmp_path: Path) -> None:
    """Non-empty allowlist keeps only listed canonical keys."""
    # Arrange - two skills, allowlist one key
    root = tmp_path / "skills"
    _write_skill_package(root / "a", name="keep", version=None)
    _write_skill_package(root / "b", name="drop", version=None)
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
        allowlist=["keep"],
    )
    # Act - discover then apply allowlist policy
    candidates, _ = discover_skill_candidates(cfg, base_path=tmp_path)
    registry = build_skill_registry(candidates, cfg)
    # Assert - only allowlisted key remains in the registry
    assert registry.get("keep") is not None
    assert registry.get("drop") is None


def test_registry_empty_when_skills_disabled() -> None:
    """Merge step returns empty when skills are disabled."""
    # Arrange - skills feature toggled off
    cfg = SkillsConfig(enabled=False)
    # Act - build registry from no candidates
    registry = build_skill_registry([], cfg)
    # Assert - empty registry and no events
    assert registry.canonical_keys() == []
    assert registry.events == []

"""Unit tests for skill catalog system-prompt formatting."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.config_schema import SkillsConfig
from lily.runtime.skill_discovery import discover_skill_candidates
from lily.runtime.skill_prompt_injector import format_skill_catalog_block
from lily.runtime.skill_registry import build_skill_registry

pytestmark = pytest.mark.unit


def _write_skill(skill_dir: Path, *, name: str, desc: str) -> None:
    """Write a minimal valid SKILL.md under ``skill_dir``."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    body = f"""---
name: {name}
description: "{desc}"
---
# T
"""
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")


def test_format_skill_catalog_block_empty_registry() -> None:
    """Empty registry yields an empty catalog string."""
    # Arrange - enabled skills config with a missing root (no candidates)
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": ["missing-root"]},
        scopes_precedence=["repository", "user", "system"],
    )
    candidates, _ = discover_skill_candidates(cfg, base_path=Path.cwd())
    registry = build_skill_registry(candidates, cfg)

    # Act - format catalog block
    block = format_skill_catalog_block(registry)

    # Assert - nothing to list
    assert block == ""


def test_format_skill_catalog_block_sorted_by_canonical_key(tmp_path: Path) -> None:
    """Catalog lines follow sorted canonical keys for stable prompts."""
    # Arrange - two skills created in reverse lexical order
    root = tmp_path / "skills"
    _write_skill(root / "zebra", name="zebra", desc="desc z")
    _write_skill(root / "alpha", name="alpha", desc="desc a")
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
    )
    candidates, _ = discover_skill_candidates(cfg, base_path=tmp_path)
    registry = build_skill_registry(candidates, cfg)

    # Act - format markdown block
    block = format_skill_catalog_block(registry)

    # Assert - alpha before zebra in output
    assert "alpha" in block
    assert "zebra" in block
    assert block.index("alpha") < block.index("zebra")
    assert "Skill catalog" in block
    assert "skill_retrieve" in block

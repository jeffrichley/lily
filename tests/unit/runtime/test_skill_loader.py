"""Unit tests for progressive skill file loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.config_schema import SkillsConfig
from lily.runtime.skill_discovery import discover_skill_candidates
from lily.runtime.skill_loader import (
    SkillLoader,
    SkillNotFoundError,
    SkillReferenceError,
    build_skill_bundle,
)
from lily.runtime.skill_registry import build_skill_registry

pytestmark = pytest.mark.unit


def _write_skill(skill_dir: Path, *, name: str, desc: str, body: str = "# Hi") -> None:
    """Write SKILL.md under ``skill_dir``."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    text = f"""---
name: {name}
description: "{desc}"
---
{body}
"""
    (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")


def _registry_and_loader(tmp_path: Path) -> SkillLoader:
    """Build a loader for one skill under ``tmp_path``."""
    root = tmp_path / "skills"
    _write_skill(root / "pkg", name="demo", desc="A demo", body="# Body\n")
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
    )
    candidates, _ = discover_skill_candidates(cfg, base_path=tmp_path)
    registry = build_skill_registry(candidates, cfg)
    return SkillLoader(registry)


def test_skill_loader_returns_full_skill_md_text(tmp_path: Path) -> None:
    """Retrieval without reference returns full SKILL.md file text."""
    # Arrange - one skill and loader
    loader = _registry_and_loader(tmp_path)

    # Act - load by canonical key
    text = loader.retrieve("demo")

    # Assert - includes frontmatter and body
    assert "name: demo" in text
    assert "# Body" in text


def test_skill_loader_cache_returns_same_second_hit(tmp_path: Path) -> None:
    """Second load of the same skill reuses the cached file text."""
    # Arrange - loader and first retrieval
    loader = _registry_and_loader(tmp_path)
    first = loader.retrieve("demo")

    # Act - second retrieval
    second = loader.retrieve("demo")

    # Assert - identical cached strings
    assert first is second
    assert second == first


def test_skill_loader_resolves_reference_file(tmp_path: Path) -> None:
    """Loads UTF-8 text from references/ with a safe relative path."""
    # Arrange - skill with references/extra.md
    root = tmp_path / "skills"
    pkg = root / "pkg"
    ref_dir = pkg / "references"
    ref_dir.mkdir(parents=True)
    _write_skill(pkg, name="ref", desc="Has refs")
    (ref_dir / "extra.md").write_text("extra content", encoding="utf-8")
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
    )
    candidates, _ = discover_skill_candidates(cfg, base_path=tmp_path)
    registry = build_skill_registry(candidates, cfg)
    loader = SkillLoader(registry)

    # Act - load reference file by subpath under references/
    text = loader.retrieve("ref", reference_subpath="extra.md")

    # Assert - UTF-8 contents match file on disk
    assert text == "extra content"


def test_skill_loader_rejects_reference_escape(tmp_path: Path) -> None:
    """Rejects paths that escape the references directory."""
    # Arrange - skill with nested references file
    root = tmp_path / "skills"
    pkg = root / "pkg"
    ref_dir = pkg / "references"
    ref_dir.mkdir(parents=True)
    _write_skill(pkg, name="x", desc="x")
    (ref_dir / "safe.md").write_text("ok", encoding="utf-8")
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
    )
    candidates, _ = discover_skill_candidates(cfg, base_path=tmp_path)
    registry = build_skill_registry(candidates, cfg)
    loader = SkillLoader(registry)

    # Act - attempt directory traversal via parent segments
    with pytest.raises(SkillReferenceError) as err:
        loader.retrieve("x", reference_subpath="../SKILL.md")

    # Assert - error mentions unsafe path components
    assert ".." in str(err.value).lower() or ".." in str(err.value)


def test_skill_loader_raises_not_found_for_unknown_name(tmp_path: Path) -> None:
    """Unknown skill name raises SkillNotFoundError."""
    # Arrange - loader with only the demo skill
    loader = _registry_and_loader(tmp_path)

    # Act - request a skill that was never indexed
    with pytest.raises(SkillNotFoundError) as err:
        loader.retrieve("nope-skill")

    # Assert - error is a not-found style message
    assert "nope" in str(err.value).lower() or "match" in str(err.value).lower()


def test_build_skill_bundle_skills_disabled_returns_none() -> None:
    """When skills are disabled, bundle is None."""
    # Arrange - skills feature explicitly off
    cfg = SkillsConfig(enabled=False)

    # Act - attempt to build a bundle from config
    bundle = build_skill_bundle(cfg, Path.cwd())

    # Assert - no bundle is produced when disabled
    assert bundle is None


def test_build_skill_bundle_skills_enabled_returns_loader_and_catalog(
    tmp_path: Path,
) -> None:
    """Enabled skills produce a non-empty catalog string and loader."""
    # Arrange - one discoverable skill under repository root
    root = tmp_path / "skills"
    _write_skill(root / "one", name="one", desc="one desc")
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
    )

    # Act - discover, merge, and build loader + catalog text
    bundle = build_skill_bundle(cfg, tmp_path)

    # Assert - catalog lists the skill and loader reads SKILL.md
    assert bundle is not None
    assert "one" in bundle.catalog_markdown
    assert bundle.loader.retrieve("one").startswith("---")

"""Unit tests for progressive skill file loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.config_schema import SkillsConfig, SkillsRetrievalConfig
from lily.runtime.skill_discovery import discover_skill_candidates
from lily.runtime.skill_loader import (
    SkillLoader,
    SkillNotFoundError,
    SkillReferenceError,
    SkillRetrievalDeniedError,
    build_skill_bundle,
)
from lily.runtime.skill_policies import build_retrieval_blocked_keys
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
    blocked = build_retrieval_blocked_keys(candidates, cfg)
    return SkillLoader(
        registry,
        skills_config=cfg,
        retrieval_blocked_keys=blocked,
    )


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
    """Loads UTF-8 text from a path under the skill directory."""
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
    blocked = build_retrieval_blocked_keys(candidates, cfg)
    loader = SkillLoader(
        registry,
        skills_config=cfg,
        retrieval_blocked_keys=blocked,
    )

    # Act - load file by path relative to skill package root
    text = loader.retrieve("ref", reference_subpath="references/extra.md")

    # Assert - UTF-8 contents match file on disk
    assert text == "extra content"


def test_skill_loader_resolves_file_under_assets_dir(tmp_path: Path) -> None:
    """Loads UTF-8 text from assets/ or any other subdirectory of the skill."""
    # Arrange - skill with assets/palette.json beside SKILL.md
    root = tmp_path / "skills"
    pkg = root / "pkg"
    assets = pkg / "assets"
    assets.mkdir(parents=True)
    _write_skill(pkg, name="asset-skill", desc="Has assets")
    (assets / "palette.json").write_text('{"primary": "#000"}', encoding="utf-8")
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
    )
    candidates, _ = discover_skill_candidates(cfg, base_path=tmp_path)
    registry = build_skill_registry(candidates, cfg)
    blocked = build_retrieval_blocked_keys(candidates, cfg)
    loader = SkillLoader(
        registry,
        skills_config=cfg,
        retrieval_blocked_keys=blocked,
    )

    # Act - load nested file outside references/
    text = loader.retrieve("asset-skill", reference_subpath="assets/palette.json")

    # Assert - JSON body is returned
    assert '"primary"' in text


def test_skill_loader_rejects_reference_escape(tmp_path: Path) -> None:
    """Rejects paths that escape the skill package directory."""
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
    blocked = build_retrieval_blocked_keys(candidates, cfg)
    loader = SkillLoader(
        registry,
        skills_config=cfg,
        retrieval_blocked_keys=blocked,
    )

    # Act - attempt directory traversal via parent segments
    with pytest.raises(SkillReferenceError) as err:
        loader.retrieve("x", reference_subpath="../SKILL.md")

    # Assert - error mentions unsafe path components or escape
    out = str(err.value).lower()
    assert ".." in out or "escape" in out


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


def test_skill_loader_denies_denylisted_skill_with_policy_error(tmp_path: Path) -> None:
    """A skill excluded by denylist raises SkillRetrievalDeniedError, not not-found."""
    # Arrange - build loader with denylisted canonical key in blocked map
    root = tmp_path / "skills"
    _write_skill(root / "pkg", name="blocked", desc="blocked desc")
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
        denylist=["blocked"],
    )
    candidates, _ = discover_skill_candidates(cfg, base_path=tmp_path)
    registry = build_skill_registry(candidates, cfg)
    blocked = build_retrieval_blocked_keys(candidates, cfg)
    loader = SkillLoader(
        registry,
        skills_config=cfg,
        retrieval_blocked_keys=blocked,
    )

    # Act - attempt retrieval of a denylisted skill name
    with pytest.raises(SkillRetrievalDeniedError) as err:
        loader.retrieve("blocked")

    # Assert - error cites denylist policy
    assert "denylist" in str(err.value).lower()


def test_skill_loader_denies_when_retrieval_scopes_exclude_winner(
    tmp_path: Path,
) -> None:
    """skills.retrieval.scopes_allowlist can block an otherwise valid skill."""
    # Arrange - registry winner is repository scope but retrieval allows only user
    root = tmp_path / "skills"
    _write_skill(root / "pkg", name="scoped", desc="d")
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
        retrieval=SkillsRetrievalConfig(scopes_allowlist=["user"]),
    )
    candidates, _ = discover_skill_candidates(cfg, base_path=tmp_path)
    registry = build_skill_registry(candidates, cfg)
    blocked = build_retrieval_blocked_keys(candidates, cfg)
    loader = SkillLoader(
        registry,
        skills_config=cfg,
        retrieval_blocked_keys=blocked,
    )

    # Act - attempt retrieval when winning scope is not allowed
    with pytest.raises(SkillRetrievalDeniedError) as err:
        loader.retrieve("scoped")

    # Assert - error explains scope restriction
    assert "scope" in str(err.value).lower()


def test_skill_loader_rejects_reference_path_that_is_directory(tmp_path: Path) -> None:
    """A references/ subpath that resolves to a directory is rejected."""
    # Arrange - skill package with references/sub as a directory only
    root = tmp_path / "skills"
    pkg = root / "pkg"
    ref_dir = pkg / "references" / "sub"
    ref_dir.mkdir(parents=True)
    _write_skill(pkg, name="dirref", desc="d")

    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
    )
    candidates, _ = discover_skill_candidates(cfg, base_path=tmp_path)
    registry = build_skill_registry(candidates, cfg)
    blocked = build_retrieval_blocked_keys(candidates, cfg)
    loader = SkillLoader(
        registry,
        skills_config=cfg,
        retrieval_blocked_keys=blocked,
    )

    # Act - request a path that is a directory
    with pytest.raises(SkillReferenceError) as err:
        loader.retrieve("dirref", reference_subpath="references/sub")

    # Assert - error distinguishes files from directories
    assert "not a file" in str(err.value).lower()

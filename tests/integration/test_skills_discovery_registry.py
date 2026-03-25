"""Integration tests for skill discovery and registry merge determinism."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.config_schema import SkillsConfig
from lily.runtime.skill_discovery import discover_skill_candidates
from lily.runtime.skill_registry import SkillRegistry, build_skill_registry

pytestmark = pytest.mark.integration


def _write_skill_package(skill_dir: Path, *, name: str, version: str | None) -> None:
    """Write a minimal valid SKILL.md under ``skill_dir``."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    ver_block = ""
    if version is not None:
        ver_block = f'\nmetadata:\n  version: "{version}"\n'
    body = f"""---
name: {name}
description: "integration skill"{ver_block}
---
# T
"""
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")


def test_registry_stable_across_identical_runs(tmp_path: Path) -> None:
    """Repeated discover+merge cycles yield identical registry contents."""
    # Arrange - same canonical key under repository, user, and system roots
    repo_root = tmp_path / "repo_skills"
    user_root = tmp_path / "user_skills"
    system_root = tmp_path / "system_skills"
    _write_skill_package(repo_root / "a", name="shared", version="1.0.0")
    _write_skill_package(user_root / "b", name="shared", version="1.0.0")
    _write_skill_package(system_root / "c", name="shared", version="1.0.0")
    cfg = SkillsConfig(
        enabled=True,
        roots={
            "repository": [str(repo_root.relative_to(tmp_path))],
            "user": [str(user_root.relative_to(tmp_path))],
            "system": [str(system_root.relative_to(tmp_path))],
        },
        scopes_precedence=["repository", "user", "system"],
    )

    # Act - run two identical discover and merge cycles
    def run_once() -> SkillRegistry:
        candidates, _events = discover_skill_candidates(cfg, base_path=tmp_path)
        return build_skill_registry(candidates, cfg)

    first = run_once()
    second = run_once()

    # Assert - canonical keys, winner scope, and paths are stable
    assert first.canonical_keys() == second.canonical_keys()
    assert first.canonical_keys() == ["shared"]
    w1 = first.get("shared")
    w2 = second.get("shared")
    assert w1 is not None and w2 is not None
    assert w1.scope == w2.scope == "system"
    assert w1.skill_dir == w2.skill_dir
    assert w1.skill_md_path == w2.skill_md_path

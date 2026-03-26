"""Unit tests for the skill_retrieve LangChain tool."""

from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.tools import BaseTool

from lily.runtime.config_schema import SkillsConfig
from lily.runtime.skill_discovery import discover_skill_candidates
from lily.runtime.skill_loader import SkillLoader
from lily.runtime.skill_policies import build_retrieval_blocked_keys
from lily.runtime.skill_registry import build_skill_registry
from lily.runtime.skill_retrieve_tool import (
    bind_skill_loader,
    reset_skill_loader,
    skill_retrieve,
)
from lily.runtime.tool_catalog import PythonToolDefinition
from lily.runtime.tool_resolvers import ToolResolvers

pytestmark = pytest.mark.unit


def _loader_with_one_skill(tmp_path: Path) -> SkillLoader:
    """Build a loader for one skill named ``demo``."""
    root = tmp_path / "skills"
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "SKILL.md").write_text(
        '---\nname: demo\ndescription: "d"\n---\n# X\n',
        encoding="utf-8",
    )
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


def test_skill_retrieve_tool_resolves_via_catalog() -> None:
    """Python catalog entry resolves to a stable tool id ``skill_retrieve``."""
    # Arrange - catalog definition matching shipped tools.toml
    definition = PythonToolDefinition(
        id="skill_retrieve",
        source="python",
        target="lily.runtime.skill_retrieve_tool:skill_retrieve",
    )
    resolvers = ToolResolvers()

    # Act - resolve Python tool target from catalog definition
    resolved = resolvers.resolve(definition)

    # Assert - LangChain tool name matches catalog id for allowlist wiring
    assert isinstance(resolved, BaseTool)
    assert resolved.name == "skill_retrieve"


def test_skill_retrieve_without_bound_loader_returns_message() -> None:
    """When context has no loader, tool returns a clear error string."""
    # Arrange - bind an explicit None loader to clear any prior context
    token = bind_skill_loader(None)
    try:
        # Act - invoke tool (StructuredTool uses invoke with dict args)
        out = skill_retrieve.invoke({"name": "demo"})
    finally:
        reset_skill_loader(token)

    # Assert - user-facing string explains missing loader binding
    assert "not available" in str(out).lower()


def test_skill_retrieve_with_bound_loader_returns_body(tmp_path: Path) -> None:
    """Bound loader returns SKILL.md text for a known skill."""
    # Arrange - loader and context binding
    loader = _loader_with_one_skill(tmp_path)
    token = bind_skill_loader(loader)
    try:
        # Act - invoke tool
        out = skill_retrieve.invoke({"name": "demo"})
    finally:
        reset_skill_loader(token)

    # Assert - tool returns raw SKILL.md text from the bound loader
    assert "name: demo" in str(out)
    assert "# X" in str(out)

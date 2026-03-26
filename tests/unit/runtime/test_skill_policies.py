"""Unit tests for skill retrieval policy and effective tool resolution (F6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.config_schema import (
    SkillsConfig,
    SkillsRetrievalConfig,
    SkillsToolsConfig,
)
from lily.runtime.skill_discovery import discover_skill_candidates
from lily.runtime.skill_policies import (
    build_retrieval_blocked_keys,
    candidate_allowed_by_lists,
    effective_skill_tools,
    list_policy_denial_reason,
    parse_allowed_tools_field,
    retrieval_config_denial_reason,
)
from lily.runtime.skill_registry import build_skill_registry

pytestmark = pytest.mark.unit


def test_candidate_allowed_by_lists_respects_denylist() -> None:
    """Denylist membership blocks the key."""
    # Arrange - denylist contains one key
    cfg = SkillsConfig(enabled=True, denylist=["secret"])

    # Act - evaluate membership for allowed and denied keys
    secret_blocked = candidate_allowed_by_lists("secret", cfg)
    public_ok = candidate_allowed_by_lists("public", cfg)

    # Assert - denylist blocks only the denied key
    assert secret_blocked is False
    assert public_ok is True


def test_candidate_allowed_by_lists_respects_nonempty_allowlist() -> None:
    """Non-empty allowlist keeps only listed keys."""
    # Arrange - explicit allowlist of one key
    cfg = SkillsConfig(enabled=True, allowlist=["alpha"])

    # Act - evaluate membership for listed and unlisted keys
    alpha_ok = candidate_allowed_by_lists("alpha", cfg)
    beta_blocked = candidate_allowed_by_lists("beta", cfg)

    # Assert - allowlist permits only listed keys
    assert alpha_ok is True
    assert beta_blocked is False


def test_list_policy_denial_reason_for_denylist() -> None:
    """Denylist produces a stable denial message."""
    # Arrange - config with a single denied key
    cfg = SkillsConfig(enabled=True, denylist=["x"])

    # Act - ask for a denial explanation
    reason = list_policy_denial_reason("x", cfg)

    # Assert - message names denylist and the key
    assert reason is not None
    assert "denylist" in reason.lower()
    assert "x" in reason


def test_effective_tools_inherit_runtime_when_allowed_tools_omitted() -> None:
    """Default policy inherit_runtime intersects full runtime tool ids."""
    # Arrange - inherit_runtime policy and a runtime tool set
    st = SkillsToolsConfig(default_policy="inherit_runtime")
    runtime = frozenset({"echo_tool", "ping_tool"})

    # Act - compute effective tools when allowed-tools is omitted
    got = effective_skill_tools(
        allowed_tools_raw=None,
        skills_tools=st,
        runtime_tool_ids=runtime,
    )

    # Assert - full runtime set is retained
    assert got == runtime


def test_effective_tools_deny_unless_allowed_yields_empty() -> None:
    """Omitted allowed-tools under deny_unless_allowed yields empty intersection."""
    # Arrange - deny_unless_allowed with a non-empty runtime
    st = SkillsToolsConfig(default_policy="deny_unless_allowed")
    runtime = frozenset({"echo_tool"})

    # Act - compute effective tools when allowed-tools is omitted
    got = effective_skill_tools(
        allowed_tools_raw=None,
        skills_tools=st,
        runtime_tool_ids=runtime,
    )

    # Assert - skill-level tool set is empty
    assert got == frozenset()


def test_effective_tools_use_default_packs() -> None:
    """use_default_packs unions pack tools then intersects runtime."""
    # Arrange - one default pack listing tools a and b
    st = SkillsToolsConfig(
        default_policy="use_default_packs",
        default_packs=["p1"],
        packs={"p1": ["a", "b"]},
    )
    runtime = frozenset({"a", "c"})

    # Act - compute effective tools when allowed-tools is omitted
    got = effective_skill_tools(
        allowed_tools_raw=None,
        skills_tools=st,
        runtime_tool_ids=runtime,
    )

    # Assert - only tools present in both pack union and runtime remain
    assert got == frozenset({"a"})


def test_effective_tools_explicit_allowed_tools_narrows_runtime() -> None:
    """Explicit allowed-tools replaces default-policy branch and intersects runtime."""
    # Arrange - default policy would deny, but explicit allowed-tools is present
    st = SkillsToolsConfig(
        default_policy="deny_unless_allowed",
        default_packs=["p1"],
        packs={"p1": ["x"]},
    )
    runtime = frozenset({"echo_tool", "ping_tool"})

    # Act - compute effective tools from explicit frontmatter list
    got = effective_skill_tools(
        allowed_tools_raw="echo_tool, ping_tool",
        skills_tools=st,
        runtime_tool_ids=runtime,
    )

    # Assert - explicit list intersects runtime
    assert got == frozenset({"echo_tool", "ping_tool"})


def test_parse_allowed_tools_field_splits_commas_and_whitespace() -> None:
    """Parser accepts comma and whitespace separators."""
    # Arrange - mixed comma and whitespace-separated ids
    raw = "a, b  c"

    # Act - parse into a token set
    got = parse_allowed_tools_field(raw)

    # Assert - all tokens are captured
    assert got == frozenset({"a", "b", "c"})


def test_build_retrieval_blocked_keys_maps_denylisted_candidates(
    tmp_path: Path,
) -> None:
    """Discovery candidates blocked by lists appear in the blocked map."""
    # Arrange - one skill on disk and denylist its key
    root = tmp_path / "skills"
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "SKILL.md").write_text(
        '---\nname: blocked-skill\ndescription: "x"\n---\n# B\n',
        encoding="utf-8",
    )
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
        denylist=["blocked-skill"],
    )
    candidates, _ = discover_skill_candidates(cfg, base_path=tmp_path)

    # Act - build blocked-key map and merged registry
    blocked = build_retrieval_blocked_keys(candidates, cfg)
    registry = build_skill_registry(candidates, cfg)

    # Assert - denylisted key is blocked for retrieval and absent from registry
    assert "blocked-skill" in blocked
    assert registry.get("blocked-skill") is None


def test_retrieval_config_denial_when_disabled() -> None:
    """skills.retrieval.enabled false denies all scopes."""
    # Arrange - retrieval disabled globally
    cfg = SkillsConfig(
        enabled=True,
        retrieval=SkillsRetrievalConfig(enabled=False),
    )

    # Act - evaluate denial for a repository-scoped skill
    reason = retrieval_config_denial_reason(cfg, skill_scope="repository")

    # Assert - a clear disabled message is returned
    assert reason is not None
    assert "disabled" in reason.lower()


def test_retrieval_config_denial_when_scope_not_in_allowlist() -> None:
    """Non-empty scopes_allowlist denies other scopes."""
    # Arrange - only user scope may retrieve
    cfg = SkillsConfig(
        enabled=True,
        retrieval=SkillsRetrievalConfig(scopes_allowlist=["user"]),
    )

    # Act - evaluate denial for repository scope
    reason = retrieval_config_denial_reason(cfg, skill_scope="repository")

    # Assert - repository scope is rejected with scope detail
    assert reason is not None
    assert "repository" in reason

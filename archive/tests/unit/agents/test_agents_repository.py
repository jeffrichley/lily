"""Unit tests for file-backed agent repository."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.agents import AgentRepositoryError, FileAgentRepository


def _write_agent_yaml(
    root: Path,
    name: str,
    *,
    summary: str = "",
    policy: str = "safe_eval",
    declared_tools: tuple[str, ...] = (),
) -> None:
    tools = ", ".join(declared_tools)
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.agent.yaml").write_text(
        (
            f"id: {name}\n"
            f"summary: {summary}\n"
            f"policy: {policy}\n"
            f"declared_tools: [{tools}]\n"
        ),
        encoding="utf-8",
    )


@pytest.mark.unit
def test_load_catalog_returns_sorted_agent_profiles(tmp_path: Path) -> None:
    """Repository should load deterministic sorted agent catalog."""
    # Arrange - write unsorted agent files and build repository
    root = tmp_path / "agents"
    _write_agent_yaml(root, "zeta", summary="Zeta")
    _write_agent_yaml(root, "alpha", summary="Alpha", declared_tools=("search", "run"))
    repo = FileAgentRepository(root_dir=root)

    # Act - load deterministic catalog snapshot
    catalog = repo.load_catalog()

    # Assert - entries are sorted and include normalized tools
    assert [agent.agent_id for agent in catalog.agents] == ["alpha", "zeta"]
    assert catalog.get("alpha") is not None
    assert catalog.get("alpha").declared_tools == ("run", "search")


@pytest.mark.unit
def test_load_catalog_returns_empty_when_root_missing(tmp_path: Path) -> None:
    """Repository should return an empty catalog when root does not exist."""
    # Arrange - repository for a missing root path
    repo = FileAgentRepository(root_dir=tmp_path / "missing")

    # Act - load catalog
    catalog = repo.load_catalog()

    # Assert - missing root maps to empty deterministic catalog
    assert catalog.agents == ()


@pytest.mark.unit
def test_reload_raises_for_invalid_agent_frontmatter(tmp_path: Path) -> None:
    """Repository should raise deterministic error for invalid YAML payload."""
    # Arrange - write malformed YAML payload (list, not mapping)
    root = tmp_path / "agents"
    root.mkdir(parents=True, exist_ok=True)
    (root / "bad.agent.yaml").write_text(
        "- bad\n- payload\n",
        encoding="utf-8",
    )
    repo = FileAgentRepository(root_dir=root)

    # Act - reload catalog and capture deterministic error
    with pytest.raises(AgentRepositoryError) as exc:
        repo.reload_catalog()

    # Assert - error explains schema payload mismatch
    assert "expected mapping payload" in str(exc.value)


@pytest.mark.unit
def test_reload_raises_when_agent_yaml_id_is_missing(tmp_path: Path) -> None:
    """Repository should fail fast when required `id` is missing."""
    # Arrange - write YAML agent contract without required id field
    root = tmp_path / "agents"
    root.mkdir(parents=True, exist_ok=True)
    (root / "missing-id.agent.yaml").write_text(
        ("summary: Missing id\npolicy: safe_eval\ndeclared_tools: []\n"),
        encoding="utf-8",
    )
    repo = FileAgentRepository(root_dir=root)

    # Act - reload catalog with invalid required-field contract
    with pytest.raises(AgentRepositoryError) as exc:
        repo.reload_catalog()
    # Assert - missing id validation is surfaced deterministically
    assert "id" in str(exc.value)


@pytest.mark.unit
def test_reload_raises_when_duplicate_agent_ids_exist(tmp_path: Path) -> None:
    """Repository should reject duplicate agent ids deterministically."""
    # Arrange - two files declare the same id
    root = tmp_path / "agents"
    _write_agent_yaml(root, "one", summary="First")
    (root / "two.agent.yaml").write_text(
        ("id: one\nsummary: Duplicate\npolicy: safe_eval\ndeclared_tools: []\n"),
        encoding="utf-8",
    )
    repo = FileAgentRepository(root_dir=root)

    # Act - reload catalog with duplicate ids
    with pytest.raises(AgentRepositoryError) as exc:
        repo.reload_catalog()
    # Assert - duplicate-id validation is surfaced deterministically
    assert "Duplicate agent id" in str(exc.value)


@pytest.mark.unit
def test_reload_raises_when_legacy_markdown_id_is_missing(tmp_path: Path) -> None:
    """Legacy markdown contracts should also require explicit `id`."""
    # Arrange - markdown contract without id in frontmatter
    root = tmp_path / "agents"
    root.mkdir(parents=True, exist_ok=True)
    (root / "legacy.md").write_text(
        (
            "---\n"
            "summary: Legacy profile\n"
            "policy: safe_eval\n"
            "declared_tools: [search]\n"
            "---\n"
            "Legacy execution profile body.\n"
        ),
        encoding="utf-8",
    )
    repo = FileAgentRepository(root_dir=root)

    # Act - reload catalog with legacy contract missing required id
    with pytest.raises(AgentRepositoryError) as exc:
        repo.reload_catalog()
    # Assert - missing id validation is surfaced deterministically
    assert "id" in str(exc.value)


@pytest.mark.unit
def test_load_catalog_supports_legacy_markdown_during_migration(tmp_path: Path) -> None:
    """Repository should continue loading legacy markdown agent definitions."""
    # Arrange - write one legacy markdown definition
    root = tmp_path / "agents"
    root.mkdir(parents=True, exist_ok=True)
    (root / "legacy.md").write_text(
        (
            "---\n"
            "id: legacy\n"
            "summary: Legacy profile\n"
            "policy: safe_eval\n"
            "declared_tools: [search]\n"
            "---\n"
            "Legacy execution profile body.\n"
        ),
        encoding="utf-8",
    )
    repo = FileAgentRepository(root_dir=root)

    # Act - load catalog from mixed-format repository support
    catalog = repo.load_catalog()

    # Assert - legacy profile is available with deterministic values
    assert [agent.agent_id for agent in catalog.agents] == ["legacy"]
    assert catalog.agents[0].declared_tools == ("search",)

"""Unit tests for named-agent workspace resolution and contract checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.agent_locator import (
    AgentLocatorError,
    default_agent_name,
    default_agents_root,
    resolve_agent_workspace,
)

pytestmark = pytest.mark.unit


def _write(path: Path, content: str = "x") -> None:
    """Write fixture content to one path."""
    path.write_text(content, encoding="utf-8")


def _create_valid_agent_workspace(root: Path, name: str, *, toml: bool = True) -> Path:
    """Create a minimal valid named-agent workspace for tests."""
    agent_dir = root / name
    agent_dir.mkdir(parents=True)
    if toml:
        _write(agent_dir / "agent.toml", "schema_version = 1\n")
        _write(agent_dir / "tools.toml", "[[definitions]]\n")
    else:
        _write(agent_dir / "agent.yaml", "schema_version: 1\n")
        _write(agent_dir / "tools.yaml", "definitions: []\n")

    for filename in ("AGENTS.md", "IDENTITY.md", "SOUL.md", "USER.md", "TOOLS.md"):
        _write(agent_dir / filename, f"# {filename}\n")
    (agent_dir / "skills").mkdir()
    (agent_dir / "memory").mkdir()
    return agent_dir


def test_default_agents_root_is_dot_lily_agents(tmp_path: Path) -> None:
    """Resolves default named-agent root under `.lily/agents`."""
    # Arrange - create deterministic workspace root.
    # Act - resolve default named-agent root from workspace path.
    resolved = default_agents_root(tmp_path)
    # Assert - root remains local-first under `.lily/agents`.
    assert resolved == tmp_path / ".lily" / "agents"


def test_default_agent_name_is_default() -> None:
    """Returns stable default named-agent identifier."""
    # Arrange - no setup required for constant accessor.
    # Act - resolve default named-agent identifier.
    resolved = default_agent_name()
    # Assert - identifier remains stable across runs.
    assert resolved == "default"


def test_resolve_agent_workspace_accepts_hyphenated_agent_name(tmp_path: Path) -> None:
    """Supports names like `pepper-potts` as a single directory segment."""
    # Arrange - create valid hyphenated named-agent workspace.
    agents_root = tmp_path / ".lily" / "agents"
    _create_valid_agent_workspace(agents_root, "pepper-potts")

    # Act - resolve named-agent workspace.
    resolved = resolve_agent_workspace(
        agent_name="pepper-potts", agents_root=agents_root
    )

    # Assert - resolved contract paths map to selected directory.
    assert resolved.agent_name == "pepper-potts"
    assert resolved.agent_dir == agents_root / "pepper-potts"
    assert resolved.config_path == agents_root / "pepper-potts" / "agent.toml"
    assert resolved.tools_config_path == agents_root / "pepper-potts" / "tools.toml"


def test_resolve_agent_workspace_defaults_to_default_agent(tmp_path: Path) -> None:
    """Uses `default` directory when no explicit agent name is provided."""
    # Arrange - create default named-agent workspace.
    agents_root = tmp_path / ".lily" / "agents"
    _create_valid_agent_workspace(agents_root, "default")

    # Act - resolve workspace without explicit agent name.
    resolved = resolve_agent_workspace(agents_root=agents_root)

    # Assert - default agent contract is selected.
    assert resolved.agent_name == "default"
    assert resolved.agent_dir == agents_root / "default"


def test_resolve_agent_workspace_rejects_path_separators_in_name(
    tmp_path: Path,
) -> None:
    """Rejects agent names that are not a single directory segment."""
    # Arrange - create agents root with invalid slash-containing name input.
    agents_root = tmp_path / ".lily" / "agents"
    agents_root.mkdir(parents=True)

    # Act - attempt to resolve invalid name and capture deterministic error.
    with pytest.raises(AgentLocatorError) as err:
        resolve_agent_workspace(agent_name="bad/name", agents_root=agents_root)

    # Assert - error explains path separator restriction.
    assert "without path separators" in str(err.value)


def test_resolve_agent_workspace_fails_when_required_markdown_file_missing(
    tmp_path: Path,
) -> None:
    """Fails fast when one required identity markdown file is missing."""
    # Arrange - create valid workspace then remove one required markdown file.
    agents_root = tmp_path / ".lily" / "agents"
    agent_dir = _create_valid_agent_workspace(agents_root, "default")
    (agent_dir / "SOUL.md").unlink()

    # Act - resolve workspace and capture required-file validation failure.
    with pytest.raises(AgentLocatorError) as err:
        resolve_agent_workspace(agent_name="default", agents_root=agents_root)

    # Assert - error references missing required markdown file.
    assert "Missing required agent file 'SOUL.md'" in str(err.value)


def test_resolve_agent_workspace_fails_when_required_directory_missing(
    tmp_path: Path,
) -> None:
    """Fails fast when one required directory path is missing."""
    # Arrange - create valid workspace then remove required memory directory.
    agents_root = tmp_path / ".lily" / "agents"
    agent_dir = _create_valid_agent_workspace(agents_root, "default")
    (agent_dir / "memory").rmdir()

    # Act - resolve workspace and capture required-directory validation failure.
    with pytest.raises(AgentLocatorError) as err:
        resolve_agent_workspace(agent_name="default", agents_root=agents_root)

    # Assert - error references missing required directory.
    assert "Missing required agent directory 'memory'" in str(err.value)


def test_resolve_agent_workspace_requires_paired_tools_config_for_toml(
    tmp_path: Path,
) -> None:
    """Requires `tools.toml` when `agent.toml` is present."""
    # Arrange - create valid TOML workspace then remove paired tools config.
    agents_root = tmp_path / ".lily" / "agents"
    agent_dir = _create_valid_agent_workspace(agents_root, "default")
    (agent_dir / "tools.toml").unlink()

    # Act - resolve workspace and capture missing paired-tools failure.
    with pytest.raises(AgentLocatorError) as err:
        resolve_agent_workspace(agent_name="default", agents_root=agents_root)

    # Assert - error mentions paired tools requirement and file name.
    assert "paired tools config" in str(err.value)
    assert "tools.toml" in str(err.value)


def test_resolve_agent_workspace_supports_yaml_pairing(tmp_path: Path) -> None:
    """Resolves `agent.yaml` with paired `tools.yaml` when TOML is absent."""
    # Arrange - create YAML-based named-agent workspace.
    agents_root = tmp_path / ".lily" / "agents"
    _create_valid_agent_workspace(agents_root, "default", toml=False)

    # Act - resolve default workspace using YAML config pair.
    resolved = resolve_agent_workspace(agent_name="default", agents_root=agents_root)

    # Assert - YAML config/tools pairing is selected deterministically.
    assert resolved.config_path == agents_root / "default" / "agent.yaml"
    assert resolved.tools_config_path == agents_root / "default" / "tools.yaml"

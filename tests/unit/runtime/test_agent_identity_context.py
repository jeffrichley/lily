"""Unit tests for agent identity context file loading and ordering."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.agent_identity_context import load_agent_identity_context
from lily.runtime.agent_locator import AgentLocatorError

pytestmark = pytest.mark.unit


def _write(path: Path, content: str) -> None:
    """Write UTF-8 fixture content to one path."""
    path.write_text(content, encoding="utf-8")


def _create_required_identity_files(agent_dir: Path) -> None:
    """Create all required identity markdown files with distinct content."""
    _write(agent_dir / "AGENTS.md", "# AGENTS\n")
    _write(agent_dir / "IDENTITY.md", "# IDENTITY\n")
    _write(agent_dir / "SOUL.md", "# SOUL\n")
    _write(agent_dir / "USER.md", "# USER\n")
    _write(agent_dir / "TOOLS.md", "# TOOLS\n")


def test_load_agent_identity_context_uses_deterministic_file_order(
    tmp_path: Path,
) -> None:
    """Builds one identity block in fixed required markdown file order."""
    # Arrange - create named-agent workspace identity markdown files.
    agent_dir = tmp_path / "pepper-potts"
    agent_dir.mkdir(parents=True)
    _create_required_identity_files(agent_dir)

    # Act - load consolidated identity markdown context block.
    context_markdown = load_agent_identity_context(agent_dir)

    # Assert - output preserves deterministic ordered section layout.
    assert "## Agent identity context" in context_markdown
    agents_idx = context_markdown.index("### AGENTS.md")
    identity_idx = context_markdown.index("### IDENTITY.md")
    soul_idx = context_markdown.index("### SOUL.md")
    user_idx = context_markdown.index("### USER.md")
    tools_idx = context_markdown.index("### TOOLS.md")
    assert agents_idx < identity_idx < soul_idx < user_idx < tools_idx


def test_load_agent_identity_context_fails_for_missing_required_file(
    tmp_path: Path,
) -> None:
    """Raises deterministic error when one required file is missing."""
    # Arrange - create workspace with one required identity file missing.
    agent_dir = tmp_path / "default"
    agent_dir.mkdir(parents=True)
    _create_required_identity_files(agent_dir)
    (agent_dir / "SOUL.md").unlink()

    # Act - load context and capture missing-file validation error.
    with pytest.raises(AgentLocatorError) as err:
        load_agent_identity_context(agent_dir)

    # Assert - error message references missing required file path.
    assert "Missing required agent file 'SOUL.md'" in str(err.value)

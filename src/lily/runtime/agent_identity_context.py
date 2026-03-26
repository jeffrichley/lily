"""Load and format agent identity markdown context from a workspace."""

from __future__ import annotations

from pathlib import Path

from lily.runtime.agent_locator import AgentLocatorError

_IDENTITY_FILES_ORDERED: tuple[str, ...] = (
    "AGENTS.md",
    "IDENTITY.md",
    "SOUL.md",
    "USER.md",
    "TOOLS.md",
)


def _read_required_markdown(path: Path) -> str:
    """Read one required markdown file from disk.

    Args:
        path: Absolute or relative markdown file path.

    Returns:
        UTF-8 decoded markdown file contents.

    Raises:
        AgentLocatorError: If file cannot be read.
    """
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"Unable to read required agent identity file '{path}': {exc}"
        raise AgentLocatorError(msg) from exc


def load_agent_identity_context(agent_workspace_dir: Path) -> str:
    """Build one deterministic identity context block from required markdown files.

    Args:
        agent_workspace_dir: Named-agent workspace directory.

    Returns:
        Stable markdown context block for middleware injection.

    Raises:
        AgentLocatorError: If any required identity markdown file is missing.
    """
    sections: list[str] = ["## Agent identity context", ""]
    for filename in _IDENTITY_FILES_ORDERED:
        file_path = agent_workspace_dir / filename
        if not file_path.exists():
            msg = f"Missing required agent file '{filename}' at '{file_path}'."
            raise AgentLocatorError(msg)
        content = _read_required_markdown(file_path).rstrip()
        sections.append(f"### {filename}")
        sections.append("")
        sections.append(content)
        sections.append("")
    return "\n".join(sections).rstrip() + "\n"

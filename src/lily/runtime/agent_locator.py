"""Named-agent workspace resolution and contract validation."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

_DEFAULT_AGENTS_ROOT = Path(".lily") / "agents"
_DEFAULT_AGENT_NAME = "default"
_REQUIRED_MARKDOWN_FILES = (
    "AGENTS.md",
    "IDENTITY.md",
    "SOUL.md",
    "USER.md",
    "TOOLS.md",
)
_REQUIRED_DIRECTORIES = ("skills", "memory")


class AgentLocatorError(ValueError):
    """Raised when an agent workspace cannot be resolved or validated."""


class AgentWorkspacePaths(BaseModel):
    """Resolved paths and identity metadata for one named agent workspace."""

    model_config = ConfigDict(frozen=True)

    agent_name: str = Field(min_length=1)
    agent_dir: Path
    config_path: Path
    tools_config_path: Path
    skills_dir: Path
    memory_dir: Path
    agents_md_path: Path
    identity_md_path: Path
    soul_md_path: Path
    user_md_path: Path
    tools_md_path: Path


def default_agents_root(workspace_root: Path | None = None) -> Path:
    """Return default root path for named-agent directories.

    Args:
        workspace_root: Optional workspace root. When omitted, returns relative
            `.lily/agents` path.

    Returns:
        Root path for named-agent directories.
    """
    if workspace_root is None:
        return _DEFAULT_AGENTS_ROOT
    return workspace_root / _DEFAULT_AGENTS_ROOT


def default_agent_name() -> str:
    """Return default named-agent directory identifier.

    Returns:
        Default named-agent identifier (`default`).
    """
    return _DEFAULT_AGENT_NAME


def _validate_agent_name(agent_name: str) -> None:
    """Validate one agent directory identifier.

    Args:
        agent_name: User-provided agent name.

    Raises:
        AgentLocatorError: If name is empty or contains path separators.
    """
    trimmed = agent_name.strip()
    if not trimmed:
        raise AgentLocatorError("Agent name must not be empty.")
    if trimmed in {".", ".."}:
        raise AgentLocatorError("Agent name must not be '.' or '..'.")
    if "/" in trimmed or "\\" in trimmed:
        msg = (
            "Agent name must be a single directory name without path separators: "
            f"'{agent_name}'."
        )
        raise AgentLocatorError(msg)


def _resolve_config_and_tools(agent_dir: Path) -> tuple[Path, Path]:
    """Resolve runtime config + paired tools config for one agent directory.

    Selection order:
    1. `agent.toml` + `tools.toml`
    2. `agent.yaml` + `tools.yaml`
    3. `agent.yml` + `tools.yaml`

    Args:
        agent_dir: Named-agent directory path.

    Returns:
        Tuple of `(config_path, tools_config_path)`.

    Raises:
        AgentLocatorError: If no valid config/tools pair exists.
    """
    candidates = (
        ("agent.toml", "tools.toml"),
        ("agent.yaml", "tools.yaml"),
        ("agent.yml", "tools.yaml"),
    )
    for config_name, tools_name in candidates:
        config_path = agent_dir / config_name
        if not config_path.exists():
            continue
        tools_path = agent_dir / tools_name
        if not tools_path.exists():
            msg = (
                "Agent config requires paired tools config: "
                f"'{tools_path}' is missing for '{config_path}'."
            )
            raise AgentLocatorError(msg)
        return config_path, tools_path

    msg = (
        "Agent directory is missing runtime config file. Expected one of: "
        "'agent.toml', 'agent.yaml', or 'agent.yml'."
    )
    raise AgentLocatorError(msg)


def _resolve_agents_root(agents_root: Path | None) -> Path:
    """Resolve and validate agents root directory path.

    Args:
        agents_root: Optional explicit root directory path override.

    Returns:
        Validated agents root directory path.

    Raises:
        AgentLocatorError: If root path does not exist or is not a directory.
    """
    root = Path(agents_root) if agents_root is not None else default_agents_root()
    if not root.exists():
        raise AgentLocatorError(f"Agents root directory does not exist: '{root}'.")
    if not root.is_dir():
        raise AgentLocatorError(f"Agents root path is not a directory: '{root}'.")
    return root


def _resolve_agent_directory(root: Path, selected_name: str) -> Path:
    """Resolve and validate selected named-agent directory path.

    Args:
        root: Validated agents root directory.
        selected_name: Selected named-agent identifier.

    Returns:
        Validated named-agent directory path.

    Raises:
        AgentLocatorError: If selected agent directory is missing or invalid.
    """
    agent_dir = root / selected_name
    if not agent_dir.exists():
        raise AgentLocatorError(
            f"Unknown agent '{selected_name}': directory not found at '{agent_dir}'."
        )
    if not agent_dir.is_dir():
        raise AgentLocatorError(
            f"Agent path is not a directory for '{selected_name}': '{agent_dir}'."
        )
    return agent_dir


def _resolve_required_markdown_paths(agent_dir: Path) -> dict[str, Path]:
    """Resolve and validate required markdown file paths for one agent.

    Args:
        agent_dir: Selected named-agent directory path.

    Returns:
        Mapping of required markdown filename to resolved path.

    Raises:
        AgentLocatorError: If any required markdown file is missing.
    """
    required_markdown_paths = {
        filename: agent_dir / filename for filename in _REQUIRED_MARKDOWN_FILES
    }
    for filename, md_path in required_markdown_paths.items():
        if not md_path.exists():
            raise AgentLocatorError(
                f"Missing required agent file '{filename}' at '{md_path}'."
            )
    return required_markdown_paths


def _resolve_required_directory_paths(agent_dir: Path) -> dict[str, Path]:
    """Resolve and validate required directory paths for one agent.

    Args:
        agent_dir: Selected named-agent directory path.

    Returns:
        Mapping of required directory name to resolved path.

    Raises:
        AgentLocatorError: If any required directory is missing or not a directory.
    """
    required_dir_paths = {
        dirname: agent_dir / dirname for dirname in _REQUIRED_DIRECTORIES
    }
    for dirname, dir_path in required_dir_paths.items():
        if not dir_path.exists():
            raise AgentLocatorError(
                f"Missing required agent directory '{dirname}' at '{dir_path}'."
            )
        if not dir_path.is_dir():
            raise AgentLocatorError(
                f"Required agent path '{dirname}' is not a directory: '{dir_path}'."
            )
    return required_dir_paths


def resolve_agent_workspace(
    *,
    agent_name: str | None = None,
    agents_root: Path | None = None,
) -> AgentWorkspacePaths:
    """Resolve and validate one named-agent workspace directory.

    Args:
        agent_name: Optional named-agent identifier. Defaults to `default`.
        agents_root: Optional root directory containing named-agent directories.
            Defaults to `.lily/agents` relative to current working directory.

    Returns:
        Validated set of resolved paths for the selected agent workspace.

    Raises:
        AgentLocatorError: If agent workspace contract validation fails.
    """
    try:
        selected_name = agent_name if agent_name is not None else default_agent_name()
        _validate_agent_name(selected_name)

        root = _resolve_agents_root(agents_root)
        agent_dir = _resolve_agent_directory(root, selected_name)

        config_path, tools_config_path = _resolve_config_and_tools(agent_dir)
        required_markdown_paths = _resolve_required_markdown_paths(agent_dir)
        required_dir_paths = _resolve_required_directory_paths(agent_dir)
    except AgentLocatorError as exc:
        raise AgentLocatorError(str(exc)) from exc

    return AgentWorkspacePaths(
        agent_name=selected_name,
        agent_dir=agent_dir,
        config_path=config_path,
        tools_config_path=tools_config_path,
        skills_dir=required_dir_paths["skills"],
        memory_dir=required_dir_paths["memory"],
        agents_md_path=required_markdown_paths["AGENTS.md"],
        identity_md_path=required_markdown_paths["IDENTITY.md"],
        soul_md_path=required_markdown_paths["SOUL.md"],
        user_md_path=required_markdown_paths["USER.md"],
        tools_md_path=required_markdown_paths["TOOLS.md"],
    )

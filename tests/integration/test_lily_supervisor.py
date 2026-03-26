"""Integration tests for LilySupervisor catalog wiring behavior."""

from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.tools import BaseTool

from lily.agents.lily_supervisor import LilySupervisor
from lily.runtime.tool_registry import ToolRegistry

pytestmark = pytest.mark.integration


def _write(path: Path, content: str) -> None:
    """Write one fixture file for tests."""
    path.write_text(content, encoding="utf-8")


def test_supervisor_from_config_paths_loads_tools_from_catalog(
    tmp_path: Path,
) -> None:
    """Resolves runtime tools from tools.yaml instead of hardcoded wiring."""
    # Arrange - create runtime + catalog YAML fixtures.
    agent_config = tmp_path / "agent.yaml"
    tools_config = tmp_path / "tools.yaml"
    _write(
        agent_config,
        """
schema_version: 1
agent:
  name: lily
  system_prompt: "You are Lily."
models:
  profiles:
    default:
      provider: openai
      model: gpt-4o-mini
      temperature: 0.1
      timeout_seconds: 30
    long_context:
      provider: openai
      model: gpt-4o
      temperature: 0.1
      timeout_seconds: 45
  routing:
    enabled: true
    default_profile: default
    long_context_profile: long_context
    complexity_threshold: 8
tools:
  allowlist:
    - ping_tool
policies:
  max_iterations: 12
  max_model_calls: 20
  max_tool_calls: 20
logging:
  level: INFO
""",
    )
    _write(
        tools_config,
        """
definitions:
  - id: echo_tool
    source: python
    target: lily.agents.lily_supervisor:echo_tool
  - id: ping_tool
    source: python
    target: lily.agents.lily_supervisor:ping_tool
""",
    )

    # Act - build supervisor and inspect pre-agent-build runtime tool set.
    supervisor = LilySupervisor.from_config_paths(
        agent_config, tools_config_path=tools_config
    )
    runtime = supervisor._runtime

    # Assert - runtime tool set comes from catalog and allowlist policy is unchanged.
    registry = ToolRegistry.from_tools(runtime._tools)
    assert registry.names() == ["echo_tool", "ping_tool"]
    assert runtime._config.tools.allowlist == ["ping_tool"]

    for tool in runtime._tools:
        assert isinstance(tool, BaseTool)


def test_supervisor_from_config_paths_loads_mcp_tools_from_server_mapping(
    tmp_path: Path,
) -> None:
    """Resolves MCP tool definitions using runtime-configured server mapping."""
    # Arrange - create runtime config with MCP server map and MCP catalog entry.
    agent_config = tmp_path / "agent.yaml"
    tools_config = tmp_path / "tools.yaml"
    _write(
        agent_config,
        """
schema_version: 1
agent:
  name: lily
  system_prompt: "You are Lily."
models:
  profiles:
    default:
      provider: openai
      model: gpt-4o-mini
      temperature: 0.1
      timeout_seconds: 30
    long_context:
      provider: openai
      model: gpt-4o
      temperature: 0.1
      timeout_seconds: 45
  routing:
    enabled: true
    default_profile: default
    long_context_profile: long_context
    complexity_threshold: 8
tools:
  allowlist:
    - mcp_ping_tool
mcp_servers:
  local_test:
    transport: test
    tool_targets:
      ping_remote: lily.agents.lily_supervisor:mcp_ping_tool
policies:
  max_iterations: 12
  max_model_calls: 20
  max_tool_calls: 20
logging:
  level: INFO
""",
    )
    _write(
        tools_config,
        """
definitions:
  - id: mcp_ping_tool
    source: mcp
    server: local_test
    remote_tool: ping_remote
""",
    )

    # Act - build supervisor and inspect resolved runtime tool set.
    supervisor = LilySupervisor.from_config_paths(
        agent_config, tools_config_path=tools_config
    )
    runtime = supervisor._runtime

    # Assert - MCP catalog entry resolved to expected runtime tool.
    registry = ToolRegistry.from_tools(runtime._tools)
    assert registry.names() == ["mcp_ping_tool"]
    assert runtime._config.tools.allowlist == ["mcp_ping_tool"]


def test_supervisor_from_config_paths_infers_tools_toml_from_agent_toml(
    tmp_path: Path,
) -> None:
    """Infers `tools.toml` when runtime config path uses `agent.toml`."""
    # Arrange - create runtime TOML + tool catalog TOML fixtures in same directory.
    agent_config = tmp_path / "agent.toml"
    tools_config = tmp_path / "tools.toml"
    _write(
        agent_config,
        """
schema_version = 1

[agent]
name = "lily"
system_prompt = "You are Lily."

[models.profiles.default]
provider = "openai"
model = "gpt-4o-mini"
temperature = 0.1
timeout_seconds = 30

[models.profiles.long_context]
provider = "openai"
model = "gpt-4o"
temperature = 0.1
timeout_seconds = 45

[models.routing]
enabled = true
default_profile = "default"
long_context_profile = "long_context"
complexity_threshold = 8

[tools]
allowlist = ["ping_tool"]

[policies]
max_iterations = 12
max_model_calls = 20
max_tool_calls = 20

[logging]
level = "INFO"
""",
    )
    _write(
        tools_config,
        """
[[definitions]]
id = "echo_tool"
source = "python"
target = "lily.agents.lily_supervisor:echo_tool"

[[definitions]]
id = "ping_tool"
source = "python"
target = "lily.agents.lily_supervisor:ping_tool"
""",
    )

    # Act - build supervisor without explicit tools path and rely on inference.
    supervisor = LilySupervisor.from_config_paths(agent_config)
    runtime = supervisor._runtime

    # Assert - runtime tools were loaded from inferred `tools.toml` catalog.
    registry = ToolRegistry.from_tools(runtime._tools)
    assert registry.names() == ["echo_tool", "ping_tool"]
    assert runtime._config.tools.allowlist == ["ping_tool"]


def test_supervisor_from_config_paths_adds_agent_local_skills_root(
    tmp_path: Path,
) -> None:
    """Adds `<agent_workspace_dir>/skills` as repository root when skills enabled."""
    # Arrange - create agent workspace with one local skill package.
    workspace_dir = tmp_path / ".lily" / "agents" / "default"
    workspace_dir.mkdir(parents=True)
    skills_dir = workspace_dir / "skills" / "math-skill"
    skills_dir.mkdir(parents=True)
    _write(
        skills_dir / "SKILL.md",
        '---\nname: math-skill\ndescription: "adds numbers"\n---\n# Math skill\n',
    )

    agent_config = workspace_dir / "agent.toml"
    tools_config = workspace_dir / "tools.toml"
    _write(
        agent_config,
        """
schema_version = 1

[agent]
name = "lily"
system_prompt = "You are Lily."

[models.profiles.default]
provider = "openai"
model = "gpt-4o-mini"
temperature = 0.1
timeout_seconds = 30

[models.profiles.long_context]
provider = "openai"
model = "gpt-4o"
temperature = 0.1
timeout_seconds = 45

[models.routing]
enabled = true
default_profile = "default"
long_context_profile = "long_context"
complexity_threshold = 8

[tools]
allowlist = ["ping_tool", "skill_retrieve"]

[policies]
max_iterations = 12
max_model_calls = 20
max_tool_calls = 20

[logging]
level = "INFO"

[skills]
enabled = true
roots = { repository = ["../skills"] }
scopes_precedence = ["repository", "user", "system"]
""",
    )
    _write(
        tools_config,
        """
[[definitions]]
id = "ping_tool"
source = "python"
target = "lily.agents.lily_supervisor:ping_tool"

[[definitions]]
id = "skill_retrieve"
source = "python"
target = "lily.runtime.skill_retrieve_tool:skill_retrieve"
""",
    )

    # Required identity files for named-agent workspace path.
    _write(workspace_dir / "AGENTS.md", "# AGENTS\n")
    _write(workspace_dir / "IDENTITY.md", "# IDENTITY\n")
    _write(workspace_dir / "SOUL.md", "# SOUL\n")
    _write(workspace_dir / "USER.md", "# USER\n")
    _write(workspace_dir / "TOOLS.md", "# TOOLS\n")
    (workspace_dir / "memory").mkdir(parents=True, exist_ok=True)

    # Act - build supervisor with named-agent workspace context.
    supervisor = LilySupervisor.from_config_paths(
        agent_config,
        tools_config_path=tools_config,
        agent_workspace_dir=workspace_dir,
    )
    runtime = supervisor._runtime

    # Assert - runtime skill bundle contains the local agent skill.
    assert runtime._skill_bundle is not None
    assert "math-skill" in runtime._skill_bundle.registry.canonical_keys()

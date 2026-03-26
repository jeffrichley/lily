"""Unit tests for runtime config schema and loader behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.config_loader import ConfigLoadError, load_runtime_config

pytestmark = pytest.mark.unit


def _write(path: Path, content: str) -> None:
    """Write test fixture content to a path."""
    path.write_text(content, encoding="utf-8")


def test_load_runtime_config_valid_yaml(tmp_path: Path) -> None:
    """Loads a valid base config and returns parsed typed fields."""
    # Arrange - write a valid runtime YAML fixture.
    config_file = tmp_path / "agent.yaml"
    _write(
        config_file,
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
    - filesystem_read
    - web_search
policies:
  max_iterations: 12
  max_model_calls: 20
  max_tool_calls: 20
logging:
  level: INFO
""",
    )

    # Act - load and validate the runtime config.
    config = load_runtime_config(config_file)

    # Assert - key typed values are available and normalized.
    assert config.agent.name == "lily"
    assert config.models.profiles["default"].provider == "openai"
    assert config.policies.max_iterations == 12


def test_load_runtime_config_valid_toml(tmp_path: Path) -> None:
    """Loads a valid TOML config and returns parsed typed fields."""
    # Arrange - write a valid runtime TOML fixture.
    config_file = tmp_path / "agent.toml"
    _write(
        config_file,
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
allowlist = ["filesystem_read", "web_search"]

[policies]
max_iterations = 12
max_model_calls = 20
max_tool_calls = 20

[logging]
level = "INFO"
""",
    )

    # Act - load and validate the runtime config.
    config = load_runtime_config(config_file)

    # Assert - key typed values are available and normalized.
    assert config.agent.name == "lily"
    assert config.models.profiles["default"].provider == "openai"
    assert config.policies.max_iterations == 12


def test_load_runtime_config_missing_required_field_raises(tmp_path: Path) -> None:
    """Raises with field-specific errors when required keys are missing."""
    # Arrange - write YAML missing one required field.
    config_file = tmp_path / "agent.yaml"
    _write(
        config_file,
        """
schema_version: 1
agent:
  name: lily
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
    - filesystem_read
policies:
  max_iterations: 12
  max_model_calls: 20
  max_tool_calls: 20
logging:
  level: INFO
""",
    )

    # Act - attempt to load invalid config and capture the error.
    with pytest.raises(ConfigLoadError) as err:
        load_runtime_config(config_file)

    # Assert - error includes deterministic field-level message.
    assert "agent.system_prompt: Field required" in str(err.value)


def test_load_runtime_config_non_mapping_yaml_raises(tmp_path: Path) -> None:
    """Raises when YAML top-level value is not a mapping."""
    # Arrange - write a list-based YAML document.
    config_file = tmp_path / "agent.yaml"
    _write(config_file, "- item1\n- item2\n")

    # Act - attempt to parse top-level non-object YAML.
    with pytest.raises(ConfigLoadError) as err:
        load_runtime_config(config_file)

    # Assert - loader reports mapping/object requirement.
    assert "top-level mapping/object" in str(err.value)


def test_load_runtime_config_merges_override_recursively(tmp_path: Path) -> None:
    """Applies override values while preserving base config defaults."""
    # Arrange - write base and override YAML fixtures.
    base_file = tmp_path / "base.yaml"
    override_file = tmp_path / "override.yaml"
    _write(
        base_file,
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
    - filesystem_read
policies:
  max_iterations: 12
  max_model_calls: 20
  max_tool_calls: 20
logging:
  level: INFO
""",
    )
    _write(
        override_file,
        """
models:
  profiles:
    default:
      provider: openai
      model: gpt-4o
      temperature: 0.3
      timeout_seconds: 40
policies:
  max_model_calls: 80
""",
    )

    # Act - load merged runtime config.
    config = load_runtime_config(base_file, override_file)

    # Assert - override values replace nested fields and base defaults remain.
    assert config.models.profiles["default"].model == "gpt-4o"
    assert config.models.profiles["default"].temperature == 0.3
    assert config.policies.max_iterations == 12
    assert config.policies.max_model_calls == 80
    assert config.policies.max_tool_calls == 20


def test_load_runtime_config_invalid_routing_profile_reference_raises(
    tmp_path: Path,
) -> None:
    """Rejects routing references to unknown model profile keys."""
    # Arrange - write YAML with invalid routing profile reference.
    config_file = tmp_path / "agent.yaml"
    _write(
        config_file,
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
  routing:
    enabled: true
    default_profile: default
    long_context_profile: does_not_exist
    complexity_threshold: 8
tools:
  allowlist:
    - filesystem_read
policies:
  max_iterations: 12
  max_model_calls: 20
  max_tool_calls: 20
logging:
  level: INFO
""",
    )

    # Act - attempt to validate invalid routing references.
    with pytest.raises(ConfigLoadError) as err:
        load_runtime_config(config_file)

    # Assert - error includes routing reference field path.
    assert "routing.long_context_profile" in str(err.value)


def test_load_runtime_config_parses_mcp_server_mapping(tmp_path: Path) -> None:
    """Parses runtime `mcp_servers` config for resolver wiring."""
    # Arrange - write valid runtime YAML with one MCP test server.
    config_file = tmp_path / "agent.yaml"
    _write(
        config_file,
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

    # Act - load config with MCP server mapping.
    config = load_runtime_config(config_file)

    # Assert - server mapping is typed and available for runtime wiring.
    assert "local_test" in config.mcp_servers
    assert config.mcp_servers["local_test"].transport == "test"
    assert (
        config.mcp_servers["local_test"]
        .tool_targets["ping_remote"]
        .endswith(":mcp_ping_tool")
    )


def test_load_runtime_config_parses_streamable_http_mcp_server(tmp_path: Path) -> None:
    """Parses streamable-http MCP server config used for real transports."""
    # Arrange - write valid runtime YAML with one streamable-http MCP server.
    config_file = tmp_path / "agent.yaml"
    _write(
        config_file,
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
    - search_langgraph_code
mcp_servers:
  langgraph_docs:
    transport: streamable_http
    url: https://gitmcp.io/langchain-ai/langgraph
policies:
  max_iterations: 12
  max_model_calls: 20
  max_tool_calls: 20
logging:
  level: INFO
""",
    )

    # Act - load config with streamable-http MCP server mapping.
    config = load_runtime_config(config_file)

    # Assert - streamable-http server mapping is parsed with expected fields.
    assert "langgraph_docs" in config.mcp_servers
    assert config.mcp_servers["langgraph_docs"].transport == "streamable_http"


def test_load_runtime_config_parses_toml_mcp_server_mapping(tmp_path: Path) -> None:
    """Parses TOML `mcp_servers` table mapping used for resolver wiring."""
    # Arrange - write valid runtime TOML with one streamable-http MCP server.
    config_file = tmp_path / "agent.toml"
    _write(
        config_file,
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
allowlist = ["search_langgraph_code"]

[mcp_servers.langgraph_docs]
transport = "streamable_http"
url = "https://gitmcp.io/langchain-ai/langgraph"

[policies]
max_iterations = 12
max_model_calls = 20
max_tool_calls = 20

[logging]
level = "INFO"
""",
    )

    # Act - load config with TOML MCP server mapping.
    config = load_runtime_config(config_file)

    # Assert - parsed server mapping is available for runtime wiring.
    assert "langgraph_docs" in config.mcp_servers
    assert config.mcp_servers["langgraph_docs"].transport == "streamable_http"


def test_load_runtime_config_parses_sse_mcp_server(tmp_path: Path) -> None:
    """Parses SSE MCP server config for endpoint-event transports."""
    # Arrange - write valid runtime YAML with one SSE MCP server.
    config_file = tmp_path / "agent.yaml"
    _write(
        config_file,
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
    - search_langgraph_code
mcp_servers:
  langgraph_docs:
    transport: sse
    url: https://gitmcp.io/langchain-ai/langgraph
policies:
  max_iterations: 12
  max_model_calls: 20
  max_tool_calls: 20
logging:
  level: INFO
""",
    )

    # Act - load config with SSE MCP server mapping.
    config = load_runtime_config(config_file)

    # Assert - SSE server mapping is parsed with expected fields.
    assert "langgraph_docs" in config.mcp_servers
    assert config.mcp_servers["langgraph_docs"].transport == "sse"


def test_load_runtime_config_parses_websocket_mcp_server(tmp_path: Path) -> None:
    """Parses WebSocket MCP server config."""
    # Arrange - write valid runtime YAML with one websocket MCP server.
    config_file = tmp_path / "agent.yaml"
    _write(
        config_file,
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
    - search_langgraph_code
mcp_servers:
  websocket_docs:
    transport: websocket
    url: wss://example.com/mcp
policies:
  max_iterations: 12
  max_model_calls: 20
  max_tool_calls: 20
logging:
  level: INFO
""",
    )

    # Act - load config with websocket MCP server mapping.
    config = load_runtime_config(config_file)

    # Assert - websocket server mapping is parsed with expected fields.
    assert "websocket_docs" in config.mcp_servers
    assert config.mcp_servers["websocket_docs"].transport == "websocket"


def test_load_runtime_config_parses_stdio_mcp_server(tmp_path: Path) -> None:
    """Parses stdio MCP server config for local process transports."""
    # Arrange - write valid runtime YAML with one stdio MCP server.
    config_file = tmp_path / "agent.yaml"
    _write(
        config_file,
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
    - search_langgraph_code
mcp_servers:
  local_stdio:
    transport: stdio
    command: uvx
    args:
      - mcp-server-example
policies:
  max_iterations: 12
  max_model_calls: 20
  max_tool_calls: 20
logging:
  level: INFO
""",
    )

    # Act - load config with stdio MCP server mapping.
    config = load_runtime_config(config_file)

    # Assert - stdio server mapping is parsed with expected fields.
    assert "local_stdio" in config.mcp_servers
    assert config.mcp_servers["local_stdio"].transport == "stdio"


def _minimal_runtime_yaml_with_skills(
    skills_block: str,
    *,
    policies_block: str | None = None,
) -> str:
    """Return a valid runtime YAML document with an optional ``skills`` section."""
    effective_policies = (
        policies_block
        or """
policies:
  max_iterations: 12
  max_model_calls: 20
  max_tool_calls: 20
"""
    )

    return f"""
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
    - filesystem_read
{effective_policies}
logging:
  level: INFO
{skills_block}
"""


def test_load_runtime_config_skills_omitted_is_none(tmp_path: Path) -> None:
    """When no ``skills`` key is present, ``RuntimeConfig.skills`` is None."""
    # Arrange - valid base YAML without a skills section
    config_file = tmp_path / "agent.yaml"
    _write(config_file, _minimal_runtime_yaml_with_skills(""))

    # Act - load and validate runtime config
    config = load_runtime_config(config_file)

    # Assert - optional skills block stays unset
    assert config.skills is None


def test_load_runtime_config_parses_skills_block_yaml(tmp_path: Path) -> None:
    """Parses ``skills`` roots list, precedence, and nested ``skills.tools``."""
    # Arrange - YAML with list-form roots and tool packs
    config_file = tmp_path / "agent.yaml"
    _write(
        config_file,
        _minimal_runtime_yaml_with_skills(
            """
skills:
  enabled: true
  roots: [".skills"]
  scopes_precedence: [repository, user, system]
  tools:
    default_policy: inherit_runtime
    packs:
      core:
        - filesystem_read
""",
        ),
    )

    # Act - load config including skills subtree
    config = load_runtime_config(config_file)

    # Assert - skills model is normalized and tool pack ids resolve
    assert config.skills is not None
    assert config.skills.enabled is True
    assert config.skills.roots == {"repository": [".skills"]}
    assert config.skills.scopes_precedence == ["repository", "user", "system"]
    assert "core" in config.skills.tools.packs
    assert config.skills.tools.packs["core"] == ["filesystem_read"]


def test_load_runtime_config_parses_conversation_compression_config(
    tmp_path: Path,
) -> None:
    """Parses ``policies.conversation_compression`` when enabled."""
    # Arrange - write runtime YAML with compression policy enabled.
    config_file = tmp_path / "agent.yaml"
    _write(
        config_file,
        _minimal_runtime_yaml_with_skills(
            """
skills:
  enabled: true
  roots: [".skills"]
""",
            policies_block="""
policies:
  max_iterations: 12
  max_model_calls: 20
  max_tool_calls: 20
  conversation_compression:
    enabled: true
    trigger:
      kind: messages
      threshold: 3
    keep:
      kind: messages
      value: 1
""",
        ),
    )

    # Act - load and validate runtime config.
    config = load_runtime_config(config_file)

    # Assert - compression policy fields are parsed and typed.
    assert config.policies.conversation_compression.enabled is True
    assert config.policies.conversation_compression.trigger.kind == "messages"
    assert config.policies.conversation_compression.trigger.threshold == 3
    assert config.policies.conversation_compression.keep.kind == "messages"
    assert config.policies.conversation_compression.keep.value == 1


def test_load_runtime_config_rejects_skills_tools_unknown_default_pack(
    tmp_path: Path,
) -> None:
    """Rejects ``default_packs`` entries that are not keys in ``skills.tools.packs``."""
    # Arrange - default_packs references a missing pack id
    config_file = tmp_path / "agent.yaml"
    _write(
        config_file,
        _minimal_runtime_yaml_with_skills(
            """
skills:
  enabled: true
  roots: [".skills"]
  tools:
    default_packs: [core]
    packs: {}
""",
        ),
    )

    # Act - attempt to validate skills.tools cross-references
    with pytest.raises(ConfigLoadError) as err:
        load_runtime_config(config_file)

    # Assert - error cites the unknown pack reference
    assert "default_packs" in str(err.value)
    assert "core" in str(err.value)


def test_load_runtime_config_rejects_skills_tools_use_default_packs_empty(
    tmp_path: Path,
) -> None:
    """Rejects ``use_default_packs`` when ``default_packs`` is empty."""
    # Arrange - policy requires packs but none are listed
    config_file = tmp_path / "agent.yaml"
    _write(
        config_file,
        _minimal_runtime_yaml_with_skills(
            """
skills:
  enabled: true
  roots: [".skills"]
  tools:
    default_policy: use_default_packs
    default_packs: []
    packs:
      core:
        - filesystem_read
""",
        ),
    )

    # Act - attempt to validate policy vs default_packs
    with pytest.raises(ConfigLoadError) as err:
        load_runtime_config(config_file)

    # Assert - error explains the forbidden combination
    assert "use_default_packs" in str(err.value).lower() or "default_packs" in str(
        err.value,
    )


def test_load_runtime_config_rejects_skills_tools_invalid_tool_id(
    tmp_path: Path,
) -> None:
    """Rejects malformed tool ids inside ``skills.tools.packs``."""
    # Arrange - tool id uses invalid characters
    config_file = tmp_path / "agent.yaml"
    _write(
        config_file,
        _minimal_runtime_yaml_with_skills(
            """
skills:
  enabled: true
  roots: [".skills"]
  tools:
    packs:
      core:
        - NOT_A_VALID_ID
""",
        ),
    )

    # Act - attempt to validate tool id pattern
    with pytest.raises(ConfigLoadError) as err:
        load_runtime_config(config_file)

    # Assert - error references the offending tool id
    assert (
        "NOT_A_VALID_ID" in str(err.value)
        or "invalid tool id"
        in str(
            err.value,
        ).lower()
    )

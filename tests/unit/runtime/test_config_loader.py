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

"""Unit tests for tool catalog schema and YAML loader behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.tool_catalog import (
    McpToolDefinition,
    PythonToolDefinition,
    ToolCatalogLoadError,
    load_tool_catalog,
)

pytestmark = pytest.mark.unit


def _write(path: Path, content: str) -> None:
    """Write one fixture file for tests."""
    path.write_text(content, encoding="utf-8")


def test_load_tool_catalog_parses_valid_python_entry(tmp_path: Path) -> None:
    """Parses one valid Python tool definition entry."""
    # Arrange - write a catalog with one Python definition.
    catalog_file = tmp_path / "tools.yaml"
    _write(
        catalog_file,
        """
definitions:
  - id: echo_tool
    source: python
    target: lily.agents.lily_supervisor:echo_tool
""",
    )

    # Act - load and parse catalog.
    catalog = load_tool_catalog(catalog_file)

    # Assert - parsed entry has expected type and fields.
    entry = catalog.definitions[0]
    assert isinstance(entry, PythonToolDefinition)
    assert entry.id == "echo_tool"
    assert entry.target == "lily.agents.lily_supervisor:echo_tool"


def test_load_tool_catalog_parses_valid_toml_python_entry(tmp_path: Path) -> None:
    """Parses one valid TOML Python tool definition entry."""
    # Arrange - write a TOML catalog with one Python definition.
    catalog_file = tmp_path / "tools.toml"
    _write(
        catalog_file,
        """
[[definitions]]
id = "echo_tool"
source = "python"
target = "lily.agents.lily_supervisor:echo_tool"
""",
    )

    # Act - load and parse catalog.
    catalog = load_tool_catalog(catalog_file)

    # Assert - parsed entry has expected type and fields.
    entry = catalog.definitions[0]
    assert isinstance(entry, PythonToolDefinition)
    assert entry.id == "echo_tool"
    assert entry.target == "lily.agents.lily_supervisor:echo_tool"


def test_load_tool_catalog_parses_valid_mcp_entry(tmp_path: Path) -> None:
    """Parses one valid MCP tool definition entry."""
    # Arrange - write a catalog with one MCP definition.
    catalog_file = tmp_path / "tools.yaml"
    _write(
        catalog_file,
        """
definitions:
  - id: weather_lookup
    source: mcp
    server: local_tools
    remote_tool: get_weather
""",
    )

    # Act - load and parse catalog.
    catalog = load_tool_catalog(catalog_file)

    # Assert - parsed entry has expected type and fields.
    entry = catalog.definitions[0]
    assert isinstance(entry, McpToolDefinition)
    assert entry.id == "weather_lookup"
    assert entry.server == "local_tools"
    assert entry.remote_tool == "get_weather"


def test_load_tool_catalog_parses_valid_toml_mcp_entry(tmp_path: Path) -> None:
    """Parses one valid TOML MCP tool definition entry."""
    # Arrange - write a TOML catalog with one MCP definition.
    catalog_file = tmp_path / "tools.toml"
    _write(
        catalog_file,
        """
[[definitions]]
id = "weather_lookup"
source = "mcp"
server = "local_tools"
remote_tool = "get_weather"
""",
    )

    # Act - load and parse catalog.
    catalog = load_tool_catalog(catalog_file)

    # Assert - parsed entry has expected type and fields.
    entry = catalog.definitions[0]
    assert isinstance(entry, McpToolDefinition)
    assert entry.id == "weather_lookup"
    assert entry.server == "local_tools"
    assert entry.remote_tool == "get_weather"


def test_load_tool_catalog_rejects_duplicate_tool_ids(tmp_path: Path) -> None:
    """Fails when two definitions use the same id."""
    # Arrange - write duplicate id entries with different source types.
    catalog_file = tmp_path / "tools.yaml"
    _write(
        catalog_file,
        """
definitions:
  - id: echo_tool
    source: python
    target: lily.agents.lily_supervisor:echo_tool
  - id: echo_tool
    source: mcp
    server: local_tools
    remote_tool: echo
""",
    )

    # Act - load invalid catalog and capture deterministic error.
    with pytest.raises(ToolCatalogLoadError) as err:
        load_tool_catalog(catalog_file)

    # Assert - error names duplicate id set.
    assert "Duplicate tool definition ids: echo_tool" in str(err.value)


def test_load_tool_catalog_rejects_missing_source_field_data(tmp_path: Path) -> None:
    """Fails when source-specific required fields are missing."""
    # Arrange - write MCP definition missing remote_tool.
    catalog_file = tmp_path / "tools.yaml"
    _write(
        catalog_file,
        """
definitions:
  - id: weather_lookup
    source: mcp
    server: local_tools
""",
    )

    # Act - load invalid catalog and capture deterministic error.
    with pytest.raises(ToolCatalogLoadError) as err:
        load_tool_catalog(catalog_file)

    # Assert - error points to missing remote tool field.
    assert "remote_tool: Field required" in str(err.value)

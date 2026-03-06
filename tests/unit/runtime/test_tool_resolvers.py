"""Unit tests for catalog tool resolvers."""

from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.tools import BaseTool, tool

from lily.runtime.config_schema import (
    McpServerStreamableHttpConfig,
    McpServerTestConfig,
)
from lily.runtime.tool_catalog import McpToolDefinition, PythonToolDefinition
from lily.runtime.tool_resolvers import (
    McpToolResolveError,
    ToolResolverError,
    ToolResolvers,
    build_mcp_server_providers,
)

pytestmark = pytest.mark.unit


class _FakeMcpServer:
    """Fake MCP server provider for resolver tests."""

    def __init__(self, tools_by_name: dict[str, BaseTool]) -> None:
        """Store remote-tool to resolved-tool mapping."""
        self._tools_by_name = tools_by_name

    def resolve_tool(self, remote_tool: str) -> BaseTool:
        """Resolve one fake remote tool name."""
        if remote_tool not in self._tools_by_name:
            msg = f"remote tool not found: {remote_tool}"
            raise KeyError(msg)
        return self._tools_by_name[remote_tool]


def test_resolve_python_import_success() -> None:
    """Resolves a valid Python target into a LangChain tool."""
    # Arrange - use existing built-in tool target.
    definition = PythonToolDefinition(
        id="echo_tool",
        source="python",
        target="lily.agents.lily_supervisor:echo_tool",
    )
    resolvers = ToolResolvers()

    # Act - resolve configured Python tool target.
    resolved = resolvers.resolve(definition)

    # Assert - resolved tool preserves stable expected name.
    assert isinstance(resolved, BaseTool)
    assert resolved.name == "echo_tool"


def test_resolve_python_missing_symbol_fails() -> None:
    """Fails deterministically when Python target attribute is missing."""
    # Arrange - point to a module attribute that does not exist.
    definition = PythonToolDefinition(
        id="echo_tool",
        source="python",
        target="lily.agents.lily_supervisor:missing_attr",
    )
    resolvers = ToolResolvers()

    # Act - resolve missing symbol and capture error.
    with pytest.raises(ToolResolverError) as err:
        resolvers.resolve(definition)

    # Assert - error message names missing attribute/module context.
    assert "Unable to resolve attribute 'missing_attr'" in str(err.value)
    assert "tool id 'echo_tool'" in str(err.value)


def test_resolve_python_non_tool_target_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fails deterministically when Python target is not tool-compatible."""
    # Arrange - create temp module with non-callable, non-BaseTool attribute.
    module_file = tmp_path / "fake_tools_module.py"
    module_file.write_text("NOT_A_TOOL = 123\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    definition = PythonToolDefinition(
        id="not_a_tool",
        source="python",
        target="fake_tools_module:NOT_A_TOOL",
    )
    resolvers = ToolResolvers()

    # Act - attempt resolving non-tool target.
    with pytest.raises(ToolResolverError) as err:
        resolvers.resolve(definition)

    # Assert - error includes deterministic type information.
    assert "resolved to non-tool value" in str(err.value)
    assert "int" in str(err.value)


def test_resolve_mcp_unknown_remote_tool_fails() -> None:
    """Fails deterministically when MCP remote tool cannot be discovered."""

    # Arrange - configure server without the requested remote tool.
    @tool
    def ping_tool() -> str:
        """Return pong."""
        return "pong"

    definition = McpToolDefinition(
        id="ping_tool",
        source="mcp",
        server="local_tools",
        remote_tool="does_not_exist",
    )
    resolvers = ToolResolvers(
        mcp_servers={"local_tools": _FakeMcpServer({"ping_tool": ping_tool})}
    )

    # Act - resolve missing remote tool and capture deterministic failure.
    with pytest.raises(McpToolResolveError) as err:
        resolvers.resolve(definition)

    # Assert - error identifies server and missing remote tool.
    assert "Unable to resolve remote MCP tool 'does_not_exist'" in str(err.value)
    assert "server 'local_tools'" in str(err.value)


def test_resolve_mcp_with_built_provider_success() -> None:
    """Resolves MCP tool when server provider is built from runtime config."""
    # Arrange - build server provider map from runtime MCP config.
    mcp_servers = {
        "local_test": McpServerTestConfig.model_validate(
            {
                "transport": "test",
                "tool_targets": {
                    "ping_remote": "lily.agents.lily_supervisor:mcp_ping_tool"
                },
            }
        )
    }
    definition = McpToolDefinition(
        id="mcp_ping_tool",
        source="mcp",
        server="local_test",
        remote_tool="ping_remote",
    )
    resolvers = ToolResolvers(mcp_servers=build_mcp_server_providers(mcp_servers))

    # Act - resolve MCP tool through built provider map.
    resolved = resolvers.resolve(definition)

    # Assert - resolver returns expected named tool.
    assert isinstance(resolved, BaseTool)
    assert resolved.name == "mcp_ping_tool"


def test_resolve_mcp_streamable_http_provider_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolves MCP tool via streamable-http provider mapping."""

    # Arrange - build streamable-http server config and fake adapter tool response.
    @tool
    def search_langgraph_code(query: str) -> str:
        """Return deterministic fake search result."""
        return f"result:{query}"

    def _fake_run_async(coro: object) -> list[BaseTool]:
        close = getattr(coro, "close", None)
        if callable(close):
            close()
        return [search_langgraph_code]

    monkeypatch.setattr("lily.runtime.tool_resolvers._run_async", _fake_run_async)
    mcp_servers = {
        "langgraph_docs": McpServerStreamableHttpConfig.model_validate(
            {
                "transport": "streamable_http",
                "url": "https://gitmcp.io/langchain-ai/langgraph",
            }
        )
    }
    definition = McpToolDefinition(
        id="search_langgraph_code",
        source="mcp",
        server="langgraph_docs",
        remote_tool="search_langgraph_code",
    )
    resolvers = ToolResolvers(mcp_servers=build_mcp_server_providers(mcp_servers))

    # Act - resolve MCP tool from streamable-http server provider.
    resolved = resolvers.resolve(definition)

    # Assert - resolved tool maps to expected catalog id.
    assert isinstance(resolved, BaseTool)
    assert resolved.name == "search_langgraph_code"


def test_resolve_python_name_mismatch_fails() -> None:
    """Fails when resolved Python tool name does not match configured id."""
    # Arrange - resolve real ping_tool but configure mismatched id.
    definition = PythonToolDefinition(
        id="echo_tool",
        source="python",
        target="lily.agents.lily_supervisor:ping_tool",
    )
    resolvers = ToolResolvers()

    # Act - resolve mismatched name target.
    with pytest.raises(ToolResolverError) as err:
        resolvers.resolve(definition)

    # Assert - mismatch error remains deterministic.
    assert "Resolved Python tool name mismatch" in str(err.value)
    assert "got 'ping_tool'" in str(err.value)
